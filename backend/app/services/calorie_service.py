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
import httpx
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

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


# ─────────────────────────────────────────────────────────────────────────────
# Local food database — USDA + Indian cuisine reference values
# ─────────────────────────────────────────────────────────────────────────────

_LOCAL_FOOD_DB: dict[str, dict] = {
    # ── Indian Staples ────────────────────────────────────────────────────
    "roti":           {"food_name": "Roti (1 piece)",              "calories": 80,  "protein": 3.0,  "carbs": 15.0, "fat": 0.5},
    "chapati":        {"food_name": "Chapati (1 piece)",           "calories": 80,  "protein": 3.0,  "carbs": 15.0, "fat": 0.5},
    "paratha":        {"food_name": "Aloo Paratha (1 piece)",      "calories": 210, "protein": 4.0,  "carbs": 32.0, "fat": 7.0},
    "naan":           {"food_name": "Naan (1 piece)",              "calories": 260, "protein": 9.0,  "carbs": 45.0, "fat": 5.0},
    "poori":          {"food_name": "Puri (1 piece)",              "calories": 120, "protein": 2.0,  "carbs": 14.0, "fat": 6.0},
    "idli":           {"food_name": "Idli (1 piece)",              "calories": 40,  "protein": 1.0,  "carbs": 8.0,  "fat": 0.1},
    "dosa":           {"food_name": "Plain Dosa (1 piece)",        "calories": 120, "protein": 2.0,  "carbs": 22.0, "fat": 3.0},
    "uttapam":        {"food_name": "Uttapam (1 piece)",           "calories": 110, "protein": 3.5,  "carbs": 18.0, "fat": 3.0},
    "upma":           {"food_name": "Upma (100g)",                 "calories": 130, "protein": 3.0,  "carbs": 22.0, "fat": 4.5},
    "poha":           {"food_name": "Poha (100g)",                 "calories": 110, "protein": 2.5,  "carbs": 23.0, "fat": 2.0},
    "khichdi":        {"food_name": "Khichdi (100g)",              "calories": 120, "protein": 4.5,  "carbs": 20.0, "fat": 3.0},
    # ── Indian Curries & Mains ────────────────────────────────────────────
    "dal":            {"food_name": "Dal Tadka (100g)",            "calories": 120, "protein": 5.0,  "carbs": 15.0, "fat": 4.0},
    "dal makhani":    {"food_name": "Dal Makhani (100g)",          "calories": 165, "protein": 6.5,  "carbs": 18.0, "fat": 7.0},
    "paneer":         {"food_name": "Paneer Butter Masala (100g)", "calories": 229, "protein": 8.0,  "carbs": 6.0,  "fat": 19.0},
    "palak paneer":   {"food_name": "Palak Paneer (100g)",         "calories": 180, "protein": 7.0,  "carbs": 8.0,  "fat": 13.0},
    "butter chicken": {"food_name": "Butter Chicken (100g)",       "calories": 240, "protein": 14.0, "carbs": 5.0,  "fat": 18.0},
    "chicken tikka":  {"food_name": "Chicken Tikka (100g)",        "calories": 190, "protein": 22.0, "carbs": 4.0,  "fat": 9.0},
    "biryani":        {"food_name": "Chicken Biryani (100g)",      "calories": 180, "protein": 10.0, "carbs": 22.0, "fat": 6.0},
    "rajma":          {"food_name": "Rajma Masala (100g)",         "calories": 140, "protein": 7.5,  "carbs": 22.0, "fat": 3.5},
    "chole":          {"food_name": "Chole Masala (100g)",         "calories": 160, "protein": 7.0,  "carbs": 24.0, "fat": 5.0},
    "aloo gobi":      {"food_name": "Aloo Gobi (100g)",            "calories": 90,  "protein": 2.5,  "carbs": 12.0, "fat": 4.0},
    "sambhar":        {"food_name": "Sambar (100g)",               "calories": 75,  "protein": 3.5,  "carbs": 10.0, "fat": 2.5},
    "rasam":          {"food_name": "Rasam (100ml)",               "calories": 40,  "protein": 1.5,  "carbs": 6.0,  "fat": 1.0},
    # ── Indian Snacks & Street Food ───────────────────────────────────────
    "samosa":         {"food_name": "Samosa (1 piece)",            "calories": 260, "protein": 3.5,  "carbs": 24.0, "fat": 16.0},
    "pakora":         {"food_name": "Pakora (1 piece)",            "calories": 80,  "protein": 2.0,  "carbs": 9.0,  "fat": 4.0},
    "vada":           {"food_name": "Medu Vada (1 piece)",         "calories": 100, "protein": 3.0,  "carbs": 12.0, "fat": 5.0},
    "pani puri":      {"food_name": "Pani Puri (6 pieces)",        "calories": 180, "protein": 3.0,  "carbs": 28.0, "fat": 6.0},
    "bhel puri":      {"food_name": "Bhel Puri (100g)",            "calories": 130, "protein": 3.0,  "carbs": 22.0, "fat": 4.0},
    "pav bhaji":      {"food_name": "Pav Bhaji (1 serving)",       "calories": 350, "protein": 8.0,  "carbs": 52.0, "fat": 12.0},
    # ── Indian Sweets & Drinks ────────────────────────────────────────────
    "gulab jamun":    {"food_name": "Gulab Jamun (1 piece)",       "calories": 150, "protein": 2.5,  "carbs": 26.0, "fat": 5.0},
    "rasgulla":       {"food_name": "Rasgulla (1 piece)",          "calories": 100, "protein": 2.0,  "carbs": 22.0, "fat": 0.5},
    "halwa":          {"food_name": "Sooji Halwa (100g)",          "calories": 280, "protein": 4.0,  "carbs": 38.0, "fat": 12.0},
    "kheer":          {"food_name": "Rice Kheer (100g)",           "calories": 145, "protein": 3.5,  "carbs": 24.0, "fat": 4.5},
    "lassi":          {"food_name": "Sweet Lassi (200ml)",         "calories": 160, "protein": 5.0,  "carbs": 26.0, "fat": 4.0},
    "chai":           {"food_name": "Masala Chai with milk (200ml)","calories": 80, "protein": 2.5,  "carbs": 11.0, "fat": 2.5},
    # ── International Staples (USDA Reference) ───────────────────────────
    "egg":            {"food_name": "Egg (1 large)",               "calories": 70,  "protein": 6.0,  "carbs": 0.6,  "fat": 5.0},
    "eggs":           {"food_name": "Eggs (1 large each)",         "calories": 70,  "protein": 6.0,  "carbs": 0.6,  "fat": 5.0},
    "omelette":       {"food_name": "Plain Omelette (2 eggs)",     "calories": 190, "protein": 13.0, "carbs": 1.0,  "fat": 15.0},
    "bread":          {"food_name": "Slice of Bread",              "calories": 80,  "protein": 3.0,  "carbs": 15.0, "fat": 1.0},
    "banana":         {"food_name": "Banana (medium)",             "calories": 90,  "protein": 1.1,  "carbs": 23.0, "fat": 0.3},
    "apple":          {"food_name": "Apple (medium)",              "calories": 52,  "protein": 0.3,  "carbs": 14.0, "fat": 0.2},
    "orange":         {"food_name": "Orange (medium)",             "calories": 62,  "protein": 1.2,  "carbs": 15.4, "fat": 0.2},
    "mango":          {"food_name": "Mango (100g)",                "calories": 60,  "protein": 0.8,  "carbs": 15.0, "fat": 0.4},
    "chicken":        {"food_name": "Chicken Breast (100g)",       "calories": 165, "protein": 31.0, "carbs": 0.0,  "fat": 3.6},
    "fish":           {"food_name": "Grilled Fish (100g)",         "calories": 140, "protein": 26.0, "carbs": 0.0,  "fat": 4.0},
    "rice":           {"food_name": "Cooked Rice (100g)",          "calories": 130, "protein": 2.7,  "carbs": 28.0, "fat": 0.3},
    "pasta":          {"food_name": "Cooked Pasta (100g)",         "calories": 158, "protein": 5.8,  "carbs": 31.0, "fat": 0.9},
    "oats":           {"food_name": "Oatmeal (100g cooked)",       "calories": 71,  "protein": 2.5,  "carbs": 12.0, "fat": 1.5},
    "milk":           {"food_name": "Milk (200ml)",                "calories": 120, "protein": 6.8,  "carbs": 10.0, "fat": 6.0},
    "curd":           {"food_name": "Curd / Yogurt (100g)",        "calories": 60,  "protein": 3.5,  "carbs": 4.5,  "fat": 3.0},
    "paneer raw":     {"food_name": "Paneer (100g raw)",           "calories": 265, "protein": 18.0, "carbs": 3.5,  "fat": 20.0},
    "pizza":          {"food_name": "Slice of Pizza",              "calories": 285, "protein": 12.0, "carbs": 36.0, "fat": 10.0},
    "burger":         {"food_name": "Burger (standard)",           "calories": 350, "protein": 18.0, "carbs": 40.0, "fat": 14.0},
    "salad":          {"food_name": "Green Salad",                 "calories": 15,  "protein": 1.0,  "carbs": 3.0,  "fat": 0.2},
    "sandwich":       {"food_name": "Sandwich (standard)",         "calories": 250, "protein": 11.0, "carbs": 34.0, "fat": 8.0},
    "coffee":         {"food_name": "Coffee with milk (200ml)",    "calories": 50,  "protein": 2.0,  "carbs": 5.0,  "fat": 2.0},
    "juice":          {"food_name": "Fruit Juice (200ml)",         "calories": 90,  "protein": 0.5,  "carbs": 22.0, "fat": 0.0},
}


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


class CalorieService:

    def __init__(self, db: AsyncSession, http_client: httpx.AsyncClient | None = None):
        self.repo         = CalorieRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.http_client  = http_client
        # OpenFoodFacts uses the same shared client (falls back to per-request only if client not injected)
        self.off_client   = OpenFoodFactsClient(http_client) if http_client else _FallbackOFFClient()
        self.orchestrator = _build_orchestrator()

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

        # Parse optional leading quantity e.g. "2 rotis"
        quantity  = 1
        num_match = re.match(r"^(\d+)\s+(.+)$", desc_lower)
        if num_match:
            quantity   = int(num_match.group(1))
            food_query = num_match.group(2)
            logger.debug(f"Quantity detected: {quantity}x '{food_query}'")
        else:
            food_query = desc_lower

        # ── 1. Orchestrated AI Pipeline (Qwen3 -> Gemma -> Groq -> USDA) ──
        logger.debug("Step 1/3: AIOrchestrator text parse")
        if not self.http_client:
            logger.error("parse_description called without http_client")
            raise ValueError("http_client is required for AI description parsing.")

        sanitized_description = self._sanitize_description(description)

        try:
            result = await self.orchestrator.parse_text(sanitized_description, self.http_client)
            if result:
                name = result.ingredients[0].name if result.ingredients else "Unknown Food"
                # Apply quantity scaling if detected
                if quantity > 1:
                    scaled_name = f"{quantity}x {name}"
                else:
                    scaled_name = name

                return {
                    "food_name": scaled_name,
                    "calories": int(result.calories * quantity),
                    "protein": round(float(result.protein_g * quantity), 1),
                    "carbs": round(float(result.carbs_g * quantity), 1),
                    "fat": round(float(result.fat_g * quantity), 1),
                    "confidence": float(result.confidence),
                }
        except Exception as e:
            logger.warning(f"AIOrchestrator text parse failed: {e}")

        logger.debug("AI orchestrator failed - falling back to databases")

        # ── 2. Local food database ────────────────────────────────────────
        logger.debug("Step 2/3: local food DB keyword match")
        for keyword, base_data in _LOCAL_FOOD_DB.items():
            if keyword in food_query:
                logger.info(f"Step 2 OK Local DB: keyword='{keyword}' > {base_data['food_name']}")
                return {
                    "food_name": f"{quantity}x {base_data['food_name']}" if quantity > 1 else base_data["food_name"],
                    "calories":  base_data["calories"] * quantity,
                    "protein":   round(base_data["protein"] * quantity, 1),
                    "carbs":     round(base_data["carbs"]   * quantity, 1),
                    "fat":       round(base_data["fat"]     * quantity, 1),
                    "confidence": 0.90,
                }
        logger.debug("Step 2: no local DB keyword match")

        # ── 3. Open Food Facts search ─────────────────────────────────────
        logger.debug("Step 3/3: Open Food Facts product search")
        try:
            off_results = await self.off_client.search_products(description)
            if off_results:
                top = off_results[0]
                logger.info(f"Step 3 OK OpenFoodFacts: {top['food_name']} ({top['calories']} kcal)")
                return {**top, "confidence": 0.80}
            else:
                logger.debug("Step 3: Open Food Facts returned no usable results")
        except Exception as e:
            logger.warning(f"Step 3 FAIL Open Food Facts error: {e}")

        # All parsers exhausted
        logger.error(f"All 3 text parsing steps failed for '{description}'.")
        raise ValueError(f"Failed to parse food description '{description}'. All fallback steps failed.")

    # ── Barcode Lookup ────────────────────────────────────────────────────

    async def lookup_barcode(self, barcode: str) -> dict | None:
        logger.info(f"lookup_barcode: '{barcode}'")
        return await self.off_client.lookup_barcode(barcode)

    # ── Image Scanner ─────────────────────────────────────────────────────

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

        # ── 1. Orchestrated AI Vision (Qwen VL -> Gemma -> Groq) ──────
        logger.debug("Step 1/2: AIOrchestrator Vision scan")
        if not self.http_client:
            logger.error("scan_image called without http_client")
            raise ValueError("http_client is required for AI image scanning.")

        base64_img = base64.b64encode(file_bytes).decode("utf-8")
        try:
            result = await self.orchestrator.parse_image(base64_img, self.http_client, filename=filename)
            if result:
                name = result.ingredients[0].name if result.ingredients else "Scanned Food"
                logger.info(f"Step 1 OK Orchestrator Vision: {name} ({result.calories} kcal)")
                return {
                    "food_name": name,
                    "calories": int(result.calories),
                    "protein": float(result.protein_g),
                    "carbs": float(result.carbs_g),
                    "fat": float(result.fat_g),
                    "confidence": float(result.confidence),
                }
        except Exception as e:
            err_msg = f"AIOrchestrator Vision failed: {e}"
            logger.warning(f"Step 1 FAIL {err_msg}")
            errors.append(err_msg)

        # ── 2. Filename heuristic ──────────────────────────────────────
        logger.debug("Step 2/2: filename heuristic")
        heuristic_result = self._filename_heuristic(filename)
        if heuristic_result:
            logger.info(
                f"Step 2 OK Heuristic: '{filename}' > "
                f"{heuristic_result['food_name']} (confidence={heuristic_result['confidence']})"
            )
            return heuristic_result

        logger.debug("Step 2: heuristic found no match")

        # All layers failed
        combined_error = " | ".join(errors)
        logger.error(f"All image scan steps failed for '{filename}'. Details: {combined_error}")
        raise ValueError(f"AI image scanning failed: {combined_error}")

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
