from datetime import date

from app.core.enums import ActivityLevel, Goal, Sex


class NutritionCalculator:
    """
    Responsible for all nutrition-related calculations.
    """

    ACTIVITY_MULTIPLIERS = {
        ActivityLevel.SEDENTARY: 1.20,
        ActivityLevel.LIGHT: 1.375,
        ActivityLevel.MODERATE: 1.55,
        ActivityLevel.VERY_ACTIVE: 1.725,
        ActivityLevel.ATHLETE: 1.90,
    }

    def calculate_age(
        self,
        date_of_birth: date,
    ) -> int:

        today = date.today()

        age = today.year - date_of_birth.year

        if (
            (today.month, today.day)
            <
            (date_of_birth.month, date_of_birth.day)
        ):
            age -= 1

        return age

    def calculate_bmi(
        self,
        weight_kg: float,
        height_cm: float,
    ) -> float:

        height_m = height_cm / 100

        bmi = weight_kg / (height_m ** 2)

        return round(bmi, 2)

    def calculate_bmr(
        self,
        sex: Sex,
        weight_kg: float,
        height_cm: float,
        age: int,
    ) -> float:

        if sex == Sex.MALE:

            bmr = (
                10 * weight_kg
                + 6.25 * height_cm
                - 5 * age
                + 5
            )

        else:

            bmr = (
                10 * weight_kg
                + 6.25 * height_cm
                - 5 * age
                - 161
            )

        return round(bmr)

    def calculate_tdee(
        self,
        bmr: float,
        activity_level: ActivityLevel,
    ) -> float:

        multiplier = self.ACTIVITY_MULTIPLIERS[
            activity_level
        ]

        return round(
            bmr * multiplier
        )

    def calculate_daily_calories(
        self,
        tdee: float,
        goal: Goal,
    ) -> int:

        if goal == Goal.LOSE:
            return max(int(tdee - 500), 1200)

        if goal == Goal.GAIN:
            return int(tdee + 300)

        return int(tdee)

    def calculate_macros(
        self,
        calories: int,
    ) -> dict:

        protein_calories = calories * 0.30

        fat_calories = calories * 0.25

        carb_calories = calories * 0.45

        protein = protein_calories / 4

        carbs = carb_calories / 4

        fat = fat_calories / 9

        return {
            "protein": round(protein),
            "carbs": round(carbs),
            "fat": round(fat),
        }

    def calculate_all(
        self,
        *,
        sex: Sex,
        date_of_birth: date,
        height_cm: float,
        weight_kg: float,
        activity_level: ActivityLevel,
        goal: Goal,
    ) -> dict:

        age = self.calculate_age(
            date_of_birth
        )

        bmi = self.calculate_bmi(
            weight_kg,
            height_cm,
        )

        bmr = self.calculate_bmr(
            sex,
            weight_kg,
            height_cm,
            age,
        )

        tdee = self.calculate_tdee(
            bmr,
            activity_level,
        )

        calories = self.calculate_daily_calories(
            tdee,
            goal,
        )

        macros = self.calculate_macros(
            calories
        )

        return {
            "age": age,
            "bmi": bmi,
            "bmr": bmr,
            "tdee": tdee,
            "daily_calories": calories,
            "protein": macros["protein"],
            "carbs": macros["carbs"],
            "fat": macros["fat"],
        }