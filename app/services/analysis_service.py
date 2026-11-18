import asyncio
import time
from collections import OrderedDict
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings
from app.errors import AnalysisError
from app.schemas import LinkResponse, Metadata
from app.services.llm_service import LLMService
from app.services.website_extractor import WebsiteExtractor, observe_seo


class AnalysisService:
    """Bounded in-memory LRU/TTL cache and single-flight requests per URL.

    One event loop owns the dictionaries; no await occurs during lookup/update.
    No failed or partially validated result enters the cache.
    """

    def __init__(self, settings: Settings, extractor: WebsiteExtractor, llm: LLMService):
        self.settings = settings
        self.extractor = extractor
        self.llm = llm
        self.cache: OrderedDict[str, tuple[float, LinkResponse]] = OrderedDict()
        self.inflight: dict[str, asyncio.Task] = {}

    async def analyze(self, url: str, request_id: str | None = None) -> LinkResponse:
        started = time.monotonic()
        request_id = request_id or uuid4().hex
        self.llm.ensure_configured()
        entry = self.cache.get(url)
        if entry and started - entry[0] < self.settings.cache_ttl_seconds:
            self.cache.move_to_end(url)
            response = entry[1].model_copy(deep=True)
            response.metadata.cached = True
            response.metadata.cache_age_seconds = int(started - entry[0])
            response.metadata.request_id = request_id
            response.metadata.elapsed_ms = int((time.monotonic() - started) * 1000)
            return response
        if entry:
            self.cache.pop(url, None)
        shared = url in self.inflight
        if not shared:
            if len(self.inflight) >= self.settings.max_concurrent_analyses:
                raise AnalysisError("server_busy", "Analysis capacity reached; retry shortly", 429)
            task = asyncio.create_task(self._generate(url))
            self.inflight[url] = task
            task.add_done_callback(lambda finished: self._finished(url, finished))
        response = (await asyncio.shield(self.inflight[url])).model_copy(deep=True)
        response.metadata.request_id = request_id
        response.metadata.elapsed_ms = int((time.monotonic() - started) * 1000)
        if shared:
            response.metadata.warnings.append(
                "Shared an in-flight analysis for this URL; no additional model call"
            )
        return response

    def _finished(self, url: str, task: asyncio.Task):
        self.inflight.pop(url, None)
        if not task.cancelled():
            task.exception()  # Retrieve exceptions even if all HTTP callers disconnected.

    async def _generate(self, url: str) -> LinkResponse:
        try:
            async with asyncio.timeout(200):
                sources, warnings = await self.extractor.extract(url)
                llm_result = await self.llm.analyze(sources)
        except TimeoutError:
            raise AnalysisError("analysis_timeout", "Analysis exceeded its total time budget", 504) from None
        warnings.extend(
            [
                "Competitors are AI suggestions; strengths and gaps require independent research",
                "The model uses a bounded catalog of captured excerpts; recommendations should be reviewed in context",
                "Search queries, SEO changes and marketing segments are recommendations, not measured performance",
            ]
        )
        if len(llm_result.output.analysis.top_services) < 5:
            warnings.append("Fewer than five services are returned to avoid inventing unsupported offerings")
        response = LinkResponse(
            website=url,
            brand=llm_result.output.brand,
            analysis=llm_result.output.analysis,
            sources=sources,
            seo_observations=observe_seo(sources),
            metadata=Metadata(
                request_id="pending",
                generated_at=datetime.now(timezone.utc).isoformat(),
                elapsed_ms=0,
                provider="OpenRouter",
                model_requested=self.settings.openrouter_model,
                model_used=llm_result.model,
                cached=False,
                cache_age_seconds=0,
                usage=llm_result.usage,
                warnings=warnings,
                competitor_research="ai_suggestions_not_independently_verified",
            ),
        )
        if self.settings.cache_ttl_seconds:
            self.cache[url] = (time.monotonic(), response.model_copy(deep=True))
            self.cache.move_to_end(url)
            while len(self.cache) > self.settings.cache_max_entries:
                self.cache.popitem(last=False)
        return response

    async def close(self):
        tasks = list(self.inflight.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
