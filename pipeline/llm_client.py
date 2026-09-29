import json
import re
import time
import google.generativeai as genai
from typing import Dict, Any, List
from core.config import settings

class LLMClient:
    """Wraps the Gemini API with structured JSON output and multi-key quota failover."""
    def __init__(self, model_name: str = None):
        primary = model_name or getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")
        candidates = [primary, "gemini-1.5-flash-lite", "gemini-1.5-flash", "gemini-2.0-flash"]
        self.candidate_models = list(dict.fromkeys(candidates))

    def _get_api_keys(self) -> List[str]:
        keys = []
        if getattr(settings, "GEMINI_API_KEY", None):
            k1 = settings.GEMINI_API_KEY.strip()
            if k1:
                keys.append(k1)
        if getattr(settings, "GEMINI_API_KEY_2", None):
            k2 = settings.GEMINI_API_KEY_2.strip()
            if k2 and k2 not in keys:
                keys.append(k2)
        if getattr(settings, "GEMINI_API_KEY_SECONDARY", None):
            ks = settings.GEMINI_API_KEY_SECONDARY.strip()
            if ks and ks not in keys:
                keys.append(ks)
        return keys

    def _is_quota_error(self, err: Exception) -> bool:
        err_str = str(err).lower()
        quota_keywords = [
            "429",
            "resource_exhausted",
            "resourceexhausted",
            "quota",
            "rate limit",
            "too many requests",
            "limit reached",
            "exceeded your current quota"
        ]
        return any(keyword in err_str for keyword in quota_keywords)

    def _call_model(self, model_name: str, prompt: str) -> Dict[str, Any]:
        model = genai.GenerativeModel(model_name)
        # Attempt 1: Direct JSON response mime-type
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            raw = response.text.strip()
            return json.loads(raw)
        except Exception:
            # Attempt 2: Standard generation with regex extraction
            response = model.generate_content(prompt)
            raw = response.text.strip()
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                return json.loads(match.group(0))
            return {"translation": raw, "detected_language": "Auto", "detected_code": "auto"}

    def generate_translation(self, prompt: str) -> Dict[str, Any]:
        api_keys = self._get_api_keys()
        if not api_keys:
            return {
                "translation": "No Gemini API key configured. Please set GEMINI_API_KEY in your .env file.",
                "detected_language": "Unknown",
                "detected_code": "unknown",
                "error": "Missing API Key"
            }

        last_error = None
        quota_exceeded_count = 0

        for key_idx, api_key in enumerate(api_keys):
            genai.configure(api_key=api_key)
            key_success = False

            for model_name in self.candidate_models:
                try:
                    result = self._call_model(model_name, prompt)
                    if result and result.get("translation"):
                        return result
                except Exception as e:
                    last_error = e
                    if self._is_quota_error(e):
                        quota_exceeded_count += 1
                        print(f"API Key #{key_idx + 1} quota/rate limit exceeded: {e}")
                    else:
                        print(f"API Key #{key_idx + 1} with model {model_name} failed: {e}")
                    break
            
            print(f"API Key #{key_idx + 1} unavailable/exhausted. Attempting next API key if available...")

        print(f"All available API keys failed. Last error: {last_error}")
        
        # If all keys failed due to quota/rate limit
        if quota_exceeded_count >= len(api_keys) or (last_error and self._is_quota_error(last_error)):
            user_msg = "Quota limit reached for all available API keys. Please try again later."
        else:
            user_msg = "Translation service encountered an error. Please try again later."

        return {
            "translation": user_msg,
            "detected_language": "Unknown",
            "detected_code": "unknown",
            "error": str(last_error) if last_error else user_msg
        }