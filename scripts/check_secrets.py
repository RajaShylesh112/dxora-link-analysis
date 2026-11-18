"""Scan Git-tracked/staged files for common credential formats and configured keys."""

import os
import re
import subprocess
from pathlib import Path

PATTERNS = [
    rb"gh[pousr]_[A-Za-z0-9]{20,}",
    rb"github_pat_[A-Za-z0-9_]{20,}",
    rb"sk-or-v1-[A-Za-z0-9]{30,}",
    rb"sk-proj-[A-Za-z0-9_-]{30,}",
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"AKIA[0-9A-Z]{16}",
]


def main():
    files = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    keys = [
        os.environ[name].encode()
        for name in ("OPENROUTER_API_KEY", "GH_TOKEN", "GITHUB_TOKEN", "ANALYSIS_API_KEY")
        if len(os.environ.get(name, "")) >= 16
    ]
    flagged = []
    for name in filter(None, files):
        data = Path(name).read_bytes()
        if (
            Path(name).name == ".env"
            or any(re.search(pattern, data) for pattern in PATTERNS)
            or any(key in data for key in keys)
        ):
            flagged.append(name)
    if flagged:
        print("Credential scan flagged files:", ", ".join(flagged))
        raise SystemExit(1)
    print(
        f"Credential scan passed for {len(list(filter(None, files)))} tracked files; no known patterns or configured keys found."
    )


if __name__ == "__main__":
    main()
