"""
Gemini AI client for NutriBudget AI.

Supports the new AQ. API key format (auth keys bound to Google Cloud
service accounts) introduced in 2025. Authentication is done via the
x-goog-api-key header instead of the legacy ?key= query parameter.

Models used:
  - gemini-2.5-flash  → vision (image scanning)  — fast, multimodal
  - gemini-2.5-pro    → text (meal description)   — most accurate

Call strategy:
  Vision : gemini-2.5-flash first, gemini-2.5-pro as fallback
  Text   : gemini-2.5-flash first, gemini-2.5-pro as fallback
"""

import base64
import json
import re
import httpx

from app.core.config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

_VISION_PROMPT = (
    "You are a professional nutrition analyst. Carefully examine this food image. "
    "Identify ALL visible food items (e.g. rice, curry, bread, drinks, sides). "
    "Estimate the TOTAL combined nutritional values for everything visible. "
    "Return ONLY a valid JSON object with exactly these keys — no markdown, no explanation:\n"
    "{\"food_name\": \"<descriptive combined name>\", "
    "\"calories\": <integer kcal>, "
    "\"protein\": <float grams>, "
    "\"carbs\": <float grams>, "
    "\"fat\": <float grams>}"
)

_TEXT_PROMPT_TEMPLATE = (
    "You are a professional nutrition expert with deep knowledge of both Indian and "
    "international cuisines. Estimate the total nutritional content for: '{description}'. "
    "Account for typical portion sizes and cooking methods used in the region. "
    "Return ONLY a valid JSON object with exactly these keys — no markdown, no explanation:\n"
    "{{\"food_name\": \"<clean descriptive name>\", "
    "\"calories\": <integer kcal>, "
    "\"protein\": <float grams>, "
    "\"carbs\": <float grams>, "
    "\"fat\": <float grams>}}"
)

# ─────────────────────────────────────────────────────────────────────────────
# Gemini REST API base
# ─────────────────────────────────────────────────────────────────────────────

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Primary model is pulled from settings at call time;
# if it fails, we escalate to the pro variant automatically.
_FLASH_MODEL = "gemini-2.5-flash"
_PRO_MODEL   = "gemini-2.5-pro"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_mime(filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".png"):  return "image/png"
    if fn.endswith(".webp"): return "image/webp"
    if fn.endswith(".gif"):  return "image/gif"
    return "image/jpeg"


def _extract_json(text: str) -> dict | None:
    """Robustly extract the first JSON object from a Gemini response."""
    # Remove markdown fences if present
    try:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return json.loads(match.group(1))
        return json.loads(text.strip())
    except Exception:
        pass
    try:
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return None


def _gemini_headers() -> dict:
    """
    Build authentication headers for the new AQ. key format.
    The new auth keys (AQ.*) MUST use the x-goog-api-key header.
    Legacy keys (AIza*) also work with this header for backward-compat.
    """
    return {
        "x-goog-api-key": settings.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }


# ─────────────────────────────────────────────────────────────────────────────
# GeminiClient
# ─────────────────────────────────────────────────────────────────────────────

import traceback

class GeminiClient:
    """
    Gemini AI client supporting the new AQ. API key format.

    Uses x-goog-api-key header authentication (required for AQ. keys).
    Automatically falls back from gemini-2.5-flash to gemini-2.5-pro
    on failure for both vision and text tasks.
    """

    # ── Vision: food image → nutrition JSON ──────────────────────────────────

    async def scan_image(self, filename: str, file_bytes: bytes) -> dict:
        """
        Analyse a food image and return nutrition data.
        Tries gemini-2.5-flash first, then gemini-2.5-pro as fallback.
        Returns dict with keys: food_name, calories, protein, carbs, fat
        Raises ValueError / exception if both models fail.
        """
        print(f"[GeminiClient] scan_image started for filename: '{filename}' ({len(file_bytes)} bytes)")
        if not settings.GEMINI_API_KEY:
            print("[GeminiClient] GEMINI_API_KEY is not configured!")
            raise ValueError("GEMINI_API_KEY is not configured in environment settings.")

        mime_type  = _detect_mime(filename)
        base64_img = base64.b64encode(file_bytes).decode("utf-8")

        payload = {
            "contents": [{
                "parts": [
                    {"text": _VISION_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_img,
                        }
                    },
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 512,
                "responseMimeType": "application/json",
            },
        }

        primary = settings.GEMINI_VISION_MODEL
        models  = [primary] if primary == _PRO_MODEL else [primary, _PRO_MODEL]
        
        errors = []
        for model in models:
            print(f"[GeminiClient] Vision: Trying model '{model}'")
            try:
                result = await self._post(model, payload, tag=f"Vision/{model}")
                if result:
                    print(f"[GeminiClient] Vision: Successfully analyzed using '{model}'")
                    return result
            except Exception as e:
                err_msg = f"Model '{model}' failed: {str(e)}"
                print(f"[GeminiClient] {err_msg}")
                errors.append(err_msg)

        raise ValueError(f"Gemini Vision scan failed. Errors: {'; '.join(errors)}")

    # ── Text: meal description → nutrition JSON ───────────────────────────────

    async def parse_description(self, description: str) -> dict:
        """
        Parse a text meal description and return nutrition data.
        Tries gemini-2.5-flash first, then gemini-2.5-pro as fallback.
        Returns dict with keys: food_name, calories, protein, carbs, fat
        Raises ValueError / exception if both models fail.
        """
        print(f"[GeminiClient] parse_description started for: '{description}'")
        if not settings.GEMINI_API_KEY:
            print("[GeminiClient] GEMINI_API_KEY is not configured!")
            raise ValueError("GEMINI_API_KEY is not configured in environment settings.")

        prompt  = _TEXT_PROMPT_TEMPLATE.format(description=description)
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 512,
                "responseMimeType": "application/json",
            },
        }

        primary = settings.GEMINI_TEXT_MODEL
        models  = [primary] if primary == _PRO_MODEL else [primary, _PRO_MODEL]
        
        errors = []
        for model in models:
            print(f"[GeminiClient] Text: Trying model '{model}'")
            try:
                result = await self._post(model, payload, tag=f"Text/{model}")
                if result:
                    print(f"[GeminiClient] Text: Successfully parsed using '{model}'")
                    return result
            except Exception as e:
                err_msg = f"Model '{model}' failed: {str(e)}"
                print(f"[GeminiClient] {err_msg}")
                errors.append(err_msg)

        raise ValueError(f"Gemini Text parse failed. Errors: {'; '.join(errors)}")

    # ── Private: POST to Gemini generateContent ───────────────────────────────

    async def _post(self, model: str, payload: dict, tag: str) -> dict:
        url = f"{_BASE_URL}/{model}:generateContent"
        print(f"[GeminiClient/{tag}] Sending request to Gemini REST API...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=_gemini_headers(),
                    timeout=30.0,
                )
                print(f"[GeminiClient/{tag}] Received response status: {response.status_code}")
                
                if response.status_code == 200:
                    res_data = response.json()
                    candidates = res_data.get("candidates", [])
                    if not candidates:
                        raise ValueError(f"Gemini API returned no candidates. Full response: {res_data}")
                        
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if not parts:
                        raise ValueError(f"Gemini candidate returned no parts. Full response: {res_data}")
                        
                    text = parts[0].get("text", "")
                    if not text:
                        raise ValueError(f"Gemini part text is empty. Full response: {res_data}")
                        
                    parsed = _extract_json(text)
                    if parsed and "food_name" in parsed and "calories" in parsed:
                        print(f"[Gemini/{tag}] ✓ {parsed['food_name']} ({parsed['calories']} kcal)")
                        return parsed
                    else:
                        raise ValueError(f"Failed to extract valid nutrition JSON from model text. Raw text: '{text}'")
                else:
                    error_text = response.text
                    print(f"[GeminiClient/{tag}] Error Response HTTP {response.status_code}: {error_text}")
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", error_text)
                        raise ValueError(f"Gemini API error (HTTP {response.status_code}): {error_msg}")
                    except Exception:
                        raise ValueError(f"Gemini API error (HTTP {response.status_code}): {error_text}")
                        
        except Exception as e:
            if not isinstance(e, ValueError):
                tb = traceback.format_exc()
                print(f"[GeminiClient/{tag}] Request Exception traceback:\n{tb}")
                raise ValueError(f"Connection/Request error: {str(e)}") from e
            raise e
