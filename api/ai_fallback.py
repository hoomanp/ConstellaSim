"""Deterministic demo AI used when cloud provider keys are absent."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable


class DemoNetworkAI:
    """Recruiter-friendly offline analyst that still feels live."""

    provider = "demo"

    def analyze_report(self, sim_report: str) -> str:
        return "".join(self.analyze_report_stream(sim_report))

    def analyze_report_stream(self, sim_report: str) -> Iterable[str]:
        latency = self._extract_float(r"Average End-to-End Latency:\s*([0-9.]+)", sim_report)
        loss = self._extract_float(r"Packet Loss Rate:\s*([0-9.]+)", sim_report) or 0.0
        chunks = [
            "Orbital mesh critique (demo mode): ",
            f"end-to-end latency is {latency:.2f} ms across the linear ISL chain. "
            if latency is not None
            else "no successful delivery — packet was dropped under buffer pressure. ",
            f"Observed loss {loss:.1f}%. ",
            "Against LEO targets (<50 ms regional hops, <1% loss), ",
            "prefer denser ISL meshes and earlier ground handovers. ",
            "Next: add a cross-plane relay and raise buffer_limit on SAT2.",
        ]
        for c in chunks:
            yield c

    def chat(self, messages: list[dict[str, str]]) -> str:
        last = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        # Support AnomalyMonitor STATUS: prompts in offline demos.
        if "NOMINAL|WARNING|CRITICAL" in last or "classify the network health" in last.lower():
            lowered = last.lower()
            if (
                '"status": "failed"' in lowered
                or '"packet_loss_pct": 100' in lowered
                or '"dropped": true' in lowered
            ):
                return (
                    "STATUS: CRITICAL — Packet delivery failed; "
                    "path loss or buffer overflow exceeded LEO demo thresholds."
                )
            try:
                import re

                m = re.search(r'"latency_ms":\s*"([0-9.]+)"', last)
                if m and float(m.group(1)) > 12:
                    return (
                        f"STATUS: WARNING — End-to-end latency {m.group(1)} ms "
                        "exceeds the 12 ms demo threshold for this mesh."
                    )
            except Exception:
                pass
            return "STATUS: NOMINAL — Metrics within LEO demo thresholds for this session."

        return (
            "Demo Mission Assistant: I can discuss latency, loss, and topology trade-offs "
            f"for this session. You asked: “{last[:160]}”. "
            "In a live deployment this reply is grounded in the knowledge_base RAG corpus."
        )

    def optimize_topology(self, sim_data: dict[str, Any], constraints: str = "") -> dict[str, Any]:
        goal = constraints.strip() or "minimize end-to-end latency"
        dropped = str(sim_data.get("latency_ms", "")).lower() == "dropped"
        score = 42 if dropped else 78
        return {
            "recommendations": [
                {
                    "change": "Add cross-plane ISL between SAT1 and SAT3",
                    "expected_impact": "Removes one hop and cuts ~5 ms of ISL delay",
                    "priority": "HIGH",
                },
                {
                    "change": "Raise SAT2 buffer_limit from 100 → 250 packets",
                    "expected_impact": "Reduces tail-drop under bursty uplink",
                    "priority": "MEDIUM",
                },
                {
                    "change": "Schedule earlier GSL handover before elevation falls below 20°",
                    "expected_impact": "Stabilizes CNR and reduces session resets",
                    "priority": "MEDIUM",
                },
            ],
            "rationale": (
                f"Demo optimizer targeting “{goal}”. "
                "Recommendations mirror typical LEO mesh hardening steps from the knowledge base."
            ),
            "health_score": score,
        }

    def generate_briefing(self, sim_data: dict[str, Any]) -> str:
        return (
            "# ConstellaSim Network Briefing (Demo)\n\n"
            f"- Source: {sim_data.get('source', 'n/a')}\n"
            f"- Destination: {sim_data.get('destination', 'n/a')}\n"
            f"- Latency: {sim_data.get('latency_ms', 'n/a')}\n"
            f"- Status: {sim_data.get('status', 'n/a')}\n\n"
            "This briefing is generated offline for recruiter demos. "
            "With a provider key configured, content is RAG-grounded in `knowledge_base/`.\n"
        )

    @staticmethod
    def _extract_float(pattern: str, text: str) -> float | None:
        m = re.search(pattern, text or "")
        if not m:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None
