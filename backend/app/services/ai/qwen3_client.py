"""
Qwen3 client for text-based meal description parsing.

Model: Qwen/Qwen3-8B (default) - configurable via QWEN3_MODEL env var.
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.nutrition import FoodInput, NutritionEstimate, ExtractedIngredient
from app.services.ai.base import NutritionProvider
from app.services.ai.utils import extract_json
from app.services.ai.exceptions import ProviderAPIError, ParsingError

logger = get_logger(__name__)

_PARSE_PROMPT_TEMPLATE = """
Analyze this meal description:

{description}

You are a nutrition API.

Your task is to estimate the total nutrition.

Rules:

- Return ONLY valid JSON.
- No markdown.
- No explanations.
- No reasoning.
- No <think> tags.
- No code blocks.
- No extra text.

JSON schema:

{{
    "food_name": "string",
    "calories": integer,
    "protein": float,
    "carbs": float,
    "fat": float
}}
"""


class Qwen3Client(NutritionProvider):
    """
    Qwen3 text meal parser via HuggingFace Inference API.
    Conforms to the NutritionProvider protocol.
    """
    name = "Qwen3"
    supports_vision = False

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(1.0),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True
    )
    async def _post_with_retry(self, http_client: httpx.AsyncClient, url: str, payload: dict, headers: dict) -> httpx.Response:
        return await http_client.post(url, json=payload, headers=headers, timeout=15.0)

    async def extract(self, food_input: FoodInput, http_client: httpx.AsyncClient) -> NutritionEstimate:
        """
        Extract nutrition data from a text description using Qwen3.
        """
        if not settings.HUGGINGFACE_API_KEY:
            raise ProviderAPIError("HUGGINGFACE_API_KEY is not configured.")

        description = food_input.text
        if not description:
            raise ProviderAPIError("Qwen3 text extractor requires a text description.")

        model = settings.QWEN3_MODEL
        logger.info(f"parse_description: '{description}'  model={model}")

        headers = {
            "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
            "Content-Type": "application/json",
        }
        prompt  = _PARSE_PROMPT_TEMPLATE.format(description=description)
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a nutrition API. "
                        "Return ONLY valid JSON. "
                        "No markdown. "
                        "No explanations. "
                        "No <think>. "
                        "No code fences."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.1,
            "max_tokens": 256,
        }

        # Try providers in order of verification
        providers = [
            ("featherless-ai", "https://router.huggingface.co/featherless-ai/v1/chat/completions"),
            ("nscale",         "https://router.huggingface.co/nscale/v1/chat/completions"),
        ]

        errors = []
        for provider_name, url in providers:
            logger.debug(f"HF/{provider_name}: POST > {url}")
            try:
                response = await self._post_with_retry(http_client, url, payload, headers)
                http_status = response.status_code
                logger.debug(f"HF/{provider_name}: Response HTTP {http_status}")

                if http_status == 200:
                    data = response.json()
                    choices = data.get("choices")
                    if not choices:
                        logger.warning(f"HF/{provider_name}: No choices returned.")
                        continue

                    message = choices[0].get("message", {})
                    text = message.get("content")
                    if text is None:
                        logger.warning(f"HF/{provider_name}: Empty content returned.")
                        continue

                    parsed = extract_json(text)
                    required = {"food_name", "calories", "protein", "carbs", "fat"}

                    if parsed and required.issubset(parsed.keys()):
                        logger.info(f"OK HF/{provider_name} Parsed: {parsed['food_name']} ({parsed['calories']} kcal)")
                        
                        return NutritionEstimate(
                            ingredients=[
                                ExtractedIngredient(
                                    name=parsed["food_name"],
                                    quantity=1.0,
                                    unit="serving"
                                )
                            ],
                            calories=float(parsed["calories"]),
                            protein_g=float(parsed["protein"]),
                            carbs_g=float(parsed["carbs"]),
                            fat_g=float(parsed["fat"]),
                            confidence=0.96,
                            source_provider=f"Qwen3 ({provider_name})"
                        )
                    else:
                        logger.warning(
                            "HF/%s returned invalid JSON Schema or format.",
                            provider_name,
                        )
                else:
                    logger.warning(f"HF/{provider_name}: HTTP {http_status} - {response.text[:200]}")
                    errors.append(f"HTTP {http_status} from {provider_name}")

            except Exception as e:
                logger.error(f"HF/{provider_name} request failed: {e}", exc_info=True)
                errors.append(f"Request failed for {provider_name}: {e}")

        # If all HF routers fail, raise error
        raise ProviderAPIError(f"Qwen3 client failed across HF routers. Details: {'; '.join(errors)}")
