"""
Nutrition Engine.

Coordinates the nutrition calculation pipeline.

Pipeline:

Ingredients
    ↓
Ingredient Matcher
    ↓
Nutrition Provider
    ↓
Scale Nutrition
    ↓
Meal Totals
"""

from __future__ import annotations

from app.services.calculators.food_nutrition.databases import (
    NutritionProvider,
)
from app.services.calculators.food_nutrition.exceptions import (
    UnsupportedUnitError,
)
from app.services.calculators.food_nutrition.matcher import (
    IngredientMatcher,
)
from app.services.calculators.food_nutrition.models import (
    Ingredient,
    IngredientMatch,
    NutritionFacts,
    NutritionResult,
    ScaledNutrition,
)


class NutritionEngine:
    """
    Deterministic nutrition calculation engine.
    """

    def __init__(
        self,
        provider: NutritionProvider,
        matcher: IngredientMatcher | None = None,
    ) -> None:
        self._provider = provider
        self._matcher = matcher or IngredientMatcher()

    def analyze(
        self,
        ingredients: list[Ingredient],
    ) -> NutritionResult:
        """
        Analyze a collection of ingredients.

        Returns
        -------
        NutritionResult
            Nutrition totals for the meal.
        """

        result = NutritionResult(
            ingredients=list(ingredients),
        )

        for ingredient in ingredients:
            match = self._match(ingredient)
            nutrition = self._lookup(match)
            scaled = self._scale(
                ingredient,
                nutrition,
            )

            result.scaled_items.append(scaled)

            self._accumulate(
                result,
                scaled,
            )

        return result

    def _match(
        self,
        ingredient: Ingredient,
    ) -> IngredientMatch:
        return self._matcher.match(ingredient)

    def _lookup(
        self,
        match: IngredientMatch,
    ) -> NutritionFacts:
        return self._provider.lookup(match)

    def _scale(
        self,
        ingredient: Ingredient,
        nutrition: NutritionFacts,
    ) -> ScaledNutrition:
        """
        Scale nutrition values to the user supplied quantity.
        """

        unit = ingredient.unit.lower()

        if unit not in {
            "g",
            "gram",
            "grams",
        }:
            raise UnsupportedUnitError(
                f"Unsupported unit '{ingredient.unit}'."
            )

        factor = (
            ingredient.quantity
            / nutrition.serving_size
        )

        return ScaledNutrition(
            ingredient=ingredient,
            base_nutrition=nutrition,
            calories=nutrition.calories * factor,
            protein=nutrition.protein * factor,
            carbohydrates=nutrition.carbohydrates * factor,
            fat=nutrition.fat * factor,
            fiber=nutrition.fiber * factor,
            sugar=nutrition.sugar * factor,
            sodium=nutrition.sodium * factor,
        )

    @staticmethod
    def _accumulate(
        result: NutritionResult,
        scaled: ScaledNutrition,
    ) -> None:
        """
        Add one scaled ingredient into meal totals.
        """

        result.total_calories += scaled.calories
        result.total_protein += scaled.protein
        result.total_carbohydrates += (
            scaled.carbohydrates
        )
        result.total_fat += scaled.fat
        result.total_fiber += scaled.fiber
        result.total_sugar += scaled.sugar
        result.total_sodium += scaled.sodium