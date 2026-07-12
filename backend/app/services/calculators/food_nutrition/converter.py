"""
Quantity Converter.

Handles conversion of non-gram units to grams using USDA portions,
manual food tables, and generic density mappings.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.services.calculators.food_nutrition.models import (
    FoodPortion,
    NutritionFacts,
)

logger = logging.getLogger(__name__)


class QuantityConverter:
    """
    Utility class for normalizing units and converting quantities to grams.
    """

    # Generic unit normalization mapping
    _UNIT_NORMALIZATION: dict[str, str] = {
        "g": "g",
        "gram": "g",
        "grams": "g",
        "kg": "kg",
        "kilogram": "kg",
        "kilograms": "kg",
        "ml": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
        "l": "l",
        "liter": "l",
        "liters": "l",
        "cup": "cup",
        "cups": "cup",
        "tbsp": "tbsp",
        "tablespoon": "tbsp",
        "tablespoons": "tbsp",
        "tsp": "tsp",
        "teaspoon": "tsp",
        "teaspoons": "tsp",
        "oz": "oz",
        "ounce": "oz",
        "ounces": "oz",
        "lb": "lb",
        "pound": "lb",
        "pounds": "lb",
        "piece": "piece",
        "pieces": "piece",
        "slice": "slice",
        "slices": "slice",
        "serving": "serving",
        "servings": "serving",
    }

    # Food-specific manual portion weights (canonical name -> normalized unit -> grams)
    _MANUAL_CONVERSION_TABLES: dict[str, dict[str, float]] = {
        "Chicken Breast": {
            "piece": 150.0,
            "slice": 30.0,
            "serving": 150.0,
        },
        "Butter": {
            "cup": 227.0,
            "tbsp": 14.2,
            "tsp": 4.7,
            "piece": 10.0,
        },
        "Rice": {
            "cup": 195.0,
            "serving": 150.0,
        },
        "Egg": {
            "piece": 50.0,
            "serving": 50.0,
        },
        "Milk": {
            "cup": 244.0,
            "tbsp": 15.0,
            "tsp": 5.0,
        },
        "Banana": {
            "piece": 120.0,
            "serving": 120.0,
        },
        "Apple": {
            "piece": 182.0,
            "serving": 182.0,
        },
        "Bread": {
            "slice": 28.0,
            "piece": 28.0,
        },
    }

    # Generic unit-to-gram conversion mapping when no food-specific portions match
    _GENERIC_DENSITY_ESTIMATION: dict[str, float] = {
        "g": 1.0,
        "kg": 1000.0,
        "ml": 1.0,  # assumption: density ~ 1g/ml
        "l": 1000.0,
        "cup": 240.0,
        "tbsp": 15.0,
        "tsp": 5.0,
        "oz": 28.35,
        "lb": 453.59,
        "piece": 100.0,
        "slice": 30.0,
        "serving": 100.0,
    }

    @classmethod
    def normalize_unit(cls, unit: str) -> str:
        """
        Normalize a raw unit string into a standard canonical form.
        """
        u = unit.strip().lower()
        return cls._UNIT_NORMALIZATION.get(u, u)

    @classmethod
    def convert_to_grams(
        cls,
        food_name: str,
        quantity: float,
        unit: str,
        nutrition_facts: Optional[NutritionFacts] = None,
    ) -> float:
        """
        Convert a quantity and unit of a specific food to grams.

        Priority order:
        1. USDA portions from nutrition_facts.food_portions or nutrition_facts.portions
        2. Food-specific manual conversion tables
        3. Generic density/weight estimation
        """
        norm_unit = cls.normalize_unit(unit)

        # ── 1. USDA Portions ──────────────────────────────────────────────────
        if nutrition_facts is not None:
            # First check structural food_portions list
            if nutrition_facts.food_portions:
                match = cls._find_usda_portion_match(norm_unit, nutrition_facts.food_portions)
                if match is not None:
                    logger.debug(
                        "QuantityConverter: USDA portion match found for '%s' (%s) -> %s g",
                        food_name,
                        unit,
                        match.gram_weight,
                    )
                    return match.gram_weight * quantity

            # Fallback to portions dictionary if present
            if getattr(nutrition_facts, "portions", None) and norm_unit in nutrition_facts.portions:
                gram_weight = nutrition_facts.portions[norm_unit]
                logger.debug(
                    "QuantityConverter: USDA portions dict match found for '%s' (%s) -> %s g",
                    food_name,
                    unit,
                    gram_weight,
                )
                return gram_weight * quantity

        # ── 2. Manual Conversion Tables ───────────────────────────────────────
        canon_name = food_name.strip().title()
        if canon_name in cls._MANUAL_CONVERSION_TABLES:
            food_table = cls._MANUAL_CONVERSION_TABLES[canon_name]
            if norm_unit in food_table:
                gram_weight = food_table[norm_unit]
                logger.debug(
                    "QuantityConverter: Manual table match found for '%s' (%s) -> %s g",
                    canon_name,
                    unit,
                    gram_weight,
                )
                return gram_weight * quantity

        # ── 3. Generic Density Estimation ─────────────────────────────────────
        if norm_unit in cls._GENERIC_DENSITY_ESTIMATION:
            gram_weight = cls._GENERIC_DENSITY_ESTIMATION[norm_unit]
            logger.debug(
                "QuantityConverter: Generic density match found for unit '%s' -> %s g",
                unit,
                gram_weight,
            )
            return gram_weight * quantity

        # Fallback: if totally unknown unit, return original quantity (best effort)
        logger.warning(
            "QuantityConverter: Unknown unit '%s' for '%s', returning quantity directly.",
            unit,
            food_name,
        )
        return quantity

    @classmethod
    def _find_usda_portion_match(
        cls,
        norm_unit: str,
        portions: list[FoodPortion],
    ) -> Optional[FoodPortion]:
        """
        Try to match standard normalized units against USDA portion descriptions.
        """
        # Exact match or normalized description lookup
        for p in portions:
            desc = p.description.strip().lower()
            # E.g., if portion description is "1 cup" or "1 tbsp" and norm_unit is "cup" or "tbsp"
            # Normalize description words
            desc_words = set(re.findall(r"\b[a-z]+\b", desc))
            if norm_unit in desc_words or desc == norm_unit:
                return p
        return None
