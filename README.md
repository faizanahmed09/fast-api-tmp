# 🎙️ FastAPI Speech Translation API

Real-time multilingual speech translation with emotion preservation using FastAPI, Deepgram, OpenSmile, DeepL, and ElevenLabs.

---

## ✨ Features

- 🗣️ **Speech-to-Text** - Automatic transcription with language detection (English/Spanish)
- 😊 **Emotion Detection** - Extract emotional attributes using OpenSmile
- 🌐 **Translation** - High-quality translation between English and Spanish
- 🎵 **Emotional Text-to-Speech** - Generate speech that preserves detected emotions
- ⚡ **Async Processing** - Fast, non-blocking API endpoints
- 💾 **Redis Caching** - Efficient temporary audio storage
- 📝 **Auto Documentation** - Interactive API docs with Swagger UI

---

## 🏗️ Architecture

**Modular Monolithic Design** - Single deployable application with organized internal modules:

```
app/
├── main.py                      # Application entry point & orchestration
├── core/
│   ├── config.py                # Configuration management
│   ├── redis_client.py          # Redis caching client
│   └── utils.py                 # Utility functions
└── modules/
    ├── speech_to_text/          # Deepgram integration
    │   ├── service.py
    │   └── router.py
    ├── emotion_detection/       # OpenSmile integration
    │   ├── service.py
    │   └── router.py
    ├── translation/             # DeepL integration
    │   ├── service.py
    │   └── router.py
    └── text_to_speech/          # ElevenLabs integration
        ├── service.py
        └── router.py
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **Redis server**
- **API keys** for Deepgram, DeepL, and ElevenLabs

> 📘 **Detailed installation guide:** [INSTALLATION.md](INSTALLATION.md)

### Automated Setup (Recommended)

**Linux/macOS:**
```bash
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### Manual Setup

```bash
# Create and activate virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start Redis and run the app
uvicorn app.main:app --reload
```

**API Documentation:** http://localhost:8000/docs

---

## 📖 Documentation

- **[INSTALLATION.md](INSTALLATION.md)** - Complete installation guide with troubleshooting
- **[API_REFERENCE.md](API_REFERENCE.md)** - Detailed API documentation and examples
- **[PYENV_GUIDE.md](PYENV_GUIDE.md)** - Python version management with pyenv
- **Interactive API Docs** - http://localhost:8000/docs
- **ReDoc** - http://localhost:8000/redoc

## 🎯 API Endpoints

### Main Pipeline Endpoint

#### `POST /api/process-audio`

Process audio through the complete translation pipeline.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: `audio` file (mp3, wav, m4a, flac, ogg, webm)

**Response:**
```json
{
  "original_text": "Hello, how are you?",
  "original_language": "English",
  "translated_text": "Hola, ¿cómo estás?",
  "target_language": "es",
  "emotion": "happy",
  "emotion_attributes": {
    "pitch_mean": 0.65,
    "energy": 0.72,
    "speaking_rate": 0.55
  },
  "audio_base64": "base64_encoded_audio_data...",
  "audio_size_bytes": 45231
}
```

### Individual Module Endpoints

#### `POST /api/speech-to-text/transcribe`
Transcribe audio with language detection.

#### `POST /api/emotion/detect`
Detect emotion from audio.

#### `POST /api/translation/translate`
Translate text between languages.

#### `POST /api/text-to-speech/generate`
Generate emotional speech from text.

#### `GET /api/text-to-speech/voices`
List available ElevenLabs voices.

## 🧪 Testing with cURL

### Process Complete Audio

```bash
curl -X POST "http://localhost:8000/api/process-audio" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@sample.wav"
```

### Transcribe Audio Only

```bash
curl -X POST "http://localhost:8000/api/speech-to-text/transcribe" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@sample.wav"
```

### Detect Emotion Only

```bash
curl -X POST "http://localhost:8000/api/emotion/detect" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@sample.wav"
```

### Translate Text

```bash
curl -X POST "http://localhost:8000/api/translation/translate" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, how are you?",
    "source_lang": "en",
    "target_lang": "es"
  }'
```

### Generate Speech

```bash
curl -X POST "http://localhost:8000/api/text-to-speech/generate" \
  -H "accept: audio/mpeg" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hola, ¿cómo estás?",
    "emotion": "happy",
    "language_code": "es"
  }' \
  --output output.mp3
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_main.py -v
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEEPGRAM_API_KEY` | Deepgram API key | - | ✅ |
| `DEEPL_API_KEY` | DeepL API key | - | ✅ |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | - | ✅ |
| `REDIS_HOST` | Redis server host | localhost | ❌ |
| `REDIS_PORT` | Redis server port | 6379 | ❌ |
| `REDIS_PASSWORD` | Redis password | - | ❌ |
| `LOG_LEVEL` | Logging level | INFO | ❌ |
| `DEBUG` | Debug mode | False | ❌ |

### Supported Audio Formats

- MP3 (`.mp3`)
- WAV (`.wav`)
- M4A (`.m4a`)
- FLAC (`.flac`)
- OGG (`.ogg`)
- WebM (`.webm`)

### Emotion Categories

- `happy` - High pitch and energy
- `sad` - Low pitch and energy
- `angry` - High energy, elevated pitch
- `neutral` - Balanced attributes
- `surprised` - High pitch, high energy

## 📊 Processing Pipeline

```
┌─────────────┐
│ Audio Input │
└──────┬──────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌──────────────┐         ┌──────────────┐
│ Speech-to-   │         │   Emotion    │
│ Text         │         │   Detection  │
│ (Deepgram)   │         │ (OpenSmile)  │
└──────┬───────┘         └──────┬───────┘
       │                        │
       ▼                        │
┌──────────────┐                │
│ Translation  │                │
│  (DeepL)     │                │
└──────┬───────┘                │
       │                        │
       └────────┬───────────────┘
                │
                ▼
        ┌──────────────┐
        │ Text-to-     │
        │ Speech       │
        │ (ElevenLabs) │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Audio Output │
        └──────────────┘
```

## 🐛 Troubleshooting

### Quick Fixes

**Redis Connection Issues:**
```bash
redis-cli ping  # Should return: PONG
```

**Python Version Issues:**
- See [PYENV_GUIDE.md](PYENV_GUIDE.md) for pyenv users
- Ensure Python 3.13+ is installed: `python --version`

**API Key Errors:**
- Verify keys in `.env` file (no extra spaces)
- Check API quotas and limits

> 📘 **For detailed troubleshooting:** [INSTALLATION.md](INSTALLATION.md#troubleshooting)

## 📝 Development

### Code Formatting
```bash
black app/
```

### Linting
```bash
flake8 app/
```

### Type Checking
```bash
mypy app/
```

## 🚀 Deployment

See [INSTALLATION.md](INSTALLATION.md#running-the-application) for production deployment options.

### Quick Production Start

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Production Checklist

- ✅ Set `DEBUG=False` in `.env`
- ✅ Configure Redis persistence
- ✅ Set up process manager (systemd/supervisord)
- ✅ Use reverse proxy (nginx)
- ✅ Enable HTTPS/TLS
- ✅ Configure rate limiting
- ✅ Set up monitoring and logging

## 📄 License

MIT

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## 📚 API Service Documentation

- [Deepgram API](https://developers.deepgram.com/)
- [DeepL API](https://www.deepl.com/docs-api)
- [ElevenLabs API](https://docs.elevenlabs.io/)
- [OpenSmile Documentation](https://audeering.github.io/opensmile-python/)

---

Built with ❤️ using FastAPI
