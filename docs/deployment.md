# Deploy on Render's Free plan

A normal **Web Service** works; a paid Blueprint plan, database and Docker are not required.

1. Sign in to Render and choose **New → Web Service**.
2. Connect the public repository `https://github.com/RajaShylesh112/dxora-link-analysis` and branch `main`.
3. Select **Python 3** as the language/runtime (if Render auto-detects Docker, change the runtime to Python for this path).
4. Build command: `pip install -r requirements.txt`.
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-proxy-headers`.
6. Select the **Free** instance type. Do not select Starter or another paid instance.
7. Add environment variables:
   - `OPENROUTER_API_KEY`: your own secret, entered in Render only.
   - `OPENROUTER_MODEL`: `inclusionai/ling-3.2-flash:free`.
   - `LLM_STRICT_SCHEMA`: `true`.
   - `LLM_DISABLE_REASONING`: `true`.
   - `LLM_TIMEOUT_SECONDS`: `100`.
   - `PYTHON_VERSION`: `3.12.14` (or rely on the repository's `.python-version`).
   - Optional `ANALYSIS_API_KEY` if you want a protected reviewer endpoint; send that key privately to reviewers, never in GitHub. Leave empty for a public rate-limited demo.
8. Set Health Check Path to `/health`. The process can be healthy while the LLM key is absent/invalid; verify `analysis_configured` and run the actual API check too.
9. Create the web service, wait for **Live**, then open its assigned `https://...onrender.com` URL.
10. Open `/docs` and POST a real accessible business URL such as `https://basecamp.com`. Confirm **all five sections**, real extracted content and an actual `metadata.model_used` are present.
11. Run `python -m scripts.smoke --base-url https://YOUR-SERVICE.onrender.com --website https://basecamp.com --out docs/evidence/live-analysis.json` and inspect the saved report. This script never substitutes a fixture.
12. Record the confirmed live URL in the submission email. Include root URL, `/link-analysis`, and `/docs`.

Do not describe the site as fully verified just because `/health`, the frontend, or the illustrative report loads. The live LLM path must succeed too.

## Free-plan behavior

Render's documentation says Free web services sleep after 15 minutes without inbound traffic and can take about one minute to wake. A first browser request may show Render's loading page. Wait for the service, then submit analysis. Memory cache/rate counters reset on restart. The default single worker and no database fit this demo.

OpenRouter free capacity is independent of Render. A `503 llm_rate_limited` or `llm_unavailable` is possible even when Render is healthy. Check the account's free limits and the current model catalog. If needed, configure one explicit `:free` model with structured output support. Use `LLM_STRICT_SCHEMA=false` only for a model supporting JSON-object mode; the full local schema and quote checks still apply.

The service needs direct outbound access to public website IPs for DNS-pinned fetching and HTTPS access to `openrouter.ai` for analysis. Some websites block cloud hosting IPs. Try another public page; do not disable SSRF or TLS checks.

## Docker alternative

```bash
docker build -t linklens .
docker run --rm --env-file .env -p 4000:4000 linklens
```

`.dockerignore` excludes local secrets, Git history and virtual environments. The image runs as a non-root user. Render also supports the Docker runtime with the same environment variables and Free instance type; use its auto-detected Dockerfile and no custom start command.

Official documentation checked 18 November 2026: [Free services](https://render.com/docs/free), [FastAPI deployment](https://render.com/docs/deploy-fastapi).
