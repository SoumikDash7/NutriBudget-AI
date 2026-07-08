"""
CalorieService — orchestrates the full AI-powered nutrition pipeline.

Image scan call order:
  1. Google Gemini 2.5 Flash Vision (primary — AQ. key format)
  2. Google Gemini 2.5 Pro Vision   (Gemini fallback)
  3. Qwen2.5-VL via HuggingFace     (secondary fallback)
  4. Filename heuristic             (last resort)

Text parse call order:
  1. Google Gemini 2.5 Flash        (primary — AQ. key format)
  2. Google Gemini 2.5 Pro          (Gemini fallback)
  3. Qwen3 via HuggingFace          (secondary fallback)
  4. USDA FoodData Central API
  5. Indian + International local food DB
  6. Open Food Facts search
  7. Generic placeholder fallback

Future (not active):
  - SAM 2 + Depth Anything V2 for portion estimation
    (scaffold: set ENABLE_PORTION_AI=true once local server is running)
"""

import re
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.calorie import CalorieLog
from app.repositories.calorie_repository import CalorieRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.ai.gemini_client import GeminiClient
from app.services.ai.qwen_vl_client import QwenVLClient
from app.services.ai.qwen3_client import Qwen3Client
from app.services.ai.usda_client import USDAClient


# ─────────────────────────────────────────────────────────────────────────────
# Open Food Facts client (barcode + fallback search)
# ─────────────────────────────────────────────────────────────────────────────

class OpenFoodFactsClient:
    async def lookup_barcode(self, barcode: str) -> dict | None:
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == 1:
                        return self._parse_product(data.get("product", {}))
        except Exception as e:
            print(f"[OpenFoodFacts/Barcode] Error: {e}")
        return None

    async def search_products(self, query: str) -> list[dict]:
        url = (
            f"https://world.openfoodfacts.org/cgi/search.pl"
            f"?search_terms={query}&search_simple=1&action=process&json=1"
        )
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for p in data.get("products", [])[:5]:
                        parsed = self._parse_product(p)
                        if parsed:
                            results.append(parsed)
                    return results
        except Exception as e:
            print(f"[OpenFoodFacts/Search] Error: {e}")
        return []

    def _parse_product(self, product: dict) -> dict | None:
        name = (
            product.get("product_name")
            or product.get("generic_name")
            or "Unknown Product"
        )
        nutriments = product.get("nutriments", {})
        calories = nutriments.get("energy-kcal_100g")
        if calories is None:
            energy_kj = nutriments.get("energy_100g", 0)
            calories = int(energy_kj / 4.184)
        else:
            calories = int(calories)
        protein = round(float(nutriments.get("proteins_100g", 0.0)), 1)
        carbs = round(float(nutriments.get("carbohydrates_100g", 0.0)), 1)
        fat = round(float(nutriments.get("fat_100g", 0.0)), 1)
        return {
            "food_name": name,
            "calories": calories,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
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


# ─────────────────────────────────────────────────────────────────────────────
# CalorieService
# ─────────────────────────────────────────────────────────────────────────────

class CalorieService:

    def __init__(self, db: AsyncSession):
        self.repo = CalorieRepository(db)
        self.profile_repo = ProfileRepository(db)
        self.off_client = OpenFoodFactsClient()
        self.gemini = GeminiClient()
        self.qwen_vl = QwenVLClient()
        self.qwen3 = Qwen3Client()
        self.usda = USDAClient()

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
        # Enforce 7-day rolling window (scoped to this user)
        await self.repo.delete_logs_older_than(user_id=user_id, days=7)

        log = CalorieLog(
            user_id=user_id,
            food_name=food_name,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            logged_date=logged_date,
        )
        return await self.repo.create_log(log)

    # ── Dashboard ─────────────────────────────────────────────────────────

    async def get_dashboard(self, user_id: UUID) -> dict:
        await self.repo.delete_logs_older_than(user_id=user_id, days=7)

        profile = await self.profile_repo.get_by_user_id(user_id)
        target_calories = profile.daily_calorie_target if profile else 2000
        target_protein  = profile.daily_protein_target  if profile else 150.0
        target_carbs    = profile.daily_carb_target     if profile else 225.0
        target_fat      = profile.daily_fat_target      if profile else 65.0

        today = date.today()
        today_logs = await self.repo.get_logs_for_date(user_id, today)

        consumed_calories = sum(l.calories for l in today_logs)
        consumed_protein  = sum(l.protein  for l in today_logs)
        consumed_carbs    = sum(l.carbs    for l in today_logs)
        consumed_fat      = sum(l.fat      for l in today_logs)

        past_logs = await self.repo.get_logs_past_days(user_id, days=7)
        history_map = {today - timedelta(days=i): 0 for i in range(7)}
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
          1. Gemini 2.5 Flash / Pro (primary — new AQ. key format)
          2. Qwen3 (HuggingFace) — secondary
          3. USDA FoodData Central — real database lookup fallback
          4. Local DB (Indian + international) — offline database lookup fallback
          5. Open Food Facts search — product lookup fallback
        """
        desc_lower = description.lower().strip()
        print(f"[CalorieService] parse_description triggered for: '{description}'")

        # Parse optional leading quantity  e.g. "2 rotis"
        quantity = 1
        num_match = re.match(r"^(\d+)\s+(.+)$", desc_lower)
        if num_match:
            quantity = int(num_match.group(1))
            food_query = num_match.group(2)
        else:
            food_query = desc_lower

        errors = []

        # ── 1. Gemini 2.5 Flash / Pro (primary) ──────────────────────────
        if settings.GEMINI_API_KEY:
            print("[CalorieService] GEMINI_API_KEY configured. Trying Gemini text parse...")
            try:
                result = await self.gemini.parse_description(description)
                if result:
                    result["confidence"] = 0.98
                    print(f"[CalorieService] Gemini text parse succeeded: {result['food_name']}")
                    return result
            except Exception as e:
                err_msg = f"Gemini text parse failed: {str(e)}"
                print(f"[CalorieService] {err_msg}")
                errors.append(err_msg)
        else:
            msg = "Gemini API key not configured (GEMINI_API_KEY)."
            print(f"[CalorieService] {msg}")
            errors.append(msg)

        # ── 2. Qwen3 (HuggingFace fallback) ──────────────────────────────
        if settings.HUGGINGFACE_API_KEY:
            print("[CalorieService] HUGGINGFACE_API_KEY configured. Trying Qwen3 text parse...")
            try:
                result = await self.qwen3.parse_description(description)
                if result:
                    result["confidence"] = 0.96
                    print(f"[CalorieService] Qwen3 text parse succeeded: {result['food_name']}")
                    return result
            except Exception as e:
                err_msg = f"Qwen3 text parse failed: {str(e)}"
                print(f"[CalorieService] {err_msg}")
                errors.append(err_msg)
        else:
            msg = "HuggingFace API key not configured (HUGGINGFACE_API_KEY)."
            print(f"[CalorieService] {msg}")
            errors.append(msg)

        # If both primary AI parsers failed, try database search fallbacks (which don't require AI keys)
        print("[CalorieService] Both primary AI parsers failed. Attempting database lookups...")

        # ── 3. USDA FoodData Central ──────────────────────────────────────
        try:
            result = await self.usda.search(food_query)
            if result:
                result["confidence"] = 0.95
                print(f"[CalorieService] USDA database lookup succeeded: {result['food_name']}")
                return result
        except Exception as e:
            print(f"[CalorieService] USDA lookup error: {e}")

        # ── 4. Local food database ────────────────────────────────────────
        for keyword, base_data in _LOCAL_FOOD_DB.items():
            if keyword in food_query:
                print(f"[CalorieService] Local database lookup succeeded for keyword '{keyword}'")
                return {
                    "food_name": f"{quantity}x {base_data['food_name']}" if quantity > 1 else base_data["food_name"],
                    "calories": base_data["calories"] * quantity,
                    "protein":  round(base_data["protein"] * quantity, 1),
                    "carbs":    round(base_data["carbs"]   * quantity, 1),
                    "fat":      round(base_data["fat"]     * quantity, 1),
                    "confidence": 0.90,
                }

        # ── 5. Open Food Facts search ─────────────────────────────────────
        try:
            off_results = await self.off_client.search_products(description)
            if off_results:
                top = off_results[0]
                print(f"[CalorieService] Open Food Facts lookup succeeded: {top['food_name']}")
                return {**top, "confidence": 0.80}
        except Exception as e:
            print(f"[CalorieService] Open Food Facts search error: {e}")

        # If we got here, all parsers and databases failed.
        combined_error = " | ".join(errors)
        print(f"[CalorieService] All text parsers failed. AI errors: {combined_error}")
        raise ValueError(f"Failed to parse food description. AI errors: {combined_error}")

    # ── Barcode Lookup ────────────────────────────────────────────────────

    async def lookup_barcode(self, barcode: str) -> dict | None:
        return await self.off_client.lookup_barcode(barcode)

    # ── Image Scanner ─────────────────────────────────────────────────────

    async def scan_image(self, filename: str, file_bytes: bytes | None = None) -> dict:
        """
        Scan a food image through a tiered AI vision pipeline.

        Pipeline:
          1. Gemini 2.5 Flash / Pro (primary — new AQ. key format, multimodal)
          2. Qwen2.5-VL (HuggingFace / Ollama) — secondary fallback
        """
        print(f"[CalorieService] scan_image triggered for '{filename}'")
        if not file_bytes:
            print("[CalorieService] Error: No file bytes received.")
            raise ValueError("No image data provided for scanning.")

        print(f"[CalorieService] Image received: '{filename}' ({len(file_bytes)} bytes)")
        
        errors = []
        
        # ── 1. Gemini 2.5 Flash / Pro (primary) ───────────────────────
        if settings.GEMINI_API_KEY:
            print("[CalorieService] GEMINI_API_KEY is configured. Launching Gemini Vision scan...")
            try:
                result = await self.gemini.scan_image(filename, file_bytes)
                if result and "food_name" in result and "calories" in result:
                    result["confidence"] = 0.98
                    print(f"[CalorieService] Gemini Vision scan succeeded: {result['food_name']}")
                    return result
            except Exception as e:
                err_msg = f"Gemini Vision scan failed: {str(e)}"
                print(f"[CalorieService] {err_msg}")
                errors.append(err_msg)
        else:
            msg = "Gemini API key not configured (GEMINI_API_KEY)."
            print(f"[CalorieService] {msg}")
            errors.append(msg)

        # ── 2. Qwen2.5-VL (Fallback) ──────────────────────────────────
        print("[CalorieService] Launching Qwen2.5-VL fallback...")
        try:
            result = await self.qwen_vl.scan_image(filename, file_bytes)
            if result and "food_name" in result and "calories" in result:
                result["confidence"] = 0.95
                print(f"[CalorieService] Qwen2.5-VL scan succeeded: {result['food_name']}")
                return result
            else:
                errors.append("Qwen2.5-VL scan returned empty/invalid result.")
        except Exception as e:
            err_msg = f"Qwen2.5-VL fallback failed: {str(e)}"
            print(f"[CalorieService] {err_msg}")
            errors.append(err_msg)

        # If we got here, all AI layers failed.
        combined_error = " | ".join(errors)
        print(f"[CalorieService] All AI scans failed. Details: {combined_error}")
        raise ValueError(f"AI image scanning failed: {combined_error}")

    # ─────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────

    # _call_gemini removed — now handled by GeminiClient in gemini_client.py

    def _filename_heuristic(self, filename: str) -> dict | None:
        filename_lower = filename.lower()
        base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
        clean_name = re.sub(r"[-_\s]+", " ", base_name).strip()
        is_generic = bool(
            re.match(r"^(img|image|photo|screenshot|camera|pic|dsc|uuid|file)\b", clean_name.lower())
            or not clean_name
            or re.match(r"^\d+$", clean_name)
        )

        for keyword, base_data in _LOCAL_FOOD_DB.items():
            if keyword in filename_lower:
                return {
                    "food_name":  f"Scanned {base_data['food_name']}",
                    "calories":   base_data["calories"],
                    "protein":    base_data["protein"],
                    "carbs":      base_data["carbs"],
                    "fat":        base_data["fat"],
                    "confidence": 0.85,
                }

        if not is_generic:
            return {
                "food_name":  f"Scanned {clean_name.title()}",
                "calories":   320,
                "protein":    12.5,
                "carbs":      38.0,
                "fat":        10.5,
                "confidence": 0.70,
            }
        return None
