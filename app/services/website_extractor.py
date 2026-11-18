import asyncio
import hashlib
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from app.config import Settings
from app.errors import AnalysisError
from app.schemas import SEOObservation, Source
from app.services.url_guard import UnsafeURL, normalize_url, resolve_public

REDIRECTS = {301, 302, 303, 307, 308}


class WebsiteExtractor:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client

    async def fetch(self, url: str) -> tuple[str, str]:
        current = normalize_url(url)
        seen = set()
        for _ in range(5):
            if current in seen:
                raise AnalysisError("redirect_loop", "Website redirects in a loop", 422)
            seen.add(current)
            addresses = await resolve_public(current)
            origin = httpx.URL(current)
            # Pin DNS at the network request, including through a configured HTTPS proxy.
            # Host + TLS SNI preserve origin virtual hosting and certificate validation.
            pinned = origin.copy_with(host=addresses[0])
            request = self.client.build_request(
                "GET",
                pinned,
                headers={
                    "Host": origin.netloc.decode("ascii"),
                    "User-Agent": "LinkLens/1.0 (+website-analysis; contact site owner for access)",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Encoding": "identity",
                },
                extensions={"sni_hostname": origin.host},
                timeout=self.settings.fetch_timeout_seconds,
            )
            request.headers.pop("cookie", None)
            try:
                response = await self.client.send(request, stream=True, follow_redirects=False)
                try:
                    if response.status_code in REDIRECTS:
                        target = response.headers.get("location")
                        if not target:
                            raise AnalysisError(
                                "invalid_redirect", "Website returned an invalid redirect", 422
                            )
                        try:
                            current = normalize_url(urljoin(current, target))
                        except UnsafeURL:
                            raise AnalysisError(
                                "unsafe_url", "Website redirects to a prohibited destination", 422
                            ) from None
                        continue
                    if response.status_code in (401, 403, 429):
                        raise AnalysisError(
                            "website_restricted",
                            "Website restricts automated access; try a public accessible page",
                            422,
                        )
                    if response.status_code >= 400:
                        raise AnalysisError("website_unavailable", "Website returned an HTTP error", 422)
                    if response.status_code < 200 or response.status_code >= 300:
                        raise AnalysisError(
                            "website_unavailable", "Website did not return a successful page", 422
                        )
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if content_type not in {"text/html", "application/xhtml+xml"}:
                        raise AnalysisError("unsupported_content", "Website must return HTML content", 422)
                    length = response.headers.get("content-length")
                    if length and length.isdecimal() and int(length) > self.settings.max_html_bytes:
                        raise AnalysisError("page_too_large", "Website HTML exceeds the download limit", 422)
                    chunks = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > self.settings.max_html_bytes:
                            raise AnalysisError(
                                "page_too_large", "Website HTML exceeds the download limit", 422
                            )
                        chunks.append(chunk)
                    return current, b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                finally:
                    await response.aclose()
            except httpx.TimeoutException:
                raise AnalysisError("website_timeout", "Website request timed out", 504) from None
            except httpx.RequestError:
                raise AnalysisError(
                    "website_unreachable", "Website could not be reached securely", 422
                ) from None
        raise AnalysisError("too_many_redirects", "Website has too many redirects", 422)

    async def extract(self, url: str) -> tuple[list[Source], list[str]]:
        try:
            async with asyncio.timeout(self.settings.fetch_timeout_seconds * 2 + 5):
                final_url, html = await self.fetch(url)
        except TimeoutError:
            raise AnalysisError("website_timeout", "Website request timed out", 504) from None
        first, links = parse_page(final_url, html, "S1", self.settings.max_content_chars)
        if first.word_count < 30:
            raise AnalysisError(
                "insufficient_content",
                "Too little readable website content; JavaScript-only sites may require a different page",
                422,
            )
        sources = [first]
        warnings = []
        budget = self.settings.max_content_chars - len(first.text)
        for link in links[: self.settings.max_pages - 1]:
            if budget < 500:
                break
            try:
                async with asyncio.timeout(self.settings.fetch_timeout_seconds + 5):
                    final, page_html = await self.fetch(link)
                if urlsplit(final).netloc != urlsplit(final_url).netloc:
                    warnings.append("A supporting page redirected off-site and was excluded")
                    continue
                source, _ = parse_page(final, page_html, f"S{len(sources) + 1}", budget)
                if source.word_count >= 20 and source.content_hash not in {s.content_hash for s in sources}:
                    sources.append(source)
                    budget -= len(source.text)
            except (AnalysisError, TimeoutError):
                warnings.append(
                    "A supporting page was unavailable and excluded; analysis uses remaining sources"
                )
        if any(source.truncated for source in sources):
            warnings.append("Website text was truncated to the configured content budget")
        warnings.append(
            "Server-rendered HTML only; JavaScript content and the full website may not be represented"
        )
        return sources, list(dict.fromkeys(warnings))


def clean_text(value: str) -> str:
    return " ".join(value.split())


def parse_page(url: str, html: str, source_id: str, budget: int) -> tuple[Source, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    title = clean_text(soup.title.get_text(" ", strip=True))[:500] if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    description = clean_text(str(meta.get("content", "")))[:1000] if meta else ""
    canonical_tag = soup.find("link", rel="canonical")
    canonical = str(canonical_tag.get("href", ""))[:2048] if canonical_tag else None
    h1 = [clean_text(x.get_text(" ", strip=True))[:300] for x in soup.find_all("h1")][:10]
    h2 = [clean_text(x.get_text(" ", strip=True))[:300] for x in soup.find_all("h2")][:20]
    images = soup.find_all("img")
    missing_alt = sum(not str(image.get("alt", "")).strip() for image in images)
    links = []
    for anchor in soup.find_all("a", href=True):
        try:
            candidate = normalize_url(urljoin(url, str(anchor["href"])))
        except UnsafeURL:
            continue
        parts = urlsplit(candidate)
        if parts.netloc == urlsplit(url).netloc and not parts.query and candidate != url:
            label = (parts.path + " " + anchor.get_text(" ", strip=True)).lower()
            if any(term in label for term in ("service", "solution", "product", "about", "company")):
                if candidate not in links:
                    links.append(candidate)
    for element in soup(["script", "style", "noscript", "svg", "iframe", "form", "nav", "footer", "header"]):
        element.decompose()
    for element in soup.select('[hidden], [aria-hidden="true"]'):
        element.decompose()
    lines = list(
        dict.fromkeys(
            clean_text(line) for line in soup.get_text("\n", strip=True).splitlines() if clean_text(line)
        )
    )
    body = "\n".join(lines)
    text = (f"Title: {title}\nDescription: {description}\n" + body)[:budget]
    return Source(
        id=source_id,
        url=url,
        title=title,
        meta_description=description,
        h1=h1,
        h2=h2,
        text=text,
        canonical=canonical,
        image_count=len(images),
        images_missing_alt=missing_alt,
        word_count=len(body.split()),
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        truncated=len(f"Title: {title}\nDescription: {description}\n" + body) > budget,
    ), links


def observe_seo(sources: list[Source]) -> list[SEOObservation]:
    observations = []
    for source in sources:
        checks = [
            (
                "title",
                f"{len(source.title)} characters" if source.title else "Missing",
                "Use a distinct, descriptive title with the primary topic; length is a display heuristic, not a ranking rule",
            ),
            (
                "meta_description",
                f"{len(source.meta_description)} characters" if source.meta_description else "Missing",
                "Write a clear summary and value proposition; search engines may rewrite snippets",
            ),
            (
                "h1",
                f"{len(source.h1)} H1 headings",
                "Use a clear page topic and a meaningful heading hierarchy",
            ),
            (
                "image_alt",
                f"{source.images_missing_alt} of {source.image_count} images have no non-empty alt",
                "Review informative images for descriptive alt text; decorative images may correctly use empty alt",
            ),
            (
                "canonical",
                "Present (not fetched or verified)" if source.canonical else "Missing",
                "Review canonical URL choices if duplicate URL versions exist",
            ),
        ]
        observations.extend(
            SEOObservation(source_id=source.id, check=check, observed=observed, recommendation=recommendation)
            for check, observed, recommendation in checks
        )
    return observations
