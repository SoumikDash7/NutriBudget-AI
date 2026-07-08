"""
USDA FoodData Central API client.

Free API key signup: https://fdc.nal.usda.gov/api-guide.html
Requires USDA_API_KEY in .env — gracefully skipped if not set.

Searches the FDC database and returns the best match with macro nutrients
normalized to a standard 100g portion.
"""

import httpx

from app.core.config import settings

_FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_FDC_DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"

# FDC nutrient IDs we care about
_NUTRIENT_MAP = {
    1008: "calories",   # Energy (kcal)
    1003: "protein",    # Protein
    1005: "carbs",      # Carbohydrate, by difference
    1004: "fat",        # Total lipid (fat)
}


class USDAClient:
    """
    USDA FoodData Central search client.
    Returns None gracefully when USDA_API_KEY is not configured.
    """

    async def search(self, query: str) -> dict | None:
        """
        Search FoodData Central for the best matching food item.
        Returns a dict with food_name, calories, protein, carbs, fat (per 100g)
        or None on failure / missing key.
        """
        if not settings.USDA_API_KEY:
            return None

        params = {
            "query": query,
            "api_key": settings.USDA_API_KEY,
            "dataType": ["SR Legacy", "Foundation", "Branded"],
            "pageSize": 5,
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(_FDC_SEARCH_URL, params=params, timeout=8.0)
                if response.status_code != 200:
                    print(f"[USDA] Search HTTP {response.status_code}")
                    return None

                data = response.json()
                foods = data.get("foods", [])
                if not foods:
                    return None

                # Pick the first food and parse its nutrients
                food = foods[0]
                return self._parse_food(food)

        except Exception as e:
            print(f"[USDA] Search failed: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────

    def _parse_food(self, food: dict) -> dict | None:
        """Extract macro nutrients from a FDC food item."""
        name = food.get("description") or food.get("lowercaseDescription") or "Unknown"
        nutrients = {n["nutrientId"]: n.get("value", 0.0) for n in food.get("foodNutrients", [])}

        calories = int(nutrients.get(1008, 0))
        protein = round(float(nutrients.get(1003, 0.0)), 1)
        carbs = round(float(nutrients.get(1005, 0.0)), 1)
        fat = round(float(nutrients.get(1004, 0.0)), 1)

        # Discard entries with zero calories (likely incomplete records)
        if calories == 0:
            return None

        print(f"[USDA] Found: {name} ({calories} kcal / 100g)")
        return {
            "food_name": name.title(),
            "calories": calories,
            "protein": protein,
            "carbs": carbs,
            "fat": fat,
        }
