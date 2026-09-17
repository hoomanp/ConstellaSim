"""FastAPI integration tests for the ConstellaSim recruiter demo backend."""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CONSTELLASIM_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")


@pytest.fixture()
def client():
    from api.main import app
    from api.state import state

    state.boot_ai()
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["service"] == "constellasim"
        assert body["ai"] is True
        assert body["ai_mode"] in {"demo", "google", "azure", "amazon"}
        assert "demo_location" in body


class TestSimulate:
    def test_stream_demo_route(self, client):
        r = client.get(
            "/api/simulate/stream",
            params={"src_lat": 34.1675, "src_lon": -118.5504, "dest_city": "Tokyo"},
        )
        assert r.status_code == 200
        assert "simresult" in r.text
        assert "event: done" in r.text

    def test_blocking_simulate(self, client):
        r = client.post(
            "/api/simulate",
            json={"src_lat": 34.1675, "src_lon": -118.5504, "dest_city": "London"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in {"Success", "Failed"}
        assert "ai_analysis" in body

    def test_bad_coords(self, client):
        r = client.post(
            "/api/simulate",
            json={"src_lat": 999, "src_lon": 0, "dest_city": "London"},
        )
        assert r.status_code == 422


class TestPlanAndOptimize:
    def test_plan_heuristic(self, client):
        r = client.post("/api/plan", json={"query": "Simulate a packet to Berlin"})
        assert r.status_code == 200
        body = r.json()
        assert body["function"] == "simulate"
        assert "Berlin" in body["destination"] or "berlin" in body["destination"].lower()

    def test_optimize_after_sim(self, client):
        client.post(
            "/api/simulate",
            json={"src_lat": 34.16, "src_lon": -118.55, "dest_city": "Paris"},
        )
        r = client.post("/api/optimize", json={"constraints": "minimize latency"})
        assert r.status_code == 200
        body = r.json()
        assert "recommendations" in body
        assert body["health_score"] is not None


class TestChatAndTopology:
    def test_chat_roundtrip(self, client):
        client.post(
            "/api/simulate",
            json={"src_lat": 51.5, "src_lon": -0.12, "dest_city": "Tokyo"},
        )
        r = client.post("/api/chat", json={"message": "Summarize latency", "session_id": "t1"})
        assert r.status_code == 200
        assert "reply" in r.json()
        r2 = client.post("/api/chat/reset?session_id=t1")
        assert r2.status_code == 200

    def test_topology(self, client):
        client.post(
            "/api/simulate",
            json={"src_lat": 34.16, "src_lon": -118.55, "dest_city": "Singapore"},
        )
        r = client.get("/api/topology")
        assert r.status_code == 200
        topo = r.json()
        assert len(topo["nodes"]) >= 4
        assert "route" in topo

    def test_alerts_evaluate(self, client):
        client.post(
            "/api/simulate",
            json={"src_lat": 34.16, "src_lon": -118.55, "dest_city": "Tokyo"},
        )
        r = client.post("/api/alerts/evaluate")
        assert r.status_code == 200
        body = r.json()
        assert "alerts" in body
        assert body["monitor"] is True

    def test_briefing(self, client):
        client.post(
            "/api/simulate",
            json={"src_lat": 34.16, "src_lon": -118.55, "dest_city": "London"},
        )
        r = client.get("/api/briefing")
        assert r.status_code == 200
        assert "Briefing" in r.text or "ConstellaSim" in r.text
