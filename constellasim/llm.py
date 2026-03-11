import os
import json
from dotenv import load_dotenv

load_dotenv()

class NetworkAI:
    """AI Assistant for analyzing LEO network topology and performance simulation reports."""
    
    def __init__(self, provider=None):
        self.provider = provider or os.getenv("NETWORK_AI_PROVIDER", "google").lower()

    def analyze_report(self, sim_report):
        """Asks the AI to analyze the simulation report and suggest improvements."""
        full_prompt = f"Analyze this LEO Satellite Network Simulation Report. What is the bottleneck? Suggest topology changes to reduce latency or packet loss.\nReport: {sim_report}"

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
            model=os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4"),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _call_amazon(self, prompt):
        import boto3
        client = boto3.client("bedrock-runtime", region_name="us-east-1")
        body = json.dumps({
            "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
            "max_tokens_to_sample": 500
        })
        response = client.invoke_model(body=body, modelId="anthropic.claude-v2")
        return json.loads(response.get("body").read())["completion"]

    def _call_google(self, prompt):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
