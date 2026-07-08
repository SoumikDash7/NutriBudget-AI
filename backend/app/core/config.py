from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    GEMINI_API_KEY: str | None = None
    # Gemini models — AQ. key format (new auth keys from Google AI Studio)
    GEMINI_VISION_MODEL: str = "gemini-2.5-flash"   # fast multimodal vision
    GEMINI_TEXT_MODEL:   str = "gemini-2.5-flash"   # fast text reasoning
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
    key_exists = s.GEMINI_API_KEY is not None and len(s.GEMINI_API_KEY) > 0
    print(f"[Config] GEMINI_API_KEY loaded: {key_exists} (Length: {len(s.GEMINI_API_KEY) if key_exists else 0})")
    return s


settings = get_settings()