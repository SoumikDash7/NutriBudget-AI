import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_cfg_log = logging.getLogger("app.core.config")


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    APP_ENV: str

    HOST: str
    PORT: int

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    ALLOWED_ORIGINS: str
    HUGGINGFACE_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_GEMMA_MODEL: str = "google/gemma-3-27b-it:free"
    GROQ_API_KEY: str | None = None
    GROQ_LLAMA_VISION_MODEL: str = "llama-3.2-11b-vision-preview"
    GROQ_LLAMA_TEXT_MODEL: str = "llama-3.3-70b-versatile"
    # USDA FoodData Central — free key: https://fdc.nal.usda.gov/api-guide.html
    USDA_API_KEY: str | None = None
    # Qwen3 model — switch to Qwen3-30B-A3B for higher accuracy
    QWEN3_MODEL: str = "Qwen/Qwen3-8B"
    # Local Ollama settings (Qwen2.5-VL runs here when Ollama is installed)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_VISION_MODEL: str = "qwen2.5vl:7b"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    or_key_len = len(s.OPENROUTER_API_KEY) if s.OPENROUTER_API_KEY is not None else 0
    groq_key_len = len(s.GROQ_API_KEY) if s.GROQ_API_KEY is not None else 0
    _cfg_log.debug(f"OPENROUTER_API_KEY loaded: {or_key_len > 0}  (length={or_key_len})")
    _cfg_log.debug(f"GROQ_API_KEY loaded: {groq_key_len > 0}  (length={groq_key_len})")
    return s


settings = get_settings()