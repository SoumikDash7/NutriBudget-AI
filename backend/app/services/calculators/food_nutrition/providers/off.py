import httpx
import difflib
import logging
from app.services.calculators.food_nutrition.models import IngredientMatch, NutritionFacts
from app.services.calculators.food_nutrition.exceptions import IngredientNotFoundError, FoodDatabaseUnavailableError

logger = logging.getLogger(__name__)

class OpenFoodFactsProvider:
    """
    OpenFoodFacts provider.
    Conforms to the NutritionProvider protocol.
    """

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._client = http_client

    async def lookup(self, ingredient: IngredientMatch) -> NutritionFacts:
        query = ingredient.canonical_name.strip()
        url = (
            f"https://world.openfoodfacts.org/cgi/search.pl"
            f"?search_terms={query}&search_simple=1&action=process&json=1"
        )
        try:
            response = await self._client.get(url, timeout=5.0)
            if response.status_code != 200:
                raise FoodDatabaseUnavailableError(f"OpenFoodFacts search returned HTTP {response.status_code}")
            
            data = response.json()
            products = data.get("products", [])
            
            results = []
            for p in products[:5]:
                parsed = self._parse_product(p)
                if parsed:
                    results.append(parsed)
            
            relevant = self._filter_relevant_results(query, results)
            if not relevant:
                raise IngredientNotFoundError(f"No relevant OpenFoodFacts results for '{query}'")
            
            top = relevant[0]
            return NutritionFacts(
                food_name=top["food_name"],
                calories=float(top["calories"]),
                protein=float(top["protein"]),
                carbohydrates=float(top["carbs"]),
                fat=float(top["fat"]),
                fiber=float(top.get("fiber", 0.0)),
                sugar=float(top.get("sugar", 0.0)),
                sodium=float(top.get("sodium", 0.0)),
                serving_unit="g"
            )
            
        except httpx.RequestError as e:
            raise FoodDatabaseUnavailableError(f"OpenFoodFacts request failed: {e}") from e

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
        fiber   = round(float(nutriments.get("fiber_100g", 0.0)), 1)
        sugar   = round(float(nutriments.get("sugars_100g", 0.0)), 1)
        sodium  = round(float(nutriments.get("sodium_100g", 0.0)) * 1000.0, 1)
        
        return {
            "food_name": name,
            "calories":  calories,
            "protein":   protein,
            "carbs":     carbs,
            "fat":       fat,
            "fiber":     fiber,
            "sugar":     sugar,
            "sodium":    sodium
        }

    def _filter_relevant_results(self, query: str, results: list[dict]) -> list[dict]:
        query_norm = query.strip().lower()
        relevant = []
        for r in results:
            name_norm = r.get("food_name", "").strip().lower()
            if not name_norm:
                continue
            similarity = difflib.SequenceMatcher(None, query_norm, name_norm).ratio()
            query_words  = set(query_norm.split())
            name_words   = set(name_norm.strip().split())
            word_overlap = len(query_words & name_words) / max(len(query_words), 1)

            score = max(similarity, word_overlap)
            if score >= 0.35:
                relevant.append(r)
        return relevant
