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

# Security: pattern to strip ASCII control characters and Unicode bidirectional
# overrides that can be used for prompt injection.
_CONTROL_CHARS_RE = re.compile(
    r'[\x00-\x1f\x7f\u200b-\u200d\u202a-\u202e\u2066-\u2069]'
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
        if not self.kb_path.startswith(_project_root):
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
                kb_content += f.read() + "\n"
            if len(kb_content) >= _MAX_KB_CHARS:
                break
        return kb_content[:_MAX_KB_CHARS]

    def _get_kb_context(self):
        return self._kb_cache

    def _init_clients(self):
        """Initialize AI clients once at startup for connection reuse."""
        if self.provider == "azure":
            from openai import AzureOpenAI
            self._azure_client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version="2024-02-15-preview",
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
        elif self.provider == "amazon":
            import boto3
            self._amazon_client = boto3.client("bedrock-runtime", region_name="us-east-1")
        elif self.provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
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
