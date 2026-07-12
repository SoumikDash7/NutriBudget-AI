from app.services.calculators.food_nutrition.constants import _LOCAL_FOOD_DB
from app.services.calculators.food_nutrition.models import IngredientMatch, NutritionFacts
from app.services.calculators.food_nutrition.exceptions import IngredientNotFoundError
from app.services.calculators.food_nutrition.providers.indian import make_nutrition_facts_from_local_db

class DeterministicFallbackProvider:
    """
    Deterministic fallback database provider.
    Conforms to the NutritionProvider protocol.
    Queries all items in _LOCAL_FOOD_DB.
    """

    async def lookup(self, ingredient: IngredientMatch) -> NutritionFacts:
        query = ingredient.canonical_name.lower().strip()
        
        # Try exact match first
        if query in _LOCAL_FOOD_DB:
            return make_nutrition_facts_from_local_db(
                _LOCAL_FOOD_DB[query]["food_name"],
                _LOCAL_FOOD_DB[query]
            )
            
        # Fallback to keyword/substring match
        for keyword in _LOCAL_FOOD_DB:
            if keyword == query or keyword in query:
                return make_nutrition_facts_from_local_db(
                    _LOCAL_FOOD_DB[keyword]["food_name"],
                    _LOCAL_FOOD_DB[keyword]
                )
                
        raise IngredientNotFoundError(
            f"DeterministicFallbackProvider: '{ingredient.canonical_name}' not found."
        )
