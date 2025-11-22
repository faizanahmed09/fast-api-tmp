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
    
    # API Keys
    DEEPGRAM_API_KEY: str = "mock-deepgram-key"
    DEEPL_API_KEY: str = "mock-deepl-key"
    ELEVENLABS_API_KEY: str = "mock-elevenlabs-key"
    
    # API Endpoints
    DEEPGRAM_API_URL: str = "https://api.deepgram.com/v1/listen"
    DEEPL_API_URL: str = "https://api-free.deepl.com/v2/translate"
    ELEVENLABS_API_URL: str = "https://api.elevenlabs.io/v1"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_TTL: int = 3600
    
    # Audio Processing
    MAX_AUDIO_SIZE_MB: int = 50  # Increased for long recordings (10+ minutes)
    MAX_CHUNK_SIZE_MB: int = 10  # Maximum size per chunk
    SUPPORTED_AUDIO_FORMATS: list = [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"]
    
    # ElevenLabs Configuration
    ELEVENLABS_VOICE_ID: str = "pNInz6obpgDQGcFmaJgB"  # Adam (Male)
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    
    # OpenSmile Configuration
    OPENSMILE_CONFIG: str = "eGeMAPSv02"  # Extended Geneva Minimalistic Acoustic Parameter Set
    
    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()

