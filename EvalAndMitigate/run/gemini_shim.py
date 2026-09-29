"""Drop-in for the notebooks' `openai_client.chat.completions.create(...)`, backed by Vertex AI Gemini."""
import os, time
from types import SimpleNamespace as NS
from google import genai
from google.genai import types


class GeminiChat:
    def __init__(self, **_):
        self.client = genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],
                                   location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"))
        self.model = os.environ.get("GEN_MODEL", "gemini-2.5-flash")
        # 0 = non-thinking ("Gemini 2.5 Flash" row in the paper); -1 = dynamic ("Flash (Reason)")
        self.thinking_budget = int(os.environ.get("THINKING_BUDGET", "0"))
        self.api_key = "vertex"
        self.chat = NS(completions=NS(create=self.create))

    def create(self, messages, temperature=None, max_tokens=None, **_):
        cfg = types.GenerateContentConfig(
            temperature=temperature, max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget))
        for attempt in range(8):
            try:
                r = self.client.models.generate_content(model=self.model, contents=messages[-1]["content"], config=cfg)
                if not r.text:
                    raise RuntimeError(f"empty response: {r.candidates[0].finish_reason if r.candidates else r.prompt_feedback}")
                break
            except Exception as e:
                if attempt == 7:
                    raise
                print(f"gemini retry {attempt + 1}: {e}")
                time.sleep(min(60, 2 ** attempt * 2))
        thoughts = r.usage_metadata.thoughts_token_count or 0
        return NS(choices=[NS(message=NS(content=r.text))], usage=NS(completion_tokens_details=NS(reasoning_tokens=thoughts)))
