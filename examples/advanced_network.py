import simpy
from constellasim.engine import ConstellationSimulator
from constellasim.node import GroundStation, Satellite

def run_simulation():
    env = simpy.Environment()
    sim = ConstellationSimulator(env)
    
    # 1. Setup a Mesh Network of 4 Satellites (ISL - Inter-Satellite Links)
    sats = ["SAT1", "SAT2", "SAT3", "SAT4"]
    for s_id in sats:
        sim.add_node(Satellite(env, s_id, 1))
    
    # Connect them in a ring/mesh
    sim.add_link("SAT1", "SAT2", weight=1.5)
    sim.add_link("SAT2", "SAT3", weight=2.0)
    sim.add_link("SAT3", "SAT4", weight=1.5)
    sim.add_link("SAT4", "SAT1", weight=2.5) # Longer path
    
    # 2. Add Ground Stations
    gs_lon = GroundStation(env, "GS-LONDON", 51.5, -0.1)
    gs_nyc = GroundStation(env, "GS-NYC", 40.7, -74.0)
    sim.add_node(gs_lon)
    sim.add_node(gs_nyc)
    
    # 3. Ground-to-Satellite Links (GSL)
    sim.add_link("GS-LONDON", "SAT1", weight=2.0)
    sim.add_link("GS-NYC", "SAT3", weight=2.0)
    
    # 4. Process: Traffic Generation (100 packets, high congestion)
    def traffic_gen():
        for i in range(100):
            yield env.timeout(1.0) # Intense traffic every 1ms
            env.process(sim.send_packet("GS-LONDON", "GS-NYC", i))

    # 5. Run the Engine
    print("--- Running Advanced LEO Mesh Simulation ---")
    env.process(traffic_gen())
    env.run(until=150)
    
    # 6. Generate Analytics Report
    print(sim.generate_report())

if __name__ == "__main__":
    run_simulation()
