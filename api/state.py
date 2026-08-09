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
        self.last_sim: dict[str, Any] = {}
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


state = AppState()
