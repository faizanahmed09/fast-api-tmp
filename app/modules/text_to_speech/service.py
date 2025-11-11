"""
Text-to-speech service using ElevenLabs API.
Synthesizes emotional speech preserving detected emotion attributes.
"""
import logging
import httpx
from typing import Dict, Optional
from app.core.config import settings
from app.core.utils import map_emotion_to_voice_settings

logger = logging.getLogger(__name__)


class TextToSpeechService:
    """Service for generating speech using ElevenLabs API."""
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = settings.ELEVENLABS_API_URL
        self.voice_id = settings.ELEVENLABS_VOICE_ID
        self.model_id = settings.ELEVENLABS_MODEL_ID
        self._client = None
    
    async def _get_client(self):
        """Get or create reusable HTTP client with optimized settings."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),  # Longer timeout for audio generation
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                http2=True
            )
        return self._client
    
    async def generate_audio(
        self,
        text: str,
        emotion: str = "neutral",
        emotion_attributes: Optional[Dict] = None,
        language_code: str = "en",
    ) -> bytes:
        """
        Generate audio from text with emotion preservation.
        
        Args:
            text: Text to synthesize
            emotion: Detected emotion (happy, sad, angry, neutral, surprised)
            emotion_attributes: Emotion attributes from detection
            language_code: Target language code
        
        Returns:
            Binary audio data (MP3)
        
        Raises:
            Exception: If generation fails
        """
        try:
            logger.info(f"[ELEVENLABS] Starting audio generation")
            logger.info(f"[ELEVENLABS] Text length: {len(text)} characters")
            logger.info(f"[ELEVENLABS] Target language: {language_code}")
            logger.info(f"[ELEVENLABS] Emotion to preserve: {emotion}")
            
            # Map emotion to voice settings
            voice_settings = map_emotion_to_voice_settings(
                emotion,
                emotion_attributes or {}
            )
            
            logger.info(f"[ELEVENLABS] Voice settings mapped:")
            logger.info(f"  - Stability: {voice_settings.get('stability', 0.5):.2f}")
            logger.info(f"  - Similarity Boost: {voice_settings.get('similarity_boost', 0.75):.2f}")
            logger.info(f"  - Style: {voice_settings.get('style', 0.0):.2f}")
            logger.info(f"  - Use Speaker Boost: {voice_settings.get('use_speaker_boost', True)}")
            
            url = f"{self.base_url}/text-to-speech/{self.voice_id}"
            
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            }
            
            payload = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": voice_settings,
                "optimize_streaming_latency": 3,  # Optimize for lower latency (0-4)
            }
            
            logger.info(f"[ELEVENLABS] Calling ElevenLabs API...")
            logger.info(f"[ELEVENLABS] Model: {self.model_id}, Voice: {self.voice_id}")
            
            client = await self._get_client()
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            audio_data = response.content
            
            logger.info(f"[ELEVENLABS] ✓ Audio generation successful")
            logger.info(f"[ELEVENLABS] Output size: {len(audio_data)} bytes")
            logger.info(f"[ELEVENLABS] Emotion preserved: {emotion}")
            
            return audio_data
        
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(f"ElevenLabs API error: {e.response.status_code}")
            logger.error(f"Response: {error_detail}")
            
            if e.response.status_code == 401:
                raise Exception("Invalid ElevenLabs API key. Please check your ELEVENLABS_API_KEY in .env file")
            elif e.response.status_code == 403:
                raise Exception("ElevenLabs API access forbidden. Check your API key and quota")
            else:
                raise Exception(f"ElevenLabs API error ({e.response.status_code}): {error_detail}")
        except Exception as e:
            error_msg = str(e) if str(e) else "Unknown audio generation error"
            logger.error(f"Audio generation error: {error_msg}")
            logger.exception("Full traceback:")
            raise Exception(error_msg)
    
    async def get_available_voices(self) -> list:
        """
        Get list of available voices from ElevenLabs.
        
        Returns:
            List of voice dictionaries
        """
        try:
            url = f"{self.base_url}/voices"
            
            headers = {
                "xi-api-key": self.api_key,
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
            
            voices = data.get("voices", [])
            logger.info(f"Retrieved {len(voices)} available voices")
            
            return voices
        
        except Exception as e:
            logger.error(f"Failed to get voices: {str(e)}")
            return []


# Global service instance
text_to_speech_service = TextToSpeechService()


