from app.models.profile import Profile
from app.repositories.profile_repository import ProfileRepository
from app.services.calculators.nutrition_calculator import NutritionCalculator


class ProfileService:

    def __init__(self, db):
        self.repo = ProfileRepository(db)
        self.calculator = NutritionCalculator()

    async def create_profile(
        self,
        user,
        request,
    ):

        existing = await self.repo.get_by_user_id(user.id)

        if existing:
            raise ValueError("Profile already exists.")

        results = self.calculator.calculate_all(
            sex=request.sex,
            date_of_birth=request.date_of_birth,
            height_cm=request.height_cm,
            weight_kg=request.current_weight_kg,
            activity_level=request.activity_level,
            goal=request.goal,
        )

        profile = Profile(
            user_id=user.id,
            full_name=request.full_name,
            sex=request.sex,
            date_of_birth=request.date_of_birth,
            height_cm=request.height_cm,
            current_weight_kg=request.current_weight_kg,
            goal_weight_kg=request.goal_weight_kg,
            goal=request.goal,
            activity_level=request.activity_level,
            exercise_days_per_week=request.exercise_days_per_week,
            preferred_unit=request.preferred_unit,
            bmi=results["bmi"],
            bmr=results["bmr"],
            tdee=results["tdee"],
            daily_calorie_target=results["daily_calories"],
            daily_protein_target=results["protein"],
            daily_carb_target=results["carbs"],
            daily_fat_target=results["fat"],
        )

        return await self.repo.create(profile)

    async def get_my_profile(
        self,
        user,
    ):

        profile = await self.repo.get_by_user_id(user.id)

        if profile is None:
            raise ValueError("Profile not found.")

        return profile

    async def update_profile(
        self,
        user,
        request,
    ):

        profile = await self.repo.get_by_user_id(user.id)

        if profile is None:
            raise ValueError("Profile not found.")

        update_data = request.model_dump(
            exclude_unset=True
        )

        for key, value in update_data.items():
            setattr(profile, key, value)

        results = self.calculator.calculate_all(
            sex=profile.sex,
            date_of_birth=profile.date_of_birth,
            height_cm=profile.height_cm,
            weight_kg=profile.current_weight_kg,
            activity_level=profile.activity_level,
            goal=profile.goal,
        )

        profile.bmi = results["bmi"]
        profile.bmr = results["bmr"]
        profile.tdee = results["tdee"]
        profile.daily_calorie_target = results["daily_calories"]
        profile.daily_protein_target = results["protein"]
        profile.daily_carb_target = results["carbs"]
        profile.daily_fat_target = results["fat"]

        return await self.repo.update(profile)