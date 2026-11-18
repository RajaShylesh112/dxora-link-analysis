"""Exercise the actual endpoint with intercepted upstream HTTP, not live websites/LLMs."""

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import RateLimiter, app
from app.schemas import ModelOutput
from app.services.analysis_service import AnalysisService
from app.services.llm_service import LLMService
from app.services.website_extractor import WebsiteExtractor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence"


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    settings = Settings(
        _env_file=None,
        openrouter_api_key="offline-test-key",
        max_pages=1,
        requests_per_minute=60,
        cache_ttl_seconds=60,
    )
    output = ModelOutput.model_validate_json((ROOT / "tests/fixtures/model-output.json").read_text())
    html = (ROOT / "tests/fixtures/agency.html").read_text()
    calls = []

    def handler(request):
        calls.append(request.url.host)
        if request.url.host == "openrouter.ai":
            return httpx.Response(
                200,
                json={
                    "model": "simulated/model:free",
                    "choices": [{"finish_reason": "stop", "message": {"content": output.model_dump_json()}}],
                    "usage": {"prompt_tokens": 2100, "completion_tokens": 1600, "cost": 0},
                },
            )
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    OUT.mkdir(parents=True, exist_ok=True)
    print(
        "OFFLINE DEMO: fictional website fixture and simulated provider; no real posts, live website requests, model calls or charges.",
        flush=True,
    )
    with patch("app.services.website_extractor.resolve_public", AsyncMock(return_value=["93.184.215.14"])):
        with TestClient(app) as client:
            original = app.state.service
            mock = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            app.state.settings = settings
            app.state.limiter = RateLimiter(60)
            app.state.service = AnalysisService(
                settings, WebsiteExtractor(settings, mock), LLMService(settings, mock)
            )
            try:
                response = client.post("/link-analysis", json={"url": "https://northstar.example/"})
                assert response.status_code == 200, response.text
                data = response.json()
                data["metadata"]["warnings"].insert(
                    0, "OFFLINE TEST: all upstream HTTP responses simulated; not a live analysis"
                )
                (OUT / "offline-pipeline-response.json").write_text(json.dumps(data, indent=2) + "\n")
                print(
                    "POST /link-analysis -> 200; five validated sections; exact source quotes verified; simulated upstream calls:",
                    len(calls),
                )
                cached = client.post("/link-analysis", json={"url": "https://northstar.example/"}).json()
                assert cached["metadata"]["cached"] and len(calls) == 2
                print("Second POST -> 200 cached; zero additional upstream calls")
                unsafe = client.post(
                    "/link-analysis", json={"url": "http://169.254.169.254/latest/meta-data/"}
                )
                assert unsafe.status_code == 422 and len(calls) == 2
                (OUT / "unsafe-url-response.json").write_text(json.dumps(unsafe.json(), indent=2) + "\n")
                print("Private metadata URL -> 422; zero additional upstream calls")
            finally:
                client.portal.call(app.state.service.close)
                client.portal.call(mock.aclose)
                app.state.service = original


if __name__ == "__main__":
    main()
