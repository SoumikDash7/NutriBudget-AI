"""
Nutrition Engine Exceptions.

This module defines custom exceptions used throughout the nutrition engine.
"""


class NutritionError(Exception):
    """Base exception for all nutrition engine errors."""


class NutritionLookupError(NutritionError):
    """Raised when nutrition data cannot be retrieved."""


class IngredientNotFoundError(NutritionLookupError):
    """Raised when an ingredient cannot be matched to nutrition data."""


class UnsupportedUnitError(NutritionError):
    """Raised when an unsupported measurement unit is encountered."""

class NutritionProviderError(NutritionLookupError):
    """Raised when a nutrition provider fails."""


class FoodDatabaseUnavailableError(NutritionProviderError):
    """Raised when a nutrition database cannot be reached."""