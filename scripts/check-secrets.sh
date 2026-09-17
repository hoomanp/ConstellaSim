#!/usr/bin/env bash
# Fail if likely secrets are present in tracked files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PATTERN='(AIza[0-9A-Za-z_-]{20,}|sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|constellasim-demo-secret-change-me)'

if git ls-files -z | xargs -0 rg -n --hidden -e "$PATTERN" 2>/dev/null; then
  echo "ERROR: possible credential material found in tracked files." >&2
  exit 1
fi

# Ensure .env is not tracked
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env is tracked by git — remove it immediately." >&2
  exit 1
fi

echo "No credential patterns found in tracked files."
