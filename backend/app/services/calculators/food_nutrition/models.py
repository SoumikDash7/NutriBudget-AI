"""
Nutrition Engine Domain Models.

This module defines the core domain models used throughout the nutrition
engine. These models are intentionally independent of FastAPI, Pydantic,
database implementations, and AI services.

The domain flow is:

Ingredient
    ↓
IngredientMatch
    ↓
NutritionFacts
    ↓
NutritionResult
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Ingredient:
    """
    Represents a single ingredient extracted by the AI layer.

    Attributes:
        name:
            Ingredient name exactly as extracted.

        quantity:
            Quantity supplied by the user.

        unit:
            Unit corresponding to the quantity
            (e.g. g, kg, ml, cup, tbsp).

        preparation:
            Optional preparation method
            (boiled, grilled, fried, etc.).

        notes:
            Optional free-form notes.
    """

    name: str
    quantity: float
    unit: str
    preparation: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.unit = self.unit.strip()

        if not self.name:
            raise ValueError("Ingredient name cannot be empty.")

        if self.quantity <= 0:
            raise ValueError("Ingredient quantity must be greater than zero.")

        if not self.unit:
            raise ValueError("Ingredient unit cannot be empty.")


@dataclass(slots=True)
class IngredientMatch:
    """
    Represents the result of ingredient normalization.

    Example:
        "Boneless chicken"

        ↓

        "Chicken Breast"
    """

    original_name: str
    canonical_name: str
    confidence: float

    def __post_init__(self) -> None:
        self.original_name = self.original_name.strip()
        self.canonical_name = self.canonical_name.strip()

        if not self.original_name:
            raise ValueError("Original ingredient name cannot be empty.")

        if not self.canonical_name:
            raise ValueError("Canonical ingredient name cannot be empty.")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "Confidence must be between 0.0 and 1.0."
            )


@dataclass(slots=True)
class NutritionFacts:
    """
    Nutritional values for a standardized serving.

    Unless otherwise specified by the database adapter,
    values are assumed to be per 100 g.
    """

    food_name: str

    calories: float

    protein: float

    carbohydrates: float

    fat: float

    fiber: float

    sugar: float

    sodium: float

    serving_unit: str = "100g"

    def __post_init__(self) -> None:
        self.food_name = self.food_name.strip()
        self.serving_unit = self.serving_unit.strip()

        if not self.food_name:
            raise ValueError("Food name cannot be empty.")

        if not self.serving_unit:
            raise ValueError("Serving unit cannot be empty.")

        nutrition_values = {
            "calories": self.calories,
            "protein": self.protein,
            "carbohydrates": self.carbohydrates,
            "fat": self.fat,
            "fiber": self.fiber,
            "sugar": self.sugar,
            "sodium": self.sodium,
        }

        for field_name, value in nutrition_values.items():
            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative."
                )


@dataclass(slots=True)
class NutritionResult:
    """
    Final nutrition totals for an analyzed meal.
    """

    ingredients: list[Ingredient] = field(default_factory=list)

    total_calories: float = 0.0

    total_protein: float = 0.0

    total_carbohydrates: float = 0.0

    total_fat: float = 0.0

    total_fiber: float = 0.0

    total_sugar: float = 0.0

    total_sodium: float = 0.0

    def __post_init__(self) -> None:
        totals = {
            "total_calories": self.total_calories,
            "total_protein": self.total_protein,
            "total_carbohydrates": self.total_carbohydrates,
            "total_fat": self.total_fat,
            "total_fiber": self.total_fiber,
            "total_sugar": self.total_sugar,
            "total_sodium": self.total_sodium,
        }

        for field_name, value in totals.items():
            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative."
                )

@dataclass(slots=True)
class FoodItem:
    """
    Represents a standardized food item with its nutritional profile.

    Attributes:
        name:
            Canonical name of the food (e.g., "Chicken Breast, Raw").

        calories:
            Energy in kcal per serving.

        protein:
            Protein in grams per serving.

        carbohydrates:
            Carbohydrates in grams per serving.

        fat:
            Fat in grams per serving.

        fiber:
            Dietary fiber in grams per serving.

        sugar:
            Sugars in grams per serving.

        sodium:
            Sodium in milligrams per serving.

        serving_size:
            The amount for which the nutritional values are provided.

        serving_unit:
            The unit of the serving size (e.g., "g", "ml", "cup", "piece").

        source:
            The database or source of this information.

        confidence:
            A measure of how confident we are in this match (0.0 to 1.0).
    """

    name: str
    calories: float
    protein: float
    carbohydrates: float
    fat: float
    fiber: float
    sugar: float
    sodium: float
    serving_size: float
    serving_unit: str
    source: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.serving_unit = self.serving_unit.strip()
        self.source = self.source.strip()

        if not self.name:
            raise ValueError("Food item name cannot be empty.")

        if self.calories < 0 or self.protein < 0 or \
           self.carbohydrates < 0 or self.fat < 0 or \
           self.fiber < 0 or self.sugar < 0 or \
           self.sodium < 0:
            raise ValueError("Nutritional values cannot be negative.")

        if self.serving_size <= 0:
            raise ValueError("Serving size must be positive.")

        if not self.serving_unit:
            raise ValueError("Serving unit cannot be empty.")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0.")