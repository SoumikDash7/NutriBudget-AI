"""
USDA FoodData Central Nutrition Provider.

Implements the NutritionProvider protocol for the food nutrition engine.

This module is intentionally isolated from the AI layer (app/services/ai/).
It reuses the FDC nutrient-ID lookup pattern from USDAClient but targets
the two-call flow required by the engine:

    1. POST  /fdc/v1/foods/search  → locate the best-matching fdcId
    2. GET   /fdc/v1/food/{fdcId}  → fetch full nutrient + portion data

Nutrient values are returned per 100 g (FDC standard).
foodPortions are parsed into FoodPortion objects for future unit conversion.
"""

from __future__ import annotations

import httpx

from app.core.caching import InMemoryTTLCache
from app.core.config import settings
from app.core.logging import get_logger
from app.services.calculators.food_nutrition.exceptions import (
    FoodDatabaseUnavailableError,
    IngredientNotFoundError,
)
from app.services.calculators.food_nutrition.models import (
    FoodPortion,
    IngredientMatch,
    NutritionFacts,
)

logger = get_logger(__name__)

# ── FDC endpoint constants ────────────────────────────────────────────────────

_FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_FDC_FOOD_URL   = "https://api.nal.usda.gov/fdc/v1/food/{fdcId}"

# Data types searched in priority order (SR Legacy = most complete for raw foods)
_DATA_TYPES = ["SR Legacy", "Foundation", "Branded"]

# ── Nutrient-ID → NutritionFacts field name ───────────────────────────────────
# Source: https://fdc.nal.usda.gov/docs/DG-Nutrient-Profiles.pdf
_NUTRIENT_MAP: dict[int, str] = {
    1008: "calories",       # Energy (kcal)
    1003: "protein",        # Protein (g)
    1005: "carbohydrates",  # Carbohydrate, by difference (g)
    1004: "fat",            # Total lipid (fat) (g)
    1079: "fiber",          # Dietary fiber (g)
    2000: "sugar",          # Total sugars (g)
    1093: "sodium",         # Sodium (mg)
    1092: "potassium",      # Potassium (mg)
    1087: "calcium",        # Calcium (mg)
    1089: "iron",           # Iron (mg)
    1106: "vitamin_a",      # Vitamin A, RAE (µg)
    1162: "vitamin_c",      # Vitamin C (mg)
    1114: "vitamin_d",      # Vitamin D (D2 + D3) (µg)
    1178: "vitamin_b12",    # Vitamin B-12 (µg)
}

# Core macros used to detect and discard empty/placeholder FDC records
_CORE_MACRO_IDS = {1008, 1003, 1005, 1004}


class USDANutritionProvider:
    """
    USDA FoodData Central nutrition provider.

    Conforms to the NutritionProvider protocol used by NutritionEngine.

    An httpx.AsyncClient must be provided at construction time so that
    connection pooling is owned by the caller (e.g., FastAPI lifespan).

    Raises
    ------
    IngredientNotFoundError
        When no matching food can be found in FDC for the given ingredient.
    FoodDatabaseUnavailableError
        When the FDC API returns an unexpected HTTP error.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        cache: InMemoryTTLCache | None = None,
    ) -> None:
        self._client = http_client
        self._cache = cache or InMemoryTTLCache(default_ttl_seconds=86400)

    async def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        """
        Look up nutrition facts for a canonical ingredient name.

        Flow
        ----
        1. Search FDC for the ingredient's canonical name.
        2. Iterate candidates until a non-empty record is found.
        3. Fetch the food detail endpoint to obtain foodPortions.
        4. Parse nutrients and portions into NutritionFacts.
        """
        if not settings.USDA_API_KEY:
            raise FoodDatabaseUnavailableError(
                "USDA_API_KEY is not configured."
            )

        fdc_id, food_name = await self._search(ingredient.canonical_name)
        detail = await self._fetch_detail(fdc_id)
        return self._parse(food_name, detail)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _search(self, query: str) -> tuple[int, str]:
        """
        Search FDC and return (fdcId, food_name) of the best non-empty hit.

        Reuses the same candidate-iteration pattern as USDAClient._parse_food:
        iterate results in order, skip records whose core macros are all zero.
        """
        cache_key = f"usda:search:{query.strip().lower()}"
        cached = self._cache.get(cache_key)

        if cached is not None:
            logger.info("USDA search cache hit for '%s'", query)
            data = cached
        else:
            logger.info("USDA search cache miss: querying API for '%s'", query)
            params = {
                "query": query,
                "api_key": settings.USDA_API_KEY,
                "dataType": _DATA_TYPES,
                "pageSize": 5,
            }

            try:
                response = await self._client.get(
                    _FDC_SEARCH_URL, params=params, timeout=8.0
                )
            except httpx.RequestError as exc:
                raise FoodDatabaseUnavailableError(
                    f"USDA search request failed: {exc}"
                ) from exc

            if response.status_code != 200:
                raise FoodDatabaseUnavailableError(
                    f"USDA search returned HTTP {response.status_code}."
                )

            data = response.json()
            self._cache.set(cache_key, data)

        foods = data.get("foods", [])

        if not foods:
            raise IngredientNotFoundError(
                f"No USDA results for '{query}'."
            )

        for food in foods:
            fdc_id    = food.get("fdcId")
            food_name = (
                food.get("description")
                or food.get("lowercaseDescription")
                or query
            ).title()

            # Reuse USDAClient discard logic: skip all-zero macro records
            nutrients = {
                n["nutrientId"]: n.get("value", 0.0)
                for n in food.get("foodNutrients", [])
            }
            if all(nutrients.get(nid, 0.0) == 0.0 for nid in _CORE_MACRO_IDS):
                logger.debug(
                    "Skipping '%s' (fdcId=%s) — all core macros are zero.",
                    food_name,
                    fdc_id,
                )
                continue

            logger.debug(
                "Selected fdcId=%s  name='%s'", fdc_id, food_name
            )
            return fdc_id, food_name

        raise IngredientNotFoundError(
            f"All USDA candidates for '{query}' have empty nutrient data."
        )

    async def _fetch_detail(self, fdc_id: int) -> dict:
        """Fetch the full food detail record from FDC."""
        cache_key = f"usda:detail:{fdc_id}"
        cached = self._cache.get(cache_key)

        if cached is not None:
            logger.info("USDA detail cache hit for fdcId=%s", fdc_id)
            return cached

        logger.info("USDA detail cache miss: querying API for fdcId=%s", fdc_id)
        url = _FDC_FOOD_URL.format(fdcId=fdc_id)
        params = {"api_key": settings.USDA_API_KEY}

        try:
            response = await self._client.get(
                url, params=params, timeout=8.0
            )
        except httpx.RequestError as exc:
            raise FoodDatabaseUnavailableError(
                f"USDA detail request failed: {exc}"
            ) from exc

        if response.status_code != 200:
            raise FoodDatabaseUnavailableError(
                f"USDA detail returned HTTP {response.status_code} "
                f"for fdcId={fdc_id}."
            )

        data = response.json()
        self._cache.set(cache_key, data)
        return data

    @staticmethod
    def _parse(food_name: str, detail: dict) -> NutritionFacts:
        """
        Map a FDC food detail dict to a NutritionFacts domain object.

        Nutrient extraction
        -------------------
        FDC detail returns foodNutrients as a list of objects with keys
        ``nutrient.id`` and ``amount``.  We build a {nutrient_id: amount}
        lookup then pull each mapped field.  Missing nutrients are left as
        None (not zero) so callers can distinguish "not reported" from "zero".

        Portion extraction
        ------------------
        foodPortions is a list of objects with ``portionDescription``,
        ``gramWeight``, and optionally ``modifier``.  Only portions with a
        positive gram_weight are kept.
        """
        # Build nutrient lookup: {nutrient_id: amount}
        nutrient_values: dict[int, float] = {}
        for entry in detail.get("foodNutrients", []):
            nutrient = entry.get("nutrient", {})
            nid      = nutrient.get("id")
            amount   = entry.get("amount")
            if nid is not None and amount is not None:
                nutrient_values[nid] = float(amount)

        def _get(nid: int) -> float | None:
            """Return the nutrient amount or None if not in the response."""
            return nutrient_values.get(nid)

        def _get_required(nid: int, field: str) -> float:
            """Return the nutrient amount, defaulting to 0.0 for required fields."""
            val = nutrient_values.get(nid, 0.0)
            return round(float(val), 2)

        # Parse foodPortions — per-food gram weights for labelled measures
        food_portions: list[FoodPortion] = []
        for p in detail.get("foodPortions", []):
            desc        = (p.get("portionDescription") or "").strip()
            gram_weight = p.get("gramWeight")
            modifier    = (p.get("modifier") or "").strip() or None

            if not desc or not gram_weight or gram_weight <= 0:
                continue

            try:
                food_portions.append(
                    FoodPortion(
                        description=desc,
                        gram_weight=float(gram_weight),
                        modifier=modifier,
                    )
                )
            except ValueError:
                logger.debug(
                    "Skipping invalid FoodPortion: desc=%r gram_weight=%r",
                    desc,
                    gram_weight,
                )

        # Optional micronutrients — None when the field is absent in the record
        def _opt(nid: int) -> float | None:
            v = _get(nid)
            return round(v, 3) if v is not None else None

        logger.info(
            "USDA parsed '%s': %.1f kcal / 100 g  (%d portions)",
            food_name,
            _get_required(1008, "calories"),
            len(food_portions),
        )

        return NutritionFacts(
            food_name=food_name,
            calories=_get_required(1008, "calories"),
            protein=_get_required(1003, "protein"),
            carbohydrates=_get_required(1005, "carbohydrates"),
            fat=_get_required(1004, "fat"),
            fiber=_get_required(1079, "fiber"),
            sugar=_get_required(2000, "sugar"),
            sodium=_get_required(1093, "sodium"),
            food_portions=food_portions or None,
            potassium=_opt(1092),
            calcium=_opt(1087),
            iron=_opt(1089),
            vitamin_a=_opt(1106),
            vitamin_c=_opt(1162),
            vitamin_d=_opt(1114),
            vitamin_b12=_opt(1178),
        )
