from app.services.calculators.food_nutrition.matcher import (
    IngredientMatcher,
)
from app.services.calculators.food_nutrition.models import (
    Ingredient,
)


def test_alias_match():
    result = IngredientMatcher.match(
        Ingredient(
            "Boneless Chicken",
            100,
            "g",
        )
    )

    assert result.canonical_name == "Chicken Breast"


def test_case_insensitive():
    result = IngredientMatcher.match(
        Ingredient(
            "CHICKEN BREAST",
            100,
            "g",
        )
    )

    assert result.canonical_name == "Chicken Breast"


def test_unknown_food():
    result = IngredientMatcher.match(
        Ingredient(
            "Dragon Fruit",
            100,
            "g",
        )
    )

    assert result.canonical_name == "Dragon Fruit"