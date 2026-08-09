"""Simulation orchestration shared by REST + SSE endpoints."""

from __future__ import annotations

import simpy

from constellasim.engine import ConstellationSimulator
from constellasim.llm import _sanitize
from constellasim.node import GroundStation, Satellite

from api.state import state

# Offline-friendly city atlas so recruiter demos work without Nominatim.
CITY_ATLAS = {
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
    "paris": (48.8566, 2.3522),
    "berlin": (52.5200, 13.4050),
    "new york": (40.7128, -74.0060),
    "nyc": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "san francisco": (37.7749, -122.4194),
    "singapore": (1.3521, 103.8198),
    "sydney": (-33.8688, 151.2093),
    "toronto": (43.6532, -79.3832),
    "dubai": (25.2048, 55.2708),
    "mumbai": (19.0760, 72.8777),
    "seoul": (37.5665, 126.9780),
    "tarzana": (34.1675, -118.5504),
}


def resolve_city(city: str) -> tuple[float | None, float | None]:
    key = city.strip().lower()
    if key in CITY_ATLAS:
        return CITY_ATLAS[key]
    # Partial match (e.g. "Paris, France")
    for name, coords in CITY_ATLAS.items():
        if name in key:
            return coords
    return state.geocoder.resolve_location(city)


def run_simulation(src_lat: float, src_lon: float, dest_city: str) -> tuple[dict | None, str | None]:
    dest_city = _sanitize(dest_city.strip())[:100]
    dest_lat, dest_lon = resolve_city(dest_city)
    if dest_lat is None:
        return None, "Destination could not be resolved"

    env = simpy.Environment()
    sim = ConstellationSimulator(env)

    sats = ["SAT1", "SAT2", "SAT3"]
    for s in sats:
        sim.add_node(Satellite(env, s, 1))
    sim.add_link("SAT1", "SAT2", weight=5.0)
    sim.add_link("SAT2", "SAT3", weight=5.0)

    gs_src = GroundStation(env, "Mobile-User", src_lat, src_lon)
    dest_node_id = f"Gateway-{abs(hash(dest_city)) % 100000}"
    gs_dest = GroundStation(env, dest_node_id, dest_lat, dest_lon)
    sim.add_node(gs_src)
    sim.add_node(gs_dest)
    sim.add_link(gs_src.node_id, "SAT1", weight=2.0)
    sim.add_link(gs_dest.node_id, "SAT3", weight=2.0)

    if not state.sim_semaphore.acquire(blocking=False):
        return None, "Server busy, please retry shortly."
    try:
        env.process(sim.send_packet(gs_src.node_id, gs_dest.node_id, 1))
        env.run(until=50)
    finally:
        state.sim_semaphore.release()

    report = sim.generate_report()
    latency = sim.stats["latencies"][0] if sim.stats["latencies"] else None
    route = sim.find_shortest_path(gs_src.node_id, gs_dest.node_id) or []
    topology = {
        "nodes": [
            {"id": nid, "type": "satellite" if nid.startswith("SAT") else "ground"}
            for nid in sim.graph.nodes()
        ],
        "edges": [
            {"source": u, "target": v, "weight": round(d.get("weight", 1.0), 1)}
            for u, v, d in sim.graph.edges(data=True)
        ],
        "route": route,
        "dropped": latency is None,
    }

    return {
        "report": report,
        "latency": latency,
        "src": f"{src_lat:.2f}, {src_lon:.2f}",
        "dest": f"{dest_city} ({dest_lat:.2f}, {dest_lon:.2f})",
        "dest_lat": dest_lat,
        "dest_lon": dest_lon,
        "topology": topology,
    }, None


def remember_simulation(result: dict) -> dict:
    snapshot = {
        "source": result["src"],
        "destination": result["dest"],
        "latency_ms": f"{result['latency']:.2f}" if result["latency"] else "dropped",
        "status": "Success" if result["latency"] else "Failed",
        "packet_loss_pct": 0 if result["latency"] else 100,
        "topology": result["topology"],
    }
    with state.sim_lock:
        state.last_sim.update(snapshot)
    return snapshot
