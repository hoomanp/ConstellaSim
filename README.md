# ConstellaSim: LEO Network Topology Simulator

**ConstellaSim** is an advanced discrete-event simulator (DES) for modeling packet-level networking and topology dynamics in Low Earth Orbit (LEO) satellite constellations. It combines SimPy-based network simulation with a multi-cloud RAG AI analyst accessible from any mobile browser.

---

## What's Inside

| Module | Technology | Purpose |
|---|---|---|
| `constellasim/engine.py` | SimPy, NetworkX | Discrete-event simulation, Dijkstra routing |
| `constellasim/node.py` | SimPy | Satellite and GroundStation node models |
| `constellasim/llm.py` | Google/Azure/Bedrock | RAG-enabled AI network analyst |
| `constellasim/planner.py` | LLM + allowlist | NL2Function mission planner |
| `constellasim/monitor.py` | threading | Background anomaly detection |
| `constellasim/utils.py` | Geopy | GPS/city geocoding with LRU cache |
| `mobile_client/app.py` | Flask, SSE | REST + Server-Sent Events API (port 5001) |

---

## Key Features

### Network Simulation Engine
- **Dijkstra-Powered Routing:** Lowest-latency path discovery across satellite meshes using NetworkX.
- **ISL & GSL Modeling:** Inter-Satellite Links and Ground-to-Satellite Links with configurable edge weights.
- **Congestion Simulation:** Per-node `buffer_limit` triggers tail-drop packet loss under load.
- **Propagation + Processing Delay:** Speed-of-light delay modeled per km, plus random CPU overhead.
- **Handover Logic:** Ground stations automatically reconnect as satellites transit the field of view.
- **Analytics Report:** Sent / Received / Dropped counts, average end-to-end latency, packet loss rate.

### AI / RAG Network Analyst (5 Features)
1. **Streaming Analysis** — `GET /api/simulate/stream` SSE endpoint: simulation result + AI commentary streamed token-by-token.
2. **Multi-Turn Chat** — `POST /api/chat` contextual follow-up about the current simulation snapshot (up to 10 turns, server-side session).
3. **NL2Function Planner** — `POST /api/plan` parses plain English into `simulate` or `topology_info` function calls via AI with strict allowlist validation.
4. **Anomaly Monitor** — Optional background thread (`ANOMALY_MONITOR=true`) polls simulation state and generates WARNING/CRITICAL alerts accessible at `GET /api/alerts`.
5. **Network Briefing** — `GET /api/briefing` downloads a structured Markdown report grounded in `knowledge_base/` LEO networking standards.

Providers: **Google Gemini 1.5 Flash**, **Azure OpenAI (GPT-4 Turbo)**, **Amazon Bedrock (Claude 3)**.

### Mobile Web UI
- GPS-based source node — phone's location sets the origin ground station automatically.
- NL Planner widget: "Simulate packet from Paris to Tokyo" → executes a full simulation.
- Streaming AI analysis with blinking cursor animation.
- Alert badge with polling every 10 seconds.
- Briefing download button (Markdown report).
- Multi-turn chat widget with New Chat / Reset.

---

## Architecture

```
ConstellaSim/
├── constellasim/
│   ├── engine.py           # ConstellationSimulator: event loop, routing, stats
│   ├── node.py             # NetworkNode, Satellite, GroundStation
│   ├── utils.py            # Geocoder (LRU cache, allowlist validation)
│   ├── llm.py              # NetworkAI: RAG analysis, streaming, chat, briefing
│   ├── planner.py          # NetworkPlanner: NL2Function with allowlist
│   └── monitor.py          # AnomalyMonitor: background thread, alert feed
├── mobile_client/
│   └── app.py              # Flask REST + SSE + security headers
├── knowledge_base/
│   └── network_standards.txt  # LEO networking benchmarks for RAG grounding
└── examples/
    ├── multi_hop_demo.py   # 3-satellite linear chain demo
    └── advanced_network.py # Multi-city mesh network demo
```

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/simulate` | Blocking simulation: src lat/lon → dest city |
| `GET` | `/api/simulate/stream` | SSE: simulation result + streaming AI analysis |
| `POST` | `/api/chat` | Multi-turn AI conversation about current simulation |
| `POST` | `/api/chat/reset` | Clear session chat history |
| `POST` | `/api/plan` | NL2Function: plain English → `simulate` or `topology_info` |
| `GET` | `/api/alerts` | Anomaly alert feed (JSON array) |
| `GET` | `/api/briefing` | Download Markdown network briefing |

---

## Installation

```bash
git clone https://github.com/hoomanp/ConstellaSim.git
cd ConstellaSim
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Run the Examples

```bash
# 3-satellite linear chain (no API key needed)
python3 -m examples.multi_hop_demo

# Multi-city mesh network
python3 -m examples.advanced_network
```

### Start the Mobile Web App

```bash
export FLASK_SECRET_KEY=your-secret-key   # required
export GOOGLE_API_KEY=your-key             # or AZURE_OPENAI_KEY / AWS creds
export PORT=5001
python3 mobile_client/app.py
```

Open `http://localhost:5001` in any browser, or `http://<YOUR_LAN_IP>:5001` on a phone connected to the same network.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | — | **Required.** Cryptographic session key |
| `PORT` | `5001` | Flask server port |
| `NETWORK_AI_PROVIDER` | `google` | AI provider: `google`, `azure`, `amazon` |
| `GOOGLE_API_KEY` | — | Google Gemini 1.5 Flash API key |
| `AZURE_OPENAI_KEY` | — | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_DEPLOYMENT_NAME` | `gpt-4-turbo` | Azure deployment name |
| `ANOMALY_MONITOR` | `false` | Enable background anomaly monitoring thread |
| `NOMINATIM_USER_AGENT` | `ConstellaSim/1.0` | Nominatim geocoder user-agent string |
| `FLASK_DEBUG` | `false` | Development mode (never `true` in production) |

---

## Tech Stack

**Simulation:** Python 3.9+, SimPy (discrete-event), NetworkX (graph/routing), Geopy (geocoding)

**API/UI:** Flask, flask-limiter (rate limiting), Werkzeug ProxyFix

**AI:** Google Generative AI (Gemini 1.5 Flash), OpenAI SDK (Azure), Boto3 (Amazon Bedrock)

**Security:** CSP nonces, X-Frame-Options, HSTS, per-request nonce generation, input allowlists, path traversal guards, prompt injection sanitisation

---

## Simulation Model

The default topology is a **linear chain**: `GroundStation(src)` → `SAT1` → `SAT2` → `SAT3` → `GroundStation(dest)`.

Link weights (ms):
- Ground-to-satellite: 2.0 ms base
- Inter-satellite: 5.0 ms base
- Each hop adds random processing delay of 0.1–0.3 ms

Packet loss occurs when a destination node's queue exceeds `buffer_limit` (default 100 packets).

---

## Changelog

### v1.2 — 5 AI Features + Security Audit (2026-02)
- Feature 1: Streaming SSE AI analysis (`/api/simulate/stream`)
- Feature 2: Multi-turn chat with server-side session history (`/api/chat`, `/api/chat/reset`)
- Feature 3: NL2Function network planner with AI allowlist validation (`/api/plan`)
- Feature 4: Background anomaly monitor thread with alert feed (`/api/alerts`)
- Feature 5: AI-generated Markdown network briefing download (`/api/briefing`)
- Security: `FLASK_SECRET_KEY` required at startup
- Security: CSP nonce headers, X-Frame-Options DENY, HSTS on all responses
- Security: Rate limiting via flask-limiter (30/min default, 5/min on briefing)
- Security: Input allowlist on geocoder queries, length caps on all string inputs
- Security: Prompt injection sanitisation in `_sanitize()` (control chars, Unicode overrides)
- Security: Path traversal guard on `kb_path` and knowledge base file resolution
- Optimization: `Geocoder` LRU cache (max 1,000 entries), `NetworkAI` KB loaded once at startup
- Optimization: Simulation semaphore (max 4 concurrent) prevents CPU overload
- Fix: `latency` buffer capped at 10,000 samples to prevent unbounded memory growth
- Fix: `received_packets` log per node capped at 10,000 entries

### v1.1 — Core Fixes
- Fixed missing `random` import in `node.py` `GroundStation.handover()`
- Fixed `multi_hop_demo.py`: wrong `send_packet` signature and missing ISL links
- Fixed `advanced_network.py`: hardcoded node IDs replaced with `gs_src.node_id` / `gs_dest.node_id`
- Removed unused `numpy`, `matplotlib`, `pandas` from `requirements.txt`
- `FLASK_DEBUG` environment variable replacing hardcoded `debug=True`

---

## License
MIT License.

## Contact
**Hooman P.** — [GitHub](https://github.com/hoomanp)
