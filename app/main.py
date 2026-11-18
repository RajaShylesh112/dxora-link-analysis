import logging
import secrets
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.errors import AnalysisError
from app.schemas import ErrorDetail, ErrorResponse, LinkRequest, LinkResponse
from app.services.analysis_service import AnalysisService
from app.services.llm_service import LLMService
from app.services.website_extractor import WebsiteExtractor

logger = logging.getLogger("linklens")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
STATIC = Path(__file__).parent / "static"
key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class RateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.clients: OrderedDict[str, deque[float]] = OrderedDict()

    def check(self, key: str):
        now = time.monotonic()
        bucket = self.clients.setdefault(key, deque())
        self.clients.move_to_end(key)
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise AnalysisError("rate_limited", "Request limit reached; retry in one minute", 429)
        bucket.append(now)
        while len(self.clients) > 1024:
            self.clients.popitem(last=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings
    app.state.limiter = RateLimiter(settings.requests_per_minute)
    # Website connections must target the DNS-vetted IP directly. HTTPX proxy
    # tunnels do not preserve an overridden SNI reliably; fail closed instead.
    # The fixed OpenRouter destination uses the inherited HTTPS proxy normally.
    async with (
        httpx.AsyncClient(trust_env=False, follow_redirects=False) as website_client,
        httpx.AsyncClient(follow_redirects=False) as llm_client,
    ):
        service = AnalysisService(
            settings, WebsiteExtractor(settings, website_client), LLMService(settings, llm_client)
        )
        app.state.service = service
        yield
        await service.close()


app = FastAPI(
    title="LinkLens · Website Link Analysis",
    version="1.0.0",
    lifespan=lifespan,
    description="Analyze a public website using actual HTML and OpenRouter free models. "
    "All five output sections are validated. Competitors are labeled AI suggestions.",
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = uuid4().hex
    # Enforce a small streaming request body budget before JSON decoding.
    if request.method == "POST" and request.url.path == "/link-analysis":
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 8192:
                return error_response(
                    request, AnalysisError("request_too_large", "Request body exceeds 8 KB", 413)
                )
            chunks.append(chunk)
        request._body = b"".join(chunks)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    if request.url.path == "/":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
    return response


def error_response(request: Request, error: AnalysisError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", uuid4().hex)
    headers = {"X-Request-ID": request_id}
    if error.status == 429:
        headers["Retry-After"] = "60"
    return JSONResponse(
        status_code=error.status,
        headers=headers,
        content=ErrorResponse(
            error=ErrorDetail(code=error.code, message=error.message, request_id=request_id)
        ).model_dump(),
    )


@app.exception_handler(AnalysisError)
async def analysis_error(request: Request, exc: AnalysisError):
    logger.info("request_id=%s outcome=%s", request.state.request_id, exc.code)
    return error_response(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return error_response(
        request,
        AnalysisError(
            "invalid_request", "Provide exactly one valid public HTTP(S) website URL in the url field", 422
        ),
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error("request_id=%s outcome=unexpected_error", request.state.request_id)
    return error_response(
        request,
        AnalysisError("internal_error", "An unexpected error occurred; use the request ID for support", 500),
    )


async def authorize(request: Request, key: str | None = Security(key_header)):
    expected = request.app.state.settings.analysis_api_key.get_secret_value()
    if expected and (key is None or not secrets.compare_digest(expected.encode(), key.encode())):
        raise AnalysisError("unauthorized", "Invalid or missing X-API-Key", 401)
    # Trust only ASGI peer address; no arbitrary X-Forwarded-For header trust.
    request.app.state.limiter.check(request.client.host if request.client else "unknown")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health", tags=["Operations"])
async def health(request: Request):
    configured = bool(request.app.state.settings.openrouter_api_key.get_secret_value())
    return {
        "status": "ok",
        "analysis_configured": configured,
        "model": request.app.state.settings.openrouter_model,
    }


@app.post(
    "/link-analysis",
    response_model=LinkResponse,
    dependencies=[Depends(authorize)],
    responses={code: {"model": ErrorResponse} for code in (401, 413, 422, 429, 500, 502, 503, 504)},
    tags=["Analysis"],
)
async def link_analysis(body: LinkRequest, request: Request):
    """Fetch up to three public pages, generate and validate the five analysis sections.

    No placeholder analysis is served if the LLM is unavailable. API keys are server-side only.
    """
    response = await request.app.state.service.analyze(body.url, request.state.request_id)
    logger.info(
        "request_id=%s outcome=success cached=%s elapsed_ms=%s",
        request.state.request_id,
        response.metadata.cached,
        response.metadata.elapsed_ms,
    )
    return response
