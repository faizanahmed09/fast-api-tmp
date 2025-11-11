# Speech Translation API - Unified Pipeline Documentation

## Overview

The Speech Translation API provides a unified endpoint for complete speech translation with emotion preservation. The system orchestrates multiple AI services to deliver seamless real-time multilingual speech translation between English and Spanish.

## Unified Pipeline Endpoint

### `POST /api/process-audio`

Complete speech translation pipeline with emotion preservation.

#### Request

**Content-Type:** `multipart/form-data`

**Parameters:**
- `audio` (file, required): Audio file to process
  - Supported formats: mp3, wav, m4a, flac, ogg, webm
  - Max size: 25MB
  - Supported languages: English, Spanish (auto-detected)

**Example cURL:**
```bash
curl -X POST "http://localhost:8000/api/process-audio" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@speech.mp3"
```

#### Response

**Status Code:** `200 OK`

**Response Body:**
```json
{
  "original_text": "Hello, how are you today?",
  "original_language": "English",
  "translated_text": "Hola, ¿cómo estás hoy?",
  "target_language": "es",
  "emotion": "happy",
  "emotion_attributes": {
    "pitch_mean": 0.65,
    "energy": 0.72,
    "speaking_rate": 0.58
  },
  "audio_base64": "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA...",
  "audio_size_bytes": 45678
}
```

**Response Fields:**
- `original_text` (string): Transcribed text from input audio
- `original_language` (string): Detected source language (English/Spanish)
- `translated_text` (string): Translated text in target language
- `target_language` (string): Target language code (en/es)
- `emotion` (string): Detected emotion (happy, sad, angry, neutral, surprised)
- `emotion_attributes` (object): Acoustic features
  - `pitch_mean` (float): Normalized pitch (0-1)
  - `energy` (float): Normalized energy/loudness (0-1)
  - `speaking_rate` (float): Normalized speaking rate (0-1)
- `audio_base64` (string): Generated audio file (base64 encoded MP3)
- `audio_size_bytes` (integer): Size of generated audio in bytes

#### Error Responses

**400 Bad Request** - Invalid input
```json
{
  "detail": "Invalid audio file: Unsupported format .txt"
}
```

**500 Internal Server Error** - Processing failure
```json
{
  "detail": "Audio processing pipeline failed: Translation service unavailable"
}
```

## Pipeline Architecture

### Stage 1: Speech-to-Text Transcription
- **Service:** Deepgram API
- **Function:** Transcribe audio and detect source language
- **Output:** Text content + language code (en/es)
- **Error Handling:** Returns 500 if transcription fails

### Stage 2: Emotion Detection
- **Service:** OpenSmile (eGeMAPSv02 feature set)
- **Function:** Extract emotional characteristics from audio
- **Features Extracted:** 88 acoustic features
- **Output:** Emotion label + acoustic attributes
- **Error Handling:** Falls back to "neutral" emotion if detection fails

### Stage 3: Text Translation
- **Service:** DeepL API
- **Function:** Translate text between English and Spanish
- **Direction:** Bidirectional (EN ↔ ES)
- **Output:** Translated text + target language
- **Error Handling:** Returns 500 if translation fails

### Stage 4: Text-to-Speech Generation
- **Service:** ElevenLabs API
- **Function:** Generate emotional speech in target language
- **Emotion Preservation:** Maps detected emotions to voice settings
- **Output:** MP3 audio file
- **Error Handling:** Returns 500 if generation fails

## Emotion Preservation

The system preserves emotional characteristics throughout the pipeline:

### Emotion Detection
Analyzes acoustic features:
- **Pitch Mean:** Voice frequency characteristics
- **Energy:** Loudness and intensity
- **Speaking Rate:** Speech tempo

### Emotion Classification
Maps acoustic features to emotions:
- **Happy:** Moderate-high pitch + energy + fast rate
- **Sad:** Low pitch + low energy
- **Angry:** High energy + high pitch
- **Surprised:** Very high pitch + moderate energy
- **Neutral:** Moderate values across all features

### Voice Settings Mapping
Emotions are mapped to ElevenLabs voice parameters:
- **Stability:** Voice consistency (0-1)
- **Similarity Boost:** Voice character preservation (0-1)
- **Style:** Emotional expressiveness (0-1)
- **Speaker Boost:** Voice clarity enhancement (boolean)

Example mappings:
```python
{
  "happy": {
    "stability": 0.4,
    "similarity_boost": 0.8,
    "style": 0.6,
    "use_speaker_boost": True
  },
  "sad": {
    "stability": 0.7,
    "similarity_boost": 0.6,
    "style": 0.3,
    "use_speaker_boost": False
  }
}
```

## Performance Characteristics

### Typical Processing Times
- **Validation:** < 0.1s
- **Transcription:** 1-3s (depends on audio length)
- **Emotion Detection:** 0.1-0.5s
- **Translation:** 0.5-2s
- **Audio Generation:** 2-5s (depends on text length)
- **Total Pipeline:** 4-10s average

### Optimization Features
- **Redis Caching:** Temporary audio storage for retry/debugging
- **Async Processing:** Non-blocking I/O operations
- **Parallel Service Calls:** Where possible
- **Automatic Cleanup:** Cache cleanup on success/failure

## Logging and Monitoring

### Log Levels
- **INFO:** Pipeline progress and stage completion
- **WARNING:** Non-critical failures (e.g., emotion detection fallback)
- **ERROR:** Critical failures requiring attention

### Example Log Output
```
================================================================================
🎙️  PIPELINE START: speech.mp3
================================================================================
✓ Audio validation passed: speech.mp3
📊 Audio size: 0.18 MB (19271 bytes)
💾 Audio cached: audio_1699308008_abc123
--------------------------------------------------------------------------------
📝 STAGE 1: Speech-to-Text Transcription
--------------------------------------------------------------------------------
✓ Transcription successful
  Language: English (en)
  Text: Hello, how are you today?
--------------------------------------------------------------------------------
😊 STAGE 2: Emotion Detection
--------------------------------------------------------------------------------
[OPENSMILE] Calling OpenSmile.process_file() - REAL MODEL EXTRACTION
✓ Emotion detection successful
  Emotion: happy
  Attributes: pitch=0.65, energy=0.72, rate=0.58
--------------------------------------------------------------------------------
🌐 STAGE 3: Text Translation
--------------------------------------------------------------------------------
[DEEPL] Translating: EN -> ES
✓ Translation successful
  Direction: EN → ES
  Translated: Hola, ¿cómo estás hoy?
--------------------------------------------------------------------------------
🔊 STAGE 4: Emotional Text-to-Speech Generation
--------------------------------------------------------------------------------
[ELEVENLABS] Emotion to preserve: happy
[ELEVENLABS] Voice settings mapped:
  - Stability: 0.40
  - Similarity Boost: 0.80
  - Style: 0.60
✓ Audio generation successful
  Size: 0.04 MB (45678 bytes)
  Emotion applied: happy
================================================================================
✅ PIPELINE COMPLETED SUCCESSFULLY
⏱️  Total Duration: 6.45s
   - Validation: 0.05s
   - Transcription: 2.10s
   - Emotion Detection: 0.35s
   - Translation: 1.20s
   - Audio Generation: 2.75s
================================================================================
```

## Individual Service Endpoints

For testing individual pipeline stages:

### Speech-to-Text
```
POST /api/speech-to-text/transcribe
```

### Emotion Detection
```
POST /api/emotion/detect
```

### Translation
```
POST /api/translation/translate
```

### Text-to-Speech
```
POST /api/text-to-speech/generate
```

## Configuration

### Environment Variables
```bash
# API Keys
DEEPGRAM_API_KEY=your_deepgram_key
DEEPL_API_KEY=your_deepl_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Audio Processing
MAX_AUDIO_SIZE_MB=25
SUPPORTED_AUDIO_FORMATS=[".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"]

# ElevenLabs Configuration
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
```

## Error Handling

### Validation Errors (400)
- Invalid file format
- File size exceeds limit
- Missing required parameters

### Processing Errors (500)
- Transcription service unavailable
- Translation API error
- Audio generation failure
- Network timeouts

### Fallback Mechanisms
- **Emotion Detection:** Falls back to "neutral" if detection fails
- **Cache Cleanup:** Automatic cleanup on errors
- **Detailed Error Messages:** Includes stage information for debugging

## Best Practices

### For Frontend Integration
1. **File Size:** Keep audio files under 10MB for optimal performance
2. **Format:** Use MP3 or WAV for best compatibility
3. **Audio Quality:** 16kHz+ sample rate recommended
4. **Error Handling:** Implement retry logic for network failures
5. **Base64 Decoding:** Decode `audio_base64` to play/download audio

### For Production Deployment
1. **API Keys:** Use environment variables, never hardcode
2. **Rate Limiting:** Implement rate limiting for API endpoints
3. **Monitoring:** Set up logging aggregation and alerting
4. **Caching:** Configure Redis for production use
5. **Timeouts:** Adjust timeouts based on expected audio length

## Example Frontend Integration

### JavaScript/TypeScript
```javascript
async function translateAudio(audioFile) {
  const formData = new FormData();
  formData.append('audio', audioFile);
  
  try {
    const response = await fetch('http://localhost:8000/api/process-audio', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    
    // Decode base64 audio
    const audioBlob = base64ToBlob(result.audio_base64, 'audio/mpeg');
    const audioUrl = URL.createObjectURL(audioBlob);
    
    // Play audio
    const audio = new Audio(audioUrl);
    audio.play();
    
    return result;
  } catch (error) {
    console.error('Translation failed:', error);
    throw error;
  }
}

function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}
```

### Python
```python
import requests
import base64

def translate_audio(audio_file_path):
    url = "http://localhost:8000/api/process-audio"
    
    with open(audio_file_path, 'rb') as f:
        files = {'audio': f}
        response = requests.post(url, files=files)
    
    if response.status_code == 200:
        result = response.json()
        
        # Decode and save audio
        audio_data = base64.b64decode(result['audio_base64'])
        with open('translated_audio.mp3', 'wb') as f:
            f.write(audio_data)
        
        return result
    else:
        raise Exception(f"Translation failed: {response.text}")
```

## Support

For issues or questions:
- Check logs for detailed error information
- Verify API keys are configured correctly
- Ensure all services (Redis, APIs) are accessible
- Review individual service endpoints for debugging

## Version

API Version: 1.0.0
Last Updated: November 2025
