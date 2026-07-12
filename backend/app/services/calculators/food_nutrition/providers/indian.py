import re
from app.services.calculators.food_nutrition.constants import _LOCAL_FOOD_DB
from app.services.calculators.food_nutrition.models import IngredientMatch, NutritionFacts
from app.services.calculators.food_nutrition.exceptions import IngredientNotFoundError

_INDIAN_FOOD_KEYS = {
    "roti", "chapati", "paratha", "naan", "poori", "idli", "dosa", "uttapam", "upma", "poha", "khichdi",
    "dal", "dal makhani", "paneer", "palak paneer", "butter chicken", "chicken tikka", "biryani",
    "rajma", "chole", "aloo gobi", "sambhar", "rasam", "samosa", "pakora", "vada", "pani puri",
    "bhel puri", "pav bhaji", "gulab jamun", "rasgulla", "halwa", "kheer", "lassi", "chai"
}

def make_nutrition_facts_from_local_db(food_name: str, base_data: dict) -> NutritionFacts:
    raw_cal = float(base_data["calories"])
    raw_prot = float(base_data["protein"])
    raw_carbs = float(base_data["carbs"])
    raw_fat = float(base_data["fat"])
    
    portions = {}
    
    piece_match = re.search(r"\((\d+)\s+pieces?\)", food_name, re.IGNORECASE)
    serving_match = re.search(r"\((\d+)\s+servings?\)", food_name, re.IGNORECASE)
    ml_match = re.search(r"\((\d+)\s*ml\)", food_name, re.IGNORECASE)
    g_match = re.search(r"\((\d+)\s*g\)", food_name, re.IGNORECASE)
    
    if piece_match:
        count = int(piece_match.group(1))
        portions["piece"] = 100.0
        portions["serving"] = 100.0 * count
        cal_100g = raw_cal / count
        prot_100g = raw_prot / count
        carbs_100g = raw_carbs / count
        fat_100g = raw_fat / count
    elif serving_match:
        count = int(serving_match.group(1))
        portions["serving"] = 100.0
        portions["piece"] = 100.0 / count
        cal_100g = raw_cal / count
        prot_100g = raw_prot / count
        carbs_100g = raw_carbs / count
        fat_100g = raw_fat / count
    elif ml_match:
        amount = int(ml_match.group(1))
        portions["ml"] = 1.0
        portions["serving"] = float(amount)
        cal_100g = raw_cal * 100.0 / amount
        prot_100g = raw_prot * 100.0 / amount
        carbs_100g = raw_carbs * 100.0 / amount
        fat_100g = raw_fat * 100.0 / amount
    elif g_match:
        amount = int(g_match.group(1))
        portions["serving"] = float(amount)
        cal_100g = raw_cal * 100.0 / amount
        prot_100g = raw_prot * 100.0 / amount
        carbs_100g = raw_carbs * 100.0 / amount
        fat_100g = raw_fat * 100.0 / amount
    elif "slice" in food_name.lower():
        portions["slice"] = 100.0
        portions["piece"] = 100.0
        portions["serving"] = 100.0
        cal_100g = raw_cal
        prot_100g = raw_prot
        carbs_100g = raw_carbs
        fat_100g = raw_fat
    elif "medium" in food_name.lower():
        portions["piece"] = 100.0
        portions["serving"] = 100.0
        cal_100g = raw_cal
        prot_100g = raw_prot
        carbs_100g = raw_carbs
        fat_100g = raw_fat
    else:
        portions["piece"] = 100.0
        portions["serving"] = 100.0
        cal_100g = raw_cal
        prot_100g = raw_prot
        carbs_100g = raw_carbs
        fat_100g = raw_fat
        
    return NutritionFacts(
        food_name=food_name,
        calories=cal_100g,
        protein=prot_100g,
        carbohydrates=carbs_100g,
        fat=fat_100g,
        fiber=0.0,
        sugar=0.0,
        sodium=0.0,
        serving_unit="g",
        portions=portions
    )

class IndianNutritionProvider:
    async def lookup(self, ingredient: IngredientMatch) -> NutritionFacts:
        query = ingredient.canonical_name.lower().strip()
        for keyword in _INDIAN_FOOD_KEYS:
            if keyword in _LOCAL_FOOD_DB:
                if keyword == query or keyword in query:
                    return make_nutrition_facts_from_local_db(
                        _LOCAL_FOOD_DB[keyword]["food_name"],
                        _LOCAL_FOOD_DB[keyword]
                    )
        raise IngredientNotFoundError(
            f"IndianNutritionProvider: '{ingredient.canonical_name}' not found."
        )
