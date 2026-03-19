"""Feature 4: AI Anomaly Monitor for ConstellaSim.

Runs a background daemon thread that periodically evaluates the latest simulation
snapshot and writes anomaly alerts to an in-memory deque. Enable with:

    ANOMALY_MONITOR=true

in the environment.
"""

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Thresholds for triggering anomaly evaluation
_PACKET_LOSS_PCT_HIGH = 20.0
_LATENCY_MS_HIGH = 30.0

_MONITOR_INTERVAL_SECONDS = 30

_SHORT_PROMPT = (
    "You are a satellite network monitor. Given the following simulation metrics, "
    "classify the network health as NOMINAL, WARNING, or CRITICAL "
    "and explain why in exactly one sentence.\n\n"
    "Metrics: {metrics}\n\n"
    "Respond in this exact format:\n"
    "STATUS: <NOMINAL|WARNING|CRITICAL> — <one-sentence explanation>"
)


class AnomalyMonitor:
    """Background thread that evaluates simulation stats and emits timestamped alerts."""

    def __init__(self, ai_client):
        self._ai = ai_client
        self._alerts = deque(maxlen=20)
        self._lock = threading.Lock()
        self._sim_ref = None
        self._sim_lock = None
        self._running = False
        self._thread = None

    def set_sim_source(self, sim_dict, sim_lock):
        """Register the module-level simulation result dict and its lock."""
        self._sim_ref = sim_dict
        self._sim_lock = sim_lock

    def start(self):
        """Start the background monitoring thread (daemon=True)."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="AnomalyMonitor")
        self._thread.start()
        logger.info("AnomalyMonitor started")

    def get_alerts(self):
        """Return a snapshot of current alerts as a list (newest first)."""
        with self._lock:
            return list(reversed(self._alerts))

    def _run(self):
        while self._running:
            try:
                self._evaluate()
            except Exception:
                logger.exception("AnomalyMonitor evaluation error")
            time.sleep(_MONITOR_INTERVAL_SECONDS)

    def _evaluate(self):
        if self._sim_ref is None or self._sim_lock is None:
            return

        with self._sim_lock:
            snapshot = dict(self._sim_ref)

        if not snapshot:
            return

        if not self._thresholds_triggered(snapshot):
            return

        metrics_str = json.dumps(snapshot)
        prompt_text = _SHORT_PROMPT.format(metrics=metrics_str)

        try:
            messages = [{"role": "user", "content": prompt_text}]
            response = self._ai.chat(messages)
        except Exception:
            logger.exception("AnomalyMonitor LLM call failed")
            return

        status, explanation = self._parse_response(response)
        if status in ("WARNING", "CRITICAL"):
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "message": explanation,
                "sim_snapshot": snapshot,
            }
            with self._lock:
                self._alerts.append(alert)
            logger.warning("Network anomaly: %s — %s", status, explanation)

    def _thresholds_triggered(self, snapshot):
        """Return True if any metric exceeds a threshold warranting LLM evaluation."""
        try:
            loss_pct = float(snapshot.get("packet_loss_pct", 0))
            if loss_pct > _PACKET_LOSS_PCT_HIGH:
                return True
        except (ValueError, TypeError):
            pass
        try:
            lat_ms = float(str(snapshot.get("latency_ms", "0")).replace(" ms", ""))
            if lat_ms > _LATENCY_MS_HIGH:
                return True
        except (ValueError, TypeError):
            pass
        if snapshot.get("status") == "Failed":
            return True
        return False

    @staticmethod
    def _parse_response(text):
        """Extract STATUS and explanation from the LLM response."""
        for line in text.splitlines():
            if line.startswith("STATUS:"):
                parts = line[len("STATUS:"):].strip().split("—", 1)
                status = parts[0].strip().upper()
                explanation = parts[1].strip() if len(parts) > 1 else line
                return status, explanation
        return "UNKNOWN", text.strip()
