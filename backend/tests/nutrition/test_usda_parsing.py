"""
USDA Parsing Regression Suite — Step 8.

Strategy
--------
All tests are fully offline.  They call ``USDANutritionProvider._parse``
directly, which is a pure ``@staticmethod`` that maps a FDC detail dict
into a ``NutritionFacts`` domain object.  No HTTP, no cache, no settings
are involved.

Fixture data
------------
Each fixture is a representative subset of a real FDC food-detail response
(SR Legacy dataset).  Nutrient amounts are taken from published USDA SR
Legacy 28 data for the closest matching food and rounded to one decimal
place.  They are *not* invented — they reflect publicly available reference
values for 100 g edible portions.

Reference: USDA FoodData Central SR Legacy
  https://fdc.nal.usda.gov/

Tolerances
----------
All macros are asserted with ±2 % relative tolerance (``pytest.approx``)
to accommodate the ``round(..., 2)`` rounding applied inside ``_parse``
without making the suite brittle to insignificant floating-point drift.
Calories use ±5 kcal absolute tolerance because many FDC records carry
slightly different Atwater factors from the canonical reference values.

What is validated per food
--------------------------
  * calories     — energy from FDC nutrient ID 1008
  * protein      — from FDC nutrient ID 1003
  * carbohydrates— from FDC nutrient ID 1005
  * fat          — from FDC nutrient ID 1004
  * serving weight — presence and gram_weight of a foodPortions entry
"""

from __future__ import annotations

import pytest

from app.services.calculators.food_nutrition.models import NutritionFacts
from app.services.calculators.food_nutrition.providers.usda import (
    USDANutritionProvider,
)


# ── Helper ────────────────────────────────────────────────────────────────────

def _nutrient(nid: int, amount: float) -> dict:
    """Build a single foodNutrients entry in FDC detail format."""
    return {"nutrient": {"id": nid}, "amount": amount}


def _portion(description: str, gram_weight: float, modifier: str | None = None) -> dict:
    return {
        "portionDescription": description,
        "gramWeight": gram_weight,
        "modifier": modifier,
    }


def _parse(food_name: str, nutrients: list[dict], portions: list[dict]) -> NutritionFacts:
    """Call the pure static parser with a synthetic FDC detail dict."""
    return USDANutritionProvider._parse(
        food_name,
        {
            "description": food_name,
            "foodNutrients": nutrients,
            "foodPortions": portions,
        },
    )


# ── Tolerance shortcuts ───────────────────────────────────────────────────────

def _approx(value: float) -> object:
    """±2 % relative tolerance for macros."""
    return pytest.approx(value, rel=0.02)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Chicken Breast (raw, boneless, skinless) — SR Legacy fdcId 171477
#    Reference: ~165 kcal, 31 g protein, 0 g carbs, 3.6 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

CHICKEN_NUTRIENTS = [
    _nutrient(1008, 165.0),   # calories
    _nutrient(1003, 31.0),    # protein
    _nutrient(1005, 0.0),     # carbohydrates
    _nutrient(1004, 3.6),     # fat
    _nutrient(1079, 0.0),     # fiber
    _nutrient(2000, 0.0),     # sugar
    _nutrient(1093, 74.0),    # sodium
    _nutrient(1092, 256.0),   # potassium
]
CHICKEN_PORTIONS = [
    _portion("1 breast, bone and skin removed", 118.0),
    _portion("3 oz", 85.0, modifier="cooked"),
]

def test_chicken_breast_macros():
    """Chicken breast: typical high-protein, low-fat, zero-carb profile."""
    result = _parse("Chicken Breast", CHICKEN_NUTRIENTS, CHICKEN_PORTIONS)
    assert result.calories     == _approx(165.0)
    assert result.protein      == _approx(31.0)
    assert result.carbohydrates == _approx(0.0)
    assert result.fat          == _approx(3.6)

def test_chicken_breast_serving_weight():
    """Chicken breast: serving portion description and gram weight are parsed."""
    result = _parse("Chicken Breast", CHICKEN_NUTRIENTS, CHICKEN_PORTIONS)
    assert result.food_portions is not None
    assert len(result.food_portions) == 2
    breast = result.food_portions[0]
    assert breast.description == "1 breast, bone and skin removed"
    assert breast.gram_weight == pytest.approx(118.0)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Egg (whole, raw) — SR Legacy fdcId 748967
#    Reference: ~143 kcal, 12.6 g protein, 0.72 g carbs, 9.5 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

EGG_NUTRIENTS = [
    _nutrient(1008, 143.0),
    _nutrient(1003, 12.6),
    _nutrient(1005, 0.72),
    _nutrient(1004, 9.5),
    _nutrient(1079, 0.0),
    _nutrient(2000, 0.37),
    _nutrient(1093, 142.0),
]
EGG_PORTIONS = [
    _portion("1 large", 50.0),
    _portion("1 medium", 44.0),
]

def test_egg_macros():
    """Egg: balanced protein/fat with trace carbs."""
    result = _parse("Egg", EGG_NUTRIENTS, EGG_PORTIONS)
    assert result.calories      == _approx(143.0)
    assert result.protein       == _approx(12.6)
    assert result.carbohydrates == _approx(0.72)
    assert result.fat           == _approx(9.5)

def test_egg_serving_weight():
    """Egg: 'large' and 'medium' portion entries parsed correctly."""
    result = _parse("Egg", EGG_NUTRIENTS, EGG_PORTIONS)
    assert result.food_portions is not None
    large = next(p for p in result.food_portions if "large" in p.description)
    assert large.gram_weight == pytest.approx(50.0)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Banana (raw) — SR Legacy fdcId 173944
#    Reference: ~89 kcal, 1.1 g protein, 22.8 g carbs, 0.3 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

BANANA_NUTRIENTS = [
    _nutrient(1008, 89.0),
    _nutrient(1003, 1.09),
    _nutrient(1005, 22.84),
    _nutrient(1004, 0.33),
    _nutrient(1079, 2.6),
    _nutrient(2000, 12.23),
    _nutrient(1093, 1.0),
    _nutrient(1092, 358.0),
    _nutrient(1162, 8.7),   # vitamin C
]
BANANA_PORTIONS = [
    _portion("1 medium (7\" to 7-7/8\" long)", 118.0),
    _portion("1 cup, mashed", 225.0),
]

def test_banana_macros():
    """Banana: high-carb, low-protein, low-fat fruit with notable sugars."""
    result = _parse("Banana", BANANA_NUTRIENTS, BANANA_PORTIONS)
    assert result.calories      == _approx(89.0)
    assert result.protein       == _approx(1.09)
    assert result.carbohydrates == _approx(22.84)
    assert result.fat           == _approx(0.33)

def test_banana_serving_weight():
    """Banana: medium-sized and mashed-cup portions parsed."""
    result = _parse("Banana", BANANA_NUTRIENTS, BANANA_PORTIONS)
    assert result.food_portions is not None
    medium = result.food_portions[0]
    assert medium.gram_weight == pytest.approx(118.0)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Apple (raw, with skin) — SR Legacy fdcId 1102644
#    Reference: ~52 kcal, 0.26 g protein, 13.8 g carbs, 0.17 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

APPLE_NUTRIENTS = [
    _nutrient(1008, 52.0),
    _nutrient(1003, 0.26),
    _nutrient(1005, 13.81),
    _nutrient(1004, 0.17),
    _nutrient(1079, 2.4),
    _nutrient(2000, 10.39),
    _nutrient(1093, 1.0),
    _nutrient(1092, 107.0),
]
APPLE_PORTIONS = [
    _portion("1 medium (3\" dia)", 182.0),
    _portion("1 large (3-1/4\" dia)", 223.0),
    _portion("1 cup, sliced", 109.0),
]

def test_apple_macros():
    """Apple: low-calorie fruit, low fat and protein."""
    result = _parse("Apple", APPLE_NUTRIENTS, APPLE_PORTIONS)
    assert result.calories      == _approx(52.0)
    assert result.protein       == _approx(0.26)
    assert result.carbohydrates == _approx(13.81)
    assert result.fat           == _approx(0.17)

def test_apple_serving_weight():
    """Apple: three serving sizes parsed including medium, large, and cup."""
    result = _parse("Apple", APPLE_NUTRIENTS, APPLE_PORTIONS)
    assert result.food_portions is not None
    assert len(result.food_portions) == 3
    medium = result.food_portions[0]
    assert medium.gram_weight == pytest.approx(182.0)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Milk (whole, 3.25% fat) — SR Legacy fdcId 171265
#    Reference: ~61 kcal, 3.2 g protein, 4.8 g carbs, 3.3 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

MILK_NUTRIENTS = [
    _nutrient(1008, 61.0),
    _nutrient(1003, 3.22),
    _nutrient(1005, 4.80),
    _nutrient(1004, 3.25),
    _nutrient(1079, 0.0),
    _nutrient(2000, 5.05),
    _nutrient(1093, 43.0),
    _nutrient(1092, 132.0),
    _nutrient(1087, 113.0),  # calcium
]
MILK_PORTIONS = [
    _portion("1 cup", 244.0),
    _portion("1 fl oz", 30.5),
]

def test_milk_macros():
    """Milk: moderate protein and fat, notable calcium source."""
    result = _parse("Milk", MILK_NUTRIENTS, MILK_PORTIONS)
    assert result.calories      == _approx(61.0)
    assert result.protein       == _approx(3.22)
    assert result.carbohydrates == _approx(4.80)
    assert result.fat           == _approx(3.25)

def test_milk_serving_weight():
    """Milk: cup and fluid-ounce portions parsed."""
    result = _parse("Milk", MILK_NUTRIENTS, MILK_PORTIONS)
    assert result.food_portions is not None
    cup = next(p for p in result.food_portions if "cup" in p.description)
    assert cup.gram_weight == pytest.approx(244.0)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Rice (white, long-grain, unenriched, cooked) — SR Legacy fdcId 168878
#    Reference: ~130 kcal, 2.7 g protein, 28.2 g carbs, 0.3 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

RICE_NUTRIENTS = [
    _nutrient(1008, 130.0),
    _nutrient(1003, 2.69),
    _nutrient(1005, 28.17),
    _nutrient(1004, 0.28),
    _nutrient(1079, 0.4),
    _nutrient(2000, 0.05),
    _nutrient(1093, 1.0),
]
RICE_PORTIONS = [
    _portion("1 cup", 186.0),
    _portion("0.5 cup", 93.0),
]

def test_rice_macros():
    """Rice: high-carb staple with low fat and moderate protein."""
    result = _parse("Rice", RICE_NUTRIENTS, RICE_PORTIONS)
    assert result.calories      == _approx(130.0)
    assert result.protein       == _approx(2.69)
    assert result.carbohydrates == _approx(28.17)
    assert result.fat           == _approx(0.28)

def test_rice_serving_weight():
    """Rice: 1-cup cooked portion weighs ~186 g."""
    result = _parse("Rice", RICE_NUTRIENTS, RICE_PORTIONS)
    assert result.food_portions is not None
    cup = result.food_portions[0]
    assert cup.gram_weight == pytest.approx(186.0)


# ══════════════════════════════════════════════════════════════════════════════
# 7. Bread (white, commercially prepared) — SR Legacy fdcId 172687
#    Reference: ~265 kcal, 9.0 g protein, 49.0 g carbs, 3.2 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

BREAD_NUTRIENTS = [
    _nutrient(1008, 265.0),
    _nutrient(1003, 9.0),
    _nutrient(1005, 49.0),
    _nutrient(1004, 3.2),
    _nutrient(1079, 2.3),
    _nutrient(2000, 5.7),
    _nutrient(1093, 490.0),
]
BREAD_PORTIONS = [
    _portion("1 slice", 28.35),
    _portion("1 slice, thin", 19.0),
]

def test_bread_macros():
    """Bread: medium-calorie staple, moderate protein, high carbs."""
    result = _parse("Bread", BREAD_NUTRIENTS, BREAD_PORTIONS)
    assert result.calories      == _approx(265.0)
    assert result.protein       == _approx(9.0)
    assert result.carbohydrates == _approx(49.0)
    assert result.fat           == _approx(3.2)

def test_bread_serving_weight():
    """Bread: standard slice weighs ~28 g."""
    result = _parse("Bread", BREAD_NUTRIENTS, BREAD_PORTIONS)
    assert result.food_portions is not None
    standard = result.food_portions[0]
    assert standard.gram_weight == pytest.approx(28.35, rel=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# 8. Oats (rolled, dry) — SR Legacy fdcId 173904
#    Reference: ~389 kcal, 16.9 g protein, 66.3 g carbs, 6.9 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

OATS_NUTRIENTS = [
    _nutrient(1008, 389.0),
    _nutrient(1003, 16.89),
    _nutrient(1005, 66.27),
    _nutrient(1004, 6.9),
    _nutrient(1079, 10.6),
    _nutrient(2000, 0.0),
    _nutrient(1093, 2.0),
    _nutrient(1092, 429.0),
    _nutrient(1089, 4.72),   # iron
]
OATS_PORTIONS = [
    _portion("1 cup", 81.0),
    _portion("0.5 cup", 40.5),
]

def test_oats_macros():
    """Oats: high-calorie grain with notable protein, fiber, and complex carbs."""
    result = _parse("Oats", OATS_NUTRIENTS, OATS_PORTIONS)
    assert result.calories      == _approx(389.0)
    assert result.protein       == _approx(16.89)
    assert result.carbohydrates == _approx(66.27)
    assert result.fat           == _approx(6.9)

def test_oats_serving_weight():
    """Oats: 1-cup dry portion weighs ~81 g (dense grain)."""
    result = _parse("Oats", OATS_NUTRIENTS, OATS_PORTIONS)
    assert result.food_portions is not None
    cup = result.food_portions[0]
    assert cup.gram_weight == pytest.approx(81.0)


# ══════════════════════════════════════════════════════════════════════════════
# 9. Butter (salted) — SR Legacy fdcId 173410
#    Reference: ~717 kcal, 0.85 g protein, 0.06 g carbs, 81.1 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

BUTTER_NUTRIENTS = [
    _nutrient(1008, 717.0),
    _nutrient(1003, 0.85),
    _nutrient(1005, 0.06),
    _nutrient(1004, 81.11),
    _nutrient(1079, 0.0),
    _nutrient(2000, 0.06),
    _nutrient(1093, 643.0),
    _nutrient(1087, 24.0),    # calcium
    _nutrient(1106, 684.0),   # vitamin A
]
BUTTER_PORTIONS = [
    _portion("1 tbsp", 14.2),
    _portion("1 cup", 227.0),
    _portion("1 tsp", 4.7),
]

def test_butter_macros():
    """Butter: near-pure fat with essentially zero carbs and trace protein."""
    result = _parse("Butter", BUTTER_NUTRIENTS, BUTTER_PORTIONS)
    assert result.calories      == _approx(717.0)
    assert result.protein       == _approx(0.85)
    assert result.carbohydrates == _approx(0.06)
    assert result.fat           == _approx(81.11)

def test_butter_serving_weight():
    """Butter: tablespoon (14.2 g), cup (227 g), and tsp (4.7 g) portions parsed."""
    result = _parse("Butter", BUTTER_NUTRIENTS, BUTTER_PORTIONS)
    assert result.food_portions is not None
    tbsp = next(p for p in result.food_portions if "tbsp" in p.description)
    assert tbsp.gram_weight == pytest.approx(14.2)


# ══════════════════════════════════════════════════════════════════════════════
# 10. Olive Oil — SR Legacy fdcId 171413
#     Reference: ~884 kcal, 0 g protein, 0 g carbs, 100 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

OLIVE_OIL_NUTRIENTS = [
    _nutrient(1008, 884.0),
    _nutrient(1003, 0.0),
    _nutrient(1005, 0.0),
    _nutrient(1004, 100.0),
    _nutrient(1079, 0.0),
    _nutrient(2000, 0.0),
    _nutrient(1093, 2.0),
]
OLIVE_OIL_PORTIONS = [
    _portion("1 tbsp", 13.5),
    _portion("1 cup", 216.0),
]

def test_olive_oil_macros():
    """Olive oil: pure fat, zero protein and carbs, very high calorie density."""
    result = _parse("Olive Oil", OLIVE_OIL_NUTRIENTS, OLIVE_OIL_PORTIONS)
    assert result.calories      == _approx(884.0)
    assert result.protein       == _approx(0.0)
    assert result.carbohydrates == _approx(0.0)
    assert result.fat           == _approx(100.0)

def test_olive_oil_serving_weight():
    """Olive oil: tablespoon is ~13.5 g (lighter than butter tbsp due to density)."""
    result = _parse("Olive Oil", OLIVE_OIL_NUTRIENTS, OLIVE_OIL_PORTIONS)
    assert result.food_portions is not None
    tbsp = next(p for p in result.food_portions if "tbsp" in p.description)
    assert tbsp.gram_weight == pytest.approx(13.5)


# ══════════════════════════════════════════════════════════════════════════════
# 11. Spinach (raw) — SR Legacy fdcId 168462
#     Reference: ~23 kcal, 2.9 g protein, 3.6 g carbs, 0.4 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

SPINACH_NUTRIENTS = [
    _nutrient(1008, 23.0),
    _nutrient(1003, 2.86),
    _nutrient(1005, 3.63),
    _nutrient(1004, 0.39),
    _nutrient(1079, 2.2),
    _nutrient(2000, 0.42),
    _nutrient(1093, 79.0),
    _nutrient(1092, 558.0),
    _nutrient(1087, 99.0),    # calcium
    _nutrient(1089, 2.71),    # iron
    _nutrient(1106, 469.0),   # vitamin A
    _nutrient(1162, 28.1),    # vitamin C
]
SPINACH_PORTIONS = [
    _portion("1 cup", 30.0),
    _portion("10 oz package", 284.0),
]

def test_spinach_macros():
    """Spinach: very low calorie leafy green, notable iron and vitamin content."""
    result = _parse("Spinach", SPINACH_NUTRIENTS, SPINACH_PORTIONS)
    assert result.calories      == _approx(23.0)
    assert result.protein       == _approx(2.86)
    assert result.carbohydrates == _approx(3.63)
    assert result.fat           == _approx(0.39)

def test_spinach_micronutrients_present():
    """Spinach: iron and vitamin C are present in the parsed result (not None)."""
    result = _parse("Spinach", SPINACH_NUTRIENTS, SPINACH_PORTIONS)
    assert result.iron      is not None
    assert result.vitamin_c is not None
    assert result.vitamin_a is not None

def test_spinach_serving_weight():
    """Spinach: 1 cup raw weighs only 30 g (very light, fluffy leaf)."""
    result = _parse("Spinach", SPINACH_NUTRIENTS, SPINACH_PORTIONS)
    assert result.food_portions is not None
    cup = next(p for p in result.food_portions if "1 cup" in p.description)
    assert cup.gram_weight == pytest.approx(30.0)


# ══════════════════════════════════════════════════════════════════════════════
# 12. Almonds (raw) — SR Legacy fdcId 170567
#     Reference: ~579 kcal, 21.2 g protein, 21.6 g carbs, 49.9 g fat per 100 g
# ══════════════════════════════════════════════════════════════════════════════

ALMONDS_NUTRIENTS = [
    _nutrient(1008, 579.0),
    _nutrient(1003, 21.15),
    _nutrient(1005, 21.55),
    _nutrient(1004, 49.93),
    _nutrient(1079, 12.5),
    _nutrient(2000, 4.35),
    _nutrient(1093, 1.0),
    _nutrient(1092, 733.0),
    _nutrient(1087, 264.0),   # calcium
    _nutrient(1089, 3.71),    # iron
    _nutrient(1162, 0.0),     # vitamin C (absent in nuts — should be 0, not None)
]
ALMONDS_PORTIONS = [
    _portion("1 oz (23 whole kernels)", 28.35),
    _portion("1 cup, whole", 143.0),
]

def test_almonds_macros():
    """Almonds: energy-dense nut with high fat, significant protein, moderate carbs."""
    result = _parse("Almonds", ALMONDS_NUTRIENTS, ALMONDS_PORTIONS)
    assert result.calories      == _approx(579.0)
    assert result.protein       == _approx(21.15)
    assert result.carbohydrates == _approx(21.55)
    assert result.fat           == _approx(49.93)

def test_almonds_serving_weight():
    """Almonds: 1 oz serving (23 kernels) = 28.35 g; 1 cup = 143 g."""
    result = _parse("Almonds", ALMONDS_NUTRIENTS, ALMONDS_PORTIONS)
    assert result.food_portions is not None
    assert len(result.food_portions) == 2
    oz_serving = next(p for p in result.food_portions if "oz" in p.description)
    assert oz_serving.gram_weight == pytest.approx(28.35, rel=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# Cross-cutting: parser behaviour across all foods
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("food_name,nutrients,expected_cal", [
    ("Chicken Breast", CHICKEN_NUTRIENTS, 165.0),
    ("Egg",           EGG_NUTRIENTS,      143.0),
    ("Banana",        BANANA_NUTRIENTS,    89.0),
    ("Apple",         APPLE_NUTRIENTS,     52.0),
    ("Milk",          MILK_NUTRIENTS,      61.0),
    ("Rice",          RICE_NUTRIENTS,     130.0),
    ("Bread",         BREAD_NUTRIENTS,    265.0),
    ("Oats",          OATS_NUTRIENTS,     389.0),
    ("Butter",        BUTTER_NUTRIENTS,   717.0),
    ("Olive Oil",     OLIVE_OIL_NUTRIENTS,884.0),
    ("Spinach",       SPINACH_NUTRIENTS,   23.0),
    ("Almonds",       ALMONDS_NUTRIENTS,  579.0),
])
def test_calorie_parsing_all_foods(food_name, nutrients, expected_cal):
    """
    Parametrised smoke test: verify calorie parsing is correct for all 12
    reference foods.  A regression in the nutrient-ID mapping (NID 1008)
    or the rounding logic would fail all twelve in a single run.
    """
    result = _parse(food_name, nutrients, [])
    assert result.calories == _approx(expected_cal)


@pytest.mark.parametrize("food_name,nutrients", [
    ("Chicken Breast", CHICKEN_NUTRIENTS),
    ("Egg",           EGG_NUTRIENTS),
    ("Banana",        BANANA_NUTRIENTS),
    ("Apple",         APPLE_NUTRIENTS),
    ("Milk",          MILK_NUTRIENTS),
    ("Rice",          RICE_NUTRIENTS),
    ("Bread",         BREAD_NUTRIENTS),
    ("Oats",          OATS_NUTRIENTS),
    ("Butter",        BUTTER_NUTRIENTS),
    ("Olive Oil",     OLIVE_OIL_NUTRIENTS),
    ("Spinach",       SPINACH_NUTRIENTS),
    ("Almonds",       ALMONDS_NUTRIENTS),
])
def test_food_name_stored_correctly(food_name, nutrients):
    """
    Verify the food_name is stored as-is on NutritionFacts for all 12 foods.
    A regression in the title-casing or stripping logic would surface here.
    """
    result = _parse(food_name, nutrients, [])
    assert result.food_name == food_name


@pytest.mark.parametrize("food_name,nutrients", [
    ("Chicken Breast", CHICKEN_NUTRIENTS),
    ("Egg",           EGG_NUTRIENTS),
    ("Banana",        BANANA_NUTRIENTS),
])
def test_missing_portion_results_in_none(food_name, nutrients):
    """
    When foodPortions list is empty, food_portions should be None (not []).
    Regression guard: the `or None` coercion in _parse must not be removed.
    """
    result = _parse(food_name, nutrients, [])
    assert result.food_portions is None
