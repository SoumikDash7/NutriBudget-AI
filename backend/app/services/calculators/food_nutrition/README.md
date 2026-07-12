# Nutrition Engine

## Purpose

The Nutrition Engine is responsible for transforming structured ingredient
data into nutritional information.

It is intentionally independent of any AI model.

```
AI
└── Ingredient Extraction

        ↓

Nutrition Engine

        ↓

Nutrition Calculation
```

The AI layer extracts ingredients from user input.

The Nutrition Engine:

- Normalizes ingredient names
- Retrieves nutrition data
- Performs calculations
- Produces nutrition totals

---

# Module Responsibilities

## engine.py

Coordinates the nutrition pipeline.

```
Ingredients
      ↓
 Matcher
      ↓
 Database Adapter
      ↓
 Calculator
      ↓
 Totals
```

This module should never communicate directly with AI models.

---

## matcher.py

Responsible for ingredient normalization.

Example:

```
Chicken breast
Chicken Breast
Boneless Chicken

↓

Chicken Breast
```

---

## databases.py

Contains adapters for nutrition databases.

Planned adapters:

- USDA FoodData Central
- Indian Food Composition Database
- OpenFoodFacts

Database adapters should only retrieve nutrition information.

They must never perform nutrition calculations.

---

## models.py

Contains shared domain models.

Planned models:

- Ingredient
- NutritionFacts
- NutritionResult

---

## constants.py

Contains shared constants.

Examples:

- Supported units
- Conversion factors
- Default serving sizes
- Density mappings

---

## exceptions.py

Contains Nutrition Engine specific exceptions.

Examples:

- NutritionLookupError
- IngredientNotFoundError
- UnsupportedUnitError

---

## Design Principles

- Independent of AI
- Independent of FastAPI
- Independent of database implementation
- Deterministic
- Easy to unit test
- Extensible