"""
Nutrition Engine Constants.

This module contains shared constants used throughout the nutrition engine.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------

NORMALIZATION_REPLACEMENTS: dict[str, str] = {
    "-": " ",
    "_": " ",
}

MULTIPLE_SPACE_PATTERN = re.compile(r"\s+")

NON_ALPHANUMERIC_PATTERN = re.compile(r"[^\w\s]")

# ---------------------------------------------------------------------
# Match confidence
# ---------------------------------------------------------------------

EXACT_MATCH_CONFIDENCE = 1.00
ALIAS_MATCH_CONFIDENCE = 0.99
UNKNOWN_MATCH_CONFIDENCE = 0.50

# ---------------------------------------------------------------------
# Food aliases
#
# Key:
#     normalized ingredient name
#
# Value:
#     canonical ingredient name
# ---------------------------------------------------------------------

FOOD_ALIASES: dict[str, str] = {
    # ---------------- Chicken ----------------
    "chicken": "Chicken",
    "chicken breast": "Chicken Breast",
    "boneless chicken": "Chicken Breast",
    "skinless chicken breast": "Chicken Breast",
    "chicken thigh": "Chicken Thigh",
    "chicken leg": "Chicken Leg",
    "chicken wings": "Chicken Wings",

    # ---------------- Eggs ----------------
    "egg": "Egg",
    "eggs": "Egg",
    "boiled egg": "Boiled Egg",
    "fried egg": "Fried Egg",

    # ---------------- Rice ----------------
    "rice": "Rice",
    "white rice": "Rice",
    "steamed rice": "Rice",
    "brown rice": "Brown Rice",
    "basmati rice": "Basmati Rice",

    # ---------------- Dairy ----------------
    "milk": "Milk",
    "whole milk": "Whole Milk",
    "skim milk": "Skim Milk",
    "curd": "Curd",
    "yogurt": "Yogurt",
    "paneer": "Paneer",
    "cheese": "Cheese",
    "butter": "Butter",
    "ghee": "Ghee",

    # ---------------- Oils ----------------
    "olive oil": "Olive Oil",
    "vegetable oil": "Vegetable Oil",
    "sunflower oil": "Sunflower Oil",

    # ---------------- Grains ----------------
    "oats": "Oats",
    "bread": "Bread",
    "whole wheat bread": "Whole Wheat Bread",

    # ---------------- Fruits ----------------
    "banana": "Banana",
    "apple": "Apple",
    "orange": "Orange",
    "mango": "Mango",

    # ---------------- Vegetables ----------------
    "potato": "Potato",
    "tomato": "Tomato",
    "onion": "Onion",
    "spinach": "Spinach",
    "broccoli": "Broccoli",
    "carrot": "Carrot",

    # ---------------- Protein ----------------
    "tofu": "Tofu",
    "lentils": "Lentils",
    "dal": "Dal",
    "black beans": "Black Beans",
    "chickpeas": "Chickpeas",

    # ---------------- Nuts ----------------
    "almonds": "Almonds",
    "cashews": "Cashews",
    "peanuts": "Peanuts",

    # ---------------- Seafood ----------------
    "salmon": "Salmon",
    "tuna": "Tuna",
    "prawns": "Prawns",

    # ---------------- Sweeteners ----------------
    "honey": "Honey",
    "sugar": "Sugar",

    # ---------------- Misc ----------------
    "salt": "Salt",
    "black pepper": "Black Pepper",
    "garlic": "Garlic",
    "garlic clove": "Garlic",
}

# ---------------------------------------------------------------------
# Unit normalization
#
# Maps every recognized unit spelling/alias to a single canonical
# unit string. Anything not present here is unsupported.
# ---------------------------------------------------------------------

UNIT_ALIASES: dict[str, str] = {
    # ---- mass ----
    "g": "g", "gram": "g", "grams": "g", "gm": "g", "gms": "g",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "mg": "mg", "milligram": "mg", "milligrams": "mg",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",

    # ---- volume ----
    "ml": "ml", "milliliter": "ml", "milliliters": "ml",
    "millilitre": "ml", "millilitres": "ml",
    "l": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "cup": "cup", "cups": "cup",
    "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp", "tbs": "tbsp",
    "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "fl_oz": "fl_oz", "fl oz": "fl_oz",
    "fluid ounce": "fl_oz", "fluid ounces": "fl_oz",

    # ---- count ----
    "piece": "piece", "pieces": "piece", "pc": "piece", "pcs": "piece",
    "whole": "piece", "medium": "piece", "large": "piece", "small": "piece",
    "slice": "slice", "slices": "slice",
    "clove": "clove", "cloves": "clove",
}

# ---------------------------------------------------------------------
# Mass conversion — direct, unambiguous, no estimation involved.
# Value = grams per 1 unit.
# ---------------------------------------------------------------------

MASS_UNIT_TO_GRAMS: dict[str, float] = {
    "g": 1.0,
    "kg": 1000.0,
    "mg": 0.001,
    "oz": 28.3495,
    "lb": 453.592,
}

# ---------------------------------------------------------------------
# Volume conversion — converts to millilitres first. Turning ml into
# grams additionally requires an ingredient density (see below), so
# volume-to-gram conversion is inherently an estimate unless the
# ingredient has a known density.
# Value = millilitres per 1 unit.
# ---------------------------------------------------------------------

VOLUME_UNIT_TO_ML: dict[str, float] = {
    "ml": 1.0,
    "l": 1000.0,
    "cup": 240.0,
    "tbsp": 15.0,
    "tsp": 5.0,
    "fl_oz": 29.5735,
}

# Units that represent a countable item rather than mass or volume.
COUNT_UNITS: frozenset[str] = frozenset({"piece", "slice", "clove"})

# Fallback density used when an ingredient has no known density.
# Water-equivalent (1 g/ml). Deliberately conservative — see
# QuantityConverter, which flags any conversion using this fallback
# as `estimated=True` so downstream code/UI can surface that.
DEFAULT_DENSITY_G_PER_ML = 1.0

# Ingredient-specific densities, keyed by canonical name (must match
# FOOD_ALIASES values). Only needed for ingredients commonly measured
# by volume.
INGREDIENT_DENSITY_G_PER_ML: dict[str, float] = {
    "Olive Oil": 0.92,
    "Vegetable Oil": 0.92,
    "Sunflower Oil": 0.92,
    "Honey": 1.42,
    "Milk": 1.03,
    "Whole Milk": 1.03,
    "Skim Milk": 1.03,
    "Butter": 0.96,   # melted
    "Ghee": 0.91,
    "Yogurt": 1.03,
    "Curd": 1.03,
}

# Default weight (grams) for one "piece" of a countable ingredient.
DEFAULT_PIECE_WEIGHT_GRAMS: dict[str, float] = {
    "Egg": 50.0,
    "Boiled Egg": 50.0,
    "Fried Egg": 50.0,
    "Banana": 118.0,
    "Apple": 182.0,
    "Orange": 131.0,
    "Mango": 200.0,
    "Potato": 170.0,
    "Tomato": 123.0,
    "Onion": 110.0,
}

# Default weight (grams) for one "slice" of a countable ingredient.
DEFAULT_SLICE_WEIGHT_GRAMS: dict[str, float] = {
    "Bread": 28.0,
    "Whole Wheat Bread": 32.0,
    "Cheese": 20.0,
}

# Default weight (grams) for one "clove" of a countable ingredient.
DEFAULT_CLOVE_WEIGHT_GRAMS: dict[str, float] = {
    "Garlic": 5.0,
}

_LOCAL_FOOD_DB: dict[str, dict] = {
    # ── Indian Staples ────────────────────────────────────────────────────
    "roti":           {"food_name": "Roti (1 piece)",              "calories": 80,  "protein": 3.0,  "carbs": 15.0, "fat": 0.5},
    "chapati":        {"food_name": "Chapati (1 piece)",           "calories": 80,  "protein": 3.0,  "carbs": 15.0, "fat": 0.5},
    "paratha":        {"food_name": "Aloo Paratha (1 piece)",      "calories": 210, "protein": 4.0,  "carbs": 32.0, "fat": 7.0},
    "naan":           {"food_name": "Naan (1 piece)",              "calories": 260, "protein": 9.0,  "carbs": 45.0, "fat": 5.0},
    "poori":          {"food_name": "Puri (1 piece)",              "calories": 120, "protein": 2.0,  "carbs": 14.0, "fat": 6.0},
    "idli":           {"food_name": "Idli (1 piece)",              "calories": 40,  "protein": 1.0,  "carbs": 8.0,  "fat": 0.1},
    "dosa":           {"food_name": "Plain Dosa (1 piece)",        "calories": 120, "protein": 2.0,  "carbs": 22.0, "fat": 3.0},
    "uttapam":        {"food_name": "Uttapam (1 piece)",           "calories": 110, "protein": 3.5,  "carbs": 18.0, "fat": 3.0},
    "upma":           {"food_name": "Upma (100g)",                 "calories": 130, "protein": 3.0,  "carbs": 22.0, "fat": 4.5},
    "poha":           {"food_name": "Poha (100g)",                 "calories": 110, "protein": 2.5,  "carbs": 23.0, "fat": 2.0},
    "khichdi":        {"food_name": "Khichdi (100g)",              "calories": 120, "protein": 4.5,  "carbs": 20.0, "fat": 3.0},
    # ── Indian Curries & Mains ────────────────────────────────────────────
    "dal":            {"food_name": "Dal Tadka (100g)",            "calories": 120, "protein": 5.0,  "carbs": 15.0, "fat": 4.0},
    "dal makhani":    {"food_name": "Dal Makhani (100g)",          "calories": 165, "protein": 6.5,  "carbs": 18.0, "fat": 7.0},
    "paneer":         {"food_name": "Paneer Butter Masala (100g)", "calories": 229, "protein": 8.0,  "carbs": 6.0,  "fat": 19.0},
    "palak paneer":   {"food_name": "Palak Paneer (100g)",         "calories": 180, "protein": 7.0,  "carbs": 8.0,  "fat": 13.0},
    "butter chicken": {"food_name": "Butter Chicken (100g)",       "calories": 240, "protein": 14.0, "carbs": 5.0,  "fat": 18.0},
    "chicken tikka":  {"food_name": "Chicken Tikka (100g)",        "calories": 190, "protein": 22.0, "carbs": 4.0,  "fat": 9.0},
    "biryani":        {"food_name": "Chicken Biryani (100g)",      "calories": 180, "protein": 10.0, "carbs": 22.0, "fat": 6.0},
    "rajma":          {"food_name": "Rajma Masala (100g)",         "calories": 140, "protein": 7.5,  "carbs": 22.0, "fat": 3.5},
    "chole":          {"food_name": "Chole Masala (100g)",         "calories": 160, "protein": 7.0,  "carbs": 24.0, "fat": 5.0},
    "aloo gobi":      {"food_name": "Aloo Gobi (100g)",            "calories": 90,  "protein": 2.5,  "carbs": 12.0, "fat": 4.0},
    "sambhar":        {"food_name": "Sambar (100g)",               "calories": 75,  "protein": 3.5,  "carbs": 10.0, "fat": 2.5},
    "rasam":          {"food_name": "Rasam (100ml)",               "calories": 40,  "protein": 1.5,  "carbs": 6.0,  "fat": 1.0},
    # ── Indian Snacks & Street Food ───────────────────────────────────────
    "samosa":         {"food_name": "Samosa (1 piece)",            "calories": 260, "protein": 3.5,  "carbs": 24.0, "fat": 16.0},
    "pakora":         {"food_name": "Pakora (1 piece)",            "calories": 80,  "protein": 2.0,  "carbs": 9.0,  "fat": 4.0},
    "vada":           {"food_name": "Medu Vada (1 piece)",         "calories": 100, "protein": 3.0,  "carbs": 12.0, "fat": 5.0},
    "pani puri":      {"food_name": "Pani Puri (6 pieces)",        "calories": 180, "protein": 3.0,  "carbs": 28.0, "fat": 6.0},
    "bhel puri":      {"food_name": "Bhel Puri (100g)",            "calories": 130, "protein": 3.0,  "carbs": 22.0, "fat": 4.0},
    "pav bhaji":      {"food_name": "Pav Bhaji (1 serving)",       "calories": 350, "protein": 8.0,  "carbs": 52.0, "fat": 12.0},
    # ── Indian Sweets & Drinks ────────────────────────────────────────────
    "gulab jamun":    {"food_name": "Gulab Jamun (1 piece)",       "calories": 150, "protein": 2.5,  "carbs": 26.0, "fat": 5.0},
    "rasgulla":       {"food_name": "Rasgulla (1 piece)",          "calories": 100, "protein": 2.0,  "carbs": 22.0, "fat": 0.5},
    "halwa":          {"food_name": "Sooji Halwa (100g)",          "calories": 280, "protein": 4.0,  "carbs": 38.0, "fat": 12.0},
    "kheer":          {"food_name": "Rice Kheer (100g)",           "calories": 145, "protein": 3.5,  "carbs": 24.0, "fat": 4.5},
    "lassi":          {"food_name": "Sweet Lassi (200ml)",         "calories": 160, "protein": 5.0,  "carbs": 26.0, "fat": 4.0},
    "chai":           {"food_name": "Masala Chai with milk (200ml)","calories": 80, "protein": 2.5,  "carbs": 11.0, "fat": 2.5},
    # ── International Staples (USDA Reference) ───────────────────────────
    "egg":            {"food_name": "Egg (1 large)",               "calories": 70,  "protein": 6.0,  "carbs": 0.6,  "fat": 5.0},
    "eggs":           {"food_name": "Eggs (1 large each)",         "calories": 70,  "protein": 6.0,  "carbs": 0.6,  "fat": 5.0},
    "omelette":       {"food_name": "Plain Omelette (2 eggs)",     "calories": 190, "protein": 13.0, "carbs": 1.0,  "fat": 15.0},
    "bread":          {"food_name": "Slice of Bread",              "calories": 80,  "protein": 3.0,  "carbs": 15.0, "fat": 1.0},
    "banana":         {"food_name": "Banana (medium)",             "calories": 90,  "protein": 1.1,  "carbs": 23.0, "fat": 0.3},
    "apple":          {"food_name": "Apple (medium)",              "calories": 52,  "protein": 0.3,  "carbs": 14.0, "fat": 0.2},
    "orange":         {"food_name": "Orange (medium)",             "calories": 62,  "protein": 1.2,  "carbs": 15.4, "fat": 0.2},
    "mango":          {"food_name": "Mango (100g)",                "calories": 60,  "protein": 0.8,  "carbs": 15.0, "fat": 0.4},
    "chicken":        {"food_name": "Chicken Breast (100g)",       "calories": 165, "protein": 31.0, "carbs": 0.0,  "fat": 3.6},
    "fish":           {"food_name": "Grilled Fish (100g)",         "calories": 140, "protein": 26.0, "carbs": 0.0,  "fat": 4.0},
    "rice":           {"food_name": "Cooked Rice (100g)",          "calories": 130, "protein": 2.7,  "carbs": 28.0, "fat": 0.3},
    "pasta":          {"food_name": "Cooked Pasta (100g)",         "calories": 158, "protein": 5.8,  "carbs": 31.0, "fat": 0.9},
    "oats":           {"food_name": "Oatmeal (100g cooked)",       "calories": 71,  "protein": 2.5,  "carbs": 12.0, "fat": 1.5},
    "milk":           {"food_name": "Milk (200ml)",                "calories": 120, "protein": 6.8,  "carbs": 10.0, "fat": 6.0},
    "curd":           {"food_name": "Curd / Yogurt (100g)",        "calories": 60,  "protein": 3.5,  "carbs": 4.5,  "fat": 3.0},
    "paneer raw":     {"food_name": "Paneer (100g raw)",           "calories": 265, "protein": 18.0, "carbs": 3.5,  "fat": 20.0},
    "pizza":          {"food_name": "Slice of Pizza",              "calories": 285, "protein": 12.0, "carbs": 36.0, "fat": 10.0},
    "burger":         {"food_name": "Burger (standard)",           "calories": 350, "protein": 18.0, "carbs": 40.0, "fat": 14.0},
    "salad":          {"food_name": "Green Salad",                 "calories": 15,  "protein": 1.0,  "carbs": 3.0,  "fat": 0.2},
    "sandwich":       {"food_name": "Sandwich (standard)",         "calories": 250, "protein": 11.0, "carbs": 34.0, "fat": 8.0},
    "coffee":         {"food_name": "Coffee with milk (200ml)",    "calories": 50,  "protein": 2.0,  "carbs": 5.0,  "fat": 2.0},
    "juice":          {"food_name": "Fruit Juice (200ml)",         "calories": 90,  "protein": 0.5,  "carbs": 22.0, "fat": 0.0},
}