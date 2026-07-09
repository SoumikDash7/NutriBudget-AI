import httpx
from typing import Protocol
from app.schemas.nutrition import FoodInput, NutritionEstimate


class NutritionProvider(Protocol):
    name: str
    supports_vision: bool

    async def extract(self, food_input: FoodInput, http_client: httpx.AsyncClient) -> NutritionEstimate:
        """No internal retries — AIOrchestrator owns retry/fallback logic."""
        ...