"""
Core configuration for the FastAPI Speech Translation application.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from .env
    )
    
    # Application
    APP_NAME: str = "Speech Translation API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API Keys (optional for development/testing)
    DEEPGRAM_API_KEY: str = "mock-deepgram-key"
    DEEPL_API_KEY: str = "mock-deepl-key"
    ELEVENLABS_API_KEY: str = "mock-elevenlabs-key"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_TTL: int = 3600  # 1 hour in seconds
    
    # Audio Processing
    MAX_AUDIO_SIZE_MB: int = 25
    SUPPORTED_AUDIO_FORMATS: list = [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"]
    
    # ElevenLabs Configuration
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Default voice (Rachel)
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    
    # OpenSmile Configuration
    OPENSMILE_CONFIG: str = "eGeMAPSv02"  # Extended Geneva Minimalistic Acoustic Parameter Set
    
    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()

