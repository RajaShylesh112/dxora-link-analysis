# Evidence and model evaluation protocol

The automated suite checks application behavior with controlled network responses. It does not measure real model accuracy or real provider response speed. The illustrative report is handcrafted from a fictional website fixture.

## Controlled quality evaluation before selecting a production model

Use at least five public sites from different business types: an agency, SaaS product, retailer, professional service, and a sparse-content site. Save a time-stamped HTML snapshot for each, with permission where appropriate. Mark expected brand facts/services and exact evidence spans manually. Do not infer ground truth from another LLM.

Run each candidate model on **the same cleaned snapshot and prompt/schema**, at least three times, with cache disabled. Keep provider/model IDs, date, all attempts and errors. Model-router results are comparable only when the actual selected model is recorded.

Record:

| Metric | How to measure |
|---|---|
| Valid JSON/schema rate | Complete validated responses / all attempts, including provider and validation failures |
| Grounded fact precision | Supported brand/service facts / checked factual claims, reviewed by a person |
| Offering recall | Correctly listed observed offerings / annotated offerings in the snapshot |
| Quote validity | Quotations that literally match cited text / all quotations |
| Competitor honesty | Suggestions clearly labeled, no invented statistics, no unsupported negative factual claims |
| Query usefulness | Five distinct, relevant queries covering all required platforms; human reviewer rating |
| SEO relevance | Proposed changes relate to the site's observed offering/content; no ranking promises |
| Latency | Client-measured end-to-end time, separate provider latency if instrumented; report median/p95 only with enough samples |
| Cost | Actual input/output tokens and provider-reported cost where available; distinguish computed estimates |

## Live smoke check

```bash
python -m scripts.smoke --base-url https://YOUR-SERVICE.onrender.com \
  --website https://basecamp.com --out docs/evidence/live-analysis.json
```

Use a fresh URL or set `CACHE_TTL_SECONDS=0` to avoid measuring cache hits as model latency. A Render cold start should be recorded separately. The saved report contains sources, generated analysis, exact model ID, timestamps, usage and warnings. Review every section before committing it as live evidence. A single successful response proves that request worked, not universal model accuracy.

## Current evidence distinction

- Unit/integration tests: simulated website/LLM traffic, real Python processing and HTTP API.
- Browser screenshots/checks: actual Chromium rendering and interactions with a clearly labeled illustrative fixture.
- Unconfigured-local API response: actual running Uvicorn server returning a truthful configuration error.
- Live provider or deployed analysis: only claim after a successful real smoke check. Never rename simulated fixtures as live results.
