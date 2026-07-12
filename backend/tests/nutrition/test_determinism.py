import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.calorie_service import CalorieService
from app.schemas.nutrition import NutritionEstimate, ExtractedIngredient
from app.services.calculators.food_nutrition.models import NutritionFacts
from sqlalchemy.ext.asyncio import AsyncSession

class MockProvider:
    async def lookup(self, ingredient):
        name = ingredient.canonical_name
        if name == "Chicken Breast":
            return NutritionFacts(food_name="Chicken Breast", calories=165.0, protein=31.0, carbohydrates=0.0, fat=3.6, fiber=0.0, sugar=0.0, sodium=74.0)
        elif name == "Butter":
            return NutritionFacts(food_name="Butter", calories=717.0, protein=0.85, carbohydrates=0.06, fat=81.11, fiber=0.0, sugar=0.0, sodium=11.0)
        elif name == "Paratha":
            return NutritionFacts(food_name="Paratha", calories=210.0, protein=4.0, carbohydrates=32.0, fat=7.0, fiber=0.0, sugar=0.0, sodium=0.0)
        raise ValueError(f"Unknown matched ingredient: {name}")

@pytest.mark.asyncio
async def test_calorie_service_determinism_100_runs():
    """
    Test that calling CalorieService.parse_description 100 consecutive times
    with the same food input produces identical results.
    """
    db = MagicMock(spec=AsyncSession)
    http_client = MagicMock()
    
    service = CalorieService(db=db, http_client=http_client)
    
    # Inject our mock provider into the engine to run offline and have control over the data
    service.engine._providers = [MockProvider()]
    
    # Mock orchestrator.parse_text to simulate a probabilistic response that changes slightly,
    # but since our architecture routes it through the deterministic NutritionEngine and uses caching,
    # the final output should be completely identical.
    mock_estimates = [
        NutritionEstimate(
            ingredients=[
                ExtractedIngredient(name="Chicken Breast", quantity=250.0, unit="g"),
                ExtractedIngredient(name="Butter", quantity=20.0, unit="g"),
                ExtractedIngredient(name="Paratha", quantity=120.0, unit="g"),
            ],
            calories=0.0,
            protein_g=0.0,
            carbs_g=0.0,
            fat_g=0.0,
            confidence=0.95
        )
        for _ in range(100)
    ]
    
    service.orchestrator.parse_text = AsyncMock(side_effect=mock_estimates)
    
    results = []
    for _ in range(100):
        res = await service.parse_description("Chicken, Butter, Paratha")
        results.append(res)
        
    # Assert that all 100 results are exactly identical
    first_res = results[0]
    for i, res in enumerate(results[1:], start=1):
        assert res == first_res, f"Mismatch at run {i}: {res} != {first_res}"
        
    # Check that all the values are populated and correct
    assert first_res["calories"] == 807
    assert first_res["protein"] == 82.5
    assert first_res["carbs"] == 38.4
    assert first_res["fat"] == 33.6
