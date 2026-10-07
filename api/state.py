"""Shared runtime state for the API process."""

from __future__ import annotations

import threading
from typing import Any, Optional

from constellasim.llm import NetworkAI
from constellasim.monitor import AnomalyMonitor
from constellasim.planner import NetworkPlanner
from constellasim.utils import Geocoder

from api.ai_fallback import DemoNetworkAI
from api.config import Settings, get_settings


class AppState:
    def __init__(self) -> None:
        self.settings: Settings = get_settings()
        self.geocoder = Geocoder()
        self.sim_semaphore = threading.Semaphore(self.settings.max_concurrent_sims)
        # Process-wide fallback snapshot (legacy / monitor source).
        self.last_sim: dict[str, Any] = {}
        # Per-client simulation snapshots keyed by session id.
        self.sim_sessions: dict[str, dict[str, Any]] = {}
        self.sim_lock = threading.Lock()
        self.chat_sessions: dict[str, list[dict[str, str]]] = {}
        self.chat_lock = threading.Lock()
        self.ai: Optional[NetworkAI | DemoNetworkAI] = None
        self.ai_mode = "offline"
        self.planner: Optional[NetworkPlanner] = None
        self.monitor: Optional[AnomalyMonitor] = None

    def boot_ai(self) -> None:
        try:
            self.ai = NetworkAI()
            self.ai_mode = getattr(self.ai, "provider", "live")
        except Exception:
            self.ai = DemoNetworkAI()
            self.ai_mode = "demo"
        self.planner = NetworkPlanner(self.ai)

        if self.settings.anomaly_monitor and self.ai is not None:
            self.monitor = AnomalyMonitor(self.ai)
            self.monitor.set_sim_source(self.last_sim, self.sim_lock)
            self.monitor.start()

    def get_sim(self, session_id: str | None = None) -> dict[str, Any]:
        sid = (session_id or "").strip()
        with self.sim_lock:
            if sid and sid in self.sim_sessions:
                return dict(self.sim_sessions[sid])
            return dict(self.last_sim)

    def put_sim(self, snapshot: dict[str, Any], session_id: str | None = None) -> None:
        sid = (session_id or "").strip()
        with self.sim_lock:
            self.last_sim.clear()
            self.last_sim.update(snapshot)
            if sid:
                self.sim_sessions[sid] = dict(snapshot)
                # Cap session map to avoid unbounded growth in long-lived demos.
                if len(self.sim_sessions) > 200:
                    oldest = next(iter(self.sim_sessions))
                    self.sim_sessions.pop(oldest, None)


state = AppState()
