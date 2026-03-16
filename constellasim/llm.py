import os
import json
import glob
from dotenv import load_dotenv

load_dotenv()

class NetworkAI:
    """RAG-Enabled AI Assistant for Analyzing LEO Network Topology."""
    
    def __init__(self, provider=None):
        self.provider = provider or os.getenv("NETWORK_AI_PROVIDER", "google").lower()
        # Optimization: normalize path to avoid traversal ambiguity with '..' components.
        self.kb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'knowledge_base'))

    def _get_kb_context(self):
        """Retrieves and consolidates all network standards from the knowledge base."""
        kb_content = ""
        for file in glob.glob(os.path.join(self.kb_path, "*.txt")):
            with open(file, 'r') as f:
                kb_content += f"\n--- Document: {os.path.basename(file)} ---\n"
                kb_content += f.read() + "\n"
        return kb_content

    def analyze_report(self, sim_report):
        """Asks the AI to analyze the simulation report GROUNDED in network standards."""
        kb_context = self._get_kb_context()
        
        system_instructions = (
            "You are a Satellite Network Architect.\n"
            "Use the provided LEO Networking Performance Standards to evaluate the simulation report.\n"
            "Critique the latency, packet loss, and buffer utilization based on the technical standards."
        )
        
        full_prompt = (
            f"{system_instructions}\n\n"
            f"--- NETWORK STANDARDS CONTEXT ---\n{kb_context}\n"
            f"--- SIMULATION REPORT ---\n{sim_report}\n\n"
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
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        response = client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4-turbo"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _call_amazon(self, prompt):
        import boto3
        client = boto3.client("bedrock-runtime", region_name="us-east-1")
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}]
        })
        response = client.invoke_model(body=body, modelId="anthropic.claude-3-sonnet-20240229-v1:0")
        return json.loads(response.get("body").read())["content"][0]["text"]

    def _call_google(self, prompt):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
