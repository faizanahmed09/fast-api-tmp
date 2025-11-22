"""
Speech-to-text service using Deepgram API.
Transcribes audio with automatic language detection (English/Spanish).
"""
import logging
import httpx
import httpcore
import asyncio
from typing import Dict
from app.core.config import settings
from app.core.audio_utils import convert_to_wav

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Service for transcribing audio using Deepgram API."""
    
    def __init__(self):
        self.api_key = settings.DEEPGRAM_API_KEY
        self.base_url = settings.DEEPGRAM_API_URL
        self._client = None
    
    async def _get_client(self):
        """Get or create reusable HTTP client with optimized settings."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),  # Increased to 120s for long audio chunks
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                http2=True  # Enable HTTP/2 for better performance
            )
        return self._client
    
    async def _reset_client(self):
        """Reset the HTTP client to handle stale connections."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.info("HTTP client reset due to connection error")
    
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
        max_retries = 3
        retry_delay = 1.0  # Initial delay in seconds
        
        for attempt in range(max_retries):
            try:
                return await self._transcribe_with_retry(audio_data, mimetype, attempt)
            except (httpcore.ConnectionNotAvailable, httpcore.RemoteProtocolError) as e:
                logger.warning(f"Connection error on attempt {attempt + 1}/{max_retries}: {type(e).__name__}")
                
                # Reset client on connection errors
                await self._reset_client()
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time:.1f} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed")
                    raise Exception(f"Connection to Deepgram failed after {max_retries} attempts. Please try again.")
            except Exception as e:
                # For non-connection errors, don't retry
                raise
    
    async def _transcribe_with_retry(self, audio_data: bytes, mimetype: str, attempt: int) -> Dict[str, str]:
        """
        Internal method to perform the actual transcription.
        
        Args:
            audio_data: Binary audio data
            mimetype: MIME type of the audio file
            attempt: Current attempt number (for logging)
        
        Returns:
            Dictionary with 'language' and 'text' keys
        """
        try:
            # Convert audio to WAV format for Deepgram compatibility
            # WebM/Opus and other formats may not be directly supported
            if mimetype not in ["audio/wav", "audio/wave"]:
                logger.info(f"[DEEPGRAM] Converting {mimetype} to WAV for compatibility")
                audio_data = convert_to_wav(audio_data, source_format=mimetype)
                mimetype = "audio/wav"
            
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": mimetype,
            }
            
            # Deepgram parameters for language detection and transcription
            params = {
                "detect_language": "true",
                "model": "nova-2",  # Fast and accurate model
                "smart_format": "true",
                "punctuate": "true",
                "diarize": "false",  # Disable diarization for speed
                "utterances": "false",  # Disable utterances for speed
            }
            
            client = await self._get_client()
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
            confidence = alternatives[0].get("confidence", 0.0)
            
            # Log the raw response for debugging
            logger.debug(f"[DEEPGRAM] Raw transcript: '{transcript}'")
            logger.debug(f"[DEEPGRAM] Confidence: {confidence}")
            logger.debug(f"[DEEPGRAM] Detected language: {detected_language}")
            
            # Check if transcript is empty
            if not transcript or transcript.strip() == "":
                logger.warning(f"[DEEPGRAM] Empty transcript returned. Audio may be silent or too short.")
                logger.warning(f"[DEEPGRAM] Audio size: {len(audio_data)} bytes")
                # Still return the result, let the main handler decide what to do
            
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
            if transcript:
                logger.info(f"[DEEPGRAM] Transcript: {transcript[:100]}...")
            else:
                logger.warning(f"[DEEPGRAM] Transcript is empty")
            
            return {
                "language": language_name,
                "language_code": language_code,  # Use detected language code
                "text": transcript,
            }
        
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(f"Deepgram API error: {e.response.status_code}")
            logger.error(f"Response: {error_detail}")
            
            # Check for authentication errors
            if e.response.status_code == 401:
                raise Exception("Invalid Deepgram API key. Please check your DEEPGRAM_API_KEY in .env file")
            elif e.response.status_code == 403:
                raise Exception("Deepgram API access forbidden. Check your API key permissions")
            else:
                raise Exception(f"Deepgram API error ({e.response.status_code}): {error_detail}")
        except (httpcore.ConnectionNotAvailable, httpcore.RemoteProtocolError) as e:
            # Re-raise connection errors to be handled by retry logic
            logger.error(f"Connection error: {type(e).__name__} - {str(e)}")
            raise
        except Exception as e:
            error_msg = str(e) if str(e) else "Unknown error occurred"
            logger.error(f"Transcription error: {error_msg}")
            logger.exception("Full traceback:")
            raise Exception(error_msg)
    
    async def cleanup(self):
        """Cleanup resources and close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("Speech-to-text service cleaned up")


# Global service instance
speech_to_text_service = SpeechToTextService()


