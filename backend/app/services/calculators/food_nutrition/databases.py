"""
Nutrition database provider interfaces.

This module defines the provider abstraction used by the nutrition engine.

Providers are responsible only for retrieving nutrition facts.

They never perform calculations.
"""

from __future__ import annotations

from typing import Protocol

from app.services.calculators.food_nutrition.exceptions import (
    IngredientNotFoundError,
)
from app.services.calculators.food_nutrition.models import (
    IngredientMatch,
    NutritionFacts,
)


class NutritionProvider(Protocol):
    """Interface implemented by every nutrition provider."""

    def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        """
        Retrieve nutrition information for a canonical ingredient.
        """
        ...


class USDANutritionProvider:
    """USDA FoodData Central provider."""

    def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        raise NotImplementedError


class IndianNutritionProvider:
    """Indian Food Composition Tables provider."""

    def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        raise NotImplementedError


class OpenFoodFactsProvider:
    """OpenFoodFacts provider."""

    def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        raise NotImplementedError


class CompositeNutritionProvider:
    """
    Attempts nutrition lookup using multiple providers.

    Providers are queried in order.

    The first successful lookup is returned.
    """

    def __init__(
        self,
        providers: list[NutritionProvider],
    ) -> None:
        self.providers = providers

    def lookup(
        self,
        ingredient: IngredientMatch,
    ) -> NutritionFacts:
        last_exception: Exception | None = None

        for provider in self.providers:
            try:
                return provider.lookup(ingredient)

            except IngredientNotFoundError as exc:
                last_exception = exc

        raise IngredientNotFoundError(
            f"Ingredient '{ingredient.canonical_name}' "
            "was not found in any nutrition provider."
        ) from last_exception