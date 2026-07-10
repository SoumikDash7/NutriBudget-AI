"""
Ingredient Name Matcher.

This module provides deterministic ingredient normalization for the
nutrition engine.

Responsibilities:
- Normalize ingredient names.
- Map aliases to canonical names.
- Produce IngredientMatch objects.

No AI models, HTTP calls, or database lookups are performed here.
"""

from __future__ import annotations

from app.services.calculators.food_nutrition.constants import (
    ALIAS_MATCH_CONFIDENCE,
    EXACT_MATCH_CONFIDENCE,
    FOOD_ALIASES,
    MULTIPLE_SPACE_PATTERN,
    NON_ALPHANUMERIC_PATTERN,
    NORMALIZATION_REPLACEMENTS,
    UNKNOWN_MATCH_CONFIDENCE,
)
from app.services.calculators.food_nutrition.models import (
    Ingredient,
    IngredientMatch,
)


class IngredientMatcher:
    """Deterministic ingredient matcher."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize an ingredient name.

        Example:
            Chicken---Breast

        becomes

            chicken breast
        """
        normalized = name.lower().strip()

        for old, new in NORMALIZATION_REPLACEMENTS.items():
            normalized = normalized.replace(old, new)

        normalized = NON_ALPHANUMERIC_PATTERN.sub(" ", normalized)
        normalized = MULTIPLE_SPACE_PATTERN.sub(" ", normalized)

        return normalized.strip()

    @staticmethod
    def canonicalize(name: str) -> tuple[str, float]:
        """
        Convert a normalized ingredient into its canonical representation.

        Returns:
            tuple[str, float]:
                (canonical_name, confidence)
        """
        normalized = IngredientMatcher.normalize_name(name)

        canonical = FOOD_ALIASES.get(normalized)

        if canonical is not None:
            if canonical.lower() == normalized:
                return canonical, EXACT_MATCH_CONFIDENCE

            return canonical, ALIAS_MATCH_CONFIDENCE

        return normalized.title(), UNKNOWN_MATCH_CONFIDENCE

    @staticmethod
    def match(ingredient: Ingredient) -> IngredientMatch:
        """
        Match an Ingredient to its canonical representation.
        """
        canonical_name, confidence = IngredientMatcher.canonicalize(
            ingredient.name
        )

        return IngredientMatch(
            original_name=ingredient.name,
            canonical_name=canonical_name,
            confidence=confidence,
        )