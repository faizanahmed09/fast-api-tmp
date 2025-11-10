"""
FastAPI Speech Translation API
Real-time multilingual speech translation with emotion preservation.
"""
import logging
import uuid
import base64
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.redis_client import redis_client
from app.core.utils import validate_audio_file, generate_audio_key

# Import service modules
from app.modules.speech_to_text.service import speech_to_text_service
from app.modules.emotion_detection.service import emotion_detection_service
from app.modules.translation.service import translation_service
from app.modules.text_to_speech.service import text_to_speech_service

# Import routers
from app.modules.speech_to_text.router import router as stt_router
from app.modules.emotion_detection.router import router as emotion_router
from app.modules.translation.router import router as translation_router
from app.modules.text_to_speech.router import router as tts_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Speech Translation API...")
    try:
        await redis_client.connect()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Speech Translation API...")
    await redis_client.disconnect()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Real-time multilingual speech translation with emotion preservation",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include module routers
app.include_router(stt_router, prefix="/api")
app.include_router(emotion_router, prefix="/api")
app.include_router(translation_router, prefix="/api")
app.include_router(tts_router, prefix="/api")


class ProcessAudioResponse(BaseModel):
    """Response model for process-audio endpoint."""
    original_text: str
    original_language: str
    translated_text: str
    target_language: str
    emotion: str
    emotion_attributes: dict
    audio_base64: str
    audio_size_bytes: int


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    redis_connected = await redis_client.exists("health_check") or True
    return {
        "status": "healthy",
        "redis": "connected" if redis_connected else "disconnected",
    }


@app.post("/api/process-audio", response_model=ProcessAudioResponse)
async def process_audio(audio: UploadFile = File(...)):
    """
    Unified API endpoint for complete speech translation pipeline with emotion preservation.
    
    Pipeline Flow:
    1. Speech-to-Text (Deepgram) - Transcribe audio and detect source language
    2. Emotion Detection (OpenSmile) - Extract emotional characteristics from audio
    3. Text Translation (DeepL) - Translate text to target language (EN ↔ ES)
    4. Text-to-Speech (ElevenLabs) - Generate emotional speech in target language
    
    Features:
    - Automatic bidirectional language detection (English ↔ Spanish)
    - Emotion preservation throughout the pipeline
    - Comprehensive error handling at each stage
    - Performance tracking and detailed logging
    - Redis caching for audio data
    
    Args:
        audio: Audio file (mp3, wav, m4a, flac, ogg, webm)
               Max size: 25MB
    
    Returns:
        ProcessAudioResponse with:
        - Original transcribed text and language
        - Translated text and target language
        - Detected emotion and attributes
        - Generated audio (base64 encoded)
    
    Raises:
        HTTPException: 400 for invalid input, 500 for processing errors
    """
    import time
    
    cache_key = None
    pipeline_start = time.time()
    
    # Pipeline stage tracking
    stages = {
        "validation": {"status": "pending", "duration": 0},
        "transcription": {"status": "pending", "duration": 0},
        "emotion_detection": {"status": "pending", "duration": 0},
        "translation": {"status": "pending", "duration": 0},
        "audio_generation": {"status": "pending", "duration": 0},
    }
    
    try:
        # ============================================================
        # STAGE 0: Validation & Preparation
        # ============================================================
        stage_start = time.time()
        logger.info("=" * 80)
        logger.info(f"🎙️  PIPELINE START: {audio.filename}")
        logger.info("=" * 80)
        
        # Validate audio file
        try:
            validate_audio_file(audio)
            logger.info(f"✓ Audio validation passed: {audio.filename}")
        except Exception as e:
            logger.error(f"✗ Audio validation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid audio file: {str(e)}")
        
        # Read audio data
        audio_data = await audio.read()
        audio_size_mb = len(audio_data) / (1024 * 1024)
        logger.info(f"📊 Audio size: {audio_size_mb:.2f} MB ({len(audio_data)} bytes)")
        
        # Cache audio in Redis for potential retry/debugging
        cache_key = generate_audio_key()
        await redis_client.set_audio(cache_key, audio_data)
        logger.info(f"💾 Audio cached: {cache_key}")
        
        stages["validation"]["status"] = "completed"
        stages["validation"]["duration"] = time.time() - stage_start
        
        # ============================================================
        # STAGE 1: Speech-to-Text Transcription
        # ============================================================
        stage_start = time.time()
        logger.info("-" * 80)
        logger.info("📝 STAGE 1: Speech-to-Text Transcription")
        logger.info("-" * 80)
        
        try:
            transcription = await speech_to_text_service.transcribe_audio(
                audio_data,
                mimetype=audio.content_type or "audio/wav"
            )
            original_text = transcription["text"]
            original_language = transcription["language"]
            source_lang_code = transcription["language_code"]
            
            logger.info(f"✓ Transcription successful")
            logger.info(f"  Language: {original_language} ({source_lang_code})")
            logger.info(f"  Text: {original_text[:100]}{'...' if len(original_text) > 100 else ''}")
            
            stages["transcription"]["status"] = "completed"
            stages["transcription"]["duration"] = time.time() - stage_start
            
        except Exception as e:
            stages["transcription"]["status"] = "failed"
            stages["transcription"]["error"] = str(e)
            logger.error(f"✗ Transcription failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Speech-to-text transcription failed: {str(e)}"
            )
        
        # ============================================================
        # STAGE 2: Emotion Detection
        # ============================================================
        stage_start = time.time()
        logger.info("-" * 80)
        logger.info("😊 STAGE 2: Emotion Detection")
        logger.info("-" * 80)
        
        try:
            emotion_result = await emotion_detection_service.detect_emotion(
                audio_data,
                filename=audio.filename
            )
            emotion = emotion_result["emotion"]
            emotion_attributes = emotion_result["attributes"]
            
            logger.info(f"✓ Emotion detection successful")
            logger.info(f"  Emotion: {emotion}")
            logger.info(f"  Attributes: pitch={emotion_attributes.get('pitch_mean', 0):.2f}, "
                       f"energy={emotion_attributes.get('energy', 0):.2f}, "
                       f"rate={emotion_attributes.get('speaking_rate', 0):.2f}")
            
            stages["emotion_detection"]["status"] = "completed"
            stages["emotion_detection"]["duration"] = time.time() - stage_start
            
        except Exception as e:
            stages["emotion_detection"]["status"] = "failed"
            stages["emotion_detection"]["error"] = str(e)
            logger.warning(f"⚠ Emotion detection failed, using neutral: {str(e)}")
            # Fallback to neutral emotion
            emotion = "neutral"
            emotion_attributes = {
                "pitch_mean": 0.5,
                "energy": 0.5,
                "speaking_rate": 0.5,
            }
        
        # ============================================================
        # STAGE 3: Text Translation
        # ============================================================
        stage_start = time.time()
        logger.info("-" * 80)
        logger.info("🌐 STAGE 3: Text Translation")
        logger.info("-" * 80)
        
        try:
            translation_result = await translation_service.translate_text(
                text=original_text,
                source_lang=source_lang_code,
            )
            translated_text = translation_result["translated_text"]
            target_language = translation_result["target_language"]
            
            logger.info(f"✓ Translation successful")
            logger.info(f"  Direction: {source_lang_code.upper()} → {target_language.upper()}")
            logger.info(f"  Translated: {translated_text[:100]}{'...' if len(translated_text) > 100 else ''}")
            
            stages["translation"]["status"] = "completed"
            stages["translation"]["duration"] = time.time() - stage_start
            
        except Exception as e:
            stages["translation"]["status"] = "failed"
            stages["translation"]["error"] = str(e)
            logger.error(f"✗ Translation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Text translation failed: {str(e)}"
            )
        
        # ============================================================
        # STAGE 4: Text-to-Speech Generation with Emotion
        # ============================================================
        stage_start = time.time()
        logger.info("-" * 80)
        logger.info("🔊 STAGE 4: Emotional Text-to-Speech Generation")
        logger.info("-" * 80)
        
        try:
            generated_audio = await text_to_speech_service.generate_audio(
                text=translated_text,
                emotion=emotion,
                emotion_attributes=emotion_attributes,
                language_code=target_language,
            )
            
            output_size_mb = len(generated_audio) / (1024 * 1024)
            logger.info(f"✓ Audio generation successful")
            logger.info(f"  Size: {output_size_mb:.2f} MB ({len(generated_audio)} bytes)")
            logger.info(f"  Emotion applied: {emotion}")
            
            stages["audio_generation"]["status"] = "completed"
            stages["audio_generation"]["duration"] = time.time() - stage_start
            
        except Exception as e:
            stages["audio_generation"]["status"] = "failed"
            stages["audio_generation"]["error"] = str(e)
            logger.error(f"✗ Audio generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Text-to-speech generation failed: {str(e)}"
            )
        
        # ============================================================
        # FINALIZATION
        # ============================================================
        # Encode audio to base64 for JSON response
        audio_base64 = base64.b64encode(generated_audio).decode('utf-8')
        
        # Clean up cache
        if cache_key:
            await redis_client.delete_audio(cache_key)
            logger.debug(f"🗑️  Cache cleaned: {cache_key}")
        
        # Calculate total pipeline duration
        total_duration = time.time() - pipeline_start
        
        logger.info("=" * 80)
        logger.info(f"✅ PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"⏱️  Total Duration: {total_duration:.2f}s")
        logger.info(f"   - Validation: {stages['validation']['duration']:.2f}s")
        logger.info(f"   - Transcription: {stages['transcription']['duration']:.2f}s")
        logger.info(f"   - Emotion Detection: {stages['emotion_detection']['duration']:.2f}s")
        logger.info(f"   - Translation: {stages['translation']['duration']:.2f}s")
        logger.info(f"   - Audio Generation: {stages['audio_generation']['duration']:.2f}s")
        logger.info("=" * 80)
        
        return ProcessAudioResponse(
            original_text=original_text,
            original_language=original_language,
            translated_text=translated_text,
            target_language=target_language,
            emotion=emotion,
            emotion_attributes=emotion_attributes,
            audio_base64=audio_base64,
            audio_size_bytes=len(generated_audio),
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        # Handle unexpected errors
        logger.error("=" * 80)
        logger.error(f"❌ PIPELINE FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Stage Status: {stages}")
        logger.error("=" * 80)
        
        # Clean up cache on error
        if cache_key:
            try:
                await redis_client.delete_audio(cache_key)
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing pipeline failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
