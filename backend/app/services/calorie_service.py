"""
CalorieService - orchestrates the full AI-powered nutrition pipeline.

Image scan call order:
  1. Qwen2.5-VL via HuggingFace / Ollama (primary vision)
  2. Gemma via OpenRouter                 (first fallback)
  3. Groq Llama Vision                    (second fallback)
  4. Filename heuristic                   (last resort)

Text parse call order:
  1. Qwen3 via HuggingFace         (primary)
  2. Gemma via OpenRouter          (first fallback)
  3. Groq Llama                    (second fallback)
  4. USDA FoodData Central API     (third fallback)
  5. Indian + International local food DB
  6. Open Food Facts search
"""

import re
import base64
import difflib
import httpx
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

import hashlib
from app.core.config import settings
from app.core.logging import get_logger
from app.models.calorie import CalorieLog
from app.repositories.calorie_repository import CalorieRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.ai.qwen_vl_client import QwenVLClient
from app.services.ai.qwen3_client import Qwen3Client
from app.services.ai.gemma_client import GemmaClient
from app.services.ai.groq_llama_client import GroqLlamaClient
from app.services.ai.usda_client import USDAClient
from app.services.ai.orchestrator import AIOrchestrator

from app.core.caching import InMemoryTTLCache
from app.services.calculators.food_nutrition.engine import NutritionEngine
from app.services.calculators.food_nutrition.databases import (
    IndianNutritionProvider,
    OpenFoodFactsProvider,
    DeterministicFallbackProvider,
)
from app.services.calculators.food_nutrition.providers.usda import USDANutritionProvider
from app.services.calculators.food_nutrition.models import Ingredient as DomainIngredient
from app.services.calculators.food_nutrition.converter import QuantityConverter

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Open Food Facts client (barcode + fallback search)
# ─────────────────────────────────────────────────────────────────────────────

class OpenFoodFactsClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self._client = http_client
        self._log = get_logger(f"{__name__}.OpenFoodFacts")

    async def lookup_barcode(self, barcode: str) -> dict | None:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        self._log.debug(f"Barcode lookup: {barcode}")
        try:
            response = await self._client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == 1:
                    result = self._parse_product(data.get("product", {}))
                    if result:
                        self._log.info(f"Barcode {barcode}: OK {result['food_name']}")
                    else:
                        self._log.warning(f"Barcode {barcode}: product found but no nutritional data")
                    return result
                else:
                    self._log.warning(f"Barcode {barcode}: product not found (status={data.get('status')})")
            else:
                self._log.warning(f"Barcode {barcode}: HTTP {response.status_code}")
        except Exception as e:
            self._log.error(f"Barcode lookup failed: {e}", exc_info=True)
        return None

    async def search_products(self, query: str) -> list[dict]:
        url = (
            f"https://world.openfoodfacts.org/cgi/search.pl"
            f"?search_terms={query}&search_simple=1&action=process&json=1"
        )
        self._log.debug(f"Product search: '{query}'")
        try:
            response = await self._client.get(url, timeout=5.0)
            if response.status_code == 200:
                data    = response.json()
                results = []
                for p in data.get("products", [])[:5]:
                    parsed = self._parse_product(p)
                    if parsed:
                        results.append(parsed)
                self._log.info(f"Product search '{query}': found {len(results)} usable result(s)")
                return results
            else:
                self._log.warning(f"Search HTTP {response.status_code}")
        except Exception as e:
            self._log.error(f"Product search failed: {e}", exc_info=True)
        return []

    def _parse_product(self, product: dict) -> dict | None:
        name = (
            product.get("product_name")
            or product.get("generic_name")
            or "Unknown Product"
        )
        nutriments = product.get("nutriments", {})
        calories   = nutriments.get("energy-kcal_100g")
        if calories is None:
            energy_kj = nutriments.get("energy_100g", 0)
            calories  = int(energy_kj / 4.184)
        else:
            calories = int(calories)
        protein = round(float(nutriments.get("proteins_100g", 0.0)), 1)
        carbs   = round(float(nutriments.get("carbohydrates_100g", 0.0)), 1)
        fat     = round(float(nutriments.get("fat_100g", 0.0)), 1)
        return {
            "food_name": name,
            "calories":  calories,
            "protein":   protein,
            "carbs":     carbs,
            "fat":       fat,
        }


from app.services.calculators.food_nutrition.constants import _LOCAL_FOOD_DB


class _FallbackOFFClient:
    async def lookup_barcode(self, barcode: str) -> dict | None:
        async with httpx.AsyncClient() as client:
            off = OpenFoodFactsClient(client)
            return await off.lookup_barcode(barcode)

    async def search_products(self, query: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            off = OpenFoodFactsClient(client)
            return await off.search_products(query)


_orchestrator_cache = None

def _build_orchestrator() -> AIOrchestrator:
    global _orchestrator_cache
    if _orchestrator_cache is None:
        _orchestrator_cache = AIOrchestrator(
            qwen_vl=QwenVLClient(),
            qwen3=Qwen3Client(),
            gemma=GemmaClient(),
            groq=GroqLlamaClient(),
            usda=USDAClient()
        )
    return _orchestrator_cache


# Units that indicate the leading number is a WEIGHT/VOLUME amount, not a
# serving-count multiplier (e.g. "250 g chicken" vs "2 rotis").
# A number followed by one of these should never be used to multiply
# nutrition totals - the amount is already baked into the description that
# gets sent to the AI (and, for the Local DB fallback, into the per-keyword
# reference value's own label, e.g. "Chicken Breast (100g)").
_WEIGHT_UNIT_PATTERN = re.compile(
    r"^(g|gm|gms|gram|grams|kg|kgs|kilogram|kilograms|"
    r"ml|mls|millilitre|millilitres|milliliter|milliliters|"
    r"l|litre|litres|liter|liters|oz|ounce|ounces|lb|lbs|pound|pounds)\b"
)


class CalorieService:

    def __init__(self, db: AsyncSession, http_client: httpx.AsyncClient | None = None):
        self.repo         = CalorieRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.http_client  = http_client
        # OpenFoodFacts uses the same shared client (falls back to per-request only if client not injected)
        self.off_client   = OpenFoodFactsClient(http_client) if http_client else _FallbackOFFClient()
        self.orchestrator = _build_orchestrator()
        
        client = http_client if http_client is not None else httpx.AsyncClient()
        self.engine = NutritionEngine(
            providers=[
                USDANutritionProvider(client),
                IndianNutritionProvider(),
                OpenFoodFactsProvider(client),
                DeterministicFallbackProvider(),
            ]
        )
        self.ingredients_cache = InMemoryTTLCache(default_ttl_seconds=86400)

    # ── Food Logging ──────────────────────────────────────────────────────

    async def log_food(
        self,
        user_id: UUID,
        food_name: str,
        calories: int,
        protein: float,
        carbs: float,
        fat: float,
        logged_date: date,
    ) -> CalorieLog:
        logger.debug(f"log_food: user={user_id}  '{food_name}'  {calories} kcal  date={logged_date}")

        log = CalorieLog(
            user_id=user_id,
            food_name=food_name,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            logged_date=logged_date,
        )
        created = await self.repo.create_log(log)
        logger.info(f"Food logged: '{food_name}'  {calories} kcal  (user={user_id})")
        return created

    # ── Dashboard ─────────────────────────────────────────────────────────

    async def get_dashboard(self, user_id: UUID) -> dict:
        logger.debug(f"get_dashboard: user={user_id}")

        profile         = await self.profile_repo.get_by_user_id(user_id)
        target_calories = profile.daily_calorie_target if profile else 2000
        target_protein  = profile.daily_protein_target  if profile else 150.0
        target_carbs    = profile.daily_carb_target     if profile else 225.0
        target_fat      = profile.daily_fat_target      if profile else 65.0

        if not profile:
            logger.warning(f"get_dashboard: no profile found for user={user_id} - using defaults")

        today      = date.today()
        today_logs = await self.repo.get_logs_for_date(user_id, today)

        consumed_calories = sum(l.calories for l in today_logs)
        consumed_protein  = sum(l.protein  for l in today_logs)
        consumed_carbs    = sum(l.carbs    for l in today_logs)
        consumed_fat      = sum(l.fat      for l in today_logs)

        logger.debug(
            f"Dashboard today: {consumed_calories}/{target_calories} kcal  "
            f"({len(today_logs)} log entries)"
        )

        past_logs    = await self.repo.get_logs_past_days(user_id, days=7)
        history_map  = {today - timedelta(days=i): 0 for i in range(7)}
        for log in past_logs:
            if log.logged_date in history_map:
                history_map[log.logged_date] += log.calories

        history_list = [
            {"date": d.isoformat(), "calories": cal}
            for d, cal in sorted(history_map.items())
        ]

        return {
            "target_calories":    target_calories,
            "consumed_calories":  consumed_calories,
            "remaining_calories": max(0, target_calories - consumed_calories),
            "target_protein":     target_protein,
            "consumed_protein":   consumed_protein,
            "target_carbs":       target_carbs,
            "consumed_carbs":     consumed_carbs,
            "target_fat":         target_fat,
            "consumed_fat":       consumed_fat,
            "logs":               today_logs,
            "history_7_days":     history_list,
        }

    # ── Text Meal Parser ──────────────────────────────────────────────────

    async def parse_description(self, description: str) -> dict:
        """
        Parse a text food description through a tiered AI pipeline.

        Pipeline:
          1. AIOrchestrator text chain (Qwen3 -> Gemma -> Groq -> USDA)
          2. Local DB (Indian + international) - offline database lookup fallback
          3. Open Food Facts search - product lookup fallback
        """
        logger.info(f"parse_description: '{description}'")
        desc_lower = description.lower().strip()

        # Leading integer, used ONLY by the Local DB fallback below.
        quantity  = 1
        num_match = re.match(r"^(\d+)\s+(.+)$", desc_lower)
        if num_match and not _WEIGHT_UNIT_PATTERN.match(num_match.group(2)):
            quantity   = int(num_match.group(1))
            food_query = num_match.group(2)
        else:
            food_query = desc_lower

        ai_ingredients = None
        confidence = 0.90

        # ── 1. AI Orchestrator ──
        if self.http_client:
            sanitized_description = self._sanitize_description(description)
            try:
                result = await self.orchestrator.parse_text(sanitized_description, self.http_client)
                if result and result.ingredients:
                    ai_ingredients = result.ingredients
                    confidence = result.confidence
            except Exception as e:
                logger.warning(f"AIOrchestrator text parse failed: {e}")

        is_fallback_db = False
        fallback_db_name = None

        if ai_ingredients is not None:
            ingredients = [
                DomainIngredient(name=ing.name, quantity=ing.quantity, unit=ing.unit)
                for ing in ai_ingredients
            ]
        else:
            logger.debug("AI orchestrator failed or returned no ingredients - falling back to databases")

            # ── 2. Local food database ──
            matched_db = False
            for keyword, base_data in _LOCAL_FOOD_DB.items():
                if keyword in food_query:
                    logger.info(f"Fallback Local DB match: keyword='{keyword}' > {base_data['food_name']}")
                    ingredients = [
                        DomainIngredient(name=base_data["food_name"], quantity=float(quantity), unit="piece" if "piece" in base_data["food_name"].lower() else "serving")
                    ]
                    confidence = 0.90
                    matched_db = True
                    is_fallback_db = True
                    fallback_db_name = f"{quantity}x {base_data['food_name']}" if quantity > 1 else base_data["food_name"]
                    break

            # ── 3. Open Food Facts search ──
            if not matched_db:
                try:
                    off_results = await self.off_client.search_products(description)
                    relevant = self._filter_relevant_off_results(description, off_results)
                    if relevant:
                        top = relevant[0]
                        logger.info(f"Fallback OpenFoodFacts match: {top['food_name']}")
                        ingredients = [
                            DomainIngredient(name=top["food_name"], quantity=1.0, unit="serving")
                        ]
                        confidence = 0.80
                    else:
                        raise ValueError("No relevant OpenFoodFacts results")
                except Exception as e:
                    logger.warning(f"Fallback OpenFoodFacts search failed: {e}")
                    raise ValueError(f"Failed to parse food description '{description}'. All fallback steps failed.")

        # Caching logic based on normalized ingredient list hash
        normalized_strings = []
        for ing in ingredients:
            canonical_name = self.engine._matcher.match(ing).canonical_name
            norm_unit = QuantityConverter.normalize_unit(ing.unit)
            normalized_strings.append(f"{canonical_name} {ing.quantity} {norm_unit}")

        normalized_strings.sort()
        normalized_str = ",".join(normalized_strings)
        cache_key = hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()

        cached = self.ingredients_cache.get(cache_key)
        if cached is not None:
            logger.info("Ingredients cache hit! Returning deterministic cached nutrition.")
            return cached

        # Run ingredients through the engine
        try:
            analysis = await self.engine.analyze(ingredients)
        except Exception as e:
            logger.error(f"NutritionEngine analysis failed: {e}")
            raise ValueError(f"Failed to parse food description: {e}")

        # Construct final food_name
        if is_fallback_db:
            food_name = fallback_db_name
        else:
            if len(ingredients) == 1:
                food_name = ingredients[0].name
            else:
                food_name = ", ".join(ing.name for ing in ingredients)

        response = {
            "food_name": food_name,
            "calories": int(analysis.total_calories),
            "protein": round(analysis.total_protein, 1),
            "carbs": round(analysis.total_carbohydrates, 1),
            "fat": round(analysis.total_fat, 1),
            "confidence": confidence,
            "ingredients": [
                {"name": ing.name, "quantity": ing.quantity, "unit": ing.unit}
                for ing in ingredients
            ]
        }

        self.ingredients_cache.set(cache_key, response)
        return response

    async def scan_image(self, filename: str, file_bytes: bytes | None = None) -> dict:
        """
        Scan a food image through a tiered AI vision pipeline.

        Pipeline:
          1. AIOrchestrator image chain (Qwen VL -> Gemma -> Groq)
          2. Filename heuristic - last resort
        """
        logger.info(f"scan_image: '{filename}'")

        if not file_bytes:
            logger.error("scan_image called with no file bytes")
            raise ValueError("No image data provided for scanning.")

        logger.debug(f"Image size: {len(file_bytes):,} bytes")
        errors = []

        ai_ingredients = None
        confidence = 0.90

        # ── 1. Orchestrated AI Vision (Qwen VL -> Gemma -> Groq) ──────
        if self.http_client:
            base64_img = base64.b64encode(file_bytes).decode("utf-8")
            try:
                result = await self.orchestrator.parse_image(base64_img, self.http_client, filename=filename)
                if result and result.ingredients:
                    ai_ingredients = result.ingredients
                    confidence = result.confidence
            except Exception as e:
                err_msg = f"AIOrchestrator Vision failed: {e}"
                logger.warning(f"AIOrchestrator Vision failed: {e}")
                errors.append(err_msg)

        is_heuristic = False

        if ai_ingredients is not None:
            ingredients = [
                DomainIngredient(name=ing.name, quantity=ing.quantity, unit=ing.unit)
                for ing in ai_ingredients
            ]
        else:
            # ── 2. Filename heuristic ──
            logger.debug("Step 2/2: filename heuristic")
            matched_keyword = None
            for keyword in _LOCAL_FOOD_DB:
                if keyword in filename.lower():
                    matched_keyword = keyword
                    break

            if matched_keyword:
                logger.info(f"Heuristic matched keyword: '{matched_keyword}'")
                ingredients = [
                    DomainIngredient(name=_LOCAL_FOOD_DB[matched_keyword]["food_name"], quantity=1.0, unit="serving")
                ]
                confidence = 0.85
                is_heuristic = True
            else:
                combined_error = " | ".join(errors)
                logger.error(f"All image scan steps failed for '{filename}'. Details: {combined_error}")
                raise ValueError(f"AI image scanning failed: {combined_error}")

        # Caching logic
        normalized_strings = []
        for ing in ingredients:
            canonical_name = self.engine._matcher.match(ing).canonical_name
            norm_unit = QuantityConverter.normalize_unit(ing.unit)
            normalized_strings.append(f"{canonical_name} {ing.quantity} {norm_unit}")

        normalized_strings.sort()
        normalized_str = ",".join(normalized_strings)
        cache_key = hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()

        cached = self.ingredients_cache.get(cache_key)
        if cached is not None:
            logger.info("Ingredients cache hit for scan_image! Returning deterministic cached nutrition.")
            return cached

        # Run ingredients through the engine
        try:
            analysis = await self.engine.analyze(ingredients)
        except Exception as e:
            logger.error(f"NutritionEngine analysis failed in scan_image: {e}")
            raise ValueError(f"AI image scanning failed: {e}")

        # Construct final food_name
        if is_heuristic:
            food_name = f"Scanned {ingredients[0].name}"
        else:
            if len(ingredients) == 1:
                food_name = ingredients[0].name
            else:
                food_name = ", ".join(ing.name for ing in ingredients)

        response = {
            "food_name": food_name,
            "calories": int(analysis.total_calories),
            "protein": round(analysis.total_protein, 1),
            "carbs": round(analysis.total_carbohydrates, 1),
            "fat": round(analysis.total_fat, 1),
            "confidence": confidence,
            "ingredients": [
                {"name": ing.name, "quantity": ing.quantity, "unit": ing.unit}
                for ing in ingredients
            ]
        }

        self.ingredients_cache.set(cache_key, response)
        return response

    # ── Barcode Lookup ────────────────────────────────────────────────────

    async def lookup_barcode(self, barcode: str) -> dict | None:
        logger.info(f"lookup_barcode: '{barcode}'")
        return await self.off_client.lookup_barcode(barcode)

    # ─────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────

    def _filename_heuristic(self, filename: str) -> dict | None:
        filename_lower = filename.lower()
        base_name      = filename.rsplit(".", 1)[0] if "." in filename else filename
        clean_name     = re.sub(r"[-_\s]+", " ", base_name).strip()
        is_generic     = bool(
            re.match(r"^(img|image|photo|screenshot|camera|pic|dsc|uuid|file)\b", clean_name.lower())
            or not clean_name
            or re.match(r"^\d+$", clean_name)
        )

        for keyword, base_data in _LOCAL_FOOD_DB.items():
            if keyword in filename_lower:
                logger.debug(f"Heuristic: filename keyword match '{keyword}'")
                return {
                    "food_name":  f"Scanned {base_data['food_name']}",
                    "calories":   base_data["calories"],
                    "protein":    base_data["protein"],
                    "carbs":      base_data["carbs"],
                    "fat":        base_data["fat"],
                    "confidence": 0.85,
                }

        # Do not fabricate nutrition data for non-generic filenames.
        # If the AI chain failed, return None so scan_image() raises the
        # "all layers failed" error and the frontend can prompt manual entry.
        logger.debug(f"Heuristic: no keyword match for '{filename}' - returning None")
        return None

    def _sanitize_description(self, description: str) -> str:
        text = description.strip()
        text = text[:500]
        text = text.replace("{", "").replace("}", "")
        return text

    def _validate_nutrition(
        self, calories: float, protein: float, carbs: float, fat: float, source: str
    ) -> dict | None:
        """
        Reject physically impossible AI output before it's accepted.

        This is a lightweight guard, not a full validation layer - it only
        catches the clearly-impossible cases (Priority 14): negative values,
        or macro grams that couldn't possibly fit given 4/4/9 kcal-per-gram
        math (allowing generous headroom for rounding/estimation error).
        """
        if calories is None or calories < 0:
            logger.warning(f"{source}: rejected - negative/missing calories ({calories})")
            return None
        if protein is None or protein < 0 or carbs is None or carbs < 0 or fat is None or fat < 0:
            logger.warning(f"{source}: rejected - negative macro value (p={protein}, c={carbs}, f={fat})")
            return None

        # Macro-implied calories should roughly match the stated total.
        # Allow generous slack (2x) since AI estimates fiber/alcohol/rounding
        # differently - this is a sanity check, not a strict recompute.
        implied_calories = protein * 4 + carbs * 4 + fat * 9
        if implied_calories > 0 and calories > 0:
            ratio = implied_calories / calories
            if ratio > 3.0 or ratio < 0.2:
                logger.warning(
                    f"{source}: rejected - macros imply {implied_calories:.0f} kcal "
                    f"vs stated {calories:.0f} kcal (ratio={ratio:.2f})"
                )
                return None

        return {
            "calories": int(calories),
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1),
        }

    def _filter_relevant_off_results(self, query: str, results: list[dict]) -> list[dict]:
        """
        Open Food Facts free-text search often returns loosely-related
        products. Filter out results whose product name has low textual
        similarity to the query (Priority 10) rather than trusting the
        first hit unconditionally.
        """
        query_norm = query.strip().lower()
        relevant = []
        for r in results:
            name_norm = r.get("food_name", "").strip().lower()
            if not name_norm:
                continue
            similarity = difflib.SequenceMatcher(None, query_norm, name_norm).ratio()
            # Also credit direct word overlap, since OFF names are often
            # branded/verbose (e.g. "Kellogg's Corn Flakes Original 500g")
            # and won't score high on raw sequence similarity alone.
            query_words  = set(query_norm.split())
            name_words   = set(name_norm.split())
            word_overlap = len(query_words & name_words) / max(len(query_words), 1)

            score = max(similarity, word_overlap)
            if score >= 0.35:
                relevant.append(r)
            else:
                logger.debug(f"OFF result filtered out (score={score:.2f}): '{r.get('food_name')}'")
        return relevant