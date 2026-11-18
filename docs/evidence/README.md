# Evidence index

| Artifact | What it demonstrates | What it does not demonstrate |
|---|---|---|
| `tests.log` | Actual pytest output for the application suite | Live website/provider accuracy |
| `browser-check.json` | Chromium runs: all tabs, mobile layout, inert rendering of model-supplied HTML-like text | A real LLM response |
| `desktop-home.png`, `mobile-home.png` | Real screenshots of the public Render UI | A real LLM response |
| `illustrative-report.png`, `mobile-illustrative-report.png` | Real UI rendering of a **handcrafted fictional fixture**, labeled on screen | Live analysis or model benchmark |
| `offline-pipeline-response.json` | Full HTTP endpoint → extraction → model integration → schema/evidence validation path, with HTTPX-intercepted upstreams | Real upstream traffic |
| `deployment-check.json` | Actual public root/docs/schema/health responses and private-URL rejection | A completed LLM result |
| `live-trial-errors.json` | Actual timeout, rate-limit and quote-validation failures encountered during live verification | A successful analysis |
| `live-analysis.json` | Real uncached Basecamp analysis on the deployed service, with actual model/usage, source quotes and all five sections | A universal accuracy or latency benchmark |
| `live-report.png` | Actual UI rendering of the real Basecamp report | A second independent model evaluation |
| `local-unconfigured-response.json` | Real local Uvicorn request without credentials returns 503, not fabricated success | Successful LLM integration |

Reproduce Python verification with `pytest -q`. Reproduce the illustrative fixture with `python -m scripts.build_fixture`. UI checks: see `scripts/browser_check.cjs` and README. Use `scripts/smoke.py` to collect actual deployed/live evidence only after a real key and deployment are configured.
