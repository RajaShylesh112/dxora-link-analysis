# Implementation walkthrough for the final discussion

Be ready to demonstrate and explain these choices in your own words.

1. **Trace one request:** FastAPI validates the URL → public DNS/IP checks → bounded HTML fetch and extraction → one OpenRouter request → Pydantic validation → exact-quote validation → five sections and sources.
2. **Why fetch before the LLM?** Ground the response in actual content instead of asking a model to guess from a domain name. The LLM is not a web browser in this implementation.
3. **Why pin the resolved IP?** Checking DNS and later letting an HTTP library resolve the host again leaves a DNS rebinding gap. The actual connection here uses the vetted IP; original Host and TLS SNI preserve HTTPS identity.
4. **Why check all DNS answers and every redirect?** A hostname can mix public and private addresses, or a public page can redirect to internal infrastructure.
5. **What is known versus inferred?** Source text and HTML counts are observed. Keywords, queries and marketing segments are recommendations. Competitors are explicitly unverified suggestions. A literal quote match checks provenance but does not prove the model's whole interpretation.
6. **Why fewer than five services sometimes?** The specification prioritizes actual website content. Filling five slots with fabricated offerings would reduce quality. Inferred service recommendations must be explicitly labeled and justified.
7. **What happens on provider failure?** A fixed, safe error response; no generic fabricated report. An optional second free model may be configured, with no paid fallback.
8. **Why OpenRouter free?** The user requested a zero-budget implementation. The router supplies feature-compatible free candidates, but random selection/rate limits reduce predictability. Record the actual model and evaluate pinned candidates before a production decision.
9. **What does caching do?** Fully validated successes only, bounded TTL/LRU and shared in-flight work for the same URL. It reduces repeated token use, but can return old information until TTL expiry. Original usage remains attached to cached reports.
10. **What would change at larger scale?** Durable queue, shared cache/rate limits, explicit user accounts, provider budgets, independently sourced competitor research, systematic model evaluation, observability and trusted-egress infrastructure. These are future work, not features claimed here.

Demo sequence: open the deployed homepage → submit a real business URL → inspect each of the five sections → show a service quote and matching source → open `/docs` → send an unsafe/private URL to show rejection → repeat a successful URL to show a cache hit. Do not present the illustrative fixture as live generation.
