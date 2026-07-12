from __future__ import annotations

import pytest

from app.services.calculators.food_nutrition.models import (
    Ingredient,
    IngredientMatch,
    NutritionFacts,
)
from app.services.calculators.food_nutrition.databases import (
    NutritionProvider,
)
from app.services.calculators.food_nutrition.exceptions import (
    IngredientNotFoundError,
)


class FakeNutritionProvider(NutritionProvider):
    """
    Fake provider used for unit tests.
    """

    DATA = {
        "Chicken Breast": NutritionFacts(
            food_name="Chicken Breast",
            calories=165,
            protein=31,
            carbohydrates=0,
            fat=3.6,
            fiber=0,
            sugar=0,
            sodium=74,
        ),
        "Butter": NutritionFacts(
            food_name="Butter",
            calories=717,
            protein=0.85,
            carbohydrates=0.06,
            fat=81.11,
            fiber=0,
            sugar=0.06,
            sodium=11,
        ),
    }

    async def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        try:
            return self.DATA[ingredient.canonical_name]
        except KeyError as exc:
            raise IngredientNotFoundError(
                ingredient.canonical_name
            ) from exc


@pytest.fixture
def provider() -> FakeNutritionProvider:
    return FakeNutritionProvider()


@pytest.fixture
def chicken() -> Ingredient:
    return Ingredient(
        name="Chicken Breast",
        quantity=250,
        unit="g",
    )


@pytest.fixture
def butter() -> Ingredient:
    return Ingredient(
        name="Butter",
        quantity=20,
        unit="g",
    )