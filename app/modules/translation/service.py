"""
Translation service using DeepL API.
Translates text between English and Spanish.
"""
import logging
import httpx
from typing import Dict
from app.core.config import settings

logger = logging.getLogger(__name__)


class TranslationService:
    """Service for translating text using DeepL API."""
    
    def __init__(self):
        self.api_key = settings.DEEPL_API_KEY
        self.base_url = settings.DEEPL_API_URL
        self._client = None
    
    async def _get_client(self):
        """Get or create reusable HTTP client with optimized settings."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                http2=True
            )
        return self._client
    
    async def translate_text(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str = None
    ) -> Dict[str, str]:
        """
        Translate text from source language to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code (en, es)
            target_lang: Target language code (if None, auto-detect opposite)
        
        Returns:
            Dictionary with 'translated_text' and 'target_language' keys
        
        Raises:
            Exception: If translation fails
        """
        try:
            # Auto-determine target language
            if target_lang is None:
                target_lang = self._get_target_language(source_lang)
            
            # Normalize language codes for DeepL
            # Source: simple codes (EN, ES), Target: can have variants (EN-US, EN-GB)
            source_lang_code = self._normalize_source_language(source_lang)
            target_lang_code = self._normalize_target_language(target_lang)
            
            logger.info(f"[DEEPL] Translating: {source_lang_code} -> {target_lang_code}")
            logger.debug(f"[DEEPL] Text to translate: {text[:100]}...")
            
            headers = {
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            data = {
                "text": text,
                "source_lang": source_lang_code,
                "target_lang": target_lang_code,
                "formality": "default",  # Faster than "more" or "less"
            }
            
            client = await self._get_client()
            response = await client.post(
                self.base_url,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract translation
            translations = result.get("translations", [])
            if not translations:
                raise Exception("No translation returned from DeepL")
            
            translated_text = translations[0].get("text", "")
            detected_source = translations[0].get("detected_source_language", source_lang_code)
            
            logger.info(f"[DEEPL] ✓ Translation successful: {source_lang_code} -> {target_lang_code}")
            logger.info(f"[DEEPL] Translated text: {translated_text[:100]}...")
            
            # Extract base language code (remove variants like -US, -GB)
            target_base_code = target_lang_code.split('-')[0].lower()
            
            logger.info(f"[DEEPL] Returning target language: {target_base_code}")
            
            return {
                "translated_text": translated_text,
                "source_language": detected_source.lower(),
                "target_language": target_base_code,  # Return base code (en, es, etc.)
            }
        
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
            logger.error(f"DeepL API error: {e.response.status_code}")
            logger.error(f"Response: {error_detail}")
            
            if e.response.status_code == 401 or e.response.status_code == 403:
                raise Exception("Invalid DeepL API key. Please check your DEEPL_API_KEY in .env file")
            else:
                raise Exception(f"DeepL API error ({e.response.status_code}): {error_detail}")
        except Exception as e:
            error_msg = str(e) if str(e) else "Unknown translation error"
            logger.error(f"Translation error: {error_msg}")
            logger.exception("Full traceback:")
            raise Exception(error_msg)
    
    def _get_target_language(self, source_lang: str) -> str:
        """
        Get target language based on source language.
        
        Logic:
        - If audio is in Spanish → translate to English
        - If audio is in English → translate to Spanish
        
        Args:
            source_lang: Source language code
        
        Returns:
            Target language code
        """
        source = source_lang.lower()[:2]
        
        # If Spanish detected, translate to English
        if source == "es":
            logger.info("[TRANSLATION] Spanish detected → translating to English")
            return "en"
        
        # If English detected, translate to Spanish
        elif source == "en":
            logger.info("[TRANSLATION] English detected → translating to Spanish")
            return "es"
        
        # Default to English for other languages
        else:
            logger.warning(f"[TRANSLATION] Unknown language '{source}' → defaulting to English")
            return "en"
    
    def _normalize_source_language(self, lang_code: str) -> str:
        """
        Normalize source language code for DeepL API.
        Source languages use simple 2-letter codes (EN, ES, DE, etc.)
        
        Args:
            lang_code: Language code
        
        Returns:
            Normalized source language code (uppercase, no variants)
        """
        # DeepL source languages: simple 2-letter codes only
        code = lang_code.upper()[:2]
        return code
    
    def _normalize_target_language(self, lang_code: str) -> str:
        """
        Normalize target language code for DeepL API.
        Target languages can use variants (EN-US, EN-GB, PT-BR, etc.)
        
        Args:
            lang_code: Language code
        
        Returns:
            Normalized target language code (uppercase, with variants)
        """
        # DeepL target languages: can have variants
        code = lang_code.upper()[:2]
        
        # Map to DeepL supported target codes with variants
        if code == "EN":
            return "EN-US"  # Default to US English (can also use EN-GB)
        elif code == "PT":
            return "PT-BR"  # Default to Brazilian Portuguese (can also use PT-PT)
        
        return code


# Global service instance
translation_service = TranslationService()


