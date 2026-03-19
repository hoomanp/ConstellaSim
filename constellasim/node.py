import simpy
import random  # Bug fix: random was used in handover() but never imported.

class NetworkNode:
    """Base class for all network nodes (Satellites and Ground Stations)."""
    def __init__(self, env, node_id, buffer_limit=100):
        self.env = env
        self.node_id = node_id
        self.packet_queue = simpy.Store(env)
        self.received_packets = []
        self.buffer_limit = buffer_limit # Simulation of satellite memory constraints

    _PACKET_LOG_MAX = 10_000  # M-4: cap to prevent unbounded memory growth.

    def receive_packet(self, packet):
        """Receive a packet and log the arrival time."""
        packet['arrival_time'] = self.env.now
        self.received_packets.append(packet)
        if len(self.received_packets) > self._PACKET_LOG_MAX:
            del self.received_packets[:-self._PACKET_LOG_MAX]

class Satellite(NetworkNode):
    """A LEO Satellite with dynamic ISL capabilities."""
    def __init__(self, env, sat_id, orbital_plane):
        super().__init__(env, sat_id)
        self.orbital_plane = orbital_plane

class GroundStation(NetworkNode):
    """A user or gateway terminal with Handover logic."""
    def __init__(self, env, gs_id, lat, lon):
        super().__init__(env, gs_id)
        self.lat = lat
        self.lon = lon
        self.current_satellite = None

    def handover(self, simulator, satellite_ids):
        """Pick the best satellite (closest) to connect to."""
        # This is a simplified handover logic. 
        # In a real system, we would calculate elevation angles.
        best_sat = random.choice(satellite_ids) # Simplified for demonstration
        self.current_satellite = best_sat
        simulator.add_link(self.node_id, best_sat, weight=1.2) # Connect
        # print(f"[{self.env.now:.2f}ms] GS {self.node_id} HANDOVER to {best_sat}")
