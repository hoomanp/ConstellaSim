import simpy
from constellasim.engine import ConstellationSimulator
from constellasim.node import GroundStation, Satellite

def run_simulation():
    # 1. Setup Environment
    env = simpy.Environment()
    sim = ConstellationSimulator(env)
    
    # 2. Add Nodes (GS1 -> SatA -> SatB -> GS2)
    gs1 = GroundStation(env, "GS-LONDON", 51.5, -0.1)
    sat_a = Satellite(env, "SAT-101", 1)
    sat_b = Satellite(env, "SAT-102", 1)
    gs2 = GroundStation(env, "GS-NYC", 40.7, -74.0)
    
    for node in [gs1, sat_a, sat_b, gs2]:
        sim.add_node(node)

    # 3. Define links for the multi-hop path (LONDON -> NYC via LEO ISLs)
    # Bug fix: no links were defined, so Dijkstra found no path and all packets were dropped.
    # Bug fix: send_packet(source_id, dest_id, packet_id) takes 3 string args, not a list.
    sim.add_link("GS-LONDON", "SAT-101", weight=2.0)
    sim.add_link("SAT-101", "SAT-102", weight=1.5)
    sim.add_link("SAT-102", "GS-NYC", weight=2.0)

    # 4. Process: Send 10 packets every 5ms
    def packet_generator():
        for i in range(10):
            yield env.timeout(5.0)  # wait 5ms between packets
            print(f"[{env.now:.2f}ms] Dispatching Packet {i} from LONDON")
            env.process(sim.send_packet("GS-LONDON", "GS-NYC", i))

    # 5. Run it!
    print("--- Starting LEO Multi-hop Network Simulation ---")
    env.process(packet_generator())
    env.run(until=100) # Run for 100ms
    
    # 6. Analyze Results
    print(f"\n--- Simulation Results ---")
    print(f"Packets received at GS-NYC: {len(gs2.received_packets)}")
    for pkt in gs2.received_packets:
        latency = pkt['arrival_time'] - pkt['start_time']
        print(f"Packet {pkt['id']}: End-to-End Latency = {latency:.2f} ms")

if __name__ == "__main__":
    run_simulation()
