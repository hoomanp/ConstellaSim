# Developer Guide: ConstellaSim

Welcome to the **ConstellaSim** code guide! This document explains how the LEO network simulator is built and how you can add new features.

## 🏗️ Core Concept: Discrete-Event Simulation (DES)

Most network simulators use a "real-time" approach (slow and inaccurate) or a "time-step" approach (clunky). **ConstellaSim** uses a **Discrete-Event Simulation** (DES) model.

Instead of checking every millisecond "what happened?", the simulator jumps from one event to the next. For example, when a packet is sent, we calculate the propagation delay (say, 2.4ms) and tell the engine: "Wake me up in 2.4ms to deliver this packet."

## 🐍 Python Best Practices: SimPy & Generators

The simulator relies heavily on Python **generators** (`yield`). 

-   When you `yield env.timeout(delay)`, you are telling the SimPy engine to pause that specific process (like a packet's journey) while allowing other processes (other packets) to keep moving.
-   `env.process(sim.send_packet(...))` launches a new "micro-thread" for every packet, allowing you to simulate thousands of simultaneous connections.

## 🔭 How to Extend This Project

### 1. Dynamic Routing (The Next Big Step)
In `examples/multi_hop_demo.py`, we manually define the `network_path`. For a real constellation, you should:
- Use `NetworkX` to create a graph of all satellites.
- Periodically update the weights (latency) between satellites.
- Use `nx.shortest_path(G, source, target, weight='latency')` to dynamically find the best route.

### 2. Handover Simulation
Satellites move quickly. You can add a process that changes which satellite a `GroundStation` is connected to every 60 seconds of simulation time. This will help you test "TCP session persistence" during handovers.

### 3. Buffer Management
Add a `capacity` limit to the `Satellite` node's packet queue. If more packets arrive than the satellite can process, simulate packet drops.

## 🧪 Running Tests
We use `pytest` for unit testing. To run the tests:

```bash
cd ConstellaSim
pytest tests/
```

*(Note: Don't forget to add a simple test file in the `tests/` directory to get started!)*
