import os
import re
import json
import glob
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Optimization: cap total KB content to prevent runaway token costs and memory use.
_MAX_KB_CHARS = 50_000

# Security: pattern to strip ASCII control characters, Unicode bidirectional overrides,
# line/paragraph separators, soft hyphen, BOM, and LRM/RLM marks — all usable for
# prompt injection or token-boundary manipulation.
_CONTROL_CHARS_RE = re.compile(
    r'[\x00-\x1f\x7f\u00ad\u200b-\u200f\u202a-\u202e\u2028\u2029\u2066-\u2069\ufeff]'
)

def _sanitize(text):
    """Strip control characters and bidirectional overrides from any string."""
    return _CONTROL_CHARS_RE.sub(' ', str(text)).strip()


class NetworkAI:
    """RAG-Enabled AI Assistant for Analyzing LEO Network Topology."""

    def __init__(self, provider=None):
        self.provider = provider or os.getenv("NETWORK_AI_PROVIDER", "google").lower()
        self.kb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'knowledge_base'))
        # Security: use if/raise instead of assert — assert is compiled away with python -O.
        _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        # M-5: append os.sep to prevent the same prefix-bypass as the calculator path check.
        if not self.kb_path.startswith(_project_root + os.sep):
            raise ValueError(f"kb_path '{self.kb_path}' resolves outside project directory")
        # Optimization: load KB once at startup; re-reading every request wastes I/O and tokens.
        self._kb_cache = self._load_kb()
        # Optimization: build AI clients once to reuse HTTP sessions across requests.
        self._azure_client = None
        self._amazon_client = None
        self._google_model = None
        self._init_clients()

    def _load_kb(self):
        """Load and cache all knowledge base documents, capped at _MAX_KB_CHARS."""
        kb_content = ""
        for file_path in glob.glob(os.path.join(self.kb_path, "*.txt")):
            # Security: resolve symlinks and verify each file stays within kb_path.
            resolved = os.path.realpath(file_path)
            if not resolved.startswith(os.path.realpath(self.kb_path)):
                continue
            with open(resolved, 'r') as f:
                kb_content += f"\n--- Document: {os.path.basename(file_path)} ---\n"
                # H-1: sanitize KB file content to prevent prompt injection via
                # a compromised or maliciously crafted knowledge base file.
                kb_content += _sanitize(f.read()) + "\n"
            if len(kb_content) >= _MAX_KB_CHARS:
                break
        return kb_content[:_MAX_KB_CHARS]

    def _get_kb_context(self):
        return self._kb_cache

    def _init_clients(self):
        """Initialize AI clients once at startup for connection reuse."""
        # V-05: validate required secrets at boot so misconfigured deployments fail fast.
        if self.provider == "azure":
            key = os.getenv("AZURE_OPENAI_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if not key or not endpoint:
                raise RuntimeError("AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT must be set for azure provider")
            from openai import AzureOpenAI
            self._azure_client = AzureOpenAI(
                api_key=key,
                api_version="2024-02-15-preview",
                azure_endpoint=endpoint
            )
        elif self.provider == "amazon":
            # H-2/H-3: validate AWS credentials at boot; make region configurable.
            import boto3
            region = os.getenv("AWS_REGION", "us-east-1")
            try:
                boto3.client("sts", region_name=region).get_caller_identity()
            except Exception as exc:
                raise RuntimeError("AWS credentials are not configured or invalid for amazon provider") from exc
            self._amazon_client = boto3.client("bedrock-runtime", region_name=region)
        elif self.provider == "google":
            key = os.getenv("GOOGLE_API_KEY")
            if not key:
                raise RuntimeError("GOOGLE_API_KEY must be set for google provider")
            import google.generativeai as genai
            genai.configure(api_key=key)
            self._google_model = genai.GenerativeModel('gemini-1.5-flash')

    def analyze_report(self, sim_report):
        """Asks the AI to analyze the simulation report GROUNDED in network standards."""
        kb_context = self._get_kb_context()
        # Security: strip all control characters to prevent prompt injection.
        # sim_report embeds user-supplied dest_city (hashed in node ID but present in report).
        safe_report = _sanitize(sim_report)

        system_instructions = (
            "You are a Satellite Network Architect.\n"
            "Use the provided LEO Networking Performance Standards to evaluate the simulation report.\n"
            "Critique the latency, packet loss, and buffer utilization based on the technical standards."
        )

        full_prompt = (
            f"{system_instructions}\n\n"
            f"--- NETWORK STANDARDS CONTEXT ---\n{kb_context}\n"
            f"--- SIMULATION REPORT ---\n{safe_report}\n\n"
            "TASK: Provide a grounded technical critique and suggest topology optimizations."
        )

        if self.provider == "azure":
            return self._call_azure(full_prompt)
        elif self.provider == "amazon":
            return self._call_amazon(full_prompt)
        elif self.provider == "google":
            return self._call_google(full_prompt)
        else:
            return "AI Provider not configured correctly."

    def _call_azure(self, prompt):
        response = self._azure_client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4-turbo"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _call_amazon(self, prompt):
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}]
        })
        response = self._amazon_client.invoke_model(body=body, modelId="anthropic.claude-3-sonnet-20240229-v1:0")
        return json.loads(response.get("body").read())["content"][0]["text"]

    def _call_google(self, prompt):
        response = self._google_model.generate_content(prompt)
        return response.text

    # --- Feature 1: Streaming ---

    def analyze_report_stream(self, sim_report):
        """Yields token chunks for streaming AI analysis via SSE."""
        kb_context = self._get_kb_context()
        safe_report = _sanitize(sim_report)

        system_instructions = (
            "You are a Satellite Network Architect.\n"
            "Use the provided LEO Networking Performance Standards to evaluate the simulation report.\n"
            "Critique the latency, packet loss, and buffer utilization based on the technical standards."
        )
        full_prompt = (
            f"{system_instructions}\n\n"
            f"--- NETWORK STANDARDS CONTEXT ---\n{kb_context}\n"
            f"--- SIMULATION REPORT ---\n{safe_report}\n\n"
            "TASK: Provide a grounded technical critique and suggest topology optimizations."
        )

        if self.provider == "azure":
            yield from self._stream_azure(full_prompt)
        elif self.provider == "amazon":
            yield from self._stream_amazon(full_prompt)
        elif self.provider == "google":
            yield from self._stream_google(full_prompt)

    def _stream_google(self, prompt):
        response = self._google_model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def _stream_azure(self, prompt):
        stream = self._azure_client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4-turbo"),
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _stream_amazon(self, prompt):
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        })
        response = self._amazon_client.invoke_model_with_response_stream(
            body=body, modelId="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk.get("type") == "content_block_delta":
                yield chunk.get("delta", {}).get("text", "")

    # --- Feature 2: Multi-Turn Chat ---

    def chat(self, messages):
        """Multi-turn conversation. messages is a list of {role, content} dicts."""
        if self.provider == "azure":
            return self._chat_azure(messages)
        elif self.provider == "amazon":
            return self._chat_amazon(messages)
        elif self.provider == "google":
            return self._chat_google(messages)
        else:
            return "AI Provider not configured correctly."

    def _chat_azure(self, messages):
        response = self._azure_client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4-turbo"),
            messages=messages,
        )
        return response.choices[0].message.content

    def _chat_amazon(self, messages):
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_msgs = [m for m in messages if m["role"] != "system"]
        body_dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": user_msgs,
        }
        if system_parts:
            body_dict["system"] = " ".join(system_parts)
        body = json.dumps(body_dict)
        response = self._amazon_client.invoke_model(
            body=body, modelId="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        return json.loads(response.get("body").read())["content"][0]["text"]

    def _chat_google(self, messages):
        """Convert OpenAI-format messages to Gemini chat format."""
        system_content = ""
        gemini_history = []
        for m in messages:
            if m["role"] == "system":
                system_content += m["content"] + "\n"
            elif m["role"] == "user":
                content = (system_content + m["content"]) if system_content else m["content"]
                system_content = ""
                gemini_history.append({"role": "user", "parts": [content]})
            elif m["role"] == "assistant":
                gemini_history.append({"role": "model", "parts": [m["content"]]})

        if not gemini_history:
            return "No messages provided."

        last_msg = gemini_history[-1]["parts"][0]
        history = gemini_history[:-1]
        chat_session = self._google_model.start_chat(history=history)
        return chat_session.send_message(last_msg).text

    # --- Feature 5: Network Briefing ---

    def generate_briefing(self, data):
        """Generate a structured Markdown network briefing report."""
        kb_context = self._get_kb_context()
        safe_data = _sanitize(json.dumps(data))

        system_instructions = (
            "You are a Satellite Network Architect. Generate a structured network briefing "
            "in GitHub-Flavored Markdown with tables and headers. Include these sections:\n"
            "# Network Topology\n# Simulation Results\n# Performance Analysis\n"
            "# Topology Optimisation Recommendations\n"
            "Use the technical standards context to ground your assessment."
        )
        full_prompt = (
            f"{system_instructions}\n\n"
            f"--- NETWORK STANDARDS CONTEXT ---\n{kb_context}\n"
            f"--- SIMULATION DATA ---\n{safe_data}\n\n"
            "Generate the complete network briefing report in Markdown format."
        )

        if self.provider == "azure":
            return self._call_azure(full_prompt)
        elif self.provider == "amazon":
            return self._call_amazon(full_prompt)
        elif self.provider == "google":
            return self._call_google(full_prompt)
        else:
            return "# Network Briefing\n\nAI Provider not configured correctly."
