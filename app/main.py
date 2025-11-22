"""
FastAPI Speech Translation API
Real-time multilingual speech translation with emotion preservation.
"""
import logging
import uuid
import base64
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict

from app.core.config import settings
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

# In-memory storage for pre-processed data (replaces Redis)
# Format: {session_id: {chunk_index: chunk_data}}
preprocessed_data_store: Dict[str, Dict[int, dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Speech Translation API...")
    try:
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Speech Translation API...")
    await speech_to_text_service.cleanup()
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
    audio_base64: str
    audio_size_bytes: int


class ChunkProcessResponse(BaseModel):
    """Response model for chunked audio processing."""
    chunk_index: int
    transcription: str
    source_language: str
    translated_text: str
    target_language: str
    audio_chunk_base64: str
    audio_chunk_size_bytes: int
    is_final: bool
    processing_time_seconds: float


class PreProcessChunkResponse(BaseModel):
    """Response model for pre-processing (without audio generation)."""
    chunk_index: int
    transcription: str
    source_language: str
    translated_text: str
    target_language: str
    emotion: str
    emotion_attributes: dict
    is_final: bool
    processing_time_seconds: float
    session_id: str  # For storing and retrieving data later


class GenerateAudioRequest(BaseModel):
    """Request model for audio generation from pre-processed data."""
    session_id: str
    chunk_index: int


class GenerateAudioResponse(BaseModel):
    """Response model for audio generation."""
    chunk_index: int
    audio_chunk_base64: str
    audio_chunk_size_bytes: int
    processing_time_seconds: float


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
    return {
        "status": "healthy",
        "storage": "in-memory",
        "sessions": len(preprocessed_data_store),
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
        
        stages["validation"]["status"] = "completed"
        stages["validation"]["duration"] = time.time() - stage_start
        
        # ============================================================
        # STAGE 1 & 2: Parallel Speech-to-Text + Emotion Detection
        # ============================================================
        import asyncio
        
        parallel_start = time.time()
        logger.info("-" * 80)
        logger.info("⚡ STAGE 1: Speech-to-Text")
        logger.info("-" * 80)
        
        # Run Speech-to-Text transcription
        try:
            transcription = await speech_to_text_service.transcribe_audio(
                audio_data,
                mimetype=audio.content_type or "audio/wav"
            )
            
            parallel_duration = time.time() - parallel_start
            logger.info(f"⚡ Transcription completed in {parallel_duration:.2f}s")
            
            original_text = transcription["text"]
            original_language = transcription["language"]
            source_lang_code = transcription["language_code"]
            
            logger.info(f"✓ Transcription successful")
            logger.info(f"  Language: {original_language} ({source_lang_code})")
            logger.info(f"  Text: {original_text[:100]}{'...' if len(original_text) > 100 else ''}")
            
            stages["transcription"]["status"] = "completed"
            stages["transcription"]["duration"] = parallel_duration
            
            # Use neutral emotion for TTS (emotion detection disabled)
            emotion = "neutral"
            emotion_attributes = {
                "pitch_mean": 0.5,
                "energy": 0.5,
                "speaking_rate": 0.5,
            }
            stages["emotion_detection"]["status"] = "skipped"
            
        except Exception as e:
            logger.error(f"✗ Parallel processing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Parallel processing failed: {str(e)}"
            )
        
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
        
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing pipeline failed: {str(e)}"
        )


@app.post("/api/process-audio-chunk", response_model=ChunkProcessResponse)
async def process_audio_chunk(
    audio: UploadFile = File(...),
    chunk_index: int = Form(...),
    is_final: bool = Form(False),
):
    """
    Process audio chunks incrementally for long recordings.
    
    This endpoint processes audio chunks (typically 2-minute segments) as they arrive,
    providing progressive results without waiting for the full recording to complete.
    Ideal for recordings longer than 10 minutes.
    
    Pipeline Flow (per chunk):
    1. Speech-to-Text (Deepgram) - Transcribe chunk and detect language
    2. Emotion Detection (OpenSmile) - Extract emotional characteristics
    3. Text Translation (DeepL) - Translate transcribed text
    4. Text-to-Speech (ElevenLabs) - Generate emotional speech in target language
    
    Args:
        audio: Audio chunk file (mp3, wav, m4a, flac, ogg, webm)
               Recommended: 2-minute segments, max 10MB per chunk
        chunk_index: Zero-based index of this chunk (0, 1, 2, ...)
        is_final: Whether this is the last chunk of the recording
    
    Returns:
        ChunkProcessResponse with:
        - Transcription and translation for this chunk
        - Detected emotion and attributes
        - Generated audio (base64 encoded)
        - Processing time and metadata
    
    Raises:
        HTTPException: 400 for invalid input, 500 for processing errors
    """
    import time
    import asyncio
    
    chunk_start = time.time()
    
    try:
        # ============================================================
        # VALIDATION
        # ============================================================
        logger.info("=" * 80)
        logger.info(f"🎙️  CHUNK {chunk_index} PROCESSING START (final: {is_final})")
        logger.info("=" * 80)
        
        # Validate audio chunk
        try:
            validate_audio_file(audio)
            logger.info(f"✓ Chunk validation passed: {audio.filename}")
        except Exception as e:
            logger.error(f"✗ Chunk validation failed: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid audio chunk: {str(e)}")
        
        # Read audio data
        audio_data = await audio.read()
        audio_size_mb = len(audio_data) / (1024 * 1024)
        
        # Check chunk size limit
        if audio_size_mb > settings.MAX_CHUNK_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"Chunk size ({audio_size_mb:.2f}MB) exceeds limit ({settings.MAX_CHUNK_SIZE_MB}MB)"
            )
        
        logger.info(f"📊 Chunk size: {audio_size_mb:.2f} MB ({len(audio_data)} bytes)")
        
        # ============================================================
        # PARALLEL PROCESSING: STT + Emotion Detection
        # ============================================================
        logger.info("-" * 80)
        logger.info("⚡ Speech-to-Text Processing")
        logger.info("-" * 80)
        
        parallel_start = time.time()
        
        try:
            transcription = await speech_to_text_service.transcribe_audio(
                audio_data,
                mimetype=audio.content_type or "audio/webm"
            )
            
            parallel_duration = time.time() - parallel_start
            logger.info(f"⚡ Transcription completed in {parallel_duration:.2f}s")
            
            original_text = transcription["text"]
            original_language = transcription["language"]
            source_lang_code = transcription["language_code"]
            
            logger.info(f"✓ Transcription successful")
            logger.info(f"  Language: {original_language} ({source_lang_code})")
            logger.info(f"  Text: {original_text[:100]}{'...' if len(original_text) > 100 else ''}")
            
            # Validate language support (only English and Spanish)
            supported_languages = ["en", "es"]
            if source_lang_code.lower()[:2] not in supported_languages:
                raise HTTPException(
                    status_code=400,
                    detail=f"Language '{original_language}' ({source_lang_code}) is not supported. Only English and Spanish are supported."
                )
            
            # Use neutral emotion for TTS (emotion detection disabled)
            emotion = "neutral"
            emotion_attributes = {
                "pitch_mean": 0.5,
                "energy": 0.5,
                "speaking_rate": 0.5,
            }
        
        except Exception as e:
            logger.error(f"✗ Parallel processing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Chunk {chunk_index} parallel processing failed: {str(e)}"
            )
        
        # ============================================================
        # TRANSLATION
        # ============================================================
        logger.info("-" * 80)
        logger.info("🌐 Text Translation")
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
        
        except Exception as e:
            logger.error(f"✗ Translation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed for chunk {chunk_index}: {str(e)}"
            )
        
        # ============================================================
        # TEXT-TO-SPEECH GENERATION
        # ============================================================
        logger.info("-" * 80)
        logger.info("🔊 Emotional Text-to-Speech Generation")
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
        
        except Exception as e:
            logger.error(f"✗ Audio generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Audio generation failed for chunk {chunk_index}: {str(e)}"
            )
        
        # ============================================================
        # FINALIZATION
        # ============================================================
        # Encode audio to base64 for JSON response
        audio_base64 = base64.b64encode(generated_audio).decode('utf-8')
        
        # Calculate total processing time
        total_duration = time.time() - chunk_start
        
        logger.info("=" * 80)
        logger.info(f"✅ CHUNK {chunk_index} COMPLETED SUCCESSFULLY")
        logger.info(f"⏱️  Processing Time: {total_duration:.2f}s")
        logger.info(f"   Final chunk: {is_final}")
        logger.info("=" * 80)
        
        return ChunkProcessResponse(
            chunk_index=chunk_index,
            transcription=original_text,
            source_language=original_language,
            translated_text=translated_text,
            target_language=target_language,
            audio_chunk_base64=audio_base64,
            audio_chunk_size_bytes=len(generated_audio),
            is_final=is_final,
            processing_time_seconds=round(total_duration, 2),
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        # Handle unexpected errors
        logger.error("=" * 80)
        logger.error(f"❌ CHUNK {chunk_index} PROCESSING FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 80)
        
        raise HTTPException(
            status_code=500,
            detail=f"Chunk {chunk_index} processing failed: {str(e)}"
        )


@app.post("/api/pre-process-chunk", response_model=PreProcessChunkResponse)
async def pre_process_chunk(
    audio: UploadFile = File(...),
    chunk_index: int = Form(...),
    is_final: bool = Form(False),
    session_id: Optional[str] = Form(None),
):
    """
    Pre-process audio chunk: Transcribe, detect emotion, and translate.
    Does NOT generate audio - that happens later on submit.
    
    This endpoint is called when user clicks "Stop Recording".
    It performs the time-consuming transcription, emotion detection, and translation,
    then stores the results in memory for later audio generation.
    
    Args:
        audio: Audio chunk file
        chunk_index: Zero-based index of this chunk
        is_final: Whether this is the last chunk
        session_id: Session ID for grouping chunks (auto-generated if not provided)
    
    Returns:
        PreProcessChunkResponse with transcription, translation, and emotion data
    """
    import time
    import asyncio
    import json
    
    chunk_start = time.time()
    cache_key = None
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    try:
        logger.info("=" * 80)
        logger.info(f"🎙️  PRE-PROCESS CHUNK {chunk_index} START (session: {session_id})")
        logger.info("=" * 80)
        
        # Validate audio chunk
        validate_audio_file(audio)
        logger.info(f"✓ Chunk validation passed: {audio.filename}")
        
        # Read audio data
        audio_data = await audio.read()
        audio_size_mb = len(audio_data) / (1024 * 1024)
        logger.info(f"📊 Chunk size: {audio_size_mb:.2f} MB")
        
        # ============================================================
        # PARALLEL PROCESSING: STT + Emotion Detection
        # ============================================================
        logger.info("-" * 80)
        logger.info("⚡ Parallel: Speech-to-Text + Emotion Detection")
        logger.info("-" * 80)
        
        parallel_start = time.time()
        
        # Run STT and emotion detection in parallel
        stt_task = speech_to_text_service.transcribe_audio(
            audio_data,
            mimetype=audio.content_type or "audio/webm"
        )
        emotion_task = emotion_detection_service.detect_emotion(
            audio_data,
            filename=audio.filename
        )
        
        results = await asyncio.gather(stt_task, emotion_task, return_exceptions=True)
        transcription = results[0]
        emotion_result = results[1]
        
        parallel_duration = time.time() - parallel_start
        logger.info(f"⚡ Parallel processing completed in {parallel_duration:.2f}s")
        
        # Handle transcription result
        if isinstance(transcription, Exception):
            raise transcription
        
        original_text = transcription["text"]
        original_language = transcription["language"]
        source_lang_code = transcription["language_code"]
        
        # Check if transcription is empty
        if not original_text or original_text.strip() == "":
            logger.warning("⚠️  Transcription returned empty text")
            raise HTTPException(
                status_code=400,
                detail="No speech detected in the audio. Please ensure you're speaking clearly into the microphone."
            )
        
        logger.info(f"✓ Transcription: {original_text[:100]}...")
        
        # Validate language support (only English and Spanish)
        supported_languages = ["en", "es"]
        if source_lang_code.lower()[:2] not in supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Language '{original_language}' ({source_lang_code}) is not supported. Only English and Spanish are supported."
            )
        
        # Handle emotion result
        emotion = "neutral"
        emotion_attributes = {
            "pitch_mean": 0.5,
            "energy": 0.5,
            "speaking_rate": 0.5,
        }
        
        if not isinstance(emotion_result, Exception):
            emotion = emotion_result["emotion"]
            emotion_attributes = emotion_result["attributes"]
            logger.info(f"✓ Emotion detected: {emotion}")
        else:
            logger.warning(f"⚠️  Emotion detection failed, using neutral: {emotion_result}")
        
        # ============================================================
        # TRANSLATION
        # ============================================================
        logger.info("-" * 80)
        logger.info("🌐 Text Translation")
        logger.info("-" * 80)
        
        translation_result = await translation_service.translate_text(
            text=original_text,
            source_lang=source_lang_code,
        )
        translated_text = translation_result["translated_text"]
        target_language = translation_result["target_language"]
        
        logger.info(f"✓ Translation: {source_lang_code.upper()} → {target_language.upper()}")
        logger.info(f"  Translated: {translated_text[:100]}...")
        
        # ============================================================
        # STORE DATA IN MEMORY FOR LATER AUDIO GENERATION
        # ============================================================
        chunk_data = {
            "chunk_index": chunk_index,
            "transcription": original_text,
            "source_language": original_language,
            "translated_text": translated_text,
            "target_language": target_language,
            "emotion": emotion,
            "emotion_attributes": emotion_attributes,
            "is_final": is_final,
        }
        
        # Store in memory with session-based key
        if session_id not in preprocessed_data_store:
            preprocessed_data_store[session_id] = {}
        
        preprocessed_data_store[session_id][chunk_index] = chunk_data
        logger.info(f"💾 Data stored in memory: session={session_id}, chunk={chunk_index}")
        logger.info(f"   Original: {original_text[:100]}...")
        logger.info(f"   Translated: {translated_text[:100]}...")
        logger.debug(f"   Total sessions: {len(preprocessed_data_store)}")
        logger.debug(f"   Chunks in this session: {len(preprocessed_data_store[session_id])}")
        
        # Calculate total processing time
        total_duration = time.time() - chunk_start
        
        logger.info("=" * 80)
        logger.info(f"✅ PRE-PROCESS CHUNK {chunk_index} COMPLETED")
        logger.info(f"⏱️  Processing Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        
        return PreProcessChunkResponse(
            chunk_index=chunk_index,
            transcription=original_text,
            source_language=original_language,
            translated_text=translated_text,
            target_language=target_language,
            emotion=emotion,
            emotion_attributes=emotion_attributes,
            is_final=is_final,
            processing_time_seconds=round(total_duration, 2),
            session_id=session_id,
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ PRE-PROCESS CHUNK {chunk_index} FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 80)
        
        raise HTTPException(
            status_code=500,
            detail=f"Pre-processing chunk {chunk_index} failed: {str(e)}"
        )


@app.post("/api/generate-audio", response_model=GenerateAudioResponse)
async def generate_audio(
    session_id: str = Form(...),
    chunk_index: int = Form(...),
):
    """
    Generate audio from pre-processed data.
    
    This endpoint is called when user clicks "Submit".
    It retrieves the pre-processed data from memory and generates the audio.
    
    Args:
        session_id: Session ID from pre-processing
        chunk_index: Chunk index to generate audio for
    
    Returns:
        GenerateAudioResponse with generated audio
    """
    import time
    import json
    
    gen_start = time.time()
    
    try:
        logger.info("=" * 80)
        logger.info(f"🔊 GENERATE AUDIO: session={session_id}, chunk={chunk_index}")
        logger.info("=" * 80)
        
        # Retrieve pre-processed data from memory
        logger.info(f"🔍 Looking for data: session={session_id}, chunk={chunk_index}")
        
        if session_id not in preprocessed_data_store:
            logger.error(f"❌ Session not found: {session_id}")
            logger.info(f"   Available sessions: {list(preprocessed_data_store.keys())}")
            
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found. The data may have been cleared or never stored."
            )
        
        if chunk_index not in preprocessed_data_store[session_id]:
            logger.error(f"❌ Chunk {chunk_index} not found in session {session_id}")
            logger.info(f"   Available chunks: {list(preprocessed_data_store[session_id].keys())}")
            
            raise HTTPException(
                status_code=404,
                detail=f"Chunk {chunk_index} not found in session {session_id}."
            )
        
        chunk_data = preprocessed_data_store[session_id][chunk_index]
        logger.info(f"✓ Retrieved pre-processed data from memory")
        logger.info(f"   Session ID: {session_id}")
        logger.info(f"   Chunk Index: {chunk_index}")
        
        # Extract data
        translated_text = chunk_data["translated_text"]
        target_language = chunk_data["target_language"]
        emotion = chunk_data["emotion"]
        emotion_attributes = chunk_data["emotion_attributes"]
        original_text = chunk_data.get("transcription", "")
        
        logger.info(f"  Original Text: {original_text[:100]}...")
        logger.info(f"  Translated Text: {translated_text[:100]}...")
        logger.info(f"  Source → Target: {chunk_data.get('source_language', 'unknown')} → {target_language}")
        logger.info(f"  Emotion: {emotion}")
        
        # ============================================================
        # TEXT-TO-SPEECH GENERATION
        # ============================================================
        logger.info("-" * 80)
        logger.info("🔊 Generating Audio")
        logger.info("-" * 80)
        
        generated_audio = await text_to_speech_service.generate_audio(
            text=translated_text,
            emotion=emotion,
            emotion_attributes=emotion_attributes,
            language_code=target_language,
        )
        
        output_size_mb = len(generated_audio) / (1024 * 1024)
        logger.info(f"✓ Audio generated: {output_size_mb:.2f} MB")
        
        # Encode audio to base64
        audio_base64 = base64.b64encode(generated_audio).decode('utf-8')
        
        # Calculate processing time
        total_duration = time.time() - gen_start
        
        logger.info("=" * 80)
        logger.info(f"✅ AUDIO GENERATION COMPLETED")
        logger.info(f"⏱️  Processing Time: {total_duration:.2f}s")
        logger.info("=" * 80)
        
        return GenerateAudioResponse(
            chunk_index=chunk_index,
            audio_chunk_base64=audio_base64,
            audio_chunk_size_bytes=len(generated_audio),
            processing_time_seconds=round(total_duration, 2),
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ AUDIO GENERATION FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 80)
        
        raise HTTPException(
            status_code=500,
            detail=f"Audio generation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
