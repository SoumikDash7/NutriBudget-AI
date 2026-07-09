"""
Unit tests for InMemoryTTLCache (app.core.caching)
and InMemoryRateLimiter (app.core.rate_limit).

These are pure in-memory utility classes — no DB, no HTTP, no settings needed.
"""

import time
import pytest
from app.core.caching import InMemoryTTLCache
from app.core.rate_limit import InMemoryRateLimiter


# ─────────────────────────────────────────────────────────────────────────────
# InMemoryTTLCache
# ─────────────────────────────────────────────────────────────────────────────


class TestInMemoryTTLCache:

    def _make_cache(self, ttl: int = 60) -> InMemoryTTLCache:
        return InMemoryTTLCache(default_ttl_seconds=ttl)

    def test_set_and_get_returns_value(self):
        cache = self._make_cache()
        cache.set("key1", {"food_name": "Apple", "calories": 95})
        result = cache.get("key1")
        assert result == {"food_name": "Apple", "calories": 95}

    def test_get_missing_key_returns_none(self):
        cache = self._make_cache()
        assert cache.get("nonexistent") is None

    def test_expired_key_returns_none(self):
        """TTL=0 means the entry expires instantly on next read."""
        cache = self._make_cache(ttl=0)
        cache.set("stale", "value")
        time.sleep(0.01)  # ensure clock advances past TTL=0
        assert cache.get("stale") is None

    def test_expired_key_is_removed_from_cache(self):
        """Expired key should be evicted on get(), not just returned as None."""
        cache = self._make_cache(ttl=0)
        cache.set("evict_me", "hello")
        time.sleep(0.01)
        cache.get("evict_me")  # triggers eviction
        assert "evict_me" not in cache.cache

    def test_unexpired_key_is_still_accessible(self):
        cache = self._make_cache(ttl=3600)
        cache.set("fresh", 42)
        assert cache.get("fresh") == 42

    def test_overwrite_existing_key(self):
        cache = self._make_cache()
        cache.set("k", "first")
        cache.set("k", "second")
        assert cache.get("k") == "second"

    def test_custom_ttl_per_key(self):
        cache = self._make_cache(ttl=3600)
        cache.set("short_lived", "value", ttl_seconds=0)
        time.sleep(0.01)
        assert cache.get("short_lived") is None

    def test_stores_any_python_object(self):
        from app.schemas.nutrition import NutritionEstimate, ExtractedIngredient
        estimate = NutritionEstimate(
            ingredients=[ExtractedIngredient(name="Roti", quantity=2.0, unit="piece")],
            calories=200.0,
            protein_g=6.0,
            carbs_g=42.0,
            fat_g=2.5,
            confidence=0.95,
            source_provider="Test",
        )
        cache = self._make_cache()
        cache.set("roti_estimate", estimate)
        result = cache.get("roti_estimate")
        assert result is estimate  # same object reference
        assert result.calories == 200.0

    def test_clear_empties_all_entries(self):
        cache = self._make_cache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert len(cache.cache) == 0

    def test_multiple_independent_keys(self):
        cache = self._make_cache()
        cache.set("apple", {"calories": 95})
        cache.set("banana", {"calories": 105})
        assert cache.get("apple")["calories"] == 95
        assert cache.get("banana")["calories"] == 105

    def test_none_value_can_be_stored(self):
        """Explicit None values should still be stored and returned."""
        cache = self._make_cache()
        cache.set("null_val", None)
        # None stored means get() returns None — identical behaviour to miss,
        # but the key should be present in the cache dict
        assert "null_val" in cache.cache


# ─────────────────────────────────────────────────────────────────────────────
# InMemoryRateLimiter
# ─────────────────────────────────────────────────────────────────────────────


class TestInMemoryRateLimiter:

    def _make_limiter(self, limit: int = 3, window: int = 60) -> InMemoryRateLimiter:
        return InMemoryRateLimiter(requests_limit=limit, window_seconds=window)

    def test_first_request_is_always_allowed(self):
        limiter = self._make_limiter()
        assert limiter.is_allowed("user-1") is True

    def test_requests_up_to_limit_are_allowed(self):
        limiter = self._make_limiter(limit=3)
        for _ in range(3):
            assert limiter.is_allowed("user-a") is True

    def test_request_exceeding_limit_is_rejected(self):
        limiter = self._make_limiter(limit=3)
        for _ in range(3):
            limiter.is_allowed("user-b")
        # 4th request should be blocked
        assert limiter.is_allowed("user-b") is False

    def test_different_users_are_isolated(self):
        limiter = self._make_limiter(limit=1)
        limiter.is_allowed("user-c")  # exhaust user-c's quota
        # user-d should still be allowed
        assert limiter.is_allowed("user-d") is True

    def test_window_expiry_resets_quota(self):
        """After the rolling window passes, the user can make requests again."""
        limiter = self._make_limiter(limit=2, window=1)  # 1-second window
        limiter.is_allowed("user-e")
        limiter.is_allowed("user-e")
        assert limiter.is_allowed("user-e") is False  # blocked
        time.sleep(1.05)  # wait for window to expire
        assert limiter.is_allowed("user-e") is True  # allowed again

    def test_old_timestamps_are_cleaned_up(self):
        """Expired timestamps should be pruned from history on each call."""
        limiter = self._make_limiter(limit=10, window=1)
        limiter.is_allowed("user-f")  # one request
        time.sleep(1.05)  # window expires
        limiter.is_allowed("user-f")  # new request — should clean up old one
        assert len(limiter.history["user-f"]) == 1  # only the new timestamp remains

    def test_limit_of_10_requests_per_minute(self):
        """Simulates the real production configuration."""
        limiter = InMemoryRateLimiter(requests_limit=10, window_seconds=60)
        user = "prod-user-1"
        for i in range(10):
            assert limiter.is_allowed(user) is True, f"Request {i+1} should be allowed"
        # 11th request should fail
        assert limiter.is_allowed(user) is False

    def test_exact_boundary_is_rejected(self):
        """The 'limit'-th request should still be allowed, limit+1 should not."""
        limiter = self._make_limiter(limit=5)
        for _ in range(5):
            limiter.is_allowed("boundary-user")
        assert limiter.is_allowed("boundary-user") is False
