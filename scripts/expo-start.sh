#!/usr/bin/env bash
# Start Expo Go workflow (backend must already be running, or start it here).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/expo-app"

if [[ ! -d node_modules ]]; then
  npm install
fi

echo "Tip: keep ./scripts/demo.sh running in another terminal (port 5001)."
echo "Physical phone: enter http://\$(ipconfig getifaddr en0):5001 in the Expo connect screen."
exec npx expo start "$@"
