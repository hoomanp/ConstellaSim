# ConstellaSim — Recruiter Demo (v2)

**ConstellaSim** is a hiring-ready LEO network lab: a discrete-event packet simulator, live topology visualizer, and streaming AI mission assistant — wrapped for web, iOS, and Android.

> Boot it, tap **Demo mode**, show the route light up, and walk a recruiter through SimPy → NetworkX → SSE → RAG.

---

## Why this stack

| Layer | Choice | Why it impresses |
|---|---|---|
| Simulation core | SimPy + NetworkX | Real DES + Dijkstra routing, not a mock |
| API | **FastAPI** + Pydantic + SSE | Typed contracts, OpenAPI, streaming |
| UI | **React 19 + Vite + TypeScript** | Modern SPA with orbital motion UI |
| Mobile | Capacitor 7 | Same demo on iPhone & Android |
| AI | Gemini / Azure / Bedrock + **offline demo AI** | Works in interviews even without keys |

---

## Quick start (interview laptop)

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

### Native mobile

```bash
cd mobile && npm install && npx cap sync
npx cap open ios      # or: npx cap open android
```

Launcher → enter LAN IP of the machine running `python -m api.main` → Connect.

---

## Architecture

```
ConstellaSim/
├── constellasim/          # Simulation + RAG engine (unchanged domain core)
├── api/                   # FastAPI backend (v2)
│   ├── main.py            # Routes, SSE, SPA hosting
│   ├── simulation.py      # Topology run + city atlas
│   └── ai_fallback.py     # Offline demo analyst
├── web/                   # React 19 recruiter UI
├── mobile/                # Capacitor iOS + Android shell
├── knowledge_base/        # RAG grounding docs
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

## Demo script (3 minutes)

1. Open the hero — call out **ConstellaSim** branding and orbital motion.
2. Click **Run demo diagnostic** (Tarzana → Tokyo).
3. Watch **Live packet route** animate; latency metrics populate.
4. Point at streaming AI critique (demo mode or live provider).
5. Ask NL planner: “Simulate a packet to Berlin”.
6. Open optimizer → health score + HIGH/MEDIUM actions.
7. Optional: launch Capacitor on a phone on the same Wi‑Fi.

---

## Environment

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `5001` | API listen port |
| `CONSTELLASIM_SECRET_KEY` / `FLASK_SECRET_KEY` | demo default | Set in shared deploys |
| `NETWORK_AI_PROVIDER` | `google` | `google` / `azure` / `amazon` |
| `GOOGLE_API_KEY` | — | Enables live Gemini |
| `DEMO_LAT` / `DEMO_LON` / `DEMO_LABEL` | Tarzana | Simulator fallback |
| `ANOMALY_MONITOR` | `false` | Background alerts |
| `CORS_ORIGINS` | localhost + Capacitor | Comma-separated |

---

## Tests

```bash
pytest -q
```

---

## License

MIT · **Hooman P.** — [GitHub](https://github.com/hoomanp)
