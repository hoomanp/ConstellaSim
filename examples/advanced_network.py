import simpy
from constellasim.engine import ConstellationSimulator
from constellasim.node import GroundStation, Satellite
from constellasim.utils import Geocoder

def run_simulation():
    env = simpy.Environment()
    sim = ConstellationSimulator(env)
    geo = Geocoder()
    
    # 1. Setup a Mesh Network of 4 Satellites (ISL - Inter-Satellite Links)
    sats = ["SAT1", "SAT2", "SAT3", "SAT4"]
    for s_id in sats:
        sim.add_node(Satellite(env, s_id, 1))
    
    # Connect them in a ring/mesh
    sim.add_link("SAT1", "SAT2", weight=1.5)
    sim.add_link("SAT2", "SAT3", weight=2.0)
    sim.add_link("SAT3", "SAT4", weight=1.5)
    sim.add_link("SAT4", "SAT1", weight=2.5) 
    
    # 2. Add Ground Stations (Dynamic Placement)
    print("--- 🌍 Set up your LEO Network Ground Stations ---")
    loc1_str = input("Enter Source City or ZIP (e.g., London): ") or "London"
    loc2_str = input("Enter Destination City or ZIP (e.g., New York): ") or "New York"
    
    lat1, lon1 = geo.resolve_location(loc1_str)
    lat2, lon2 = geo.resolve_location(loc2_str)
    
    gs_src = GroundStation(env, f"GS-{loc1_str.upper()}", lat1 or 0, lon1 or 0)
    gs_dest = GroundStation(env, f"GS-{loc2_str.upper()}", lat2 or 0, lon2 or 0)
    
    sim.add_node(gs_src)
    sim.add_node(gs_dest)
    
    # 3. Connect Ground Stations to the LEO Mesh
    sim.add_link(gs_src.node_id, "SAT1", weight=2.0)
    sim.add_link(gs_dest.node_id, "SAT3", weight=2.0)
    
    # 4. Process: Traffic Generation (100 packets, high congestion)
    def traffic_gen():
        # Bug fix: hardcoded "GS-LONDON"/"GS-NYC" IDs would break if the user enters
        # different city names. Use the actual node IDs built from user input.
        for i in range(100):
            yield env.timeout(1.0)  # Intense traffic every 1ms
            env.process(sim.send_packet(gs_src.node_id, gs_dest.node_id, i))

    # 5. Run the Engine
    print("--- Running Advanced LEO Mesh Simulation ---")
    env.process(traffic_gen())
    env.run(until=150)
    
    # 6. Generate Analytics Report
    print(sim.generate_report())

if __name__ == "__main__":
    run_simulation()
