"""
Unit tests for QuantityConverter.
"""

import pytest

from app.services.calculators.food_nutrition.converter import (
    QuantityConverter,
)
from app.services.calculators.food_nutrition.models import (
    FoodPortion,
    NutritionFacts,
)


def test_normalize_unit():
    """Verify units are normalized correctly."""
    assert QuantityConverter.normalize_unit("Grams") == "g"
    assert QuantityConverter.normalize_unit("cups") == "cup"
    assert QuantityConverter.normalize_unit("Tablespoon") == "tbsp"
    assert QuantityConverter.normalize_unit("UnknownUnit") == "unknownunit"


def test_convert_to_grams_usda_portions():
    """Verify USDA portion has highest priority."""
    # USDA portion: 1 cup = 158 g for Rice
    portions = [
        FoodPortion(description="1 cup", gram_weight=158.0),
        FoodPortion(description="1 serving", gram_weight=150.0),
    ]
    facts = NutritionFacts(
        food_name="Rice",
        calories=130,
        protein=2.7,
        carbohydrates=28.2,
        fat=0.3,
        fiber=0.4,
        sugar=0.1,
        sodium=1.0,
        food_portions=portions,
    )

    # USDA portion matches (158 g per cup * 2 cups = 316 g)
    res = QuantityConverter.convert_to_grams("Rice", 2.0, "cups", facts)
    assert res == 316.0


def test_convert_to_grams_manual_fallback():
    """Verify fallback to manual conversion table when no USDA portion match exists."""
    facts_no_portions = NutritionFacts(
        food_name="Butter",
        calories=717,
        protein=0.85,
        carbohydrates=0.06,
        fat=81.11,
        fiber=0,
        sugar=0.06,
        sodium=11,
        food_portions=None,
    )

    # Butter tbsp is in manual conversion tables (14.2 g * 3 tbsp = 42.6 g)
    res = QuantityConverter.convert_to_grams(
        "Butter", 3.0, "tbsp", facts_no_portions
    )
    assert res == pytest.approx(42.6)


def test_convert_to_grams_generic_fallback():
    """Verify fallback to generic density estimation when neither USDA nor manual maps exist."""
    facts = NutritionFacts(
        food_name="Unknown Vegetable",
        calories=50,
        protein=1.0,
        carbohydrates=10.0,
        fat=0.1,
        fiber=1.0,
        sugar=2.0,
        sodium=5.0,
        food_portions=None,
    )

    # Generic cup weight is 240g
    res = QuantityConverter.convert_to_grams(
        "Unknown Vegetable", 1.5, "cups", facts
    )
    assert res == 360.0
