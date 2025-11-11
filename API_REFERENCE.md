# API Reference Guide

## Base URL
```
http://localhost:8000  (Development)
https://your-domain.com  (Production)
```

---

## 📡 Endpoints

### 1. Health Check

#### Simple Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Codes:**
- `200 OK` - Service is running

---

#### Detailed Health Check
```http
GET /health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-10T22:15:00Z",
  "services": {
    "deepgram": "connected",
    "deepl": "connected",
    "elevenlabs": "connected",
    "redis": "connected",
    "opensmile": "available"
  },
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK` - All services healthy
- `503 Service Unavailable` - One or more services down

---

### 2. Process Audio (Main Endpoint)

```http
POST /api/process-audio
Content-Type: multipart/form-data
```

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `audio` | File | Yes | Audio file to process |
| `target_language` | String | No | Target language code (en, es) - auto-detected if not provided |

**Example Request (cURL):**
```bash
curl -X POST "http://localhost:8000/api/process-audio" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@sample.wav" \
  -F "target_language=es"
```

**Example Request (Python):**
```python
import requests

url = "http://localhost:8000/api/process-audio"
files = {"audio": open("sample.wav", "rb")}
data = {"target_language": "es"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Example Request (JavaScript):**
```javascript
const formData = new FormData();
formData.append('audio', audioFile);
formData.append('target_language', 'es');

fetch('http://localhost:8000/api/process-audio', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "original_text": "Hello, how are you today?",
  "original_language": "English",
  "original_language_code": "en",
  "translated_text": "Hola, ¿cómo estás hoy?",
  "target_language": "Spanish",
  "target_language_code": "es",
  "detected_emotion": "happy",
  "emotion_attributes": {
    "pitch_mean": 0.65,
    "energy": 0.72,
    "speaking_rate": 0.58
  },
  "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA...",
  "processing_details": {
    "total_duration": 7.23,
    "stages": {
      "validation": {
        "status": "completed",
        "duration": 0.05
      },
      "transcription": {
        "status": "completed",
        "duration": 2.81
      },
      "emotion_detection": {
        "status": "completed",
        "duration": 2.81
      },
      "translation": {
        "status": "completed",
        "duration": 1.02
      },
      "audio_generation": {
        "status": "completed",
        "duration": 3.54
      }
    }
  },
  "metadata": {
    "audio_format": "audio/wav",
    "audio_size_bytes": 245760,
    "processing_timestamp": "2025-11-10T22:15:30Z"
  }
}
```

**Error Responses:**

**400 Bad Request** - Invalid input
```json
{
  "detail": "No audio file provided"
}
```

**413 Payload Too Large** - File too large
```json
{
  "detail": "Audio file too large. Maximum size: 25MB"
}
```

**500 Internal Server Error** - Processing failed
```json
{
  "detail": "Speech-to-text transcription failed: Invalid API key"
}
```

**Status Codes:**
- `200 OK` - Processing successful
- `400 Bad Request` - Invalid request (missing file, wrong format)
- `413 Payload Too Large` - File exceeds 25MB limit
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Processing error

---

## 📋 Response Fields Explained

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | Boolean | Whether processing was successful |
| `original_text` | String | Transcribed text from audio |
| `original_language` | String | Detected language name (e.g., "English") |
| `original_language_code` | String | ISO language code (e.g., "en") |
| `translated_text` | String | Translated text |
| `target_language` | String | Target language name (e.g., "Spanish") |
| `target_language_code` | String | Target ISO language code (e.g., "es") |
| `detected_emotion` | String | Detected emotion (happy, sad, angry, neutral, etc.) |
| `audio_base64` | String | Base64-encoded audio file of translated speech |

### Emotion Attributes

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `pitch_mean` | Float | 0.0-1.0 | Average pitch of voice |
| `energy` | Float | 0.0-1.0 | Voice energy/intensity |
| `speaking_rate` | Float | 0.0-1.0 | Speed of speech |

### Processing Details

| Field | Type | Description |
|-------|------|-------------|
| `total_duration` | Float | Total processing time in seconds |
| `stages` | Object | Breakdown of each processing stage |
| `stages.*.status` | String | Stage status (completed, failed) |
| `stages.*.duration` | Float | Stage duration in seconds |
| `stages.*.error` | String | Error message if stage failed |

---

## 🎯 Supported Audio Formats

The API accepts most common audio formats:

✅ **Recommended:**
- WAV (`.wav`)
- MP3 (`.mp3`)
- M4A (`.m4a`)
- FLAC (`.flac`)

✅ **Also Supported:**
- OGG (`.ogg`)
- WEBM (`.webm`)
- AAC (`.aac`)

**Limitations:**
- Maximum file size: 25MB
- Maximum duration: ~10 minutes (depends on format)
- Recommended: 16kHz or higher sample rate

---

## 🌍 Supported Languages

### Currently Supported

| Language | Code | Direction |
|----------|------|-----------|
| English | `en` | Source ↔ Target |
| Spanish | `es` | Source ↔ Target |

### Translation Logic

- **English audio** → Automatically translates to Spanish
- **Spanish audio** → Automatically translates to English
- **Other languages** → Defaults to English translation

### Future Languages (Easily Extensible)

The system can be extended to support:
- French (`fr`)
- German (`de`)
- Italian (`it`)
- Portuguese (`pt`)
- And 20+ more languages supported by DeepL

---

## 😊 Emotion Detection

### Detected Emotions

| Emotion | Description | Attributes |
|---------|-------------|------------|
| `happy` | Positive, upbeat tone | High pitch, high energy |
| `sad` | Low, melancholic tone | Low pitch, low energy |
| `angry` | Aggressive, intense tone | High energy, fast rate |
| `neutral` | Calm, balanced tone | Medium pitch, medium energy |
| `excited` | Enthusiastic, energetic | High pitch, high energy, fast rate |

### Emotion Preservation

The system maps detected emotions to ElevenLabs voice settings:

```python
Emotion → Voice Settings
- Stability: How consistent the voice is
- Similarity Boost: How close to original voice
- Style: Emotional expressiveness (0.0-1.0)
- Speaker Boost: Voice clarity
```

---

## 🔐 Authentication

### Current Status
- No authentication required (development)

### Production Recommendations
- Implement API key authentication
- Use JWT tokens for user sessions
- Rate limiting per API key
- IP whitelisting for trusted clients

**Example with API Key (Future):**
```http
POST /api/process-audio
Authorization: Bearer your-api-key-here
Content-Type: multipart/form-data
```

---

## ⚠️ Error Handling

### Common Errors

#### 1. Missing Audio File
```json
{
  "detail": "No audio file provided"
}
```
**Solution:** Include audio file in request

#### 2. Invalid API Key
```json
{
  "detail": "Invalid Deepgram API key. Please check your DEEPGRAM_API_KEY in .env file"
}
```
**Solution:** Verify API keys in `.env` file

#### 3. File Too Large
```json
{
  "detail": "Audio file too large. Maximum size: 25MB"
}
```
**Solution:** Compress audio or split into smaller files

#### 4. Unsupported Format
```json
{
  "detail": "Unsupported audio format"
}
```
**Solution:** Convert to WAV or MP3

#### 5. Service Unavailable
```json
{
  "detail": "Redis connection failed"
}
```
**Solution:** Ensure Redis is running

---

## 📊 Rate Limits

### Current Limits (Development)
- No rate limits applied

### Recommended Production Limits
- **Per IP:** 100 requests/hour
- **Per API Key:** 1000 requests/day
- **Concurrent requests:** 10 per client
- **File size:** 25MB max

---

## 🧪 Testing Examples

### Test with cURL

```bash
# Basic request
curl -X POST "http://localhost:8000/api/process-audio" \
  -F "audio=@test.wav"

# With target language
curl -X POST "http://localhost:8000/api/process-audio" \
  -F "audio=@test.wav" \
  -F "target_language=es"

# Save response to file
curl -X POST "http://localhost:8000/api/process-audio" \
  -F "audio=@test.wav" \
  -o response.json
```

### Test with Python

```python
import requests
import base64
import json

# Process audio
with open("sample.wav", "rb") as f:
    files = {"audio": f}
    response = requests.post(
        "http://localhost:8000/api/process-audio",
        files=files
    )

result = response.json()

# Save translated audio
if result["success"]:
    audio_data = base64.b64decode(result["audio_base64"])
    with open("translated.mp3", "wb") as f:
        f.write(audio_data)
    
    print(f"Original: {result['original_text']}")
    print(f"Translated: {result['translated_text']}")
    print(f"Emotion: {result['detected_emotion']}")
```

### Test with Postman

1. **Create new request:**
   - Method: `POST`
   - URL: `http://localhost:8000/api/process-audio`

2. **Set body:**
   - Type: `form-data`
   - Key: `audio` (type: File)
   - Value: Select your audio file

3. **Send request**

4. **View response:**
   - Check `audio_base64` field
   - Copy and decode to get audio file

---

## 📈 Performance Metrics

### Average Processing Times

| Stage | Duration | Percentage |
|-------|----------|------------|
| Validation | 0.05s | 0.6% |
| STT + Emotion (Parallel) | 2.8s | 36.4% |
| Translation | 1.0s | 13.0% |
| Text-to-Speech | 3.5s | 45.5% |
| Cleanup | 0.35s | 4.5% |
| **Total** | **7.7s** | **100%** |

### Optimization Tips

1. **Use smaller audio files** - Shorter audio = faster processing
2. **Compress audio** - Lower bitrate = faster upload
3. **Use connection pooling** - Already implemented
4. **Enable caching** - For repeated translations
5. **Use CDN** - For serving generated audio

---

## 🔧 Configuration

### Environment Variables

```env
# Application
APP_NAME="Speech Translation API"
APP_VERSION="1.0.0"
DEBUG=False

# API Keys
DEEPGRAM_API_KEY="your-key-here"
DEEPL_API_KEY="your-key-here"
ELEVENLABS_API_KEY="your-key-here"

# Redis
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0

# Limits
MAX_AUDIO_SIZE_MB=25

# Logging
LOG_LEVEL="INFO"
```

---

## 📚 Additional Resources

- **Interactive API Docs:** http://localhost:8000/docs
- **Alternative API Docs:** http://localhost:8000/redoc
- **OpenAPI Schema:** http://localhost:8000/openapi.json

---

## 💡 Best Practices

### For Clients

1. **Always check `success` field** before processing response
2. **Handle errors gracefully** with try-catch blocks
3. **Validate audio files** before uploading
4. **Decode base64 audio** properly
5. **Monitor processing times** for performance issues
6. **Implement retry logic** for transient failures

### For Production

1. **Use HTTPS** for all requests
2. **Implement authentication** (API keys or JWT)
3. **Set up monitoring** and alerts
4. **Enable rate limiting** to prevent abuse
5. **Cache responses** when appropriate
6. **Log all requests** for debugging
7. **Use load balancer** for high traffic

---

**Last Updated:** November 10, 2025  
**API Version:** 1.0.0  
**Documentation Version:** 1.0.0
