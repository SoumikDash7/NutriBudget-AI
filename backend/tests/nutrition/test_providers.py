"""
Provider priority tests.

These tests verify that NutritionEngine correctly applies provider
priority: the first provider that returns a result wins; providers
that raise IngredientNotFoundError are skipped.
"""

import pytest

from app.services.calculators.food_nutrition.engine import (
    NutritionEngine,
)
from app.services.calculators.food_nutrition.exceptions import (
    IngredientNotFoundError,
)
from app.services.calculators.food_nutrition.models import (
    Ingredient,
    IngredientMatch,
    NutritionFacts,
)


# ---------------------------------------------------------------------------
# Local stub providers
# ---------------------------------------------------------------------------

class AlwaysFailProvider:
    """Simulates a provider that never has the requested ingredient."""

    async def lookup(self, ingredient: IngredientMatch) -> NutritionFacts:
        raise IngredientNotFoundError(
            f"AlwaysFailProvider: '{ingredient.canonical_name}' not found."
        )


class FixedProvider:
    """Returns a predetermined NutritionFacts for any ingredient."""

    def __init__(self, food_name: str, calories: float) -> None:
        self.food_name = food_name
        self.calories = calories

    async def lookup(self, ingredient: IngredientMatch) -> NutritionFacts:
        return NutritionFacts(
            food_name=self.food_name,
            calories=self.calories,
            protein=0,
            carbohydrates=0,
            fat=0,
            fiber=0,
            sugar=0,
            sodium=0,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_provider_wins():
    """Engine returns the result from the first provider that succeeds."""
    primary = FixedProvider("Primary Result", calories=100)
    secondary = FixedProvider("Secondary Result", calories=999)

    engine = NutritionEngine([primary, secondary])

    result = await engine.analyze(
        [Ingredient("anything", 100, "g")]
    )

    assert result.scaled_items[0].nutrition.food_name == "Primary Result"


@pytest.mark.asyncio
async def test_fallback_to_second_provider():
    """Engine falls back to the second provider when the first fails."""
    engine = NutritionEngine(
        [
            AlwaysFailProvider(),
            FixedProvider("Fallback Result", calories=200),
        ]
    )

    result = await engine.analyze(
        [Ingredient("anything", 100, "g")]
    )

    assert result.scaled_items[0].nutrition.food_name == "Fallback Result"


@pytest.mark.asyncio
async def test_all_providers_fail_raises():
    """Engine raises IngredientNotFoundError when all providers fail."""
    engine = NutritionEngine(
        [
            AlwaysFailProvider(),
            AlwaysFailProvider(),
        ]
    )

    with pytest.raises(IngredientNotFoundError):
        await engine.analyze(
            [Ingredient("Unknown Food", 100, "g")]
        )


def test_empty_provider_list_raises():
    """Constructing NutritionEngine with no providers raises ValueError."""
    with pytest.raises(ValueError, match="at least one provider"):
        NutritionEngine([])