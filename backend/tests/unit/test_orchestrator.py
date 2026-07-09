"""
Unit tests for AIOrchestrator (app.services.ai.orchestrator)

Verifies:
  - Successful parse delegates to the correct chain
  - Cache hits short-circuit provider calls
  - Fallback fires on provider failure
  - AIOrchestrationError raised when the entire chain fails
  - Image vs. text chains differ correctly
"""

import hashlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.schemas.nutrition import FoodInput, NutritionEstimate, ExtractedIngredient
from app.services.ai.orchestrator import AIOrchestrator
from app.services.ai.exceptions import AIOrchestrationError, ProviderAPIError


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_estimate(source: str = "MockProvider", calories: float = 300.0) -> NutritionEstimate:
    return NutritionEstimate(
        ingredients=[ExtractedIngredient(name="Test Food", quantity=1.0, unit="serving")],
        calories=calories,
        protein_g=10.0,
        carbs_g=40.0,
        fat_g=5.0,
        confidence=0.9,
        source_provider=source,
    )


def _make_provider(name: str, supports_vision: bool = True, result=None, raises=None):
    """Build a mock NutritionProvider."""
    provider = AsyncMock()
    provider.name = name
    provider.supports_vision = supports_vision
    if raises:
        provider.extract = AsyncMock(side_effect=raises)
    else:
        provider.extract = AsyncMock(return_value=result or _make_estimate(name))
    return provider


def _make_orchestrator(qwen_vl=None, qwen3=None, gemma=None, groq=None, usda=None):
    return AIOrchestrator(
        qwen_vl=qwen_vl or _make_provider("QwenVL"),
        qwen3=qwen3 or _make_provider("Qwen3"),
        gemma=gemma or _make_provider("Gemma"),
        groq=groq or _make_provider("Groq"),
        usda=usda or _make_provider("USDA"),
    )


_FAKE_HTTP = AsyncMock(spec=httpx.AsyncClient)
_FAKE_IMAGE_B64 = "aGVsbG8gd29ybGQ="  # base64("hello world")


# ─────────────────────────────────────────────────────────────────────────────
# parse_text — happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestParseText:

    @pytest.mark.asyncio
    async def test_qwen3_succeeds_on_first_call(self):
        qwen3 = _make_provider("Qwen3", result=_make_estimate("Qwen3", 500.0))
        gemma = _make_provider("Gemma")
        orch = _make_orchestrator(qwen3=qwen3, gemma=gemma)

        result = await orch.parse_text("2 rotis", _FAKE_HTTP)

        assert result.source_provider == "Qwen3"
        assert result.calories == 500.0
        qwen3.extract.assert_called_once()
        gemma.extract.assert_not_called()  # Gemma not touched on first-try success

    @pytest.mark.asyncio
    async def test_fallback_to_gemma_when_qwen3_fails(self):
        qwen3 = _make_provider("Qwen3", raises=ProviderAPIError("HF timeout"))
        gemma = _make_provider("Gemma", result=_make_estimate("Gemma", 400.0))
        groq = _make_provider("Groq")
        orch = _make_orchestrator(qwen3=qwen3, gemma=gemma, groq=groq)

        result = await orch.parse_text("dosa with chutney", _FAKE_HTTP)

        assert result.source_provider == "Gemma"
        qwen3.extract.assert_called_once()
        gemma.extract.assert_called_once()
        groq.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_to_groq_when_gemma_fails(self):
        qwen3 = _make_provider("Qwen3", raises=ProviderAPIError("fail"))
        gemma = _make_provider("Gemma", raises=ProviderAPIError("fail"))
        groq = _make_provider("Groq", result=_make_estimate("Groq", 250.0))
        usda = _make_provider("USDA")
        orch = _make_orchestrator(qwen3=qwen3, gemma=gemma, groq=groq, usda=usda)

        result = await orch.parse_text("apple", _FAKE_HTTP)
        assert result.source_provider == "Groq"
        groq.extract.assert_called_once()
        usda.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_to_usda_when_llms_fail(self):
        failing = ProviderAPIError("fail")
        qwen3 = _make_provider("Qwen3", raises=failing)
        gemma = _make_provider("Gemma", raises=failing)
        groq = _make_provider("Groq", raises=failing)
        usda = _make_provider("USDA", result=_make_estimate("USDA", 95.0))
        orch = _make_orchestrator(qwen3=qwen3, gemma=gemma, groq=groq, usda=usda)

        result = await orch.parse_text("apple", _FAKE_HTTP)
        assert result.source_provider == "USDA"

    @pytest.mark.asyncio
    async def test_raises_orchestration_error_when_entire_chain_fails(self):
        failing = ProviderAPIError("fail")
        orch = _make_orchestrator(
            qwen3=_make_provider("Qwen3", raises=failing),
            gemma=_make_provider("Gemma", raises=failing),
            groq=_make_provider("Groq", raises=failing),
            usda=_make_provider("USDA", raises=failing),
        )
        with pytest.raises(AIOrchestrationError, match="All fallback providers failed"):
            await orch.parse_text("mystery food", _FAKE_HTTP)


# ─────────────────────────────────────────────────────────────────────────────
# parse_image — happy path
# ─────────────────────────────────────────────────────────────────────────────

class TestParseImage:

    @pytest.mark.asyncio
    async def test_qwen_vl_succeeds_on_first_call(self):
        qwen_vl = _make_provider("QwenVL", result=_make_estimate("QwenVL", 700.0))
        gemma = _make_provider("Gemma")
        orch = _make_orchestrator(qwen_vl=qwen_vl, gemma=gemma)

        result = await orch.parse_image(_FAKE_IMAGE_B64, _FAKE_HTTP, filename="food.jpg")
        assert result.source_provider == "QwenVL"
        assert result.calories == 700.0
        gemma.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_to_gemma_when_qwen_vl_fails(self):
        qwen_vl = _make_provider("QwenVL", raises=ProviderAPIError("fail"))
        gemma = _make_provider("Gemma", result=_make_estimate("Gemma", 600.0))
        groq = _make_provider("Groq")
        orch = _make_orchestrator(qwen_vl=qwen_vl, gemma=gemma, groq=groq)

        result = await orch.parse_image(_FAKE_IMAGE_B64, _FAKE_HTTP)
        assert result.source_provider == "Gemma"
        groq.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_to_groq_when_gemma_fails_on_image(self):
        failing = ProviderAPIError("fail")
        qwen_vl = _make_provider("QwenVL", raises=failing)
        gemma = _make_provider("Gemma", raises=failing)
        groq = _make_provider("Groq", result=_make_estimate("Groq", 500.0))
        orch = _make_orchestrator(qwen_vl=qwen_vl, gemma=gemma, groq=groq)

        result = await orch.parse_image(_FAKE_IMAGE_B64, _FAKE_HTTP)
        assert result.source_provider == "Groq"

    @pytest.mark.asyncio
    async def test_raises_orchestration_error_when_image_chain_fails(self):
        failing = ProviderAPIError("fail")
        orch = _make_orchestrator(
            qwen_vl=_make_provider("QwenVL", raises=failing),
            gemma=_make_provider("Gemma", raises=failing),
            groq=_make_provider("Groq", raises=failing),
        )
        with pytest.raises(AIOrchestrationError):
            await orch.parse_image(_FAKE_IMAGE_B64, _FAKE_HTTP)


# ─────────────────────────────────────────────────────────────────────────────
# Caching behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchestratorCache:

    @pytest.mark.asyncio
    async def test_text_cache_hit_skips_providers(self):
        qwen3 = _make_provider("Qwen3", result=_make_estimate("Qwen3", 200.0))
        orch = _make_orchestrator(qwen3=qwen3)

        # First call — populates cache
        await orch.parse_text("banana", _FAKE_HTTP)
        # Second call — should be a cache hit
        result = await orch.parse_text("banana", _FAKE_HTTP)

        # Provider should only have been called ONCE despite two requests
        assert qwen3.extract.call_count == 1
        assert result.calories == 200.0

    @pytest.mark.asyncio
    async def test_text_cache_key_is_case_insensitive(self):
        qwen3 = _make_provider("Qwen3")
        orch = _make_orchestrator(qwen3=qwen3)

        await orch.parse_text("BANANA", _FAKE_HTTP)
        await orch.parse_text("banana", _FAKE_HTTP)

        # Both "BANANA" and "banana" should resolve to the same cache key
        assert qwen3.extract.call_count == 1

    @pytest.mark.asyncio
    async def test_image_cache_hit_skips_providers(self):
        qwen_vl = _make_provider("QwenVL", result=_make_estimate("QwenVL", 900.0))
        orch = _make_orchestrator(qwen_vl=qwen_vl)

        await orch.parse_image(_FAKE_IMAGE_B64, _FAKE_HTTP)
        result = await orch.parse_image(_FAKE_IMAGE_B64, _FAKE_HTTP)

        assert qwen_vl.extract.call_count == 1
        assert result.calories == 900.0

    @pytest.mark.asyncio
    async def test_different_texts_get_different_cache_entries(self):
        qwen3 = _make_provider("Qwen3")
        orch = _make_orchestrator(qwen3=qwen3)

        await orch.parse_text("apple", _FAKE_HTTP)
        await orch.parse_text("orange", _FAKE_HTTP)

        # Each unique text should trigger one provider call
        assert qwen3.extract.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_stores_and_returns_correct_result(self):
        estimate = _make_estimate("Qwen3", 111.0)
        qwen3 = _make_provider("Qwen3", result=estimate)
        orch = _make_orchestrator(qwen3=qwen3)

        first = await orch.parse_text("mango lassi", _FAKE_HTTP)
        second = await orch.parse_text("mango lassi", _FAKE_HTTP)

        assert first.calories == 111.0
        assert second.calories == 111.0
