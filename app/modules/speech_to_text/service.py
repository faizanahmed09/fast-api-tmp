"""
Speech-to-text service using Deepgram API.
Transcribes audio with automatic language detection (English/Spanish).
"""
import logging
import httpx
from typing import Dict
from app.core.config import settings

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Service for transcribing audio using Deepgram API."""
    
    def __init__(self):
        self.api_key = settings.DEEPGRAM_API_KEY
        self.base_url = "https://api.deepgram.com/v1/listen"
    
    async def transcribe_audio(self, audio_data: bytes, mimetype: str = "audio/wav") -> Dict[str, str]:
        """
        Transcribe audio to text with language detection.
        
        Args:
            audio_data: Binary audio data
            mimetype: MIME type of the audio file
        
        Returns:
            Dictionary with 'language' and 'text' keys
        
        Raises:
            Exception: If transcription fails
        """
        try:
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": mimetype,
            }
            
            # Deepgram parameters for language detection and transcription
            params = {
                "detect_language": "true",
                "model": "nova-2",
                "smart_format": "true",
                "punctuate": "true",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    params=params,
                    content=audio_data,
                )
                response.raise_for_status()
                data = response.json()
            
            # Extract transcription and detected language
            results = data.get("results", {})
            channels = results.get("channels", [])
            
            if not channels:
                raise Exception("No transcription results returned from Deepgram")
            
            alternatives = channels[0].get("alternatives", [])
            if not alternatives:
                raise Exception("No transcription alternatives found")
            
            transcript = alternatives[0].get("transcript", "")
            detected_language = channels[0].get("detected_language", "en")
            
            # Map language codes
            language_map = {
                "en": "English",
                "es": "Spanish",
            }
            
            # Extract base language code (2-letter code)
            language_code = detected_language.lower()[:2]
            language_name = language_map.get(language_code, "English")
            
            logger.info(f"[DEEPGRAM] Transcription successful")
            logger.info(f"[DEEPGRAM] Detected language: {language_name} ({language_code})")
            logger.debug(f"[DEEPGRAM] Transcript: {transcript[:100]}...")
            
            return {
                "language": language_name,
                "language_code": language_code,  # Use detected language code
                "text": transcript,
            }
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Deepgram API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Transcription failed: {e.response.text}")
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise


# Global service instance
speech_to_text_service = SpeechToTextService()


