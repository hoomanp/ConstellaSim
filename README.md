# ConstellaSim: LEO Satellite Network Topology Simulator

**ConstellaSim** is a discrete-event simulator for modeling packet-level networking across Low Earth Orbit (LEO) satellite constellations. 

It allows researchers and engineers to analyze end-to-end latency, jitter, and handover performance in dynamic, high-speed space networks.

## 🚀 Key Features

- **Discrete-Event Core:** Powered by `SimPy` for high-fidelity timing and concurrency.
- **Multi-hop Routing:** Simulate packet movement across Inter-Satellite Links (ISL) and Ground-to-Satellite Links (GSL).
- **Latency Modeling:** Calculate propagation delay based on speed-of-light physics (distance/300km/ms) and variable processing overhead.
- **Node Management:** Classes for Satellites and Ground Stations with distinct behavior profiles.

## 🛠️ Installation

```bash
git clone https://github.com/YOUR_USERNAME/ConstellaSim.git
cd ConstellaSim
pip install -r requirements.txt
```

## 📊 Quick Start

Run the multi-hop demonstration to see packets traveling from London to NYC via LEO satellites:

```bash
python3 -m examples.multi_hop_demo
```

## 🏗️ Architecture

1.  **Engine (`engine.py`):** Manages the simulation clock and packet delivery logic.
2.  **Nodes (`node.py`):** Defines the characteristics of ground terminals and satellite routers.
3.  **Simulation Loop:** Uses Python generators (`yield`) to model time passing during signal propagation.

## 🛰️ Technical Context

In a LEO constellation, the network topology is constantly changing. Satellites move at ~7.5 km/s, meaning a ground station must "handover" its connection every few minutes. **ConstellaSim** provides the foundation to test routing algorithms that can handle this extreme dynamism.

## 🚧 Roadmap

- [ ] **Dynamic Topology:** Integration with `Skyfield` to calculate distances between satellites in real-time.
- [ ] **Shortest Path First (SPF):** Implement Dijkstra's algorithm using `NetworkX` to find the lowest-latency path.
- [ ] **Congestion Modeling:** Simulate packet drops when satellite buffers are full.

## 📄 License
MIT
