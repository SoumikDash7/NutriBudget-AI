"""
Qwen2.5-VL client for food image understanding.

Call order:
  1. HuggingFace / Novita provider  (Qwen2.5-VL-7B-Instruct)
  2. HuggingFace / Nebius provider  (same model, second HF router)
  3. Local Ollama endpoint           (qwen2.5vl:7b) when running locally
"""

import base64
import json
import re
import httpx

from app.core.config import settings

# Nutrition extraction prompt — deterministic, JSON-only output
_VISION_PROMPT = (
    "You are a professional nutrition analyst. Carefully examine this food image. "
    "Identify ALL visible food items (e.g. rice, curry, bread, drinks). "
    "Estimate the TOTAL combined nutrition for everything on the plate or in the image. "
    "Return ONLY a valid JSON object with exactly these keys — no markdown, no extra text:\n"
    "{\"food_name\": \"<descriptive combined name>\", "
    "\"calories\": <integer kcal>, "
    "\"protein\": <float grams>, "
    "\"carbs\": <float grams>, "
    "\"fat\": <float grams>}"
)


def _detect_mime(filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".png"):
        return "image/png"
    if fn.endswith(".webp"):
        return "image/webp"
    if fn.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def _extract_json(text: str) -> dict | None:
    """Robustly extract the first JSON object from a model response."""
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


class QwenVLClient:
    """
    Qwen2.5-VL image understanding client.

    Call order:
      1. HuggingFace Inference API  (requires HUGGINGFACE_API_KEY)
      2. Local Ollama endpoint       (requires Ollama running locally)
    """

    async def scan_image(
        self,
        filename: str,
        file_bytes: bytes,
    ) -> dict | None:
        """
        Returns a dict with keys: food_name, calories, protein, carbs, fat
        or None if both providers fail.
        """
        mime_type = _detect_mime(filename)
        base64_img = base64.b64encode(file_bytes).decode("utf-8")

        # ── 1. HuggingFace Inference API ──────────────────────────────────
        if settings.HUGGINGFACE_API_KEY:
            result = await self._call_hf(mime_type, base64_img)
            if result:
                return result

        # ── 2. Local Ollama fallback ───────────────────────────────────────
        result = await self._call_ollama(mime_type, base64_img)
        return result

    # ─────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────

    async def _call_hf(self, mime_type: str, base64_img: str) -> dict | None:
        """
        HuggingFace router for Qwen2.5-VL-7B-Instruct.
        Tries 'novita' provider first, then 'nebius' as secondary.
        Both support multimodal vision — hf-inference does NOT.
        """
        providers = [
            ("novita",  "https://router.huggingface.co/novita/v1/chat/completions"),
            ("nebius",  "https://router.huggingface.co/nebius/v1/chat/completions"),
        ]
        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "Qwen/Qwen2.5-VL-7B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_img}"
                            },
                        },
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }
            ],
            "max_tokens": 256,
            "temperature": 0.1,
        }
        for provider_name, url in providers:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                    if response.status_code == 200:
                        data = response.json()
                        text = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                        )
                        parsed = _extract_json(text)
                        if parsed and "food_name" in parsed and "calories" in parsed:
                            print(f"[QwenVL/{provider_name}] Identified: {parsed['food_name']} ({parsed['calories']} kcal)")
                            return parsed
                    else:
                        print(f"[QwenVL/{provider_name}] HTTP {response.status_code}: {response.text[:200]}")
            except Exception as e:
                print(f"[QwenVL/{provider_name}] Request failed: {e}")
        return None

    async def _call_ollama(self, mime_type: str, base64_img: str) -> dict | None:
        """
        Local Ollama multimodal endpoint — no API key required.
        Run: ollama pull qwen2.5vl:7b
        """
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": settings.OLLAMA_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": _VISION_PROMPT,
                    "images": [base64_img],
                }
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("message", {}).get("content", "")
                    parsed = _extract_json(text)
                    if parsed and "food_name" in parsed and "calories" in parsed:
                        print(f"[QwenVL/Ollama] Identified: {parsed['food_name']} ({parsed['calories']} kcal)")
                        return parsed
                else:
                    print(f"[QwenVL/Ollama] HTTP {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"[QwenVL/Ollama] Request failed (is Ollama running?): {e}")
        return None
