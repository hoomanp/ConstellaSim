import simpy
import random

class ConstellationSimulator:
    """Discrete-event engine for LEO network simulation."""
    def __init__(self, env):
        self.env = env
        self.nodes = {} # node_id -> NetworkNode object

    def add_node(self, node):
        self.nodes[node.node_id] = node

    def simulate_hop(self, source_id, dest_id, packet, distance_km):
        """Simulate a packet hop with latency based on physical distance."""
        # Calculate propagation delay (speed of light ~300km/ms)
        prop_delay_ms = distance_km / 300.0
        
        # Add a small processing delay for the router/satellite processor
        proc_delay_ms = random.uniform(0.1, 0.5) 
        
        total_delay = prop_delay_ms + proc_delay_ms
        
        # SimPy Wait (Yield)
        yield self.env.timeout(total_delay)
        
        # Hand off to the next node
        if dest_id in self.nodes:
            self.nodes[dest_id].receive_packet(packet)
            return True
        return False

    def send_packet(self, path, packet_id):
        """Send a packet along a predefined multi-hop path."""
        packet = {'id': packet_id, 'start_time': self.env.now, 'hops': 0}
        
        for i in range(len(path) - 1):
            source = path[i]
            dest = path[i+1]
            
            # For demonstration, assume a standard distance of 600km between hops
            # In a real system, this would be calculated dynamically
            success = yield from self.simulate_hop(source, dest, packet, distance_km=600.0)
            if not success:
                break
            packet['hops'] += 1
        
        return packet
