import simpy
import random
import networkx as nx

class ConstellationSimulator:
    """Advanced Discrete-event engine for LEO network simulation with routing."""
    def __init__(self, env):
        self.env = env
        self.nodes = {} 
        self.graph = nx.Graph()
        self.stats = {"sent": 0, "received": 0, "dropped": 0, "latencies": []}

    def add_node(self, node):
        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id)

    def add_link(self, node_a, node_b, weight=1.0):
        """Add a bidirectional link between two nodes."""
        self.graph.add_edge(node_a, node_b, weight=weight)

    def find_shortest_path(self, source, dest):
        """Use Dijkstra's algorithm to find the lowest-latency path."""
        try:
            return nx.dijkstra_path(self.graph, source, dest, weight='weight')
        except nx.NetworkXNoPath:
            return None

    def simulate_hop(self, source_id, dest_id, packet):
        """Simulate a packet hop with latency based on the edge weight."""
        # Bug fix: guard against missing edge to avoid a silent KeyError crashing the SimPy process.
        if not self.graph.has_edge(source_id, dest_id):
            self.stats["dropped"] += 1
            return False
        weight = self.graph[source_id][dest_id]['weight']
        
        # Propagation delay + processing
        total_delay = weight + random.uniform(0.1, 0.3)
        yield self.env.timeout(total_delay)
        
        # Check for buffer overflow (Congestion Simulation)
        dest_node = self.nodes[dest_id]
        if hasattr(dest_node, 'buffer_limit') and len(dest_node.packet_queue.items) >= dest_node.buffer_limit:
            self.stats["dropped"] += 1
            # print(f"[{self.env.now:.2f}ms] Packet {packet['id']} DROPPED at {dest_id} (Buffer Full)")
            return False
            
        dest_node.receive_packet(packet)
        return True

    def send_packet(self, source_id, dest_id, packet_id):
        """Find a route and send a packet."""
        self.stats["sent"] += 1
        path = self.find_shortest_path(source_id, dest_id)
        
        if not path:
            self.stats["dropped"] += 1
            return
            
        packet = {'id': packet_id, 'start_time': self.env.now, 'hops': 0}
        
        for i in range(len(path) - 1):
            success = yield from self.simulate_hop(path[i], path[i+1], packet)
            if not success:
                return
            packet['hops'] += 1
            
        self.stats["received"] += 1
        self.stats["latencies"].append(self.env.now - packet['start_time'])

    def generate_report(self):
        """Generate a summary of the simulation results."""
        if not self.stats["latencies"]:
            return "No data collected."
            
        avg_latency = sum(self.stats["latencies"]) / len(self.stats["latencies"])
        # Bug fix: guard against division by zero if generate_report is called before any send_packet.
        p_loss = (self.stats["dropped"] / self.stats["sent"]) * 100 if self.stats["sent"] > 0 else 0.0
        
        report = f"\n--- ConstellaSim Analytics Report ---\n"
        report += f"Total Packets Sent: {self.stats['sent']}\n"
        report += f"Total Packets Received: {self.stats['received']}\n"
        report += f"Packet Loss Rate: {p_loss:.2f}%\n"
        report += f"Average End-to-End Latency: {avg_latency:.2f} ms\n"
        report += f"------------------------------------"
        return report
