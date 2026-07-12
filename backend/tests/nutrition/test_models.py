import pytest

from app.services.calculators.food_nutrition.models import (
    Ingredient,
    IngredientMatch,
    NutritionFacts,
)


def test_valid_ingredient():
    ingredient = Ingredient("Rice", 100, "g")
    assert ingredient.name == "Rice"


def test_invalid_quantity():
    with pytest.raises(ValueError):
        Ingredient("Rice", 0, "g")


def test_empty_name():
    with pytest.raises(ValueError):
        Ingredient("", 100, "g")


def test_empty_unit():
    with pytest.raises(ValueError):
        Ingredient("Rice", 100, "")


def test_invalid_confidence():
    with pytest.raises(ValueError):
        IngredientMatch(
            "Rice",
            "Rice",
            1.5,
        )


def test_negative_calories():
    with pytest.raises(ValueError):
        NutritionFacts(
            food_name="Rice",
            calories=-1,
            protein=0,
            carbohydrates=0,
            fat=0,
            fiber=0,
            sugar=0,
            sodium=0,
        )