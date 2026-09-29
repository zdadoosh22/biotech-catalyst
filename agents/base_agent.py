"""Base agent class supporting Google Gemini API with fallback to deterministic heuristic engines.
"""

import os
import json
from typing import Optional, Dict, Any
from core.config import GEMINI_API_KEY


class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.api_key = GEMINI_API_KEY
        self.model = None
        self._init_llm()

    def _init_llm(self) -> None:
        if not self.api_key:
            return
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config={"response_mime_type": "application/json"}
            )
        except Exception:
            self.model = None

    def call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Invokes Gemini LLM and attempts to parse structured JSON response."""
        if not self.model:
            return None

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            # Clean markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())
        except Exception:
            return None
