"""
Groq Llama client for text + vision nutrition analysis.

Models: 
- llama-3.2-11b-vision-preview (for vision tasks)
- llama-3.3-70b-versatile (for text-only tasks)
Implements the NutritionProvider protocol.
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.nutrition import FoodInput, NutritionEstimate, ExtractedIngredient
from app.services.ai.base import NutritionProvider
from app.services.ai.utils import extract_json, detect_mime
from app.services.ai.exceptions import ProviderAPIError

logger = get_logger(__name__)

_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
_SYSTEM_PROMPT = "Return ONLY valid JSON. No markdown. No explanations. No reasoning blocks."

_USER_PROMPT_TEMPLATE = (
    "You are a professional nutrition analyst. Analyze this meal description: '{description}'. "
    "Estimate the TOTAL combined nutrition. Return ONLY a valid JSON object with "
    "exactly these keys — no markdown, no extra text:\n"
    '{{"food_name": "<descriptive combined name>", '
    '"calories": <integer kcal>, '
    '"protein": <float grams>, '
    '"carbs": <float grams>, '
    '"fat": <float grams>}}'
)

_VISION_PROMPT_TEMPLATE = (
    "You are a professional nutrition analyst. {context_instruction} "
    "Estimate the TOTAL combined nutrition. Return ONLY a valid JSON object with "
    "exactly these keys — no markdown, no extra text:\n"
    '{{"food_name": "<descriptive combined name>", '
    '"calories": <integer kcal>, '
    '"protein": <float grams>, '
    '"carbs": <float grams>, '
    '"fat": <float grams>}}'
)


class GroqLlamaClient(NutritionProvider):
    name = "Groq Llama"
    supports_vision = True

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(1.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True
    )
    async def _post_with_retry(self, http_client: httpx.AsyncClient, payload: dict, headers: dict) -> httpx.Response:
        return await http_client.post(_BASE_URL, json=payload, headers=headers, timeout=15.0)

    async def extract(self, food_input: FoodInput, http_client: httpx.AsyncClient) -> NutritionEstimate:
        if not settings.GROQ_API_KEY:
            raise ProviderAPIError("GROQ_API_KEY is not set — Groq client unavailable.")

        model = settings.GROQ_LLAMA_TEXT_MODEL
        if food_input.image_base64:
            model = settings.GROQ_LLAMA_VISION_MODEL
            mime_type = detect_mime(food_input.filename or "image.jpg")
            context_instruction = "Carefully examine this food image and identify ALL visible food items."
            content = [
                {"type": "text", "text": _VISION_PROMPT_TEMPLATE.format(context_instruction=context_instruction)},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{food_input.image_base64}"}},
            ]
            messages = [{"role": "user", "content": content}]
        elif food_input.text:
            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(description=food_input.text)},
            ]
        else:
            raise ProviderAPIError("GroqLlamaClient requires either image_base64 or text in FoodInput.")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 256,
        }
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        logger.debug(f"Groq Llama: POST -> {_BASE_URL}  model={model}")
        try:
            response = await self._post_with_retry(http_client, payload, headers)
        except httpx.TimeoutException as e:
            raise ProviderAPIError(f"Groq request timed out: {e}")
        except httpx.RequestError as e:
            raise ProviderAPIError(f"Groq network error: {e}")

        if response.status_code == 429:
            raise ProviderAPIError("Groq free tier rate limit hit (HTTP 429).")
        if response.status_code != 200:
            raise ProviderAPIError(
                f"Groq call failed: HTTP {response.status_code} — {response.text[:200]}"
            )

        choices = response.json().get("choices", [])
        if not choices:
            raise ProviderAPIError("Groq returned empty choices list.")

        raw_text = choices[0].get("message", {}).get("content", "")
        parsed = extract_json(raw_text)

        required = {"food_name", "calories", "protein", "carbs", "fat"}
        if not parsed or not required.issubset(parsed.keys()):
            raise ProviderAPIError(
                f"Groq returned unparseable/incomplete JSON. Raw: '{raw_text[:200]}'"
            )

        logger.info(f"Groq Llama: ✓ {parsed['food_name']} ({parsed['calories']} kcal)")
        return NutritionEstimate(
            ingredients=[ExtractedIngredient(name=parsed["food_name"], quantity=1.0, unit="serving")],
            calories=float(parsed["calories"]),
            protein_g=float(parsed["protein"]),
            carbs_g=float(parsed["carbs"]),
            fat_g=float(parsed["fat"]),
            confidence=0.80,
            source_provider="Groq Llama",
        )