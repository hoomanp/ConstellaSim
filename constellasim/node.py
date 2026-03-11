import simpy

class NetworkNode:
    """Base class for all network nodes (Satellites and Ground Stations)."""
    def __init__(self, env, node_id):
        self.env = env
        self.node_id = node_id
        self.packet_queue = simpy.Store(env)
        self.received_packets = []

    def receive_packet(self, packet):
        """Receive a packet and log the arrival time."""
        packet['arrival_time'] = self.env.now
        self.received_packets.append(packet)
        # print(f"[{self.env.now:.2f}ms] Node {self.node_id} received packet {packet['id']}")

class Satellite(NetworkNode):
    """A LEO Satellite with Inter-Satellite Link (ISL) capabilities."""
    def __init__(self, env, sat_id, orbital_plane):
        super().__init__(env, sat_id)
        self.orbital_plane = orbital_plane
        self.connected_neighbors = [] # List of neighboring satellites

class GroundStation(NetworkNode):
    """A user or gateway terminal on Earth."""
    def __init__(self, env, gs_id, lat, lon):
        super().__init__(env, gs_id)
        self.lat = lat
        self.lon = lon
        self.current_satellite = None # Currently connected satellite (for handover simulation)
