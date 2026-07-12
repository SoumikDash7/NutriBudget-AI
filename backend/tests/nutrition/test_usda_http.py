"""
Step 9 — HTTP-Mocked integration tests for USDANutritionProvider.

Strategy
--------
All tests use ``respx.mock()`` as a global context manager.  Within each
context, ``respx`` intercepts all httpx traffic from any ``httpx.AsyncClient``
instance — no real TCP connections are possible.  Using real ``httpx.Response``
objects means ``.status_code``, ``.json()``, and error propagation all follow
the production code path exactly.

Each test:
  * Enters a ``respx.mock()`` block — all HTTP is intercepted.
  * Creates a fresh ``httpx.AsyncClient()`` inside that block.
  * Passes the client to ``USDANutritionProvider``.
  * Registers routes on the router; any unregistered URL raises an error.
  * Asserts expected outcomes after the block exits.

Settings are monkeypatched to inject a fake API key in every test, so the
API-key guard in ``lookup()`` never short-circuits.

Mocked scenarios
----------------
  1. Successful search + detail (happy path)
  2. Missing micronutrients in detail → optional fields are None
  3. Missing foodPortions → food_portions is None
  4. All search candidates have zero core macros → IngredientNotFoundError
  5. Empty foods list in search response → IngredientNotFoundError
  6. HTTP 404 on search → FoodDatabaseUnavailableError
  7. HTTP 500 on search → FoodDatabaseUnavailableError
  8. HTTP 404 on detail → FoodDatabaseUnavailableError
  9. HTTP 500 on detail → FoodDatabaseUnavailableError
 10. Network timeout on search → FoodDatabaseUnavailableError
 11. Network timeout on detail → FoodDatabaseUnavailableError
 12. Cache miss — both GET calls made exactly once
 13. Cache hit — second lookup makes zero HTTP calls
 14. Provider fallback inside NutritionEngine
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.core.caching import InMemoryTTLCache
from app.services.calculators.food_nutrition.engine import NutritionEngine
from app.services.calculators.food_nutrition.exceptions import (
    FoodDatabaseUnavailableError,
    IngredientNotFoundError,
)
from app.services.calculators.food_nutrition.models import (
    Ingredient,
    IngredientMatch,
    NutritionFacts,
)
from app.services.calculators.food_nutrition.providers.usda import (
    USDANutritionProvider,
    _FDC_FOOD_URL,
    _FDC_SEARCH_URL,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_API_KEY   = "test-api-key"
_FDC_ID    = 171477
_FOOD_NAME = "Chicken, broilers or fryers, breast, meat only, raw"

_SEARCH_URL = _FDC_SEARCH_URL
_DETAIL_URL = _FDC_FOOD_URL.format(fdcId=_FDC_ID)

MATCH = IngredientMatch("Chicken Breast", "Chicken Breast", 1.0)

# ── Canonical fixtures ────────────────────────────────────────────────────────

SEARCH_FOOD = {
    "fdcId": _FDC_ID,
    "description": _FOOD_NAME,
    "foodNutrients": [
        {"nutrientId": 1008, "value": 165.0},
        {"nutrientId": 1003, "value": 31.0},
        {"nutrientId": 1005, "value": 0.0},
        {"nutrientId": 1004, "value": 3.6},
    ],
}

DETAIL_RESPONSE = {
    "description": _FOOD_NAME,
    "foodNutrients": [
        {"nutrient": {"id": 1008}, "amount": 165.0},
        {"nutrient": {"id": 1003}, "amount": 31.0},
        {"nutrient": {"id": 1005}, "amount": 0.0},
        {"nutrient": {"id": 1004}, "amount": 3.6},
        {"nutrient": {"id": 1079}, "amount": 0.0},
        {"nutrient": {"id": 2000}, "amount": 0.0},
        {"nutrient": {"id": 1093}, "amount": 74.0},
        {"nutrient": {"id": 1092}, "amount": 256.0},
        {"nutrient": {"id": 1162}, "amount": 0.0},
        {"nutrient": {"id": 1106}, "amount": 18.0},
    ],
    "foodPortions": [
        {"portionDescription": "1 breast", "gramWeight": 118.0, "modifier": None},
        {"portionDescription": "3 oz",     "gramWeight": 85.0,  "modifier": "cooked"},
    ],
}


# ── Shared fixtures / helpers ─────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Inject a fake USDA API key for every test in this module."""
    from unittest.mock import MagicMock
    monkeypatch.setattr(
        "app.services.calculators.food_nutrition.providers.usda.settings",
        MagicMock(USDA_API_KEY=_API_KEY),
    )


def _json_resp(data: dict, *, status: int = 200) -> httpx.Response:
    """Build a real httpx.Response with a JSON body."""
    return httpx.Response(
        status,
        headers={"content-type": "application/json"},
        content=json.dumps(data).encode(),
    )


def _make_provider(cache: InMemoryTTLCache | None = None) -> USDANutritionProvider:
    """Return a provider with a fresh real httpx.AsyncClient (no transport override)."""
    client = httpx.AsyncClient()
    return USDANutritionProvider(client, cache=cache or InMemoryTTLCache())


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 1 — Successful search + detail (happy path)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_successful_search_and_detail():
    """
    Two HTTP calls are intercepted.  The provider returns a fully-populated
    NutritionFacts including micronutrients and food_portions.
    """
    with respx.mock(assert_all_called=True) as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [SEARCH_FOOD]}))
        router.get(_DETAIL_URL).mock(return_value=_json_resp(DETAIL_RESPONSE))

        provider = _make_provider()
        result   = await provider.lookup(MATCH)

    assert result.calories  == pytest.approx(165.0)
    assert result.protein   == pytest.approx(31.0)
    assert result.fat       == pytest.approx(3.6)
    assert result.sodium    == pytest.approx(74.0)
    assert result.potassium == pytest.approx(256.0)
    assert result.vitamin_a == pytest.approx(18.0)
    assert result.food_portions is not None
    assert len(result.food_portions) == 2
    assert result.food_portions[0].description == "1 breast"
    assert result.food_portions[0].gram_weight == pytest.approx(118.0)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 2 — Missing micronutrients → optional fields are None
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_missing_micronutrients_are_none():
    """
    When FDC detail omits vitamin / mineral nutrient IDs, the parser must
    leave those fields as ``None``, not coerce them to 0.
    """
    sparse_detail = {
        "description": _FOOD_NAME,
        "foodNutrients": [
            {"nutrient": {"id": 1008}, "amount": 165.0},
            {"nutrient": {"id": 1003}, "amount": 31.0},
            {"nutrient": {"id": 1005}, "amount": 0.0},
            {"nutrient": {"id": 1004}, "amount": 3.6},
        ],
        "foodPortions": [],
    }

    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [SEARCH_FOOD]}))
        router.get(_DETAIL_URL).mock(return_value=_json_resp(sparse_detail))

        provider = _make_provider()
        result   = await provider.lookup(MATCH)

    assert result.potassium   is None
    assert result.calcium     is None
    assert result.iron        is None
    assert result.vitamin_a   is None
    assert result.vitamin_c   is None
    assert result.vitamin_d   is None
    assert result.vitamin_b12 is None


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 3 — Missing foodPortions → food_portions is None
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_missing_food_portions_results_in_none():
    """
    An empty ``foodPortions`` list in the FDC detail must produce
    ``NutritionFacts.food_portions = None`` (not an empty list).
    """
    no_portions_detail = {**DETAIL_RESPONSE, "foodPortions": []}

    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [SEARCH_FOOD]}))
        router.get(_DETAIL_URL).mock(return_value=_json_resp(no_portions_detail))

        provider = _make_provider()
        result   = await provider.lookup(MATCH)

    assert result.food_portions is None


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 4 — All candidates have zero core macros → IngredientNotFoundError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_all_candidates_zero_macros_raises():
    """
    The provider must skip candidates where every core macro (1008/1003/1005/1004)
    is zero and raise IngredientNotFoundError when none survive.
    """
    empty_macro_food = {
        "fdcId": 9999,
        "description": "Empty Placeholder Food",
        "foodNutrients": [
            {"nutrientId": 1008, "value": 0.0},
            {"nutrientId": 1003, "value": 0.0},
            {"nutrientId": 1005, "value": 0.0},
            {"nutrientId": 1004, "value": 0.0},
        ],
    }

    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [empty_macro_food]}))

        provider = _make_provider()
        with pytest.raises(IngredientNotFoundError):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 5 — Empty foods list → IngredientNotFoundError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_empty_search_foods_list_raises():
    """
    A valid 200 response whose ``foods`` list is empty means the food is simply
    absent from FDC — IngredientNotFoundError must be raised.
    """
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": []}))

        provider = _make_provider()
        with pytest.raises(IngredientNotFoundError):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 6 — HTTP 404 on search → FoodDatabaseUnavailableError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_search_http_404_raises():
    """A 404 from the FDC search endpoint raises FoodDatabaseUnavailableError."""
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=httpx.Response(404))

        provider = _make_provider()
        with pytest.raises(FoodDatabaseUnavailableError, match="404"):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 7 — HTTP 500 on search → FoodDatabaseUnavailableError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_search_http_500_raises():
    """A 500 from the FDC search endpoint raises FoodDatabaseUnavailableError."""
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=httpx.Response(500))

        provider = _make_provider()
        with pytest.raises(FoodDatabaseUnavailableError, match="500"):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 8 — HTTP 404 on detail → FoodDatabaseUnavailableError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_detail_http_404_raises():
    """A 404 from the FDC food-detail endpoint raises FoodDatabaseUnavailableError."""
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [SEARCH_FOOD]}))
        router.get(_DETAIL_URL).mock(return_value=httpx.Response(404))

        provider = _make_provider()
        with pytest.raises(FoodDatabaseUnavailableError, match="404"):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 9 — HTTP 500 on detail → FoodDatabaseUnavailableError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_detail_http_500_raises():
    """A 500 from the FDC food-detail endpoint raises FoodDatabaseUnavailableError."""
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [SEARCH_FOOD]}))
        router.get(_DETAIL_URL).mock(return_value=httpx.Response(500))

        provider = _make_provider()
        with pytest.raises(FoodDatabaseUnavailableError, match="500"):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 10 — Network timeout on search → FoodDatabaseUnavailableError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_search_timeout_raises():
    """
    When the FDC search request times out (httpx.TimeoutException), the provider
    must catch it and raise FoodDatabaseUnavailableError.
    """
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(
            side_effect=httpx.TimeoutException("timed out")
        )

        provider = _make_provider()
        with pytest.raises(FoodDatabaseUnavailableError, match="search request failed"):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 11 — Network timeout on detail → FoodDatabaseUnavailableError
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_detail_timeout_raises():
    """
    When the FDC food-detail request times out, the provider must raise
    FoodDatabaseUnavailableError (not leak the raw TimeoutException).
    """
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [SEARCH_FOOD]}))
        router.get(_DETAIL_URL).mock(
            side_effect=httpx.TimeoutException("timed out")
        )

        provider = _make_provider()
        with pytest.raises(FoodDatabaseUnavailableError, match="detail request failed"):
            await provider.lookup(MATCH)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 12 — Cache miss: both HTTP calls made exactly once
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cache_miss_makes_two_http_calls():
    """
    On a cold cache, both the search and detail endpoints must be called
    exactly once, and their responses stored in the cache.
    """
    cache = InMemoryTTLCache(default_ttl_seconds=300)

    with respx.mock() as router:
        search_route = router.get(_SEARCH_URL).mock(
            return_value=_json_resp({"foods": [SEARCH_FOOD]})
        )
        detail_route = router.get(_DETAIL_URL).mock(
            return_value=_json_resp(DETAIL_RESPONSE)
        )

        provider = _make_provider(cache=cache)
        await provider.lookup(MATCH)

    assert search_route.call_count == 1, "Expected exactly one search HTTP call"
    assert detail_route.call_count == 1, "Expected exactly one detail HTTP call"

    assert cache.get(f"usda:search:{MATCH.canonical_name.lower()}") is not None
    assert cache.get(f"usda:detail:{_FDC_ID}") is not None


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 13 — Cache hit: second lookup makes zero HTTP calls
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cache_hit_makes_no_http_calls():
    """
    After the first successful lookup, a second identical call must use the
    in-memory cache and issue no HTTP requests at all.
    """
    cache = InMemoryTTLCache(default_ttl_seconds=300)

    # ── First call: populate cache (2 HTTP calls expected) ──────────────────
    with respx.mock() as router:
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": [SEARCH_FOOD]}))
        router.get(_DETAIL_URL).mock(return_value=_json_resp(DETAIL_RESPONSE))

        p1 = _make_provider(cache=cache)
        first = await p1.lookup(MATCH)

    # ── Second call: cache already warm — any real HTTP call is a test failure
    # Register no routes; respx.mock with assert_all_mocked=True (default)
    # will raise httpx.ConnectError if any real request is attempted.
    with respx.mock(assert_all_called=False) as router:
        p2 = _make_provider(cache=cache)   # same cache object, populated above
        second = await p2.lookup(MATCH)

    # No routes were registered, so if any call had been made it would have
    # raised an error — arriving here proves zero HTTP was issued.
    assert second.calories  == pytest.approx(first.calories)
    assert second.food_name == first.food_name


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 14 — Provider fallback inside NutritionEngine
# ══════════════════════════════════════════════════════════════════════════════

class _StaticFallbackProvider:
    """
    Deterministic fallback used only to verify engine fallback routing.
    Returns a hard-coded NutritionFacts for "Chicken Breast" with no HTTP.
    """
    async def lookup(self, ingredient: IngredientMatch) -> NutritionFacts:
        if ingredient.canonical_name != "Chicken Breast":
            raise IngredientNotFoundError(ingredient.canonical_name)
        return NutritionFacts(
            food_name="Chicken Breast (fallback)",
            calories=165.0,
            protein=31.0,
            carbohydrates=0.0,
            fat=3.6,
            fiber=0.0,
            sugar=0.0,
            sodium=74.0,
        )


@pytest.mark.asyncio
async def test_engine_falls_back_when_usda_finds_nothing():
    """
    When USDANutritionProvider raises IngredientNotFoundError (search returned
    no usable results), NutritionEngine must transparently try the next provider
    in the priority list without surfacing the USDA error to the caller.
    """
    with respx.mock() as router:
        # USDA returns an empty list → will raise IngredientNotFoundError
        router.get(_SEARCH_URL).mock(return_value=_json_resp({"foods": []}))

        usda_provider = _make_provider()
        fallback      = _StaticFallbackProvider()

        engine = NutritionEngine([usda_provider, fallback])
        result = await engine.analyze(
            [Ingredient("Chicken Breast", quantity=100, unit="g")]
        )

    assert result.scaled_items[0].nutrition.food_name == "Chicken Breast (fallback)"
    assert result.scaled_items[0].calories == pytest.approx(165.0)
