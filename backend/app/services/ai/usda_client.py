"""
USDA FoodData Central API client.

Free API key signup: https://fdc.nal.usda.gov/api-guide.html
Requires USDA_API_KEY in .env - gracefully skipped if not set.

Searches the FDC database and returns the best match with macro nutrients
normalized to a standard 100g portion.
"""

import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.nutrition import FoodInput, NutritionEstimate, ExtractedIngredient
from app.services.ai.base import NutritionProvider
from app.services.ai.exceptions import ProviderAPIError

logger = get_logger(__name__)

_FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# FDC nutrient IDs we care about
_NUTRIENT_MAP = {
    1008: "calories",   # Energy (kcal)
    1003: "protein",    # Protein
    1005: "carbs",      # Carbohydrate, by difference
    1004: "fat",        # Total lipid (fat)
}


class USDAClient(NutritionProvider):
    """
    USDA FoodData Central search client.
    Conforms to the NutritionProvider protocol.
    """
    name = "USDA FoodData Central"
    supports_vision = False

    async def extract(self, food_input: FoodInput, http_client: httpx.AsyncClient) -> NutritionEstimate:
        """
        Search FoodData Central for the best matching food item.
        Returns a NutritionEstimate model.
        """
        if not settings.USDA_API_KEY:
            raise ProviderAPIError("USDA_API_KEY is not configured.")

        query = food_input.text
        if not query:
            raise ProviderAPIError("USDA text search requires a search query text.")

        logger.info(f"search: '{query}'")
        params = {
            "query": query,
            "api_key": settings.USDA_API_KEY,
            "dataType": ["SR Legacy", "Foundation", "Branded"],
            "pageSize": 5,
        }

        logger.debug(f"GET > {_FDC_SEARCH_URL}  query='{query}'")
        try:
            response = await http_client.get(_FDC_SEARCH_URL, params=params, timeout=8.0)
            status = response.status_code
            if status != 200:
                raise ProviderAPIError(f"HTTP {status} from USDA API")

            data = response.json()
            foods = data.get("foods", [])
            if not foods:
                raise ProviderAPIError(f"No USDA food entries found for query '{query}'")

            # Try to parse candidates in order until a valid non-empty one is found
            for food in foods:
                parsed_data = self._parse_food(food)
                if parsed_data:
                    logger.info(f"OK Found: {parsed_data['food_name']}  ({parsed_data['calories']} kcal / 100g)")
                    return NutritionEstimate(
                        ingredients=[
                            ExtractedIngredient(
                                name=parsed_data["food_name"],
                                quantity=100.0,
                                unit="g"
                            )
                        ],
                        calories=float(parsed_data["calories"]),
                        protein_g=float(parsed_data["protein"]),
                        carbs_g=float(parsed_data["carbs"]),
                        fat_g=float(parsed_data["fat"]),
                        confidence=0.95,
                        source_provider=self.name
                    )

            raise ProviderAPIError(f"All USDA food candidates for query '{query}' were empty or invalid.")

        except Exception as e:
            if isinstance(e, ProviderAPIError):
                raise
            logger.error(f"USDA API request failed: {e}", exc_info=True)
            raise ProviderAPIError(f"USDA API request failed: {e}") from e

    # ─────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────

    def _parse_food(self, food: dict) -> dict | None:
        """Extract macro nutrients from a FDC food item."""
        name      = food.get("description") or food.get("lowercaseDescription") or "Unknown"
        nutrients = {n["nutrientId"]: n.get("value", 0.0) for n in food.get("foodNutrients", [])}

        calories = int(nutrients.get(1008, 0))
        protein  = round(float(nutrients.get(1003, 0.0)), 1)
        carbs    = round(float(nutrients.get(1005, 0.0)), 1)
        fat      = round(float(nutrients.get(1004, 0.0)), 1)

        # Discard entries only if they are completely empty/incomplete (macros & calories are all 0)
        # Legitimate 0-calorie foods (water, diet sodas, spices) will have some valid trace details or descriptions
        if calories == 0 and protein == 0.0 and carbs == 0.0 and fat == 0.0:
            logger.debug(f"Discarding '{name}' - completely empty USDA record (likely placeholder)")
            return None

        return {
            "food_name": name.title(),
            "calories":  calories,
            "protein":   protein,
            "carbs":     carbs,
            "fat":       fat,
        }
