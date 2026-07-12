import re
import json

# ─────────────────────────────────────────────────────────────────────────────
# Image mime detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_mime(filename: str) -> str:
    fn = filename.lower()
    if fn.endswith(".png"):  return "image/png"
    if fn.endswith(".webp"): return "image/webp"
    if fn.endswith(".gif"):  return "image/gif"
    return "image/jpeg"


# ─────────────────────────────────────────────────────────────────────────────
# Raw JSON extraction from LLM text output
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(text: str | None) -> dict | None:
    """
    Extract the first valid JSON object from an LLM response.

    Handles:
    - ```json ... ```
    - <think>...</think>
    - Extra explanation before/after JSON
    - Multiple JSON objects (returns the first valid one)
    """

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    # Remove markdown fences
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    # Remove thinking blocks
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    text = text.strip()

    # -------------------------------------------------------
    # Try parsing the entire response first
    # -------------------------------------------------------
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # -------------------------------------------------------
    # Find the first complete JSON object using brace matching
    # -------------------------------------------------------
    start = None
    depth = 0

    for i, ch in enumerate(text):

        if ch == "{":
            if start is None:
                start = i
            depth += 1

        elif ch == "}":
            if start is not None:
                depth -= 1

                if depth == 0:
                    candidate = text[start:i + 1]

                    try:
                        obj = json.loads(candidate)

                        if isinstance(obj, dict):
                            return obj

                    except Exception:
                        pass

                    start = None

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Shared nutrition JSON prompt — IDENTICAL across every provider.
#
# This is the single source of truth for the schema every model is asked to
# return. Do not fork this per-provider (Priority 4) — if a provider needs
# different wording, add a parameter here rather than duplicating the block.
# ─────────────────────────────────────────────────────────────────────────────

NUTRITION_JSON_INSTRUCTIONS = """Return ONLY valid JSON. No markdown. No explanations. No reasoning. No <think> tags. No code fences. No extra text before or after the JSON.

Break the food down into individual ingredients. You must NOT calculate calories, protein, carbohydrates, fat, fiber, sugar, or sodium. No nutrition estimation.

For each ingredient:
- "name": short ingredient name (e.g. "Egg", "Chicken Breast", "Butter")
- "quantity": a plain number
- "unit": one of "g", "ml", "kg", "l", "piece", "slice", "cup", "tbsp", "tsp", "serving"

Unit rules (important):
- If an amount is given as a weight or volume (e.g. "250 g chicken", "20 ml oil", "1 kg rice"), use that exact number as quantity and the matching unit ("g", "ml", "kg", or "l"). Do NOT convert it into a count of pieces.
- If an amount is given as a count of whole items (e.g. "2 eggs", "3 slices of bread", "1 roti"), use that count as quantity and a countable unit ("piece", "slice", etc.) matching the item. Do NOT convert it into a weight.
- If no amount is given at all for an item, assume one typical serving: quantity 1, unit "serving".

Respond with exactly this JSON shape and no other keys:
{
  "ingredients": [
    {"name": "string", "quantity": number, "unit": "string"}
  ],
  "confidence": number between 0 and 1
}

Worked example - if the input were "2 eggs, 3 slices bread, 250 ml milk", the correct response is:
{
  "ingredients": [
    {"name": "Egg", "quantity": 2, "unit": "piece"},
    {"name": "Bread", "quantity": 3, "unit": "slice"},
    {"name": "Milk", "quantity": 250, "unit": "ml"}
  ],
  "confidence": 0.9
}

Notice every distinct food item became its own entry in "ingredients", each with its own quantity and unit - never combine multiple items into a single entry or a single descriptive name."""


def build_text_prompt(description: str) -> str:
    """Prompt for text-description meal parsing (Qwen3, Gemma text, Groq text)."""
    return (
        "Analyze this meal description and identify every distinct ingredient with its amount:\n\n"
        f"{description}\n\n"
        f"{NUTRITION_JSON_INSTRUCTIONS}"
    )


def build_vision_prompt() -> str:
    """Prompt for image-based meal parsing (QwenVL, Gemma vision, Groq vision)."""
    return (
        "You are a professional nutrition analyst. Carefully examine this food image and "
        "identify ALL visible food items as separate ingredients, estimating a reasonable "
        "quantity/unit for each based on typical portions visible in the image.\n\n"
        f"{NUTRITION_JSON_INSTRUCTIONS}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Unified response normalization — every provider funnels its parsed JSON
# through this before building a NutritionEstimate. This is what makes the
# schema identical across providers (Priority 4) and absorbs key drift
# (Priority 7), e.g. "energy" vs "calories", "protein_g" vs "protein", totals
# nested under "total"/"totals" vs flat at the top level.
# ─────────────────────────────────────────────────────────────────────────────

_TOTAL_KEY_ALIASES = {
    "energy": "calories",
    "kcal": "calories",
    "calorie": "calories",
    "protein_g": "protein",
    "proteins": "protein",
    "carbs_g": "carbs",
    "carbohydrate": "carbs",
    "carbohydrates": "carbs",
    "fat_g": "fat",
    "fats": "fat",
}

_INGREDIENT_KEY_ALIASES = {
    "item": "name",
    "food": "name",
    "ingredient": "name",
    "amount": "quantity",
    "qty": "quantity",
    "value": "quantity",
    "measure": "unit",
    "measurement": "unit",
    "units": "unit",
}


def _normalize_keys(d: dict, aliases: dict) -> dict:
    return {aliases.get(k, k): v for k, v in d.items()}


def normalize_ingredient(raw: dict | None) -> dict | None:
    """
    Normalize a single raw ingredient dict into {"name", "quantity", "unit"}.
    Tolerant of missing quantity/unit (defaults to 1.0 / "serving") but
    requires a usable name.
    """
    if not isinstance(raw, dict):
        return None

    raw = _normalize_keys(raw, _INGREDIENT_KEY_ALIASES)
    name = raw.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return None

    try:
        quantity = float(raw.get("quantity", 1.0))
    except (TypeError, ValueError):
        quantity = 1.0

    unit = raw.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        unit = "serving"

    return {"name": name.strip(), "quantity": quantity, "unit": unit.strip().lower()}


def parse_nutrition_response(parsed: dict | None) -> dict | None:
    """
    Normalize a raw LLM JSON response (already extracted via extract_json)
    into a consistent internal shape:

        {
            "ingredients": [{"name": str, "quantity": float, "unit": str}, ...],
            "calories": float,
            "protein": float,
            "carbs": float,
            "fat": float,
            "confidence": float | None,
        }

    Returns None if the response can't be salvaged into something usable.

    Handles schema drift across providers/models:
    - totals nested under "total" / "totals", or flat at the top level
    - a structured "ingredients" list, OR (backward-compat) a single flat
      "food_name" / "food" / "name" with no breakdown
    - key aliases (energy -> calories, protein_g -> protein, etc.)
    """
    if not isinstance(parsed, dict):
        return None

    # ---- totals (defaulted to 0.0 under the new ingredients-only flow) ----
    calories = 0.0
    protein = 0.0
    carbs = 0.0
    fat = 0.0

    # ---- ingredients ----
    raw_ingredients = parsed.get("ingredients")
    ingredients = []
    if isinstance(raw_ingredients, list):
        for item in raw_ingredients:
            norm = normalize_ingredient(item)
            if norm:
                ingredients.append(norm)

    if not ingredients:
        # Backward-compat: a model that ignores the structured-schema
        # instruction and returns a single flat food_name should still
        # produce a usable (if unstructured) result, rather than failing
        # the whole provider outright.
        fallback_name = parsed.get("food_name") or parsed.get("name") or parsed.get("food")
        if fallback_name:
            ingredients = [{"name": str(fallback_name), "quantity": 1.0, "unit": "serving"}]
        else:
            return None

    confidence = parsed.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
        if confidence is not None and not (0.0 <= confidence <= 1.0):
            confidence = None
    except (TypeError, ValueError):
        confidence = None

    return {
        "ingredients": ingredients,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "confidence": confidence,
    }