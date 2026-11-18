"""Check a real deployment. No mock path; returns nonzero unless analysis succeeds."""

import argparse
import json
import os
import time
from pathlib import Path

import httpx

from app.schemas import LinkResponse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:4000")
    parser.add_argument("--website", default="https://basecamp.com")
    parser.add_argument("--out", default="work/live-smoke.json")
    args = parser.parse_args()
    headers = {}
    if os.environ.get("ANALYSIS_API_KEY"):
        headers["X-API-Key"] = os.environ["ANALYSIS_API_KEY"]
    with httpx.Client(timeout=220, follow_redirects=False) as client:
        started = time.monotonic()
        response = client.post(
            args.base_url.rstrip("/") + "/link-analysis", json={"url": args.website}, headers=headers
        )
        data = response.json()
        if response.status_code != 200:
            print(json.dumps({"status": response.status_code, "error": data.get("error")}, indent=2))
            raise SystemExit(1)
        parsed = LinkResponse.model_validate(data)
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(parsed.model_dump_json(indent=2) + "\n")
        print(
            json.dumps(
                {
                    "status": response.status_code,
                    "website": parsed.website,
                    "brand": parsed.brand.name,
                    "sections": len(parsed.analysis.model_fields_set),
                    "model": parsed.metadata.model_used,
                    "cached": parsed.metadata.cached,
                    "elapsed_seconds_measured": round(time.monotonic() - started, 2),
                    "usage": parsed.metadata.usage.model_dump(),
                    "saved": str(path),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
