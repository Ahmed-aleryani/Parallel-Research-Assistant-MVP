from __future__ import annotations

import os
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential

from .schemas import TaskModel

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional at import time
    genai = None  # type: ignore


SYSTEM_DECOMPOSE = (
    "You are an expert task planner and orchestrator. "
    "Given a single user prompt, produce a small list of 1-3 atomic tasks that can run in parallel. "
    "Return only concise task titles and objectives with constraints that help web research."
)

SYSTEM_SUMMARIZE = (
    "You are an executive assistant. Summarize the combined research into a short, actionable plan. "
    "Prefer clarity, bullet points, and include short rationale."
)


class GeminiClient:
    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash-002")
        if genai is None:
            raise RuntimeError("google-generativeai is not installed. Please install requirements.")
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self.model.generate_content([
            {"role": "user", "parts": [system_prompt + "\n\n" + user_prompt]},
        ])
        return response.text or ""

    def decompose(self, user_prompt: str) -> List[dict]:
        schema_hint = (
            "Return JSON list with objects: {title, objective, constraints (array of short strings)}. "
            "Max 3 tasks."
        )
        raw = self._generate(SYSTEM_DECOMPOSE, f"{schema_hint}\n\nUSER PROMPT:\n{user_prompt}")
        # Be tolerant to minor JSON issues
        import json
        import re
        text = raw.strip()
        text = re.sub(r"```json|```", "", text)
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "tasks" in data:
                data = data["tasks"]
            assert isinstance(data, list)
            return data[:3]
        except Exception:
            # Fallback to single generic task
            return [
                {
                    "title": "Research and compile results",
                    "objective": user_prompt,
                    "constraints": ["Use reputable sources", "Include 3+ citations"],
                }
            ]

    def summarize(self, combined_markdown: str) -> str:
        prompt = (
            "Summarize the following task results into an actionable plan with citations at the end.\n\n"
            f"{combined_markdown}"
        )
        return self._generate(SYSTEM_SUMMARIZE, prompt)
