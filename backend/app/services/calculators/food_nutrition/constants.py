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
}
