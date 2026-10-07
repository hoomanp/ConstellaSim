#!/usr/bin/env bash
# End-to-end API feature smoke test (all recruiter demo features).
set -euo pipefail
BASE="${1:-http://127.0.0.1:5001}"

echo "== health =="
curl -fsS "$BASE/api/health" | python3 -m json.tool >/tmp/cs-health.json
python3 - <<'PY'
import json
h=json.load(open("/tmp/cs-health.json"))
assert h["status"]=="ok", h
print("ai_mode=", h.get("ai_mode"), "monitor=", h.get("anomaly_monitor"))
PY

echo "== simulate stream =="
curl -fsS "$BASE/api/simulate/stream?src_lat=34.1675&src_lon=-118.5504&dest_city=Tokyo" >/tmp/cs-sse.txt
grep -q "event: simresult" /tmp/cs-sse.txt
grep -q "event: done" /tmp/cs-sse.txt

echo "== topology =="
curl -fsS "$BASE/api/topology" | python3 -m json.tool >/tmp/cs-topo.json
python3 - <<'PY'
import json
t=json.load(open("/tmp/cs-topo.json"))
assert t["nodes"] and t["route"], t
print("route=", " → ".join(t["route"]))
PY

echo "== plan =="
curl -fsS -X POST "$BASE/api/plan" -H 'Content-Type: application/json' \
  -d '{"query":"Simulate a packet to Berlin"}' | python3 -m json.tool >/tmp/cs-plan.json

echo "== chat =="
curl -fsS -X POST "$BASE/api/chat" -H 'Content-Type: application/json' \
  -d '{"message":"Summarize latency","session_id":"e2e"}' | python3 -m json.tool >/tmp/cs-chat.json

echo "== optimize =="
curl -fsS -X POST "$BASE/api/optimize" -H 'Content-Type: application/json' \
  -d '{"constraints":"minimize latency"}' | python3 -m json.tool >/tmp/cs-opt.json

echo "== alerts evaluate =="
curl -fsS -X POST "$BASE/api/alerts/evaluate" | python3 -m json.tool >/tmp/cs-alerts.json

echo "== briefing =="
curl -fsS "$BASE/api/briefing" | head -5

echo "ALL FEATURES OK against $BASE"
