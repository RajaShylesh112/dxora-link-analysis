import json

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.errors import AnalysisError
from app.schemas import ModelOutput
from app.services.llm_service import LLMService, grounded_schema, validate_evidence
from tests.conftest import model_response


@pytest.mark.asyncio
async def test_request_uses_free_model_schema_and_separates_untrusted_content(settings, source, model_output):
    def handler(request):
        assert request.url == "https://openrouter.ai/api/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == "openrouter/free"
        assert payload["reasoning"] == {"enabled": False}
        assert payload["response_format"]["type"] == "json_schema"
        evidence_schema = payload["response_format"]["json_schema"]["schema"]["$defs"]["Evidence"]
        assert all(quote in source.text for quote in evidence_schema["properties"]["quote"]["enum"])
        assert evidence_schema["properties"]["source_id"]["enum"] == ["S1"]
        assert payload["provider"]["max_price"] == {"prompt": 0, "completion": 0}
        assert payload["provider"]["require_parameters"] is True
        assert "UNTRUSTED DATA" in payload["messages"][0]["content"]
        assert source.text in json.loads(payload["messages"][1]["content"])["sources"][0]["text"]
        return model_response(model_output)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await LLMService(settings, client).analyze([source])
    assert result.model == "test/model:free" and result.usage.reported_cost_usd == 0
    assert len(result.output.analysis.target_search_queries) == 5


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "llm_auth_failed"),
        (403, "llm_auth_failed"),
        (402, "llm_account_restricted"),
        (429, "llm_rate_limited"),
        (500, "llm_unavailable"),
        (400, "llm_request_rejected"),
    ],
)
@pytest.mark.asyncio
async def test_upstream_errors_are_safe(settings, source, status, code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="SECRET-API-KEY"))
    ) as client:
        with pytest.raises(AnalysisError) as exc:
            await LLMService(settings, client).analyze([source])
    assert exc.value.code == code and "SECRET" not in str(exc.value)


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"choices": []},
        {"choices": [[]]},
        {"choices": [None]},
        {"choices": [{"message": {"content": "not json"}}]},
        {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
        {"error": {"message": "secret"}},
    ],
)
@pytest.mark.asyncio
async def test_invalid_model_response_never_becomes_success(settings, source, data):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data))
    ) as client:
        with pytest.raises(AnalysisError) as exc:
            await LLMService(settings, client).analyze([source])
    assert exc.value.code == "invalid_model_output"


def test_fabricated_quote_is_rejected(source, model_output):
    output = model_output.model_copy(deep=True)
    output.brand.evidence[0].quote = "We have a million customers and the best product in the world."
    with pytest.raises(AnalysisError):
        validate_evidence(output, [source])


def test_unknown_source_is_rejected(source, model_output):
    output = model_output.model_copy(deep=True)
    output.brand.evidence[0].source_id = "S5"
    with pytest.raises(AnalysisError):
        validate_evidence(output, [source])


def test_grounded_schema_is_bounded_and_supports_multiple_sources(source):
    second = source.model_copy(
        update={"id": "S2", "text": "A different public business source with enough context."}
    )
    schema = grounded_schema([source, second])
    evidence = schema["$defs"]["Evidence"]["properties"]
    assert evidence["source_id"]["enum"] == ["S1", "S2"]
    quotes = evidence["quote"]["enum"]
    assert quotes and sum(map(len, quotes)) <= 14000
    assert all(quote in source.text or quote in second.text for quote in quotes)
    assert second.text in quotes


@pytest.mark.parametrize(
    "kind",
    [
        "missing_section",
        "invented_volume",
        "missing_platform",
        "missing_service_evidence",
        "unverified_location",
        "missing_inference_reason",
    ],
)
def test_semantic_contract(model_output, kind):
    data = model_output.model_dump()
    if kind == "missing_section":
        del data["analysis"]["seo_improvements"]
    elif kind == "invented_volume":
        data["analysis"]["target_search_queries"][0]["search_volume"] = 100000
    elif kind == "missing_platform":
        data["analysis"]["target_search_queries"][4]["platforms"] = ["Google"]
    elif kind == "missing_service_evidence":
        data["analysis"]["top_services"][0]["evidence"] = []
    elif kind == "unverified_location":
        data["analysis"]["target_audience"]["geographical_focus"] = "India"
    else:
        data["analysis"]["top_services"][0]["basis"] = "inferred_recommendation"
    with pytest.raises(ValidationError):
        ModelOutput.model_validate(data)


@pytest.mark.asyncio
async def test_free_fallback_once_on_rate_limit(settings, source, model_output):
    settings = settings.model_copy(update={"openrouter_fallback_model": "test/fallback:free"})
    calls = []

    def handler(request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(429) if len(calls) == 1 else model_response(model_output)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await LLMService(settings, client).analyze([source])
    assert calls == ["openrouter/free", "test/fallback:free"]


def test_paid_models_are_not_allowed():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, openrouter_model="provider/paid-model")
