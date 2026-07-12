"""
Nutrition Engine.

Coordinates the nutrition calculation pipeline.

Pipeline:

Ingredients
    ↓
Ingredient Matcher
    ↓
Providers (in priority order — first successful result wins)
    ↓
Scale Nutrition
    ↓
Meal Totals
"""

from __future__ import annotations

import logging

from app.services.calculators.food_nutrition.databases import (
    NutritionProvider,
)
from app.services.calculators.food_nutrition.exceptions import (
    IngredientNotFoundError,
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

logger = logging.getLogger(__name__)


class NutritionEngine:
    """
    Deterministic nutrition calculation engine.

    Accepts an ordered list of providers.  On each lookup the engine
    tries providers left-to-right and returns the first successful
    result.  If all providers raise IngredientNotFoundError the
    exception from the last provider is propagated.
    """

    def __init__(
        self,
        providers: list[NutritionProvider],
        matcher: IngredientMatcher | None = None,
    ) -> None:
        if not providers:
            raise ValueError(
                "NutritionEngine requires at least one provider."
            )
        self._providers = providers
        self._matcher = matcher or IngredientMatcher()

    async def analyze(
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
            nutrition = await self._lookup(match)
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

    async def _lookup(
        self,
        match: IngredientMatch,
    ) -> NutritionFacts:
        """
        Try each provider in priority order.

        Returns the first successful result.
        Raises IngredientNotFoundError if every provider fails.
        """
        last_exc: IngredientNotFoundError | None = None

        for provider in self._providers:
            try:
                return await provider.lookup(match)
            except IngredientNotFoundError as exc:
                logger.debug(
                    "Provider %s did not find '%s'; trying next.",
                    type(provider).__name__,
                    match.canonical_name,
                )
                last_exc = exc

        raise IngredientNotFoundError(
            f"Ingredient '{match.canonical_name}' "
            "was not found in any provider."
        ) from last_exc

    def _scale(
        self,
        ingredient: Ingredient,
        nutrition: NutritionFacts,
    ) -> ScaledNutrition:
        """
        Scale nutrition values to the user supplied quantity.
        """
        from app.services.calculators.food_nutrition.converter import QuantityConverter

        norm_unit = QuantityConverter.normalize_unit(ingredient.unit)

        # Check if matched in USDA portions
        has_usda_portion = False
        if nutrition.food_portions:
            has_usda_portion = (
                QuantityConverter._find_usda_portion_match(
                    norm_unit, nutrition.food_portions
                )
                is not None
            )
        if (
            not has_usda_portion
            and getattr(nutrition, "portions", None)
        ):
            has_usda_portion = norm_unit in nutrition.portions

        if (
            norm_unit not in QuantityConverter._UNIT_NORMALIZATION
            and not has_usda_portion
        ):
            raise UnsupportedUnitError(
                f"Unsupported unit '{ingredient.unit}'."
            )

        grams = QuantityConverter.convert_to_grams(
            ingredient.name,
            ingredient.quantity,
            ingredient.unit,
            nutrition,
        )

        factor = grams / 100.00
        estimated = norm_unit not in {"g", "kg", "oz", "lb"}

        return ScaledNutrition(
            ingredient=ingredient,
            nutrition=nutrition,
            calories=nutrition.calories * factor,
            protein=nutrition.protein * factor,
            carbohydrates=nutrition.carbohydrates * factor,
            fat=nutrition.fat * factor,
            fiber=nutrition.fiber * factor,
            sugar=nutrition.sugar * factor,
            sodium=nutrition.sodium * factor,
            estimated_quantity=estimated,
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