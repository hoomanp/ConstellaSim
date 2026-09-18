"""Extensive security + regression tests for ConstellaSim v2 API."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CONSTELLASIM_SECRET_KEY", "test-secret")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ["ANOMALY_MONITOR"] = "true"
os.environ["CORS_ALLOW_ALL"] = "false"
os.environ.pop("REQUIRE_API_KEY", None)
os.environ.pop("CONSTELLASIM_API_KEY", None)


@pytest.fixture()
def client():
    from api.main import app
    from api.state import state

    state.settings = __import__("api.config", fromlist=["get_settings"]).get_settings()
    state.boot_ai()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(monkeypatch):
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    monkeypatch.setenv("CONSTELLASIM_API_KEY", "test-api-key-xyz")
    # Reload settings on state
    from api import config, state as st
    from api.main import app

    st.state.settings = config.get_settings()
    st.state.boot_ai()
    with TestClient(app) as c:
        yield c


class TestSecurityHeaders:
    def test_api_sets_security_headers(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert "Content-Security-Policy" in r.headers
        assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]


class TestPathTraversal:
    def test_safe_web_file_blocks_dotdot(self):
        from api.main import WEB_DIST, _safe_web_file

        if not WEB_DIST.exists():
            pytest.skip("web/dist not built")
        assert _safe_web_file("../requirements.txt") is None
        assert _safe_web_file("..%2f..%2fetc/passwd") is None
        assert _safe_web_file("/etc/passwd") is None
        assert _safe_web_file("assets/../../../api/config.py") is None

    def test_spa_rejects_traversal(self, client):
        # Even if dist missing, path must not leak files via 200 with secret content.
        r = client.get("/../../requirements.txt")
        # Starlette may normalize; either 404 or SPA index — never requirements body.
        body = r.text.lower()
        assert "simpy>=" not in body
        assert "fastapi>=" not in body


class TestCors:
    def test_cors_not_wildcard_by_default(self, client):
        r = client.options(
            "/api/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Disallowed origin should not get ACAO *
        acao = r.headers.get("access-control-allow-origin")
        assert acao != "*"

    def test_localhost_origin_allowed(self, client):
        r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


class TestApiKeyGate:
    def test_health_open_when_api_key_required(self, auth_client):
        r = auth_client.get("/api/health")
        assert r.status_code == 200

    def test_simulate_requires_key(self, auth_client):
        r = auth_client.post(
            "/api/simulate",
            json={"src_lat": 34.1, "src_lon": -118.5, "dest_city": "Tokyo"},
        )
        assert r.status_code == 401

    def test_simulate_accepts_valid_key(self, auth_client):
        r = auth_client.post(
            "/api/simulate",
            headers={"X-API-Key": "test-api-key-xyz"},
            json={"src_lat": 34.1, "src_lon": -118.5, "dest_city": "Tokyo"},
        )
        assert r.status_code == 200


class TestPlannerCities:
    @pytest.mark.parametrize(
        "query,needle",
        [
            ("Simulate a packet to Dubai", "Dubai"),
            ("send packet to New York", "New York"),
            ("Simulate to nyc", "New York"),
            ("packet to Los Angeles", "Los Angeles"),
            ("Simulate a packet to Seoul", "Seoul"),
            ("Simulate a packet to Mumbai", "Mumbai"),
            ("Simulate a packet to Berlin", "Berlin"),
        ],
    )
    def test_heuristic_resolves_atlas_cities(self, client, query, needle):
        # Force heuristic by making planner return null function.
        from api.state import state

        class NullPlanner:
            def parse(self, _q):
                return {"function": None, "params": {}}

        with patch.object(state, "planner", NullPlanner()):
            r = client.post("/api/plan", json={"query": query})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["function"] == "simulate"
        assert needle.lower() in body["destination"].lower()


class TestSessionIsolation:
    def test_sessions_keep_separate_snapshots(self, client):
        r1 = client.post(
            "/api/simulate",
            headers={"X-Session-Id": "sess_alpha"},
            json={"src_lat": 34.16, "src_lon": -118.55, "dest_city": "Tokyo"},
        )
        assert r1.status_code == 200
        r2 = client.post(
            "/api/simulate",
            headers={"X-Session-Id": "sess_beta"},
            json={"src_lat": 34.16, "src_lon": -118.55, "dest_city": "Berlin"},
        )
        assert r2.status_code == 200

        t_a = client.get("/api/topology", headers={"X-Session-Id": "sess_alpha"})
        t_b = client.get("/api/topology", headers={"X-Session-Id": "sess_beta"})
        assert t_a.status_code == 200 and t_b.status_code == 200
        # Destinations differ → gateway node ids differ.
        ids_a = {n["id"] for n in t_a.json()["nodes"]}
        ids_b = {n["id"] for n in t_b.json()["nodes"]}
        assert ids_a != ids_b

    def test_invalid_session_id_rejected(self, client):
        r = client.post(
            "/api/simulate",
            headers={"X-Session-Id": "../evil"},
            json={"src_lat": 34.16, "src_lon": -118.55, "dest_city": "Tokyo"},
        )
        assert r.status_code == 400


class TestInputValidation:
    def test_dest_city_too_long(self, client):
        r = client.post(
            "/api/simulate",
            json={"src_lat": 1, "src_lon": 1, "dest_city": "A" * 101},
        )
        assert r.status_code == 422

    def test_chat_empty_rejected(self, client):
        r = client.post("/api/chat", json={"message": "   "})
        assert r.status_code == 422

    def test_plan_gibberish_rejected(self, client):
        from api.state import state

        class NullPlanner:
            def parse(self, _q):
                return {"function": None, "params": {}}

        with patch.object(state, "planner", NullPlanner()):
            r = client.post("/api/plan", json={"query": "hello world"})
        assert r.status_code == 422

    def test_optimize_without_sim(self, client):
        from api.state import state

        with state.sim_lock:
            state.last_sim.clear()
            state.sim_sessions.clear()
        r = client.post(
            "/api/optimize",
            headers={"X-Session-Id": "fresh_empty"},
            json={"constraints": "x"},
        )
        assert r.status_code == 400


class TestSanitizeAndDemoAI:
    def test_sanitize_strips_injection(self):
        from constellasim.llm import _sanitize

        assert "\x00" not in _sanitize("a\x00b")
        assert "\u202e" not in _sanitize("x\u202e y")

    def test_demo_ai_status_warning_not_false_critical(self):
        from api.ai_fallback import DemoNetworkAI

        ai = DemoNetworkAI()
        prompt = (
            "classify the network health as NOMINAL, WARNING, or CRITICAL\n"
            'Metrics: {"latency_ms": "14.50", "status": "Success", '
            '"packet_loss_pct": 0, "topology": {"dropped": false}}\n'
            "Respond STATUS: ..."
        )
        out = ai.chat([{"role": "user", "content": prompt}])
        assert out.startswith("STATUS: WARNING")
        assert "CRITICAL" not in out.split("—")[0]


class TestExtractCity:
    def test_longest_match_wins(self):
        from api.simulation import extract_city_from_query

        assert extract_city_from_query("fly to New York please") == "New York"
        assert extract_city_from_query("go to Los Angeles now") == "Los Angeles"
        assert extract_city_from_query("nowhere land") is None


class TestNoCommittedSecrets:
    def test_config_has_no_fixed_demo_secret(self, monkeypatch):
        monkeypatch.delenv("CONSTELLASIM_SECRET_KEY", raising=False)
        monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
        from api import config

        s1 = config.get_settings()
        s2 = config.get_settings()
        assert "change-me" not in s1.secret_key
        assert "constellasim-demo-secret" not in s1.secret_key
        # Ephemeral keys differ across calls when unset.
        assert s1.secret_key != s2.secret_key
        assert len(s1.secret_key) >= 32

    def test_env_example_has_no_live_values(self):
        text = open(".env.example", encoding="utf-8").read()
        assert "AIza" not in text
        assert "sk-" not in text
        assert "AKIA" not in text
        # Keys appear only as commented placeholders / empty assignments.
        for line in text.splitlines():
            if "API_KEY" in line or "SECRET" in line:
                assert line.strip().startswith("#") or line.endswith("=") or "false" in line
