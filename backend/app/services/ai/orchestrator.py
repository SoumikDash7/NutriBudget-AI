import time
import hashlib
from typing import List
import httpx
from app.core.logging import get_logger
from app.schemas.nutrition import FoodInput, NutritionEstimate
from app.services.ai.base import NutritionProvider
from app.services.ai.exceptions import AIOrchestrationError
from app.core.caching import InMemoryTTLCache

logger = get_logger(__name__)


class AIOrchestrator:
    """
    Orchestrates the tiered fallback sequence for food analysis.
    Logs latency and details of provider failures/successes.
    caches results in-memory using InMemoryTTLCache.
    """

    def __init__(
        self,
        qwen_vl: NutritionProvider,
        qwen3: NutritionProvider,
        gemma: NutritionProvider,
        groq: NutritionProvider,
        usda: NutritionProvider,
    ):
        self.qwen_vl = qwen_vl
        self.qwen3 = qwen3
        self.gemma = gemma
        self.groq = groq
        self.usda = usda
        self.cache = InMemoryTTLCache(default_ttl_seconds=86400)

    async def parse_image(self, image_base64: str, http_client: httpx.AsyncClient, filename: str | None = None) -> NutritionEstimate:
        """
        Multimodal image scanner fallback flow:
        Qwen VL -> Gemma (OpenRouter) -> Groq
        """
        cache_key = hashlib.sha256(image_base64.encode("utf-8")).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            logger.info("Orchestrator: Image scan cache hit!")
            return cached

        food_input = FoodInput(input_type="image", image_base64=image_base64, filename=filename)
        chain = [self.qwen_vl, self.gemma, self.groq]
        result = await self._execute_chain(food_input, chain, http_client)
        self.cache.set(cache_key, result)
        return result

    async def parse_text(self, text: str, http_client: httpx.AsyncClient) -> NutritionEstimate:
        """
        Text description parsing fallback flow:
        Qwen3 -> Gemma (OpenRouter) -> Groq -> USDA Lookup
        """
        cache_key = hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Orchestrator: Text parse cache hit for '{text}'")
            return cached

        food_input = FoodInput(input_type="text", text=text)
        chain = [self.qwen3, self.gemma, self.groq, self.usda]
        result = await self._execute_chain(food_input, chain, http_client)
        self.cache.set(cache_key, result)
        return result

    async def _execute_chain(
        self,
        food_input: FoodInput,
        chain: List[NutritionProvider],
        http_client: httpx.AsyncClient,
    ) -> NutritionEstimate:
        errors = []
        is_image = food_input.image_base64 is not None
        input_label = "image" if is_image else f"'{food_input.text}'"

        for provider in chain:
            start_time = time.perf_counter()
            logger.info(f"Orchestrator calling provider '{provider.name}' for {input_label}")
            try:
                result = await provider.extract(food_input, http_client)
                latency = (time.perf_counter() - start_time) * 1000
                logger.info(
                    f"OK Provider '{provider.name}' succeeded in {latency:.1f}ms for {input_label}"
                )
                return result
            except Exception as e:
                latency = (time.perf_counter() - start_time) * 1000
                err_msg = f"Provider '{provider.name}' failed after {latency:.1f}ms: {e}"
                logger.warning(err_msg)
                errors.append(err_msg)

        raise AIOrchestrationError(
            f"All fallback providers failed for {input_label}. Details: {' | '.join(errors)}"
        )
