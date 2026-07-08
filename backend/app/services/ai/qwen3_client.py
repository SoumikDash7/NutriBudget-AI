"""
Qwen3 client for text-based meal description parsing.

Model: Qwen/Qwen3-8B (default) — configurable via QWEN3_MODEL env var.
Upgrade path: set QWEN3_MODEL=Qwen/Qwen3-30B-A3B for higher accuracy.

Uses the /v1/chat/completions endpoint on HuggingFace Inference API.
"""

import json
import re
import httpx

from app.core.config import settings

_PARSE_PROMPT_TEMPLATE = (
    "You are a professional nutrition expert with deep knowledge of both Indian and international cuisines. "
    "Estimate the total nutritional content for the following food description: '{description}'. "
    "Account for typical portion sizes and cooking methods. "
    "Return ONLY a valid JSON object with exactly these keys — no markdown, no explanation:\n"
    "{{\"food_name\": \"<clean descriptive name>\", "
    "\"calories\": <integer kcal>, "
    "\"protein\": <float grams>, "
    "\"carbs\": <float grams>, "
    "\"fat\": <float grams>}}"
)


def _extract_json(text: str) -> dict | None:
    """Robustly extract the first JSON object from a Qwen3 response."""
    # Strip <think>...</think> reasoning blocks that Qwen3 may emit
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
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


class Qwen3Client:
    """
    Qwen3 text meal parser via HuggingFace Inference API.
    Returns None if the API key is not configured or the call fails.
    """

    async def parse_description(self, description: str) -> dict | None:
        """
        Returns a dict with keys: food_name, calories, protein, carbs, fat
        or None if parsing fails.
        """
        if not settings.HUGGINGFACE_API_KEY:
            return None

        url = f"https://router.huggingface.co/hf-inference/models/{settings.QWEN3_MODEL}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json",
        }
        prompt = _PARSE_PROMPT_TEMPLATE.format(description=description)
        payload = {
            "model": settings.QWEN3_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 256,
            "temperature": 0.1,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    text = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    parsed = _extract_json(text)
                    if parsed and "food_name" in parsed and "calories" in parsed:
                        print(f"[Qwen3] Parsed: {parsed['food_name']} ({parsed['calories']} kcal)")
                        return parsed
                else:
                    print(f"[Qwen3] HTTP {response.status_code}: {response.text[:200]}")
        except Exception as e:
            print(f"[Qwen3] Request failed: {e}")
        return None
