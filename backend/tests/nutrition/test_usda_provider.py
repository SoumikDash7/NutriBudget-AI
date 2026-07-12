"""
Unit tests for USDANutritionProvider.

Uses a mock httpx.AsyncClient to avoid real network calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.calculators.food_nutrition.providers.usda import (
    USDANutritionProvider,
)
from app.services.calculators.food_nutrition.exceptions import (
    FoodDatabaseUnavailableError,
    IngredientNotFoundError,
)
from app.services.calculators.food_nutrition.models import IngredientMatch


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_search_response(foods: list[dict]) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"foods": foods}
    return r


def _make_detail_response(detail: dict) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = detail
    return r


def _make_client(search_resp, detail_resp) -> AsyncMock:
    client = AsyncMock()
    client.get = AsyncMock(side_effect=[search_resp, detail_resp])
    return client


CHICKEN_SEARCH = {
    "fdcId": 171477,
    "description": "Chicken, broilers or fryers, breast, meat only, raw",
    "foodNutrients": [
        {"nutrientId": 1008, "value": 120},   # calories
        {"nutrientId": 1003, "value": 22.5},  # protein
        {"nutrientId": 1005, "value": 0.0},   # carbs
        {"nutrientId": 1004, "value": 2.6},   # fat
    ],
}

CHICKEN_DETAIL = {
    "description": "Chicken, broilers or fryers, breast, meat only, raw",
    "foodNutrients": [
        {"nutrient": {"id": 1008}, "amount": 120.0},
        {"nutrient": {"id": 1003}, "amount": 22.5},
        {"nutrient": {"id": 1005}, "amount": 0.0},
        {"nutrient": {"id": 1004}, "amount": 2.6},
        {"nutrient": {"id": 1079}, "amount": 0.0},
        {"nutrient": {"id": 2000}, "amount": 0.0},
        {"nutrient": {"id": 1093}, "amount": 74.0},
        {"nutrient": {"id": 1092}, "amount": 256.0},
        {"nutrient": {"id": 1162}, "amount": 0.0},
    ],
    "foodPortions": [
        {
            "portionDescription": "1 breast",
            "gramWeight": 118.0,
            "modifier": None,
        },
        {
            "portionDescription": "3 oz",
            "gramWeight": 85.0,
            "modifier": "cooked",
        },
    ],
}

MATCH = IngredientMatch("Chicken Breast", "Chicken Breast", 1.0)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lookup_returns_nutrition_facts(monkeypatch):
    monkeypatch.setattr(
        "app.services.calculators.food_nutrition.providers.usda.settings",
        MagicMock(USDA_API_KEY="test-key"),
    )

    client = _make_client(
        _make_search_response([CHICKEN_SEARCH]),
        _make_detail_response(CHICKEN_DETAIL),
    )

    provider = USDANutritionProvider(client)
    result = await provider.lookup(MATCH)

    assert result.food_name == "Chicken, Broilers Or Fryers, Breast, Meat Only, Raw"
    assert result.calories == 120.0
    assert result.protein == 22.5
    assert result.sodium == 74.0
    assert result.potassium == 256.0


@pytest.mark.asyncio
async def test_food_portions_parsed(monkeypatch):
    monkeypatch.setattr(
        "app.services.calculators.food_nutrition.providers.usda.settings",
        MagicMock(USDA_API_KEY="test-key"),
    )

    client = _make_client(
        _make_search_response([CHICKEN_SEARCH]),
        _make_detail_response(CHICKEN_DETAIL),
    )

    provider = USDANutritionProvider(client)
    result = await provider.lookup(MATCH)

    assert result.food_portions is not None
    assert len(result.food_portions) == 2
    assert result.food_portions[0].description == "1 breast"
    assert result.food_portions[0].gram_weight == 118.0
    assert result.food_portions[1].modifier == "cooked"


@pytest.mark.asyncio
async def test_no_api_key_raises(monkeypatch):
    monkeypatch.setattr(
        "app.services.calculators.food_nutrition.providers.usda.settings",
        MagicMock(USDA_API_KEY=None),
    )
    provider = USDANutritionProvider(AsyncMock())
    with pytest.raises(FoodDatabaseUnavailableError):
        await provider.lookup(MATCH)


@pytest.mark.asyncio
async def test_empty_search_results_raises(monkeypatch):
    monkeypatch.setattr(
        "app.services.calculators.food_nutrition.providers.usda.settings",
        MagicMock(USDA_API_KEY="test-key"),
    )
    client = AsyncMock()
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"foods": []}
    client.get = AsyncMock(return_value=r)

    provider = USDANutritionProvider(client)
    with pytest.raises(IngredientNotFoundError):
        await provider.lookup(MATCH)


@pytest.mark.asyncio
async def test_missing_micronutrients_are_none(monkeypatch):
    """Micronutrients absent from the FDC response default to None, not 0."""
    monkeypatch.setattr(
        "app.services.calculators.food_nutrition.providers.usda.settings",
        MagicMock(USDA_API_KEY="test-key"),
    )

    # Detail with no vitamin fields
    detail_no_vitamins = {
        "description": "Chicken breast",
        "foodNutrients": [
            {"nutrient": {"id": 1008}, "amount": 120.0},
            {"nutrient": {"id": 1003}, "amount": 22.5},
            {"nutrient": {"id": 1005}, "amount": 0.0},
            {"nutrient": {"id": 1004}, "amount": 2.6},
            {"nutrient": {"id": 1079}, "amount": 0.0},
            {"nutrient": {"id": 2000}, "amount": 0.0},
            {"nutrient": {"id": 1093}, "amount": 74.0},
        ],
        "foodPortions": [],
    }

    client = _make_client(
        _make_search_response([CHICKEN_SEARCH]),
        _make_detail_response(detail_no_vitamins),
    )

    provider = USDANutritionProvider(client)
    result = await provider.lookup(MATCH)

    assert result.vitamin_a is None
    assert result.vitamin_c is None
    assert result.vitamin_d is None
    assert result.vitamin_b12 is None
    assert result.potassium is None


@pytest.mark.asyncio
async def test_caching_hit_and_miss_behavior(monkeypatch):
    monkeypatch.setattr(
        "app.services.calculators.food_nutrition.providers.usda.settings",
        MagicMock(USDA_API_KEY="test-key"),
    )

    from app.core.caching import InMemoryTTLCache

    # Mock client will track call counts
    client = AsyncMock()
    
    search_resp = _make_search_response([CHICKEN_SEARCH])
    detail_resp = _make_detail_response(CHICKEN_DETAIL)
    
    # We will set side_effect to return these on first calls.
    # If the provider attempts to make HTTP requests during hits, it will raise StopIteration or fail.
    client.get = AsyncMock(side_effect=[search_resp, detail_resp])

    cache = InMemoryTTLCache(default_ttl_seconds=300)
    provider = USDANutritionProvider(client, cache=cache)

    # First lookup: Should be a cache miss for both search and detail, calls client.get twice.
    res1 = await provider.lookup(MATCH)
    assert res1.food_name == "Chicken, Broilers Or Fryers, Breast, Meat Only, Raw"
    assert client.get.call_count == 2

    # Second lookup: Cache hit for both search and detail! No client.get calls.
    res2 = await provider.lookup(MATCH)
    assert res2.food_name == "Chicken, Broilers Or Fryers, Breast, Meat Only, Raw"
    # Call count remains 2
    assert client.get.call_count == 2

    # Verify keys are populated in cache
    assert cache.get("usda:search:chicken breast") is not None
    assert cache.get("usda:detail:171477") is not None
