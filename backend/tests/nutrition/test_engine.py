import pytest

from app.services.calculators.food_nutrition.engine import (
    NutritionEngine,
)
from app.services.calculators.food_nutrition.models import (
    Ingredient,
)
from app.services.calculators.food_nutrition.exceptions import (
    UnsupportedUnitError,
)


@pytest.mark.asyncio
async def test_engine_calculates_totals(
    provider,
    chicken,
):
    engine = NutritionEngine([provider])

    result = await engine.analyze([chicken])

    assert round(result.total_calories, 1) == 412.5
    assert round(result.total_protein, 1) == 77.5


@pytest.mark.asyncio
async def test_engine_multiple_items(
    provider,
    chicken,
    butter,
):
    engine = NutritionEngine([provider])

    result = await engine.analyze(
        [
            chicken,
            butter,
        ]
    )

    assert result.total_calories > 500


@pytest.mark.asyncio
async def test_invalid_unit(provider):
    engine = NutritionEngine([provider])

    ingredient = Ingredient(
        "Chicken Breast",
        1,
        "invalid_unit",
    )

    with pytest.raises(UnsupportedUnitError):
        await engine.analyze([ingredient])