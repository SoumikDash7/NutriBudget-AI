"""
Qwen2.5-VL client for food image understanding.

Call order:
  1. HuggingFace / Novita provider  (Qwen2.5-VL-7B-Instruct)
  2. HuggingFace / Nebius provider  (same model, second HF router)
  3. Local Ollama endpoint           (qwen2.5vl:7b) when running locally
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

_VISION_PROMPT = (
    "You are a professional nutrition analyst. Carefully examine this food image. "
    "Identify ALL visible food items (e.g. rice, curry, bread, drinks). "
    "Estimate the TOTAL combined nutrition for everything on the plate or in the image. "
    "Return ONLY a valid JSON object with exactly these keys -- no markdown, no extra text:\n"
    "{\"food_name\": \"<descriptive combined name>\", "
    "\"calories\": <integer kcal>, "
    "\"protein\": <float grams>, "
    "\"carbs\": <float grams>, "
    "\"fat\": <float grams>}"
)


class QwenVLClient(NutritionProvider):
    name = "QwenVL"
    supports_vision = True

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(1.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True
    )
    async def _post_with_retry(self, http_client: httpx.AsyncClient, url: str, payload: dict, headers: dict | None = None) -> httpx.Response:
        return await http_client.post(url, json=payload, headers=headers, timeout=30.0)

    async def extract(self, food_input: FoodInput, http_client: httpx.AsyncClient) -> NutritionEstimate:
        base64_img = food_input.image_base64
        if not base64_img:
            raise ProviderAPIError("QwenVL vision extractor requires image base64 data.")

        mime_type = detect_mime(food_input.filename or "image.jpg")
        logger.info("extract image with QwenVLClient")
        errors = []

        if settings.HUGGINGFACE_API_KEY:
            try:
                result = await self._call_hf(mime_type, base64_img, http_client)
                if result:
                    return result
            except Exception as e:
                errors.append(f"HF Error: {e}")
                logger.warning(f"HuggingFace providers failed: {e}")
        else:
            logger.warning("HUGGINGFACE_API_KEY not set -- skipping HF, going directly to Ollama")

        try:
            result = await self._call_ollama(mime_type, base64_img, http_client)
            if result:
                return result
        except Exception as e:
            errors.append(f"Ollama Error: {e}")
            logger.warning(f"Ollama local fallback failed: {e}")

        raise ProviderAPIError(f"QwenVLClient failed to scan image. Details: {'; '.join(errors)}")

    async def _call_hf(self, mime_type: str, base64_img: str, http_client: httpx.AsyncClient) -> NutritionEstimate | None:
        providers = [
            ("novita", "https://router.huggingface.co/novita/v1/chat/completions"),
            ("nebius", "https://router.huggingface.co/nebius/v1/chat/completions"),
        ]
        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "Qwen/Qwen2.5-VL-7B-Instruct",
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_img}"}},
                {"type": "text", "text": _VISION_PROMPT},
            ]}],
            "max_tokens": 256,
            "temperature": 0.1,
        }
        for provider_name, url in providers:
            logger.debug(f"HF/{provider_name}: POST -> {url}")
            try:
                response = await self._post_with_retry(http_client, url, payload, headers)
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    parsed = extract_json(text)
                    required = {"food_name", "calories", "protein", "carbs", "fat"}
                    if parsed and required.issubset(parsed.keys()):
                        logger.info(f"HF/{provider_name}: ok {parsed['food_name']} ({parsed['calories']} kcal)")
                        return NutritionEstimate(
                            ingredients=[ExtractedIngredient(name=parsed["food_name"], quantity=1.0, unit="serving")],
                            calories=float(parsed["calories"]),
                            protein_g=float(parsed["protein"]),
                            carbs_g=float(parsed["carbs"]),
                            fat_g=float(parsed["fat"]),
                            confidence=0.95,
                            source_provider=f"QwenVL ({provider_name})"
                        )
                    else:
                        logger.warning(f"HF/{provider_name}: JSON extraction failed. Raw: '{text[:200]}'")
                else:
                    logger.warning(f"HF/{provider_name}: HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"HF/{provider_name}: request failed -- {e}", exc_info=True)
        return None

    async def _call_ollama(self, mime_type: str, base64_img: str, http_client: httpx.AsyncClient) -> NutritionEstimate | None:
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        logger.debug(f"Ollama: POST -> {url}  model={settings.OLLAMA_VISION_MODEL}")
        payload = {
            "model": settings.OLLAMA_VISION_MODEL,
            "messages": [{"role": "user", "content": _VISION_PROMPT, "images": [base64_img]}],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        try:
            response = await self._post_with_retry(http_client, url, payload)
            if response.status_code == 200:
                data = response.json()
                text = data.get("message", {}).get("content", "")
                parsed = extract_json(text)
                required = {"food_name", "calories", "protein", "carbs", "fat"}
                if parsed and required.issubset(parsed.keys()):
                    logger.info(f"Ollama: ok {parsed['food_name']} ({parsed['calories']} kcal)")
                    return NutritionEstimate(
                        ingredients=[ExtractedIngredient(name=parsed["food_name"], quantity=1.0, unit="serving")],
                        calories=float(parsed["calories"]),
                        protein_g=float(parsed["protein"]),
                        carbs_g=float(parsed["carbs"]),
                        fat_g=float(parsed["fat"]),
                        confidence=0.95,
                        source_provider="Ollama (Local QwenVL)"
                    )
                else:
                    logger.warning(f"Ollama: JSON extraction failed. Raw: '{text[:200]}'")
            else:
                logger.warning(f"Ollama: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Ollama: request failed -- {e}", exc_info=True)
        return None
