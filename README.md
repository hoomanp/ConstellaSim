# 🌐 ConstellaSim: LEO Network Topology Simulator

**ConstellaSim** is an advanced discrete-event simulator (DES) developed to model packet-level networking and topology dynamics in Low Earth Orbit (LEO) satellite constellations.

Designed for scalability and realism, it handles the unique challenges of space-based networks: high relative velocities, constant topology changes, and the requirement for sub-ms latency optimization.

---

## 🚀 Key Simulation Features

### 📡 Network Layer & Routing
- **Dijkstra-Powered Routing:** Real-time pathfinding across satellite-to-satellite meshes using `NetworkX` for lowest-latency discovery.
- **ISL & GSL Modeling:** Simulation of both **Inter-Satellite Links (ISL)** and **Ground-to-Satellite Links (GSL)**.
- **Dynamic Topology:** Support for time-varying weights (latency) representing changing physical distances between satellites.

### 🚦 Congestion & Traffic Management
- **Buffer/Memory Constraints:** Each node has a defined `buffer_limit`. Experience real-world **Packet Drops** and tail-drop congestion during high traffic loads.
- **Propagation vs. Processing Delay:** Precise modeling of speed-of-light delay (km / 300,000 km/s) and random CPU processing overhead.
- **Handover Logic:** Automated connection management for Ground Stations as satellites transit in and out of the field of view.

### 📊 Analytics & Insights
- **Live Analytics Report:** Summary statistics including:
  - Total packets Sent / Received.
  - End-to-End Latency (ms).
  - Packet Loss Percentage (congestion analysis).
  - Hop Count tracking.

### 📱 Full-Stack Mobile & RAG Diagnostic
- **Flask Configuration API:** A mobile-optimized web app that uses your phone's GPS to set the **Source Node** of a simulation.
- **🤖 RAG-Enabled AI Network Analyst:** Intelligent simulation analysis using **Azure OpenAI**, **Amazon Bedrock (Claude 3)**, or **Google Gemini (1.5 Flash)**.
- **📚 Grounded Optimization:** Uses **Retrieval-Augmented Generation (RAG)** to "read" network performance standards from the `knowledge_base/` folder. It provides technical critiques and topology suggestions based on LEO networking benchmarks.

---

## ☁️ Multi-Cloud & RAG Support
This project includes an advanced AI diagnostic layer (`llm.py`) for multi-cloud RAG analysis:
- **Grounded Results:** The analyst scans `knowledge_base/*.txt` to ensure simulation reports meet industry-standard LEO benchmarks.
- **Cloud-Agnostic Engine:** Dynamically switch between **Amazon Bedrock**, **Azure**, or **Google** via the `NETWORK_AI_PROVIDER` environment variable.

---

## 🛠️ Tech Stack
- **Simulation Engine:** SimPy (Discrete-Event)
- **Graph Theory:** NetworkX (Topology management)
- **Geospatial Processing:** Geopy
- **API/UI:** Flask (Web UI + REST endpoints)

---

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/hoomanp/ConstellaSim.git
   cd ConstellaSim
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Multi-Hop Demo:**
   ```bash
   python3 -m examples.multi_hop_demo
   ```

4. **Run the Advanced Mesh Network Demo:**
   ```bash
   python3 -m examples.advanced_network
   ```

---

## 📱 Mobile Configuration Guide

1. **Configure environment (optional):**
   ```bash
   export NETWORK_AI_PROVIDER=google   # or: azure, amazon
   export GOOGLE_API_KEY=your_key
   # FLASK_DEBUG defaults to false; set to true only for local development
   export FLASK_DEBUG=false
   ```

2. **Start the Simulator Web App:**
   ```bash
   python3 mobile_client/app.py
   ```

3. **On your Mobile Phone:**
   Navigate to `http://<YOUR_LAPTOP_IP>:5001`.

4. **Simulate:** Tap "Run AI Diagnostic" to see how data travels from your current coordinates across a LEO mesh to a target city!

---

## 🏗️ Architecture Design

| Module | Responsibility |
|---|---|
| `engine.py` | Simulation orchestrator — event loop, packet lifecycle, Dijkstra routing, and analytics report generation. |
| `node.py` | Object-oriented definitions for `NetworkNode` (base), `Satellite` (with orbital plane), and `GroundStation` (with handover logic). |
| `utils.py` | Geocoding and location resolution via Geopy. |
| `llm.py` | RAG-enabled AI analyst; reads `knowledge_base/` and queries Azure / Bedrock / Gemini to critique simulation reports. |
| `mobile_client/app.py` | Flask REST API + mobile-optimized web UI for GPS-based simulation setup. |

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NETWORK_AI_PROVIDER` | `google` | AI provider: `google`, `azure`, or `amazon` |
| `GOOGLE_API_KEY` | — | API key for Google Gemini |
| `AZURE_OPENAI_KEY` | — | API key for Azure OpenAI |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI endpoint URL |
| `AZURE_DEPLOYMENT_NAME` | `gpt-4-turbo` | Azure deployment name |
| `FLASK_DEBUG` | `false` | Set to `true` only for local development |

---

## 📋 Changelog

### Latest
- **Fix:** `node.py` — `random` module was used in `GroundStation.handover()` but never imported; handover now works correctly.
- **Fix:** `multi_hop_demo.py` — `send_packet()` was called with a path list instead of `(source_id, dest_id, packet_id)`, and no inter-node links were defined, so all packets were silently dropped. Both issues are resolved; the demo now produces valid latency results.
- **Fix:** `advanced_network.py` — traffic generator hardcoded `"GS-LONDON"` / `"GS-NYC"` node IDs regardless of user input. It now uses `gs_src.node_id` / `gs_dest.node_id` so any city pair works correctly.
- **Security:** Flask `debug=True` replaced with `FLASK_DEBUG` environment variable (defaults to `false`).
- **Security:** Added full input validation, coordinate range checks, and destination city length/type checks on the `/api/simulate` endpoint.
- **Optimization:** `kb_path` in `llm.py` is now resolved with `os.path.abspath()`.

---

## 📄 License
MIT License.

## 🤝 Contact
**Hooman P.** - [GitHub](https://github.com/hoomanp)
