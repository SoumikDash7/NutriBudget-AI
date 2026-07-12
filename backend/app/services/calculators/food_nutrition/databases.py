"""
Nutrition database provider interfaces and registrations.

This module defines the NutritionProvider protocol.
Concrete providers live in app/services/calculators/food_nutrition/providers/.

Providers are responsible only for retrieving nutrition facts.
They never perform calculations.
"""

from __future__ import annotations

from typing import Protocol

from app.services.calculators.food_nutrition.models import (
    IngredientMatch,
    NutritionFacts,
)


class NutritionProvider(Protocol):
    """Interface implemented by every nutrition provider."""

    async def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        """
        Retrieve nutrition information for a canonical ingredient.

        Raises IngredientNotFoundError when the ingredient is not
        available in this provider's data source.
        """
        ...



from app.services.calculators.food_nutrition.providers.indian import IndianNutritionProvider
from app.services.calculators.food_nutrition.providers.off import OpenFoodFactsProvider
from app.services.calculators.food_nutrition.providers.fallback import DeterministicFallbackProvider
