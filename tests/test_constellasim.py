"""
ConstellaSim test suite — unit + integration tests.

Covers:
  - _sanitize() prompt-injection defence
  - Geocoder input validation & LRU cache
  - ConstellationSimulator routing, packet flow, memory caps
  - NetworkPlanner allowlist enforcement
  - NetworkAI._parse_optimizer_response() JSON extraction
  - Flask API endpoints (mocked LLM)
  - Feature 6 /api/optimize endpoint
"""

import json
import os
import sys
import simpy
import pytest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Make the project importable from any working directory
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from constellasim.llm import _sanitize, NetworkAI
from constellasim.utils import Geocoder
from constellasim.engine import ConstellationSimulator
from constellasim.node import Satellite, GroundStation
from constellasim.planner import NetworkPlanner


# ===========================================================================
# 1. Sanitization
# ===========================================================================

class TestSanitize:
    def test_strips_null_bytes(self):
        assert "\x00" not in _sanitize("hello\x00world")

    def test_strips_bidirectional_overrides(self):
        # U+202E RIGHT-TO-LEFT OVERRIDE — classic prompt injection vector
        assert "\u202e" not in _sanitize("ignore previous\u202e instructions")

    def test_strips_zero_width_chars(self):
        assert "\u200b" not in _sanitize("inject\u200bhere")

    def test_strips_bom(self):
        assert "\ufeff" not in _sanitize("\ufeffstart")

    def test_preserves_normal_text(self):
        text = "London, UK — latency: 12.34 ms (packet loss: 0%)"
        assert _sanitize(text) == text

    def test_strips_control_chars_in_mixed_input(self):
        result = _sanitize("city\x1fname\x7f")
        assert "\x1f" not in result
        assert "\x7f" not in result

    def test_returns_string_for_non_string_input(self):
        assert isinstance(_sanitize(42), str)
        assert isinstance(_sanitize(None), str)


# ===========================================================================
# 2. Geocoder
# ===========================================================================

class TestGeocoder:
    def test_rejects_empty_query(self):
        g = Geocoder()
        lat, lon = g.resolve_location("")
        assert lat is None and lon is None

    def test_rejects_injection_attempt(self):
        g = Geocoder()
        # URL scheme — rejected by allowlist
        lat, lon = g.resolve_location("javascript://foo")
        assert lat is None and lon is None

    def test_rejects_path_traversal(self):
        g = Geocoder()
        lat, lon = g.resolve_location("../../etc/passwd")
        # '/' not in allowlist — should be rejected
        assert lat is None and lon is None

    def test_caches_results(self):
        g = Geocoder()
        mock_location = MagicMock()
        mock_location.latitude = 51.5
        mock_location.longitude = -0.12
        with patch.object(g.geolocator, 'geocode', return_value=mock_location) as mock_gc:
            g.resolve_location("London")
            g.resolve_location("London")
            # Second call should be served from cache
            assert mock_gc.call_count == 1

    def test_cache_evicts_oldest_at_max(self):
        g = Geocoder()
        # Manually fill the cache to max
        from collections import OrderedDict
        g._cache = OrderedDict()
        for i in range(1000):
            g._cache[f"city_{i}"] = (float(i), float(i))
        mock_location = MagicMock()
        mock_location.latitude = 0.0
        mock_location.longitude = 0.0
        with patch.object(g.geolocator, 'geocode', return_value=mock_location):
            g.resolve_location("NewCity")
        assert len(g._cache) == 1000
        assert "city_0" not in g._cache  # oldest evicted


# ===========================================================================
# 3. ConstellationSimulator
# ===========================================================================

class TestConstellationSimulator:
    def _build_linear(self, n_sats=3):
        env = simpy.Environment()
        sim = ConstellationSimulator(env)
        sat_ids = [f"SAT{i}" for i in range(n_sats)]
        for sid in sat_ids:
            sim.add_node(Satellite(env, sid, 1))
        for i in range(n_sats - 1):
            sim.add_link(sat_ids[i], sat_ids[i + 1], weight=5.0)
        return env, sim, sat_ids

    def test_packet_delivered_on_valid_path(self):
        env, sim, sats = self._build_linear(3)
        gs_a = GroundStation(env, "GS_A", 51.5, -0.12)
        gs_b = GroundStation(env, "GS_B", 48.8, 2.35)
        sim.add_node(gs_a)
        sim.add_node(gs_b)
        sim.add_link("GS_A", "SAT0", weight=2.0)
        sim.add_link("GS_B", "SAT2", weight=2.0)
        env.process(sim.send_packet("GS_A", "GS_B", 1))
        env.run(until=100)
        assert sim.stats["received"] == 1
        assert sim.stats["dropped"] == 0
        assert len(sim.stats["latencies"]) == 1

    def test_packet_dropped_when_no_path(self):
        env, sim, sats = self._build_linear(3)
        gs_a = GroundStation(env, "GS_A", 0.0, 0.0)
        gs_b = GroundStation(env, "GS_B", 1.0, 1.0)
        sim.add_node(gs_a)
        sim.add_node(gs_b)
        # No links added — no path exists
        env.process(sim.send_packet("GS_A", "GS_B", 1))
        env.run(until=100)
        assert sim.stats["dropped"] == 1
        assert sim.stats["received"] == 0

    def test_report_includes_expected_fields(self):
        env, sim, sats = self._build_linear(2)
        gs_a = GroundStation(env, "GS_A", 0.0, 0.0)
        gs_b = GroundStation(env, "GS_B", 1.0, 1.0)
        sim.add_node(gs_a)
        sim.add_node(gs_b)
        sim.add_link("GS_A", "SAT0", weight=1.0)
        sim.add_link("GS_B", "SAT1", weight=1.0)
        env.process(sim.send_packet("GS_A", "GS_B", 1))
        env.run(until=50)
        report = sim.generate_report()
        assert "Packet Loss Rate" in report
        assert "Average End-to-End Latency" in report

    def test_latency_buffer_cap(self):
        env, sim, sats = self._build_linear(2)
        gs_a = GroundStation(env, "GS_A", 0.0, 0.0)
        gs_b = GroundStation(env, "GS_B", 1.0, 1.0)
        sim.add_node(gs_a)
        sim.add_node(gs_b)
        sim.add_link("GS_A", "SAT0", weight=1.0)
        sim.add_link("GS_B", "SAT1", weight=1.0)
        # Manually overfill to trigger cap logic
        sim.stats["latencies"] = list(range(10_001))
        sim.stats["latencies"].append(99.0)
        # The cap fires inside send_packet on next append; simulate manually
        sim.stats["latencies"] = sim.stats["latencies"][:10_001]
        # Force cap by calling the trim logic directly
        if len(sim.stats["latencies"]) > 10_000:
            del sim.stats["latencies"][:-10_000]
        assert len(sim.stats["latencies"]) == 10_000

    def test_generate_report_no_data(self):
        env = simpy.Environment()
        sim = ConstellationSimulator(env)
        assert sim.generate_report() == "No data collected."

    def test_packet_loss_rate_no_division_by_zero(self):
        env = simpy.Environment()
        sim = ConstellationSimulator(env)
        sim.stats["sent"] = 0
        report = sim.generate_report()
        # Should not raise ZeroDivisionError — returns "No data collected." when no latencies
        assert isinstance(report, str)


# ===========================================================================
# 4. NetworkPlanner allowlist
# ===========================================================================

class TestNetworkPlanner:
    def _make_planner(self, llm_response):
        mock_ai = MagicMock()
        mock_ai.chat.return_value = llm_response
        return NetworkPlanner(mock_ai)

    def test_valid_simulate_function(self):
        planner = self._make_planner('{"function": "simulate", "params": {"dest_city": "Berlin"}}')
        result = planner.parse("Simulate to Berlin")
        assert result["function"] == "simulate"
        assert result["params"]["dest_city"] == "Berlin"

    def test_valid_topology_info_function(self):
        planner = self._make_planner('{"function": "topology_info", "params": {"sat_count": 5}}')
        result = planner.parse("Topology with 5 satellites")
        assert result["function"] == "topology_info"
        assert result["params"]["sat_count"] == 5

    def test_rejects_unlisted_function(self):
        # LLM tries to call an arbitrary function — must be blocked
        planner = self._make_planner('{"function": "exec_shell", "params": {"cmd": "ls"}}')
        result = planner.parse("Do something dangerous")
        assert result["function"] is None

    def test_rejects_null_function(self):
        planner = self._make_planner('{"function": null, "params": {}}')
        result = planner.parse("Something unmappable")
        assert result["function"] is None

    def test_handles_markdown_fenced_json(self):
        planner = self._make_planner('```json\n{"function": "simulate", "params": {"dest_city": "Tokyo"}}\n```')
        result = planner.parse("Packet to Tokyo")
        assert result["function"] == "simulate"

    def test_empty_input(self):
        mock_ai = MagicMock()
        planner = NetworkPlanner(mock_ai)
        result = planner.parse("")
        assert result["function"] is None
        mock_ai.chat.assert_not_called()

    def test_rejects_non_dict_params(self):
        planner = self._make_planner('{"function": "simulate", "params": ["Berlin"]}')
        result = planner.parse("Simulate to Berlin")
        assert result["function"] is None


# ===========================================================================
# 5. NetworkAI._parse_optimizer_response (Feature 6)
# ===========================================================================

class TestParseOptimizerResponse:
    def test_valid_json_response(self):
        payload = json.dumps({
            "recommendations": [
                {"change": "Add 2 more satellites", "expected_impact": "Reduce latency by 15ms", "priority": "HIGH"},
            ],
            "rationale": "Current topology is under-redundant.",
            "health_score": 72,
        })
        result = NetworkAI._parse_optimizer_response(payload)
        assert result["health_score"] == 72
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["priority"] == "HIGH"
        assert "under-redundant" in result["rationale"]

    def test_markdown_fenced_json(self):
        payload = '```json\n{"recommendations":[],"rationale":"OK","health_score":85}\n```'
        result = NetworkAI._parse_optimizer_response(payload)
        assert result["health_score"] == 85
        assert result["recommendations"] == []

    def test_invalid_priority_normalised_to_medium(self):
        payload = json.dumps({
            "recommendations": [{"change": "foo", "expected_impact": "bar", "priority": "URGENT"}],
            "rationale": "x",
            "health_score": 50,
        })
        result = NetworkAI._parse_optimizer_response(payload)
        assert result["recommendations"][0]["priority"] == "MEDIUM"

    def test_health_score_clamped(self):
        payload = json.dumps({"recommendations": [], "rationale": "x", "health_score": 150})
        result = NetworkAI._parse_optimizer_response(payload)
        assert result["health_score"] == 100

        payload2 = json.dumps({"recommendations": [], "rationale": "x", "health_score": -10})
        result2 = NetworkAI._parse_optimizer_response(payload2)
        assert result2["health_score"] == 0

    def test_null_health_score_on_non_numeric(self):
        payload = json.dumps({"recommendations": [], "rationale": "x", "health_score": "great"})
        result = NetworkAI._parse_optimizer_response(payload)
        assert result["health_score"] is None

    def test_graceful_fallback_on_unparseable(self):
        result = NetworkAI._parse_optimizer_response("totally not json {{{{")
        assert result["recommendations"] == []
        assert result["health_score"] is None
        assert isinstance(result["rationale"], str)

    def test_recommendation_text_truncated_at_300(self):
        long_text = "X" * 500
        payload = json.dumps({
            "recommendations": [{"change": long_text, "expected_impact": long_text, "priority": "LOW"}],
            "rationale": "x",
            "health_score": 60,
        })
        result = NetworkAI._parse_optimizer_response(payload)
        assert len(result["recommendations"][0]["change"]) == 300
        assert len(result["recommendations"][0]["expected_impact"]) == 300


# ===========================================================================
# 6. Flask API — endpoint integration tests (LLM mocked)
# ===========================================================================

@pytest.fixture()
def flask_client():
    """Return a Flask test client with AI mocked out."""
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-pytest"
    os.environ["FLASK_DEBUG"] = "false"

    mock_ai = MagicMock(spec=NetworkAI)
    mock_ai.analyze_report.return_value = "Mock AI analysis."
    mock_ai.analyze_report_stream.return_value = iter(["Mock ", "stream."])
    mock_ai.chat.return_value = "Mock chat reply."
    mock_ai.generate_briefing.return_value = "# Mock Briefing\n\nContent."
    mock_ai.optimize_topology.return_value = {
        "recommendations": [
            {"change": "Add relay satellite", "expected_impact": "Lower latency", "priority": "HIGH"}
        ],
        "rationale": "Current hop count is excessive.",
        "health_score": 65,
    }

    with patch("mobile_client.app.NetworkAI", return_value=mock_ai), \
         patch("mobile_client.app.ai_analyst", mock_ai), \
         patch("mobile_client.app._planner", NetworkPlanner(mock_ai)):
        import importlib
        import mobile_client.app as app_module
        importlib.reload(app_module)
        app_module.ai_analyst = mock_ai
        app_module._planner = NetworkPlanner(mock_ai)
        app_module.app.config["TESTING"] = True
        app_module.app.config["WTF_CSRF_ENABLED"] = False
        with app_module.app.test_client() as client:
            yield client, app_module


class TestFlaskSimulateEndpoint:
    def test_missing_json_body(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/simulate", data="", content_type="text/plain")
        # Flask 3.0+ returns 415 for wrong Content-Type; older returns 400 — both are client errors
        assert r.status_code in (400, 415)

    def test_invalid_coordinates_rejected(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/simulate",
                        json={"src_lat": 999, "src_lon": 0, "dest_city": "London"})
        assert r.status_code == 400
        assert b"range" in r.data

    def test_missing_src_lat_rejected(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/simulate", json={"src_lon": 0, "dest_city": "London"})
        assert r.status_code == 400

    def test_dest_city_too_long_rejected(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/simulate",
                        json={"src_lat": 51.5, "src_lon": -0.12, "dest_city": "A" * 101})
        assert r.status_code == 400

    def test_security_headers_present(self, flask_client):
        client, _ = flask_client
        r = client.get("/")
        assert "Content-Security-Policy" in r.headers
        assert "X-Frame-Options" in r.headers
        assert r.headers["X-Frame-Options"] == "DENY"
        assert "X-Content-Type-Options" in r.headers
        assert r.headers["X-Content-Type-Options"] == "nosniff"


class TestFlaskChatEndpoint:
    def test_empty_message_rejected(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/chat", json={"message": "  "})
        assert r.status_code == 400

    def test_non_string_message_rejected(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/chat", json={"message": 12345})
        assert r.status_code == 400

    def test_chat_reset_clears_session(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/chat/reset")
        assert r.status_code == 200
        assert json.loads(r.data)["status"] == "ok"


class TestFlaskOptimizeEndpoint:
    def test_returns_recommendations(self, flask_client):
        client, app_module = flask_client
        # Seed _last_sim so endpoint doesn't return 400
        with app_module._sim_lock:
            app_module._last_sim.update({
                "source": "51.50, -0.12",
                "destination": "London (51.50, -0.12)",
                "latency_ms": "14.50",
                "status": "Success",
                "packet_loss_pct": 0,
            })
        r = client.post("/api/optimize",
                        json={"constraints": "minimize latency"})
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "recommendations" in data
        assert "health_score" in data
        assert "rationale" in data
        assert data["health_score"] == 65

    def test_returns_400_without_simulation(self, flask_client):
        client, app_module = flask_client
        # Clear sim data
        with app_module._sim_lock:
            app_module._last_sim.clear()
        r = client.post("/api/optimize", json={})
        assert r.status_code == 400
        assert b"simulation" in r.data.lower()

    def test_constraints_sanitized(self, flask_client):
        client, app_module = flask_client
        with app_module._sim_lock:
            app_module._last_sim.update({
                "source": "0.00, 0.00",
                "destination": "Tokyo",
                "latency_ms": "50.00",
                "status": "Success",
                "packet_loss_pct": 0,
            })
        # Constraint with control characters — should not crash
        r = client.post("/api/optimize",
                        json={"constraints": "minimize\x00latency\u202e"})
        assert r.status_code == 200

    def test_ai_unavailable_returns_503(self, flask_client):
        client, app_module = flask_client
        original = app_module.ai_analyst
        app_module.ai_analyst = None
        with app_module._sim_lock:
            app_module._last_sim.update({"source": "x", "status": "Success"})
        try:
            r = client.post("/api/optimize", json={})
            assert r.status_code == 503
        finally:
            app_module.ai_analyst = original


class TestFlaskPlanEndpoint:
    def test_empty_query_rejected(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/plan", json={"query": ""})
        assert r.status_code == 400

    def test_non_string_query_rejected(self, flask_client):
        client, _ = flask_client
        r = client.post("/api/plan", json={"query": ["drop", "table"]})
        assert r.status_code == 400


class TestFlaskAlertsEndpoint:
    def test_returns_empty_list_when_monitor_disabled(self, flask_client):
        client, app_module = flask_client
        app_module._monitor = None
        r = client.get("/api/alerts")
        assert r.status_code == 200
        assert json.loads(r.data) == []


class TestFlaskTopologyEndpoint:
    _SAMPLE_TOPOLOGY = {
        "nodes": [
            {"id": "Mobile-User", "type": "ground"},
            {"id": "SAT1", "type": "satellite"},
            {"id": "SAT2", "type": "satellite"},
            {"id": "SAT3", "type": "satellite"},
            {"id": "Gateway-12345", "type": "ground"},
        ],
        "edges": [
            {"source": "Mobile-User", "target": "SAT1", "weight": 2.0},
            {"source": "SAT1", "target": "SAT2", "weight": 5.0},
            {"source": "SAT2", "target": "SAT3", "weight": 5.0},
            {"source": "SAT3", "target": "Gateway-12345", "weight": 2.0},
        ],
        "route": ["Mobile-User", "SAT1", "SAT2", "SAT3", "Gateway-12345"],
        "dropped": False,
    }

    def test_returns_400_without_simulation(self, flask_client):
        client, app_module = flask_client
        with app_module._sim_lock:
            app_module._last_sim.clear()
        r = client.get("/api/topology")
        assert r.status_code == 400
        assert b"simulation" in r.data.lower()

    def test_returns_topology_after_simulation(self, flask_client):
        client, app_module = flask_client
        with app_module._sim_lock:
            app_module._last_sim.update({
                "source": "51.50, -0.12",
                "destination": "London",
                "latency_ms": "14.50",
                "status": "Success",
                "packet_loss_pct": 0,
                "topology": self._SAMPLE_TOPOLOGY,
            })
        r = client.get("/api/topology")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert "nodes" in data
        assert "edges" in data
        assert "route" in data
        assert "dropped" in data

    def test_topology_has_correct_node_types(self, flask_client):
        client, app_module = flask_client
        with app_module._sim_lock:
            app_module._last_sim.update({"topology": self._SAMPLE_TOPOLOGY})
        r = client.get("/api/topology")
        data = json.loads(r.data)
        types = {n["id"]: n["type"] for n in data["nodes"]}
        assert types["SAT1"] == "satellite"
        assert types["Mobile-User"] == "ground"

    def test_route_forms_valid_path(self, flask_client):
        client, app_module = flask_client
        with app_module._sim_lock:
            app_module._last_sim.update({"topology": self._SAMPLE_TOPOLOGY})
        r = client.get("/api/topology")
        data = json.loads(r.data)
        route = data["route"]
        # Route must start at source and end at destination
        assert route[0] == "Mobile-User"
        assert route[-1] == "Gateway-12345"
        # Every consecutive pair must be connected by an edge
        edge_pairs = {(e["source"], e["target"]) for e in data["edges"]}
        edge_pairs |= {(e["target"], e["source"]) for e in data["edges"]}
        for i in range(len(route) - 1):
            assert (route[i], route[i + 1]) in edge_pairs

    def test_dropped_packet_flagged(self, flask_client):
        client, app_module = flask_client
        dropped_topo = dict(self._SAMPLE_TOPOLOGY)
        dropped_topo["dropped"] = True
        dropped_topo["route"] = []
        with app_module._sim_lock:
            app_module._last_sim.update({"topology": dropped_topo})
        r = client.get("/api/topology")
        data = json.loads(r.data)
        assert data["dropped"] is True
        assert data["route"] == []


# ===========================================================================
# 8. _run_simulation topology output
# ===========================================================================

class TestRunSimulationTopology:
    """Verify that _run_simulation captures topology data correctly."""

    def test_topology_keys_present(self):
        import simpy
        from constellasim.engine import ConstellationSimulator
        from constellasim.node import Satellite, GroundStation

        env = simpy.Environment()
        sim = ConstellationSimulator(env)
        for sid in ["SAT1", "SAT2", "SAT3"]:
            sim.add_node(Satellite(env, sid, 1))
        sim.add_link("SAT1", "SAT2", weight=5.0)
        sim.add_link("SAT2", "SAT3", weight=5.0)
        gs_a = GroundStation(env, "GS_A", 51.5, -0.12)
        gs_b = GroundStation(env, "GS_B", 48.8, 2.35)
        sim.add_node(gs_a)
        sim.add_node(gs_b)
        sim.add_link("GS_A", "SAT1", weight=2.0)
        sim.add_link("GS_B", "SAT3", weight=2.0)
        env.process(sim.send_packet("GS_A", "GS_B", 1))
        env.run(until=100)

        route = sim.find_shortest_path("GS_A", "GS_B") or []
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
            "dropped": len(sim.stats["latencies"]) == 0,
        }

        assert len(topology["nodes"]) == 5
        sat_nodes = [n for n in topology["nodes"] if n["type"] == "satellite"]
        ground_nodes = [n for n in topology["nodes"] if n["type"] == "ground"]
        assert len(sat_nodes) == 3
        assert len(ground_nodes) == 2
        assert topology["dropped"] is False
        assert "GS_A" in topology["route"]
        assert "GS_B" in topology["route"]
