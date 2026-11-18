import asyncio
import socket
from unittest.mock import AsyncMock

import httpx
import pytest

from app.errors import AnalysisError
from app.schemas import LinkRequest
from app.services.url_guard import UnsafeURL, normalize_url, require_public, resolve_public
from app.services.website_extractor import WebsiteExtractor


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com",
        "ftp://example.com",
        "file:///etc/passwd",
        "http://localhost",
        "http://a.local",
        "http://localhost.",
        "http://internal",
        "http://127.0.0.1",
        "http://127.1",
        "http://0.0.0.0",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]",
        "http://[fc00::1]",
        "http://[::ffff:127.0.0.1]",
        "https://user:secret@example.com",
        "https://example.com:8443",
        "https://example.com/path\nInjected",
        "https://example.com\\@127.0.0.1",
        "http://[fe80::1%25eth0]",
        "http://224.0.0.1",
        "https://-invalid.example/",
        "https://bad..example/",
    ],
)
def test_block_invalid_and_internal_urls(url):
    with pytest.raises(ValueError):
        LinkRequest(url=url)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://EXAMPLE.com", "https://example.com/"),
        ("https://example.com/path?q=1#fragment", "https://example.com/path?q=1"),
        ("http://example.com:80", "http://example.com/"),
        ("https://bücher.de", "https://xn--bcher-kva.de/"),
        ("https://8.8.8.8", "https://8.8.8.8/"),
    ],
)
def test_normalization(url, expected):
    assert normalize_url(url) == expected


@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "::1", "169.254.169.254", "::ffff:192.168.0.1", "2002:7f00:0001::", "ff02::1", "192.0.2.1"],
)
def test_non_public_addresses(ip):
    with pytest.raises(UnsafeURL):
        require_public(ip)


@pytest.mark.asyncio
async def test_dns_mixed_public_private_is_rejected(monkeypatch):
    resolver = AsyncMock(
        return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443)),
        ]
    )
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolver)
    with pytest.raises(AnalysisError, match="private"):
        await resolve_public("https://public-looking.example/")


@pytest.mark.asyncio
async def test_dns_failure_is_graceful(monkeypatch):
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", AsyncMock(side_effect=socket.gaierror()))
    with pytest.raises(AnalysisError) as exc:
        await resolve_public("https://not-found.example/")
    assert exc.value.code == "dns_failed"


@pytest.mark.asyncio
async def test_numeric_connection_is_pinned_with_original_host_and_sni(settings, html, public_dns):
    def handler(request):
        assert request.url.host == "93.184.215.14"
        assert request.headers["host"] == "northstar.example"
        assert request.extensions["sni_hostname"] == "northstar.example"
        assert "cookie" not in request.headers
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), cookies={"private": "never-forward"}
    ) as client:
        extractor = WebsiteExtractor(settings, client)
        final, _ = await extractor.fetch("https://northstar.example/")
    assert final == "https://northstar.example/"
    public_dns.assert_awaited_once()


@pytest.mark.asyncio
async def test_private_redirect_never_fetched(settings, public_dns):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).fetch("https://northstar.example/")
    assert exc.value.code == "unsafe_url"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_redirect_domain_resolving_private_is_rejected(settings, public_dns):
    public_dns.side_effect = [["93.184.215.14"], AnalysisError("unsafe_url", "Blocked DNS", 422)]
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"location": "https://sneaky.example/"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AnalysisError) as exc:
            await WebsiteExtractor(settings, client).fetch("https://northstar.example/")
    assert exc.value.code == "unsafe_url"
    assert len(requests) == 1
