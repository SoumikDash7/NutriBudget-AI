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
class FoodPortion:
    """
    A single portion definition for a food item.

    Contains only the data required for quantity conversion:
    mapping a human-readable portion label to a gram weight.

    Attributes:
        description:
            Human-readable portion label as stored in the source
            database (e.g. "1 cup", "1 tablespoon", "1 oz").
            Used to match against user-supplied unit strings.

        gram_weight:
            Gram equivalent of this portion.
            This is the conversion factor used to scale nutrition
            values when the user supplies a non-gram quantity.

        modifier:
            Optional secondary qualifier supplied by the source
            database (e.g. "cooked", "drained", "without skin").
            Not all providers populate this field.
    """

    description: str
    gram_weight: float
    modifier: str | None = None

    def __post_init__(self) -> None:
        self.description = self.description.strip()

        if not self.description:
            raise ValueError("FoodPortion description cannot be empty.")

        if self.gram_weight <= 0:
            raise ValueError(
                "FoodPortion gram_weight must be greater than zero."
            )

        if self.modifier is not None:
            self.modifier = self.modifier.strip() or None


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

    serving_unit: str = "g"

    portions: dict[str, float] = field(default_factory=dict)
    """
    Optional real per-food gram weights for specific units, sourced
    from the provider (e.g. USDA FDC's `foodPortions`).

    Keys are canonical unit strings matching
    `QuantityConverter.normalize_unit()` output (e.g. "cup", "piece",
    "tbsp"). Values are grams for one of that unit, *for this specific
    food* — not a generic density/weight guess.

    Empty dict (the default) means the provider has no portion data;
    QuantityConverter then falls back to its generic density/weight
    tables.
    """

    food_portions: list[FoodPortion] | None = None
    """
    Optional structured portion data sourced from the provider.

    Each entry maps a human-readable label (e.g. "1 cup") to its
    gram weight for this specific food item. Defaults to None when
    the provider has no portion data available.

    Not used by the engine in Step 2 — carried for future use.
    """

    # ── Optional micronutrients (all per 100 g, None = not available) ──────

    potassium: float | None = None
    """Potassium in mg per 100 g."""

    calcium: float | None = None
    """Calcium in mg per 100 g."""

    iron: float | None = None
    """Iron in mg per 100 g."""

    vitamin_a: float | None = None
    """Vitamin A in µg RAE per 100 g."""

    vitamin_c: float | None = None
    """Vitamin C in mg per 100 g."""

    vitamin_d: float | None = None
    """Vitamin D in µg per 100 g."""

    vitamin_b12: float | None = None
    """Vitamin B12 in µg per 100 g."""

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

    scaled_items: list["ScaledNutrition"] = field(default_factory=list)

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
class ScaledNutrition:
    """
    Nutrition for an ingredient after quantity scaling.
    """

    ingredient: Ingredient

    nutrition: NutritionFacts

    calories: float

    protein: float

    carbohydrates: float

    fat: float

    fiber: float

    sugar: float

    sodium: float

    estimated_quantity: bool = False
    """
    True if converting this ingredient's quantity/unit into grams
    required a default density or default item weight rather than an
    exact mass conversion (e.g. "1 cup olive oil" or "2 pieces
    banana"). False for unambiguous mass units (g, kg, oz, lb).
    """

    def __post_init__(self) -> None:
        values = {
            "calories": self.calories,
            "protein": self.protein,
            "carbohydrates": self.carbohydrates,
            "fat": self.fat,
            "fiber": self.fiber,
            "sugar": self.sugar,
            "sodium": self.sodium,
        }

        for field_name, value in values.items():
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative.")