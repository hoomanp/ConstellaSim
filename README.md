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
- **Handover Logic:** Automated connection management for Ground Stations as satellites transit in and out of the "field of view."

### 📊 Analytics & Insights
- **Live Analytics Report:** Summary statistics including:
  - Total packets Sent/Received.
  - End-to-End Latency (ms).
  - Packet Loss Percentage (Congestion analysis).
  - Hop Count tracking.

### 📱 Full-Stack Mobile & AI Diagnostic
- **Flask Configuration API:** A mobile-optimized web app that uses your phone's GPS to set the **Source Node** of a simulation.
- **🤖 AI Network Topology Analyst:** Intelligent simulation analysis using **Azure OpenAI**, **Amazon Bedrock**, or **Google Gemini**. Automatically suggests ISL/GSL optimizations and routing improvements to reduce latency and congestion.

---

## ☁️ Multi-Cloud AI Support
This project includes a unified AI diagnostic layer (`llm.py`) for multi-cloud support:
- **Amazon Bedrock:** Optimized for cloud-native network simulations.
- **Azure OpenAI:** Enterprise-grade AI analysis.
- **Google Gemini:** High-speed network topology processing.

## 🛠️ Tech Stack
- **Simulation Engine:** SimPy (Discrete-Event)
- **Graph Theory:** NetworkX (Topology management)
- **Geospatial Processing:** Geopy
- **API/UI:** Flask (Web UI + REST endpoints)
- **Data Structures:** NumPy, Pandas

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

3. **Run the Advanced Mesh Network Demo:**
   ```bash
   python3 -m examples.advanced_network
   ```

---

## 📱 Mobile Configuration Guide

1. **Start the Simulator Web App:**
   ```bash
   python3 mobile_client/app.py
   ```
2. **On your Mobile Phone:**
   Navigate to `http://<YOUR_LAPTOP_IP>:5001`.
3. **Simulate:** Tap "Run Latency Test" to see how data would travel from your current coordinates across a LEO mesh to a target city!

---

## 🏗️ Architecture Design
- `engine.py`: The simulation orchestrator, managing events, packet life cycles, and routing graphs.
- `node.py`: Object-oriented definitions for Ground Terminals and LEO Satellite routers.
- `utils.py`: Geocoding and distance resolution services.
- `mobile_client/`: Flask implementation for a mobile configurator UI.

---

## 📄 License
MIT License. 

## 🤝 Contact
**Hooman P.** - [GitHub](https://github.com/hoomanp)
