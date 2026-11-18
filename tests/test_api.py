import asyncio
import json
import time
from contextlib import contextmanager

import httpx
import pytest
from fastapi.testclient import TestClient

from app.errors import AnalysisError
from app.main import RateLimiter, app
from app.services.analysis_service import AnalysisService
from app.services.llm_service import LLMService
from app.services.website_extractor import WebsiteExtractor
from tests.conftest import model_response

URL = "https://northstar.example/"


@contextmanager
def configured_client(settings, html, model_output, handler=None):
    calls = []

    def default_handler(request):
        calls.append(str(request.url))
        if request.url.host == "openrouter.ai":
            return model_response(model_output)
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    with TestClient(app) as client:
        original = app.state.service
        mock = httpx.AsyncClient(transport=httpx.MockTransport(handler or default_handler))
        app.state.settings = settings
        app.state.limiter = RateLimiter(settings.requests_per_minute)
        app.state.service = AnalysisService(
            settings, WebsiteExtractor(settings, mock), LLMService(settings, mock)
        )
        try:
            yield client, calls
        finally:
            client.portal.call(app.state.service.close)
            client.portal.call(mock.aclose)
            app.state.service = original


def test_complete_pipeline_and_cached_second_request(settings, html, model_output, public_dns):
    with configured_client(settings, html, model_output) as (client, calls):
        response = client.post("/link-analysis", json={"url": URL})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["success"] is True
        assert set(data["analysis"]) == {
            "competitor_analysis",
            "target_search_queries",
            "seo_improvements",
            "top_services",
            "target_audience",
        }
        assert data["brand"]["name"] == "Northstar Studio"
        assert len(data["analysis"]["competitor_analysis"]["competitors"]) == 3
        assert len(data["analysis"]["top_services"]) == 5
        assert not data["metadata"]["cached"]
        assert "disclose the API key" not in data["sources"][0]["text"]
        assert len(calls) == 2
        second = client.post("/link-analysis", json={"url": URL}).json()
        assert second["metadata"]["cached"]
        assert len(calls) == 2
        assert second["metadata"]["request_id"] != data["metadata"]["request_id"]
        assert response.headers["x-request-id"] == data["metadata"]["request_id"]


@pytest.mark.parametrize(
    "payload",
    [{}, {"url": "http://localhost/"}, {"url": URL, "prompt": "injected"}, {"url": 123}, {"url": None}],
)
def test_invalid_input_never_calls_network(settings, html, model_output, public_dns, payload):
    with configured_client(settings, html, model_output) as (client, calls):
        response = client.post("/link-analysis", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert calls == []


def test_malformed_json(settings, html, model_output):
    with configured_client(settings, html, model_output) as (client, calls):
        response = client.post(
            "/link-analysis", content="{broken", headers={"content-type": "application/json"}
        )
    assert response.status_code == 422 and calls == []


def test_request_body_limit(settings, html, model_output):
    with configured_client(settings, html, model_output) as (client, calls):
        response = client.post(
            "/link-analysis",
            content=json.dumps({"url": "x" * 9000}),
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 413 and calls == []


def test_no_credentials_never_returns_placeholder_success(settings, html, model_output, public_dns):
    settings = settings.model_copy(update={"openrouter_api_key": settings.openrouter_api_key.__class__("")})
    with configured_client(settings, html, model_output) as (client, calls):
        response = client.post("/link-analysis", json={"url": URL})
    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "llm_not_configured"
    assert calls == []


def test_optional_auth(settings, html, model_output, public_dns):
    settings = settings.model_copy(
        update={"analysis_api_key": settings.analysis_api_key.__class__("test-local")}
    )
    with configured_client(settings, html, model_output) as (client, calls):
        assert client.post("/link-analysis", json={"url": URL}).status_code == 401
        assert calls == []
        assert (
            client.post("/link-analysis", json={"url": URL}, headers={"X-API-Key": "test-local"}).status_code
            == 200
        )


def test_rate_limit_cannot_be_bypassed_by_forwarded_header(settings, html, model_output, public_dns):
    settings = settings.model_copy(update={"requests_per_minute": 1})
    with configured_client(settings, html, model_output) as (client, calls):
        assert client.post("/link-analysis", json={"url": URL}).status_code == 200
        response = client.post("/link-analysis", json={"url": URL}, headers={"X-Forwarded-For": "1.2.3.4"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


def test_health_docs_and_frontend(settings, html, model_output):
    with configured_client(settings, html, model_output) as (client, calls):
        assert client.get("/health").json()["analysis_configured"] is True
        assert client.get("/docs").status_code == 200
        page = client.get("/")
        assert page.status_code == 200
        assert "LinkLens" in page.text
        assert "default-src 'self'" in page.headers["content-security-policy"]
        assert (
            client.get("/static/sample-report.json").json()["metadata"]["model_used"]
            == "illustrative-handcrafted-fixture"
        )
        schema = client.get("/openapi.json").json()
        assert "/link-analysis" in schema["paths"]
        assert calls == []


def test_invalid_llm_output_is_error_not_generic_report(settings, html, model_output, public_dns):
    def handler(request):
        if request.url.host == "openrouter.ai":
            return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    with configured_client(settings, html, model_output, handler) as (client, calls):
        response = client.post("/link-analysis", json={"url": URL})
        assert not app.state.service.cache
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "invalid_model_output"


@pytest.mark.asyncio
async def test_single_flight_shares_one_model_call(settings, source, model_output):
    from unittest.mock import AsyncMock

    from app.schemas import Usage
    from app.services.llm_service import LLMResult

    extractor = AsyncMock()
    extractor.extract.return_value = ([source], [])
    llm = AsyncMock()
    llm.ensure_configured = lambda: None
    llm.analyze.return_value = LLMResult(
        model_output, "test/model:free", Usage(input_tokens=1, output_tokens=1, reported_cost_usd=0)
    )
    service = AnalysisService(settings, extractor, llm)
    first, second = await asyncio.gather(service.analyze(URL), service.analyze(URL))
    assert first.success and second.success
    llm.analyze.assert_awaited_once()
    assert any("in-flight" in warning for warning in second.metadata.warnings)
    await service.close()


@pytest.mark.asyncio
async def test_expired_cache_refreshes(settings, source, model_output):
    from unittest.mock import AsyncMock

    from app.schemas import Usage
    from app.services.llm_service import LLMResult

    extractor = AsyncMock()
    extractor.extract.return_value = ([source], [])
    llm = AsyncMock()
    llm.ensure_configured = lambda: None
    llm.analyze.return_value = LLMResult(
        model_output, "test/model:free", Usage(input_tokens=1, output_tokens=1, reported_cost_usd=0)
    )
    service = AnalysisService(settings, extractor, llm)
    await service.analyze(URL)
    _, response = service.cache[URL]
    service.cache[URL] = (time.monotonic() - 100, response)
    await service.analyze(URL)
    assert llm.analyze.await_count == 2
    await service.close()


@pytest.mark.asyncio
async def test_capacity_limit(settings):
    from unittest.mock import AsyncMock

    settings = settings.model_copy(update={"max_concurrent_analyses": 1})
    extractor = AsyncMock()
    llm = AsyncMock()
    llm.ensure_configured = lambda: None
    service = AnalysisService(settings, extractor, llm)
    blocker = asyncio.create_task(asyncio.Event().wait())
    service.inflight["https://busy.example/"] = blocker
    with pytest.raises(AnalysisError) as exc:
        await service.analyze(URL)
    assert exc.value.code == "server_busy"
    await service.close()
