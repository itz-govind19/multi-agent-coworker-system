import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.db.repository import update_heartbeat, log_event

class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

    def ping(self, status: str = "IDLE", current_task_id: Optional[str] = None, details: str = ""):
        """Pings heartbeat table."""
        update_heartbeat(self.name, self.role, status, current_task_id, details)

    def log(self, project_id: Optional[str], message: str, level: str = "INFO"):
        """Logs an event into SQLite."""
        log_event(project_id, self.name, message, level)

    def call_llm(self, prompt: str, json_mode: bool = False, project_id: Optional[str] = None) -> str:
        """Invokes Gemini model with automatic retry and model fallback."""
        if not self.client:
            return "MOCK_RESPONSE: GEMINI_API_KEY is not configured in .env"

        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt,
            temperature=0.2,
        )
        if json_mode:
            config.response_mime_type = "application/json"

        # List of valid models to try in sequence if one has high demand (503)
        candidate_models = [GEMINI_MODEL, "gemini-2.0-flash", "gemini-1.5-flash"]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        last_error = None
        for model_name in candidate_models:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config,
                    )
                    return response.text.strip()
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    # If 503 high demand or 429 rate limit, pause briefly and retry
                    if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                        import time
                        time.sleep(2 * (attempt + 1))
                        continue
                    else:
                        break  # Break attempt loop to try next candidate model

        err_msg = f"LLM Call Error: {str(last_error)}"
        self.log(project_id, err_msg, level="ERROR")
        return f'{{"error": "{err_msg}"}}' if json_mode else err_msg
