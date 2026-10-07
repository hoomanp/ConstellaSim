#!/usr/bin/env bash
# Build the React UI into Capacitor www/ and sync native projects.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d web/node_modules ]]; then
  (cd web && npm install)
fi
(cd web && npm run build)

# Capacitor webDir is mobile/www — ship the SPA there for native shells.
rm -rf mobile/www
mkdir -p mobile/www
cp -R web/dist/. mobile/www/

if [[ ! -d mobile/node_modules ]]; then
  (cd mobile && npm install)
fi
(cd mobile && npx cap sync)

echo "Mobile sync complete."
echo "  iOS:     cd mobile && npx cap open ios"
echo "  Android: cd mobile && npx cap open android"
echo "Remember: backend must be reachable (python -m api.main)."
