import httpx
import pytest

from app.errors import AnalysisError
from app.services.website_extractor import WebsiteExtractor, observe_seo, parse_page


def test_html_extraction_removes_boilerplate_and_scripts(html):
    source, links = parse_page("https://northstar.example/", html, "S1", 22000)
    assert "Northstar Studio" in source.text
    assert "disclose the API key" not in source.text
    assert "Repeated navigation" not in source.text
    assert "Footer should" not in source.text
    assert source.h1 == ["Digital products with a clearer direction."]
    assert source.images_missing_alt == 1 and source.image_count == 2
    assert links == ["https://northstar.example/services"]
    assert len(source.content_hash) == 64


def test_truncation_and_deduplication(html):
    source, _ = parse_page("https://northstar.example/", html, "S1", 200)
    assert source.truncated and len(source.text) == 200


def test_seo_observations_are_measured(source):
    observations = observe_seo([source])
    assert len(observations) == 5
    assert (
        next(o for o in observations if o.check == "image_alt").observed
        == "1 of 2 images have no non-empty alt"
    )


@pytest.mark.parametrize(
    "status,code",
    [
        (403, "website_restricted"),
        (429, "website_restricted"),
        (404, "website_unavailable"),
        (500, "website_unavailable"),
    ],
)
@pytest.mark.asyncio
async def test_website_http_errors(settings, public_dns, status, code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="secret"))
    ) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).fetch("https://northstar.example/")
    assert exc.value.code == code and "secret" not in str(exc.value)


@pytest.mark.asyncio
async def test_non_html_rejected(settings, public_dns):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"pdf")
        )
    ) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).fetch("https://northstar.example/")
    assert exc.value.code == "unsupported_content"


@pytest.mark.asyncio
async def test_stream_size_limit(settings, public_dns):
    class LargeStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"x" * 600
            yield b"y" * 600

    settings = settings.model_copy(update={"max_html_bytes": 1000})
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, stream=LargeStream())
        )
    ) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).fetch("https://northstar.example/")
    assert exc.value.code == "page_too_large"


@pytest.mark.asyncio
async def test_timeout(settings, public_dns):
    def handler(request):
        raise httpx.ReadTimeout("secret request detail", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).fetch("https://northstar.example/")
    assert exc.value.code == "website_timeout" and "secret" not in str(exc.value)


@pytest.mark.asyncio
async def test_insufficient_content(settings, public_dns):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, text="<html><p>JavaScript required</p></html>", headers={"content-type": "text/html"}
            )
        )
    ) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).extract("https://northstar.example/")
    assert exc.value.code == "insufficient_content"


@pytest.mark.asyncio
async def test_secondary_failure_keeps_main_content(settings, public_dns, html):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls > 1:
            return httpx.Response(403)
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    settings = settings.model_copy(update={"max_pages": 3})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        sources, warnings = await WebsiteExtractor(settings, client).extract("https://northstar.example/")
    assert len(sources) == 1
    assert any("supporting page was unavailable" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_redirect_loop(settings, public_dns):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(302, headers={"location": "/"}))
    ) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).fetch("https://northstar.example/")
    assert exc.value.code == "redirect_loop"
