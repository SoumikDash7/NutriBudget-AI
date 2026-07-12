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
from app.services.ai.utils import extract_json, build_text_prompt, parse_nutrition_response
from app.services.ai.exceptions import ProviderAPIError, ParsingError

logger = get_logger(__name__)

_DEFAULT_CONFIDENCE = 0.96


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
        prompt = build_text_prompt(description)
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert food analyzer. "
                        "Your job is to identify and extract ingredients, quantities, and units from the meal description. "
                        "You must NOT calculate calories, protein, carbohydrates, fat, fiber, sugar, or sodium. "
                        "Return ONLY valid JSON matching the requested schema. No markdown. No explanations."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\n"
                        "Guidelines:\n"
                        "- Extract all distinct ingredients.\n"
                        "- Do not estimate nutrition values or calculate calories/macros.\n"
                        "\n/no_think"
                    ),
                },
            ],
            "temperature": 0.0,
            "max_tokens": 2048,
            "chat_template_kwargs": {
                "enable_thinking": False
            },
        }        # Try providers in order of verification
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
                    reasoning = message.get("reasoning_content")
                    finish_reason = choices[0].get("finish_reason")

                    if not text:
                        if reasoning:
                            # Some reasoning-model routers put the model's thinking (and
                            # sometimes the whole answer) into a separate reasoning_content
                            # field instead of content. Fall back to it rather than treating
                            # this as a hard failure.
                            logger.warning(
                                f"HF/{provider_name}: content field empty but "
                                f"reasoning_content present (finish_reason={finish_reason}) - "
                                f"model likely returned its answer on a separate reasoning "
                                f"channel. Attempting to extract JSON from reasoning_content."
                            )
                            text = reasoning
                        else:
                            logger.warning(
                                f"HF/{provider_name}: Empty content returned "
                                f"(finish_reason={finish_reason})."
                            )
                            continue

                    if finish_reason == "length":
                        logger.warning(
                            f"HF/{provider_name}: response was truncated by max_tokens "
                            f"(finish_reason=length) - the model may not have finished "
                            f"writing its JSON. Consider raising max_tokens further."
                        )

                    # ---------------- DEBUG ----------------#
                    logger.debug("=" * 80)
                    logger.debug("HF/%s RAW MODEL OUTPUT:", provider_name)
                    logger.debug("%s", text)
                    logger.debug("=" * 80)
                    # ---------------------------------------#

                    raw_parsed = extract_json(text)
                    logger.info("RAW MODEL OUTPUT:\n%s", text)
                    logger.debug("Extracted JSON:\n%s", raw_parsed)

                    normalized = parse_nutrition_response(raw_parsed)

                    if normalized:
                        ingredient_names = ", ".join(i["name"] for i in normalized["ingredients"])
                        logger.info(
                            f"OK HF/{provider_name} Parsed: [{ingredient_names}] "
                            f"({normalized['calories']} kcal total)"
                        )

                        confidence = normalized["confidence"] if normalized["confidence"] is not None else _DEFAULT_CONFIDENCE

                        return NutritionEstimate(
                            ingredients=[
                                ExtractedIngredient(
                                    name=ing["name"],
                                    quantity=ing["quantity"],
                                    unit=ing["unit"],
                                )
                                for ing in normalized["ingredients"]
                            ],
                            calories=normalized["calories"],
                            protein_g=normalized["protein"],
                            carbs_g=normalized["carbs"],
                            fat_g=normalized["fat"],
                            confidence=confidence,
                            source_provider=f"Qwen3 ({provider_name})"
                        )
                    else:
                        logger.warning(
                            "HF/%s invalid/unusable schema (finish_reason=%s).\nExtracted=%s",
                            provider_name,
                            finish_reason,
                            raw_parsed,
                        )
                else:
                    logger.warning(f"HF/{provider_name}: HTTP {http_status} - {response.text[:200]}")
                    errors.append(f"HTTP {http_status} from {provider_name}")

            except Exception as e:
                logger.error(f"HF/{provider_name} request failed: {e}", exc_info=True)
                errors.append(f"Request failed for {provider_name}: {e}")

        # If all HF routers fail, raise error
        raise ProviderAPIError(f"Qwen3 client failed across HF routers. Details: {'; '.join(errors)}")