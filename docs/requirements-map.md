# Requirements → implementation → verification

Assignment source: [official Link Analysis specification](https://github.com/chivoxai/practical-test/blob/main/link-analysis.md), reviewed 18 November 2026.

| Requirement | Implementation | Verification |
|---|---|---|
| Python/FastAPI POST `/link-analysis` on port 4000 | `app/main.py`, `Dockerfile` | Full endpoint integration tests; live deployment smoke script |
| Valid public URL and graceful inaccessible-site errors | `services/url_guard.py`, `website_extractor.py` | Malformed/private/IPv6/encoded IP/DNS/redirect/error/timeout tests |
| Actual website content extraction | Bounded HTTPX HTML download, BeautifulSoup cleanup, up to three pages | Parser, source selection, truncation, metadata and script/boilerplate removal tests |
| Real LLM API integration | Fixed OpenRouter Chat Completions endpoint, free-only model guard and zero-price routing | Request contract/error/schema tests; real provider success must be established by a live smoke check |
| Five sections | `schemas.ModelOutput` and `Analysis` | Missing-section rejection and full pipeline response |
| Brand and competitors | Source-quoted brand/offerings; unverified competitor hypotheses with required labels | Quote matching and schema validation; no claim of independent competitor research |
| Five search queries across five platforms | Exactly five unique queries with enum platforms and all-platform validation | Platform coverage and invalid-field tests |
| SEO keywords/title/meta/support content | Typed recommendations plus deterministic HTML observations | Response schema and measured title/meta/H1/alt/canonical extraction tests |
| Top five services | 1–5 offerings with exact quotes for observed services and required inference reasons | Service evidence and inferred-label tests; fewer allowed to avoid fabrication |
| Audience details and geography | Structured audience fields; geography requires source evidence | Location without evidence rejected |
| Current model/cost research, three providers | README comparison of OpenRouter plus OpenAI, Google and Anthropic; official source links | Public catalog snapshot and documented arithmetic; performance estimates explicitly not benchmarks |
| Cost optimization | Text/page/output caps, deduplication, TTL/LRU caching, single-flight concurrency | Cache-hit, expiry, concurrent duplicate and capacity tests |
| SSRF protection | All DNS answers checked; numeric-IP connections with original Host/TLS SNI; redirects revalidated | Private/mixed-DNS/metadata/redirect/pinned-connection tests |
| Error management and credentials | Fixed error envelope, optional endpoint key, environment-only secrets, request IDs | Provider body redaction, auth and no-credentials tests; credential scan |
| Public source/README/examples/evidence | Public GitHub repository, docs, JSON responses, logs/screenshots | CI and remote repository verification |
| Public FastAPI demo and `/docs` | Render Free Web Service | Verify root, `/docs`, `/health` and a real POST; loading the fixture alone is insufficient |

The invitation and specification contain inconsistent dates (22 and 27 November). Plan to submit by **22 November 2026** unless the recruiter clarifies. This implementation does not follow social accounts or send email automatically; profile links and personal details belong in the user's final submission.
