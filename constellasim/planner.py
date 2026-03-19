"""Feature 3: Natural Language Network Planner (NL2Function) for ConstellaSim."""

import json
import re
import logging

logger = logging.getLogger(__name__)

# Strict allowlist — only these function names may be executed.
_ALLOWED_FUNCTIONS = {"simulate", "topology_info"}

_FUNCTION_SCHEMAS = {
    "simulate": {
        "description": "Simulate a packet from the user's current GPS location to a destination city.",
        "params": {
            "dest_city": "string — destination city name, e.g. 'Berlin'",
            "src_city": "string (optional) — override source city instead of using live GPS",
        },
    },
    "topology_info": {
        "description": "Describe the current constellation topology or explain how changing satellite count affects performance.",
        "params": {
            "sat_count": "integer (optional) — number of satellites to consider",
        },
    },
}

_SYSTEM_PROMPT = (
    "You are a satellite network planning assistant. "
    "Parse the user's natural language request and return ONLY a JSON object "
    "with two keys: \"function\" (one of the available function names) and \"params\" "
    "(an object with the required parameters). "
    "Do not include any explanation or markdown — only raw JSON.\n\n"
    "Available functions:\n"
    + json.dumps(_FUNCTION_SCHEMAS, indent=2)
    + "\n\nIf you cannot map the request to any function, return: "
    "{\"function\": null, \"params\": {}}"
)


class NetworkPlanner:
    """Parse plain-English network commands into executable function calls."""

    def __init__(self, ai_client):
        self._ai = ai_client

    def parse(self, user_text):
        """
        Returns dict: {"function": str|None, "params": dict}
        Validates the function name against the allowlist before returning.
        """
        if not user_text or not user_text.strip():
            return {"function": None, "params": {}}

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_text.strip()[:500]},
        ]

        try:
            raw = self._ai.chat(messages)
            parsed = self._extract_json(raw)
        except Exception:
            logger.exception("NetworkPlanner LLM call failed")
            return {"function": None, "params": {}}

        func_name = parsed.get("function")
        params = parsed.get("params", {})

        if func_name not in _ALLOWED_FUNCTIONS:
            return {"function": None, "params": {}}

        if not isinstance(params, dict):
            return {"function": None, "params": {}}

        return {"function": func_name, "params": params}

    @staticmethod
    def _extract_json(text):
        """Extract JSON from LLM response even if surrounded by markdown fences."""
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"function": None, "params": {}}
