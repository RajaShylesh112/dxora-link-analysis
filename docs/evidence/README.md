# Evidence index

| Artifact | What it demonstrates | What it does not demonstrate |
|---|---|---|
| `tests.log` | Actual pytest output for the application suite | Live website/provider accuracy |
| `browser-check.json` | Chromium runs: all tabs, mobile layout, inert rendering of model-supplied HTML-like text | A real LLM response |
| `desktop-home.png`, `mobile-home.png` | Real screenshots of the running local UI | Deployment |
| `illustrative-report.png`, `mobile-illustrative-report.png` | Real UI rendering of a **handcrafted fictional fixture**, labeled on screen | Live analysis or model benchmark |
| `offline-pipeline-response.json` | Full HTTP endpoint → extraction → model integration → schema/evidence validation path, with HTTPX-intercepted upstreams | Real upstream traffic |
| `local-unconfigured-response.json` | Real local Uvicorn request without credentials returns 503, not fabricated success | Successful LLM integration |

Reproduce Python verification with `pytest -q`. Reproduce the illustrative fixture with `python -m scripts.build_fixture`. UI checks: see `scripts/browser_check.cjs` and README. Use `scripts/smoke.py` to collect actual deployed/live evidence only after a real key and deployment are configured.
