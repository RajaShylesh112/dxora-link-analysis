import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.schemas import ModelOutput
from app.services.llm_service import evidence_catalog
from app.services.website_extractor import parse_page
from scripts.fixture_utils import reference_fixture

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        openrouter_api_key="test-not-a-real-key",
        openrouter_model="openrouter/free",
        max_pages=1,
        requests_per_minute=60,
        cache_ttl_seconds=60,
        llm_timeout_seconds=5,
    )


@pytest.fixture
def html():
    return (FIXTURES / "agency.html").read_text()


@pytest.fixture
def model_output():
    return ModelOutput.model_validate_json((FIXTURES / "model-output.json").read_text())


@pytest.fixture
def source(html):
    return parse_page("https://northstar.example/", html, "S1", 22000)[0]


@pytest.fixture
def public_dns(monkeypatch):
    resolver = AsyncMock(return_value=["93.184.215.14"])
    monkeypatch.setattr("app.services.website_extractor.resolve_public", resolver)
    return resolver


def model_response(output, **overrides):
    source = parse_page("https://northstar.example/", (FIXTURES / "agency.html").read_text(), "S1", 22000)[0]
    wire = reference_fixture(output, evidence_catalog([source]))
    data = {
        "model": "test/model:free",
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(wire)}}],
        "usage": {"prompt_tokens": 2100, "completion_tokens": 1600, "cost": 0},
    }
    data.update(overrides)
    return httpx.Response(200, json=data)
