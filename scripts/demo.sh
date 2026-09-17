#!/usr/bin/env bash
# One-command recruiter demo boot.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

if [[ ! -d web/node_modules ]]; then
  (cd web && npm install)
fi
(cd web && npm run build)

export PORT="${PORT:-5001}"
# Prefer caller-provided secret; otherwise generate an ephemeral one (not committed).
if [[ -z "${CONSTELLASIM_SECRET_KEY:-}" && -z "${FLASK_SECRET_KEY:-}" ]]; then
  export CONSTELLASIM_SECRET_KEY
  CONSTELLASIM_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi

# Optional local overrides (never commit .env)
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

echo "ConstellaSim demo → http://127.0.0.1:${PORT}"
exec python -m api.main
