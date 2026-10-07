# ConstellaSim: LEO Satellite Network Topology & Discrete-Event Simulator

> **Enterprise-grade discrete-event simulator (DES) for packet-level routing, dynamic Inter-Satellite Link (ISL) mesh topologies, and multi-cloud RAG network telemetry analysis in Low Earth Orbit (LEO) mega-constellations** — with a hiring-ready FastAPI + React + Expo Go demo path.

[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Simulation: SimPy + NetworkX](https://img.shields.io/badge/Simulation-SimPy%20%2B%20NetworkX-orange.svg)](https://simpy.readthedocs.io/)
[![API: FastAPI + SSE](https://img.shields.io/badge/API-FastAPI%20%2B%20SSE-009688.svg)](#quick-start-interview--demo-laptop)
[![AI: Multi-Cloud RAG](https://img.shields.io/badge/AI-Multi--Cloud%20RAG%20(Gemini%2FAzure%2FBedrock)-purple.svg)](#core-capabilities)
[![Domain: LEO Aerospace Networks](https://img.shields.io/badge/Domain-LEO%20Aerospace%20Networks-00bcd4.svg)](#orbital-dynamics--mathematical-formulations)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Boot it, tap **Demo mode**, show the route light up, and walk through SimPy → NetworkX → SSE → RAG.

---

## Executive Summary & Aerospace Systems Thesis

Low Earth Orbit (LEO) mega-constellations—such as **Amazon Project Kuiper**, **SpaceX Starlink**, and **Telesat Lightspeed**—operate in an intensely dynamic regime. Satellites traverse the sky at ~7.5 km/s, completing an orbit every 90–100 minutes. As a consequence:

1. **Dynamic topography & churn** — Ground-to-Satellite Links (GSLs) persist for only 5–10 minutes before handover.
2. **Optical Inter-Satellite Link (OISL) routing** — Global packets hop across dynamic laser meshes where propagation delay changes continuously.
3. **Queue congestion & buffer sizing** — On-orbit hardware limits memory buffers; packet drops under bursty load are a critical mission risk.

**ConstellaSim** models packet-level routing, Dijkstra shortest-path discovery, buffer queue dynamics, and link handovers, coupled with an **SSE-streamed multi-cloud RAG AI analyst** accessible from desktop or mobile command interfaces.

---

## Orbital Dynamics & Mathematical Formulations

### 1. Dynamic Inter-Satellite Propagation Delay

Propagation delay between satellite nodes $S_A$ and $S_B$ at epoch $t$:

$$t_{\text{prop}}(t) = \frac{\|\mathbf{r}_{A}(t) - \mathbf{r}_{B}(t)\|}{c}$$

### 2. End-to-End Latency Formulation

For multi-hop path $\mathcal{P} = (e_1, e_2, \dots, e_k)$:

$$T_{\text{e2e}} = \sum_{e \in \mathcal{P}} \left[ t_{\text{prop}}(e) + t_{\text{trans}}(e) + t_{\text{queue}}(e) + t_{\text{proc}}(e) \right]$$

Where $t_{\text{trans}}(e) = L_{\text{packet}} / R_{\text{bandwidth}}(e)$, $t_{\text{queue}}$ is FIFO contention under SimPy, and $t_{\text{proc}} \in [0.1, 0.3]\text{ ms}$ models routing overhead.

### 3. Buffer Contention & Tail-Drop Model

$$P(\text{Drop}) = \begin{cases} 1 & \text{if } Q_{\text{current}}(v) \ge Q_{\text{capacity}}(v) \\ 0 & \text{otherwise} \end{cases}$$

### 4. Ecosystem Interoperability: ConstellaSim + PyOrbit-Link

ConstellaSim pairs with [**PyOrbit-Link**](https://github.com/hoomanp/PyOrbit-Link) as a space telecom suite:

- **PyOrbit-Link (Physics & RF)** — NORAD TLEs via SGP4, Doppler ($\pm 65\text{ kHz}$ at Ka-band), ITU-R P.618 rain fade / link availability.
- **ConstellaSim (Network & Routing)** — Ingests dynamic edge weights and contact windows; runs DES packet routing with Dijkstra path switching.

### 5. Discrete-Event Simulation Benchmarks

| Simulation Parameter | Metric Benchmark | Operational Guarantee |
| :--- | :--- | :--- |
| **Event Throughput** | **`> 85,000 events/sec`** | SimPy DES loop (hybrid Rust acceleration roadmap) |
| **Max Concurrent Satellite Nodes** | **`500+ Nodes in Mesh`** | NetworkX graph updates with $< 12\text{ ms}$ re-route convergence |
| **SSE Streaming Latency** | **`< 25 ms per token`** | Real-time Server-Sent Events to connected clients |
| **Memory Ceiling** | **`< 120 MB bounded`** | Ring-buffered telemetry capped at 10,000 samples |

---

## Why this stack (v2 demo)

| Layer | Choice | Why it impresses |
|---|---|---|
| Simulation core | SimPy + NetworkX | Real DES + Dijkstra routing, not a mock |
| API | **FastAPI** + Pydantic + SSE | Typed contracts, OpenAPI, streaming |
| UI | **React 19 + Vite + TypeScript** | Modern SPA with orbital motion UI |
| Mobile | Capacitor 7 + **Expo Go** | Same demo on iPhone & Android |
| AI | Gemini / Azure / Bedrock + **offline demo AI** | Works in interviews even without keys |

---

## Quick start (interview / demo laptop)

```bash
git clone https://github.com/hoomanp/ConstellaSim.git
cd ConstellaSim
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd web && npm install && npm run build && cd ..

# One-port demo (API + UI)
export PORT=5001
python -m api.main
```

Open **http://localhost:5001** — brand hero, then **Mission console**.

Optional live AI (otherwise demo AI kicks in automatically):

```bash
export GOOGLE_API_KEY=your-key   # or AZURE_* / AWS for Bedrock
export NETWORK_AI_PROVIDER=google
```

### Dev mode (hot reload UI)

```bash
# Terminal A
python -m api.main

# Terminal B
cd web && npm run dev   # http://localhost:5173 (proxies /api → :5001)
```

### Expo Go (Mac mini — recommended for quick phone demos)

```bash
# Terminal A
./scripts/demo.sh

# Terminal B
./scripts/expo-start.sh
# scan QR with Expo Go, enter http://<Mac-LAN-IP>:5001, tap Open
```

Details: [`expo-app/README.md`](expo-app/README.md).

### CLI verification scenarios (no cloud keys)

```bash
python3 -m examples.multi_hop_demo
python3 -m examples.advanced_network
```

---

## Architecture

```
ConstellaSim/
├── constellasim/          # Simulation + RAG engine
│   ├── engine.py          # ConstellationSimulator event loop & Dijkstra routing
│   ├── node.py            # Satellite and GroundStation models
│   ├── llm.py             # Multi-cloud RAG analyst
│   ├── planner.py         # NL2Function with allowlist
│   └── monitor.py         # Background anomaly thread
├── api/                   # FastAPI backend (v2)
│   ├── main.py            # Routes, SSE, SPA hosting
│   ├── simulation.py      # Topology run + city atlas
│   └── ai_fallback.py     # Offline demo analyst
├── web/                   # React 19 recruiter UI
├── expo-app/              # Expo Go WebView shell (Mac mini phone demos)
├── mobile/                # Capacitor iOS + Android shell
├── mobile_client/         # Legacy Flask UI (prefer api/)
├── knowledge_base/        # RAG grounding docs
├── examples/              # CLI demos
└── tests/                 # pytest (engine + API)
```

### API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Readiness + AI mode |
| POST | `/api/simulate` | Blocking sim + analysis |
| GET | `/api/simulate/stream` | SSE sim + token stream |
| POST | `/api/chat` | Multi-turn follow-ups |
| POST | `/api/plan` | NL → simulate / topology_info |
| GET | `/api/topology` | Graph + active route |
| POST | `/api/optimize` | Mesh recommendations |
| GET | `/api/alerts` | Anomaly feed |
| GET | `/api/briefing` | Markdown briefing download |

---

## Core Capabilities

### Hybrid Simulation Engine
- **SimPy + NetworkX** — Discrete-event loop with microsecond fidelity and Dijkstra mesh routing.
- **Dynamic topology / handover** — Ground stations reconnect as satellites transit the field of view.
- **Congestion & tail-drop** — Per-node `buffer_limit` models on-orbit memory constraints.

### Multi-Cloud AI / RAG Mission Analyst
1. **Streaming analysis** — `GET /api/simulate/stream` (SSE, token-by-token).
2. **Multi-turn chat** — `POST /api/chat` with per-session snapshots.
3. **NL2Function planner** — `POST /api/plan` with strict allowlists.
4. **Anomaly alerts** — `GET /api/alerts` (+ evaluate endpoint for demos).
5. **Standards briefing** — `GET /api/briefing` grounded in `knowledge_base/`.

Providers: **Google Gemini**, **Azure OpenAI**, **Amazon Bedrock**, plus offline **Demo AI** when keys are absent.

---

## Demo script (3 minutes)

1. Open the hero — call out **ConstellaSim** branding and orbital motion.
2. Click **Run demo diagnostic** (Tarzana → Tokyo).
3. Watch **Live packet route** animate; latency metrics populate.
4. Point at streaming AI critique (demo mode or live provider).
5. Ask NL planner: “Simulate a packet to Berlin”.
6. Open optimizer → health score + HIGH/MEDIUM actions.
7. Optional: Expo Go or Capacitor on a phone on the same Wi‑Fi.

---

## Security notes (demo vs shared deploy)

Local recruiter demos bind `0.0.0.0:5001` so phones on LAN can connect. For any shared host:

```bash
export REQUIRE_API_KEY=true
export CONSTELLASIM_API_KEY='long-random-secret'
export CORS_ALLOW_ALL=false
export HOST=127.0.0.1   # optional local-only bind
```

v2 mitigations: SPA path containment, security headers, rate limits (slowapi), optional API key, per-session simulation snapshots (`X-Session-Id`), tightened CORS (no `*` unless `CORS_ALLOW_ALL=true`), Android cleartext limited to debug/local domains, iOS ATS without global arbitrary loads.

### Environment

Copy `.env.example` → `.env` for local keys (`.env` is gitignored — never commit it):

```bash
cp .env.example .env
```

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `5001` | API listen port |
| `CONSTELLASIM_SECRET_KEY` / `FLASK_SECRET_KEY` | ephemeral if unset | Set for shared deploys |
| `NETWORK_AI_PROVIDER` | `google` | `google` / `azure` / `amazon` |
| `GOOGLE_API_KEY` | — | Live Gemini — store only in local `.env` |
| `DEMO_LAT` / `DEMO_LON` / `DEMO_LABEL` | Tarzana | Simulator fallback |
| `ANOMALY_MONITOR` | `true` | Background alerts |
| `CORS_ORIGINS` | localhost + Capacitor | Comma-separated |
| `REQUIRE_API_KEY` / `CONSTELLASIM_API_KEY` | off | Shared-host gate |

```bash
./scripts/check-secrets.sh   # fail if credential patterns appear in tracked files
pytest -q
```

---

## License

MIT · **Hooman Parta** — [GitHub](https://github.com/hoomanp)
