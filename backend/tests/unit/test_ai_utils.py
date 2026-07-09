"""
Unit tests for app.services.ai.utils

Tests the two pure functions:
  - extract_json()  — robust JSON extraction from raw LLM text
  - detect_mime()   — filename → MIME type mapping
"""

import pytest
from app.services.ai.utils import extract_json, detect_mime


# ─────────────────────────────────────────────────────────────────────────────
# extract_json
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractJson:

    # ── Happy paths ──────────────────────────────────────────────────────────

    def test_clean_json_is_parsed(self):
        text = '{"food_name": "Apple", "calories": 95, "protein": 0.5, "carbs": 25.0, "fat": 0.3}'
        result = extract_json(text)
        assert result == {
            "food_name": "Apple",
            "calories": 95,
            "protein": 0.5,
            "carbs": 25.0,
            "fat": 0.3,
        }

    def test_json_wrapped_in_markdown_code_fence(self):
        text = '```json\n{"food_name": "Banana", "calories": 105}\n```'
        result = extract_json(text)
        assert result is not None
        assert result["food_name"] == "Banana"
        assert result["calories"] == 105

    def test_json_wrapped_in_bare_code_fence(self):
        text = '```\n{"food_name": "Mango", "calories": 60}\n```'
        result = extract_json(text)
        assert result is not None
        assert result["food_name"] == "Mango"

    def test_json_with_surrounding_text(self):
        """LLM adds preamble then the JSON — second-pass extraction should still work."""
        text = 'Here is the nutrition estimate:\n{"food_name": "Rice", "calories": 200} Done.'
        result = extract_json(text)
        assert result is not None
        assert result["food_name"] == "Rice"

    def test_think_block_before_json_is_stripped(self):
        """Qwen3 / DeepSeek models often emit <think>…</think> before the answer."""
        text = "<think>Let me analyse…</think>\n{\"food_name\": \"Dal\", \"calories\": 180}"
        result = extract_json(text)
        assert result is not None
        assert result["food_name"] == "Dal"

    def test_think_block_without_closing_tag_stripped(self):
        """Regex handles <think> that is not properly closed — falls back on '{'."""
        text = "<think>thinking...\n{\"food_name\": \"Idli\", \"calories\": 58}"
        result = extract_json(text)
        assert result is not None
        assert result["food_name"] == "Idli"

    def test_json_with_nested_object_ignored(self):
        """When JSON is nested the outer dict is returned, not the inner."""
        text = '{"food_name": "Thali", "calories": 800, "breakdown": {"rice": 300}}'
        result = extract_json(text)
        assert result is not None
        assert result["food_name"] == "Thali"
        assert result["calories"] == 800

    def test_extra_whitespace_is_handled(self):
        text = "   \n   {\"food_name\": \"Bread\", \"calories\": 79}   \n   "
        result = extract_json(text)
        assert result is not None
        assert result["food_name"] == "Bread"

    def test_float_values_are_preserved(self):
        text = '{"food_name": "Chicken", "calories": 335, "protein": 31.5, "carbs": 0.0, "fat": 21.8}'
        result = extract_json(text)
        assert result is not None
        assert result["protein"] == 31.5
        assert result["fat"] == 21.8

    # ── Edge cases ───────────────────────────────────────────────────────────

    def test_none_input_returns_none(self):
        assert extract_json(None) is None

    def test_empty_string_returns_none(self):
        assert extract_json("") is None

    def test_whitespace_only_returns_none(self):
        assert extract_json("   \n\t  ") is None

    def test_non_string_input_returns_none(self):
        # Defensive: passing a non-string (e.g. already-parsed dict) should not crash
        assert extract_json(42) is None   # type: ignore[arg-type]

    def test_no_json_braces_returns_none(self):
        assert extract_json("There is no JSON here at all.") is None

    def test_invalid_json_braces_returns_none(self):
        """Opening brace exists but content is not valid JSON."""
        assert extract_json("{this is not json}") is None

    def test_list_at_root_returns_none(self):
        """Root-level JSON array — we only accept objects."""
        result = extract_json('[{"food_name": "Apple"}]')
        # The function only returns dicts; the list should cause it to fall through
        # to the brace-extraction path which should also fail for a list
        assert result is None

    def test_truncated_json_returns_none(self):
        assert extract_json('{"food_name": "Roti", "calories": 10') is None

    def test_only_think_block_returns_none(self):
        text = "<think>I am thinking only.</think>"
        assert extract_json(text) is None


# ─────────────────────────────────────────────────────────────────────────────
# detect_mime
# ─────────────────────────────────────────────────────────────────────────────


class TestDetectMime:

    def test_jpeg_extension(self):
        assert detect_mime("photo.jpg") == "image/jpeg"

    def test_jpeg_uppercase_extension(self):
        assert detect_mime("PHOTO.JPG") == "image/jpeg"

    def test_png_extension(self):
        assert detect_mime("food.png") == "image/png"

    def test_webp_extension(self):
        assert detect_mime("dish.webp") == "image/webp"

    def test_gif_extension(self):
        assert detect_mime("animation.gif") == "image/gif"

    def test_unknown_extension_defaults_to_jpeg(self):
        assert detect_mime("file.bmp") == "image/jpeg"

    def test_no_extension_defaults_to_jpeg(self):
        assert detect_mime("noextension") == "image/jpeg"

    def test_path_with_directory(self):
        assert detect_mime("/uploads/food/image.png") == "image/png"

    def test_mixed_case_png(self):
        assert detect_mime("Image.PNG") == "image/png"

    def test_mixed_case_webp(self):
        assert detect_mime("Image.WEBP") == "image/webp"
