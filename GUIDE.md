# Developer Guide: ConstellaSim v2

## Stack map

- **`constellasim/`** — domain engine (SimPy DES, NetworkX routing, RAG AI, planner, monitor)
- **`api/`** — FastAPI surface used for demos and mobile
- **`web/`** — React 19 + Vite mission console UI
- **`mobile/`** — Capacitor wrapper for iOS/Android
- **`mobile_client/`** — legacy Flask UI (kept for older tests; prefer `api/`)

## Extending the simulator

1. **Dynamic routing weights** — update ISL edge weights from orbital geometry each tick.
2. **Handover process** — schedule `GroundStation.handover()` on a SimPy interval.
3. **Congestion scenarios** — lower `buffer_limit` and flood `send_packet` to demo drops.

## Offline demo AI

If provider keys are missing, `api/ai_fallback.py` (`DemoNetworkAI`) boots automatically so recruiter demos never hard-fail.

## Tests

```bash
pytest -q
```
