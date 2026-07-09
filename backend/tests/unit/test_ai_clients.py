"""
Unit tests for the AI provider clients:
  - Qwen3Client   (text)
  - GemmaClient   (text + vision)
  - GroqLlamaClient (text + vision)
  - QwenVLClient  (vision)
  - USDAClient    (structured search)

All HTTP calls are mocked with unittest.mock so no real API keys are needed.
Settings are patched to inject fake API keys where clients check for them.
"""

import json
import base64
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from app.schemas.nutrition import FoodInput, NutritionEstimate
from app.services.ai.exceptions import ProviderAPIError
from app.services.ai.qwen3_client import Qwen3Client
from app.services.ai.gemma_client import GemmaClient
from app.services.ai.groq_llama_client import GroqLlamaClient
from app.services.ai.qwen_vl_client import QwenVLClient
from app.services.ai.usda_client import USDAClient


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

VALID_NUTRITION_JSON = {
    "food_name": "Chicken Biryani",
    "calories": 650,
    "protein": 38.0,
    "carbs": 72.0,
    "fat": 18.5,
}


def _make_openai_response(content: str, status: int = 200) -> MagicMock:
    """Build a fake httpx Response that looks like an OpenAI-compatible completion."""
    body = {
        "choices": [
            {"message": {"content": content}}
        ]
    }
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status
    mock_resp.json.return_value = body
    mock_resp.text = json.dumps(body)
    return mock_resp


def _make_error_response(status: int, text: str = "Error") -> MagicMock:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status
    mock_resp.json.return_value = {}
    mock_resp.text = text
    return mock_resp


def _make_http_client(return_value: MagicMock) -> AsyncMock:
    """Return an AsyncMock that acts as an httpx.AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post = AsyncMock(return_value=return_value)
    client.get = AsyncMock(return_value=return_value)
    return client


def _fake_image_b64() -> str:
    return base64.b64encode(b"fake-image-bytes").decode()


# ─────────────────────────────────────────────────────────────────────────────
# Qwen3Client
# ─────────────────────────────────────────────────────────────────────────────


class TestQwen3Client:

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen3_client.settings")
    async def test_successful_text_parse(self, mock_settings):
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"
        mock_settings.QWEN3_MODEL = "Qwen/Qwen3-8B"

        raw = json.dumps(VALID_NUTRITION_JSON)
        http_client = _make_http_client(_make_openai_response(raw))

        client = Qwen3Client()
        food = FoodInput(input_type="text", text="Chicken biryani 1 plate")
        result = await client.extract(food, http_client)

        assert isinstance(result, NutritionEstimate)
        assert result.calories == 650.0
        assert result.protein_g == 38.0
        assert result.source_provider.startswith("Qwen3")

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen3_client.settings")
    async def test_raises_when_no_api_key(self, mock_settings):
        mock_settings.HUGGINGFACE_API_KEY = None

        client = Qwen3Client()
        food = FoodInput(input_type="text", text="2 rotis")
        with pytest.raises(ProviderAPIError, match="HUGGINGFACE_API_KEY"):
            await client.extract(food, AsyncMock())

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen3_client.settings")
    async def test_raises_when_no_text(self, mock_settings):
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"
        mock_settings.QWEN3_MODEL = "Qwen/Qwen3-8B"

        client = Qwen3Client()
        food = FoodInput(input_type="image", image_base64=_fake_image_b64())
        with pytest.raises(ProviderAPIError, match="text description"):
            await client.extract(food, AsyncMock())

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen3_client.settings")
    async def test_raises_on_http_error(self, mock_settings):
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"
        mock_settings.QWEN3_MODEL = "Qwen/Qwen3-8B"

        http_client = _make_http_client(_make_error_response(429))
        client = Qwen3Client()
        food = FoodInput(input_type="text", text="dosa")
        with pytest.raises(ProviderAPIError):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen3_client.settings")
    async def test_json_with_think_block_is_parsed(self, mock_settings):
        """Client should handle <think>…</think> prefix correctly via extract_json."""
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"
        mock_settings.QWEN3_MODEL = "Qwen/Qwen3-8B"

        raw = f"<think>Thinking...</think>\n{json.dumps(VALID_NUTRITION_JSON)}"
        http_client = _make_http_client(_make_openai_response(raw))

        client = Qwen3Client()
        food = FoodInput(input_type="text", text="biryani")
        result = await client.extract(food, http_client)
        assert result.calories == 650.0


# ─────────────────────────────────────────────────────────────────────────────
# GemmaClient
# ─────────────────────────────────────────────────────────────────────────────


class TestGemmaClient:

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_successful_text_parse(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"
        mock_settings.OPENROUTER_GEMMA_MODEL = "google/gemma-3-27b-it:free"

        raw = json.dumps(VALID_NUTRITION_JSON)
        http_client = _make_http_client(_make_openai_response(raw))

        client = GemmaClient()
        food = FoodInput(input_type="text", text="Chicken biryani")
        result = await client.extract(food, http_client)

        assert isinstance(result, NutritionEstimate)
        assert result.source_provider == "Gemma (OpenRouter)"
        assert result.carbs_g == 72.0

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_successful_image_parse(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"
        mock_settings.OPENROUTER_GEMMA_MODEL = "google/gemma-3-27b-it:free"

        raw = json.dumps(VALID_NUTRITION_JSON)
        http_client = _make_http_client(_make_openai_response(raw))

        client = GemmaClient()
        food = FoodInput(
            input_type="image",
            image_base64=_fake_image_b64(),
            filename="food.jpg",
        )
        result = await client.extract(food, http_client)
        assert result.calories == 650.0

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_raises_when_no_api_key(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = None

        client = GemmaClient()
        food = FoodInput(input_type="text", text="salad")
        with pytest.raises(ProviderAPIError, match="OPENROUTER_API_KEY"):
            await client.extract(food, AsyncMock())

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_raises_on_rate_limit_429(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"
        mock_settings.OPENROUTER_GEMMA_MODEL = "google/gemma-3-27b-it:free"

        http_client = _make_http_client(_make_error_response(429))
        client = GemmaClient()
        food = FoodInput(input_type="text", text="pizza")
        with pytest.raises(ProviderAPIError, match="429"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_raises_on_empty_choices(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"
        mock_settings.OPENROUTER_GEMMA_MODEL = "google/gemma-3-27b-it:free"

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": []}
        http_client = _make_http_client(mock_resp)

        client = GemmaClient()
        food = FoodInput(input_type="text", text="pasta")
        with pytest.raises(ProviderAPIError, match="empty choices"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_raises_on_invalid_json_response(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"
        mock_settings.OPENROUTER_GEMMA_MODEL = "google/gemma-3-27b-it:free"

        http_client = _make_http_client(_make_openai_response("This is not JSON at all."))
        client = GemmaClient()
        food = FoodInput(input_type="text", text="soup")
        with pytest.raises(ProviderAPIError, match="unparseable"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_raises_on_missing_required_keys(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"
        mock_settings.OPENROUTER_GEMMA_MODEL = "google/gemma-3-27b-it:free"

        incomplete = '{"food_name": "Bread", "calories": 80}'  # missing protein/carbs/fat
        http_client = _make_http_client(_make_openai_response(incomplete))

        client = GemmaClient()
        food = FoodInput(input_type="text", text="bread")
        with pytest.raises(ProviderAPIError, match="incomplete"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_raises_on_timeout(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"
        mock_settings.OPENROUTER_GEMMA_MODEL = "google/gemma-3-27b-it:free"

        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        client = GemmaClient()
        food = FoodInput(input_type="text", text="noodles")
        with pytest.raises(ProviderAPIError, match="timed out"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.gemma_client.settings")
    async def test_raises_when_no_input(self, mock_settings):
        mock_settings.OPENROUTER_API_KEY = "or-test-key"

        client = GemmaClient()
        # FoodInput with neither image nor text
        food = FoodInput(input_type="text", text="x")  # valid but we patch text to None
        food.text = None
        food.image_base64 = None
        with pytest.raises(ProviderAPIError, match="requires either"):
            await client.extract(food, AsyncMock())


# ─────────────────────────────────────────────────────────────────────────────
# GroqLlamaClient
# ─────────────────────────────────────────────────────────────────────────────


class TestGroqLlamaClient:

    @pytest.mark.asyncio
    @patch("app.services.ai.groq_llama_client.settings")
    async def test_successful_text_parse(self, mock_settings):
        mock_settings.GROQ_API_KEY = "groq-test-key"
        mock_settings.GROQ_LLAMA_TEXT_MODEL = "llama-3.3-70b-versatile"
        mock_settings.GROQ_LLAMA_VISION_MODEL = "llama-3.2-11b-vision-preview"

        raw = json.dumps(VALID_NUTRITION_JSON)
        http_client = _make_http_client(_make_openai_response(raw))

        client = GroqLlamaClient()
        food = FoodInput(input_type="text", text="Chicken biryani")
        result = await client.extract(food, http_client)

        assert isinstance(result, NutritionEstimate)
        assert result.source_provider == "Groq Llama"
        assert result.fat_g == 18.5

    @pytest.mark.asyncio
    @patch("app.services.ai.groq_llama_client.settings")
    async def test_uses_vision_model_for_image_input(self, mock_settings):
        mock_settings.GROQ_API_KEY = "groq-test-key"
        mock_settings.GROQ_LLAMA_TEXT_MODEL = "llama-3.3-70b-versatile"
        mock_settings.GROQ_LLAMA_VISION_MODEL = "llama-3.2-11b-vision-preview"

        raw = json.dumps(VALID_NUTRITION_JSON)
        http_client = _make_http_client(_make_openai_response(raw))

        client = GroqLlamaClient()
        food = FoodInput(
            input_type="image",
            image_base64=_fake_image_b64(),
            filename="plate.jpg",
        )
        result = await client.extract(food, http_client)
        assert result.calories == 650.0

        # Check that the payload sent used the vision model
        call_kwargs = http_client.post.call_args[1]
        assert call_kwargs["json"]["model"] == "llama-3.2-11b-vision-preview"

    @pytest.mark.asyncio
    @patch("app.services.ai.groq_llama_client.settings")
    async def test_raises_when_no_api_key(self, mock_settings):
        mock_settings.GROQ_API_KEY = None

        client = GroqLlamaClient()
        food = FoodInput(input_type="text", text="dal")
        with pytest.raises(ProviderAPIError, match="GROQ_API_KEY"):
            await client.extract(food, AsyncMock())

    @pytest.mark.asyncio
    @patch("app.services.ai.groq_llama_client.settings")
    async def test_raises_on_http_500(self, mock_settings):
        mock_settings.GROQ_API_KEY = "groq-test-key"
        mock_settings.GROQ_LLAMA_TEXT_MODEL = "llama-3.3-70b-versatile"
        mock_settings.GROQ_LLAMA_VISION_MODEL = "llama-3.2-11b-vision-preview"

        http_client = _make_http_client(_make_error_response(500))
        client = GroqLlamaClient()
        food = FoodInput(input_type="text", text="biryani")
        with pytest.raises(ProviderAPIError, match="HTTP 500"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.groq_llama_client.settings")
    async def test_raises_on_unparseable_response(self, mock_settings):
        mock_settings.GROQ_API_KEY = "groq-test-key"
        mock_settings.GROQ_LLAMA_TEXT_MODEL = "llama-3.3-70b-versatile"
        mock_settings.GROQ_LLAMA_VISION_MODEL = "llama-3.2-11b-vision-preview"

        http_client = _make_http_client(_make_openai_response("Sorry, I cannot help."))
        client = GroqLlamaClient()
        food = FoodInput(input_type="text", text="mystery food")
        with pytest.raises(ProviderAPIError, match="unparseable"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.groq_llama_client.settings")
    async def test_raises_on_rate_limit(self, mock_settings):
        mock_settings.GROQ_API_KEY = "groq-test-key"
        mock_settings.GROQ_LLAMA_TEXT_MODEL = "llama-3.3-70b-versatile"
        mock_settings.GROQ_LLAMA_VISION_MODEL = "llama-3.2-11b-vision-preview"

        http_client = _make_http_client(_make_error_response(429))
        client = GroqLlamaClient()
        food = FoodInput(input_type="text", text="idli")
        with pytest.raises(ProviderAPIError, match="429"):
            await client.extract(food, http_client)


# ─────────────────────────────────────────────────────────────────────────────
# USDAClient
# ─────────────────────────────────────────────────────────────────────────────


def _make_usda_response(foods: list, status: int = 200) -> MagicMock:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status
    mock_resp.json.return_value = {"foods": foods}
    mock_resp.text = ""
    return mock_resp


SAMPLE_USDA_FOOD = {
    "description": "Chicken, breast, roasted",
    "foodNutrients": [
        {"nutrientId": 1008, "value": 165},   # calories
        {"nutrientId": 1003, "value": 31.0},  # protein
        {"nutrientId": 1005, "value": 0.0},   # carbs
        {"nutrientId": 1004, "value": 3.6},   # fat
    ],
}


class TestUSDAClient:

    @pytest.mark.asyncio
    @patch("app.services.ai.usda_client.settings")
    async def test_successful_search(self, mock_settings):
        mock_settings.USDA_API_KEY = "usda-test-key"

        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.get = AsyncMock(return_value=_make_usda_response([SAMPLE_USDA_FOOD]))

        client = USDAClient()
        food = FoodInput(input_type="text", text="chicken breast")
        result = await client.extract(food, http_client)

        assert isinstance(result, NutritionEstimate)
        assert result.calories == 165.0
        assert result.protein_g == 31.0
        assert result.fat_g == 3.6
        assert result.source_provider == "USDA FoodData Central"

    @pytest.mark.asyncio
    @patch("app.services.ai.usda_client.settings")
    async def test_raises_when_no_api_key(self, mock_settings):
        mock_settings.USDA_API_KEY = None

        client = USDAClient()
        food = FoodInput(input_type="text", text="apple")
        with pytest.raises(ProviderAPIError, match="USDA_API_KEY"):
            await client.extract(food, AsyncMock())

    @pytest.mark.asyncio
    @patch("app.services.ai.usda_client.settings")
    async def test_raises_on_empty_foods_list(self, mock_settings):
        mock_settings.USDA_API_KEY = "usda-test-key"

        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.get = AsyncMock(return_value=_make_usda_response([]))

        client = USDAClient()
        food = FoodInput(input_type="text", text="unicorn steak")
        with pytest.raises(ProviderAPIError, match="No USDA food entries"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.usda_client.settings")
    async def test_raises_when_all_candidates_are_empty(self, mock_settings):
        """All returned foods have zero macros — should raise after exhausting all."""
        mock_settings.USDA_API_KEY = "usda-test-key"

        empty_food = {
            "description": "Water",
            "foodNutrients": [
                {"nutrientId": 1008, "value": 0},
                {"nutrientId": 1003, "value": 0.0},
                {"nutrientId": 1005, "value": 0.0},
                {"nutrientId": 1004, "value": 0.0},
            ],
        }
        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.get = AsyncMock(return_value=_make_usda_response([empty_food]))

        client = USDAClient()
        food = FoodInput(input_type="text", text="water")
        with pytest.raises(ProviderAPIError, match="empty or invalid"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.usda_client.settings")
    async def test_skips_empty_and_returns_valid_candidate(self, mock_settings):
        """First candidate is empty, second is valid — client should use the second."""
        mock_settings.USDA_API_KEY = "usda-test-key"

        empty_food = {
            "description": "Placeholder",
            "foodNutrients": [
                {"nutrientId": 1008, "value": 0},
                {"nutrientId": 1003, "value": 0.0},
                {"nutrientId": 1005, "value": 0.0},
                {"nutrientId": 1004, "value": 0.0},
            ],
        }
        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.get = AsyncMock(
            return_value=_make_usda_response([empty_food, SAMPLE_USDA_FOOD])
        )

        client = USDAClient()
        food = FoodInput(input_type="text", text="chicken")
        result = await client.extract(food, http_client)
        assert result.calories == 165.0

    @pytest.mark.asyncio
    @patch("app.services.ai.usda_client.settings")
    async def test_raises_on_http_error(self, mock_settings):
        mock_settings.USDA_API_KEY = "usda-test-key"

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 403
        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.get = AsyncMock(return_value=mock_resp)

        client = USDAClient()
        food = FoodInput(input_type="text", text="banana")
        with pytest.raises(ProviderAPIError, match="HTTP 403"):
            await client.extract(food, http_client)

    def test_parse_food_returns_none_for_all_zero_macros(self):
        """_parse_food is a synchronous helper — test it directly."""
        client = USDAClient()
        food_item = {
            "description": "Empty",
            "foodNutrients": [
                {"nutrientId": 1008, "value": 0},
                {"nutrientId": 1003, "value": 0.0},
                {"nutrientId": 1005, "value": 0.0},
                {"nutrientId": 1004, "value": 0.0},
            ],
        }
        assert client._parse_food(food_item) is None

    def test_parse_food_returns_dict_for_valid_food(self):
        client = USDAClient()
        result = client._parse_food(SAMPLE_USDA_FOOD)
        assert result is not None
        assert result["calories"] == 165
        assert result["protein"] == 31.0
        assert result["fat"] == 3.6
        assert result["food_name"] == "Chicken, Breast, Roasted"  # title-cased


# ─────────────────────────────────────────────────────────────────────────────
# QwenVLClient
# ─────────────────────────────────────────────────────────────────────────────


class TestQwenVLClient:

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen_vl_client.settings")
    async def test_raises_when_no_image(self, mock_settings):
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"

        client = QwenVLClient()
        food = FoodInput(input_type="text", text="hello")
        food.image_base64 = None  # ensure no image
        with pytest.raises(ProviderAPIError, match="image base64"):
            await client.extract(food, AsyncMock())

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen_vl_client.settings")
    async def test_successful_hf_provider_call(self, mock_settings):
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_VISION_MODEL = "qwen2.5vl:7b"

        raw = json.dumps(VALID_NUTRITION_JSON)
        http_client = _make_http_client(_make_openai_response(raw))

        client = QwenVLClient()
        food = FoodInput(
            input_type="image",
            image_base64=_fake_image_b64(),
            filename="food.jpg",
        )
        result = await client.extract(food, http_client)

        assert isinstance(result, NutritionEstimate)
        assert result.calories == 650.0
        assert "QwenVL" in result.source_provider

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen_vl_client.settings")
    async def test_falls_back_to_ollama_when_hf_fails(self, mock_settings):
        """If HF returns non-200, client should fall back to Ollama."""
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_VISION_MODEL = "qwen2.5vl:7b"

        hf_error = _make_error_response(503)
        ollama_raw = json.dumps(VALID_NUTRITION_JSON)
        ollama_resp = MagicMock(spec=httpx.Response)
        ollama_resp.status_code = 200
        ollama_resp.json.return_value = {"message": {"content": ollama_raw}}

        # First call → HF 503, second call → Ollama 200
        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.post = AsyncMock(side_effect=[hf_error, hf_error, ollama_resp])

        client = QwenVLClient()
        food = FoodInput(
            input_type="image",
            image_base64=_fake_image_b64(),
        )
        result = await client.extract(food, http_client)
        assert result.source_provider == "Ollama (Local QwenVL)"

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen_vl_client.settings")
    async def test_raises_when_all_providers_fail(self, mock_settings):
        """All HF routers fail AND Ollama fails → ProviderAPIError raised."""
        mock_settings.HUGGINGFACE_API_KEY = "hf-test-key"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_VISION_MODEL = "qwen2.5vl:7b"

        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.post = AsyncMock(return_value=_make_error_response(500))

        client = QwenVLClient()
        food = FoodInput(input_type="image", image_base64=_fake_image_b64())
        with pytest.raises(ProviderAPIError, match="QwenVLClient failed"):
            await client.extract(food, http_client)

    @pytest.mark.asyncio
    @patch("app.services.ai.qwen_vl_client.settings")
    async def test_skips_hf_and_goes_to_ollama_when_no_hf_key(self, mock_settings):
        """No HF key configured → skip HF entirely, go straight to Ollama."""
        mock_settings.HUGGINGFACE_API_KEY = None
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.OLLAMA_VISION_MODEL = "qwen2.5vl:7b"

        ollama_raw = json.dumps(VALID_NUTRITION_JSON)
        ollama_resp = MagicMock(spec=httpx.Response)
        ollama_resp.status_code = 200
        ollama_resp.json.return_value = {"message": {"content": ollama_raw}}

        http_client = AsyncMock(spec=httpx.AsyncClient)
        http_client.post = AsyncMock(return_value=ollama_resp)

        client = QwenVLClient()
        food = FoodInput(input_type="image", image_base64=_fake_image_b64())
        result = await client.extract(food, http_client)
        assert result.source_provider == "Ollama (Local QwenVL)"
