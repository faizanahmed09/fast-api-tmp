# 🛠️ Installation Guide

Complete installation instructions for the FastAPI Speech Translation API.

> **Quick Start:** If you just want to get started quickly, run `./setup.sh` (Linux/Mac) or `setup.bat` (Windows)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Automated Installation](#automated-installation)
3. [Manual Installation](#manual-installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required

1. **Python 3.13+** - [Installation instructions below](#installing-python-313)
2. **Redis server** - For caching audio data
3. **API Keys:**
   - [Deepgram](https://console.deepgram.com/) - Speech-to-Text
   - [DeepL](https://www.deepl.com/pro-api) - Translation
   - [ElevenLabs](https://elevenlabs.io/) - Text-to-Speech

### Optional

- **MediaInfo** - Required for MP3 emotion detection on Windows only
  - Install: `choco install mediainfo`

### Installing Python 3.13

**Using pyenv (Recommended):**
```bash
# Install pyenv
curl https://pyenv.run | bash

# Install Python 3.13
pyenv install 3.13.0
pyenv global 3.13.0
```
> See [PYENV_GUIDE.md](PYENV_GUIDE.md) for detailed pyenv instructions

**macOS:**
```bash
brew install python@3.13
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.13 python3.13-venv python3.13-dev
```

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- ⚠️ Check "Add Python to PATH" during installation

### Installing Redis

Redis is required for caching audio data during processing.

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo service redis-server start
```

**Windows:**
- Download from [GitHub Releases](https://github.com/microsoftarchive/redis/releases)
- Or use WSL (Windows Subsystem for Linux)

**Verify Redis:**
```bash
redis-cli ping
# Should return: PONG
```

---

## Automated Installation

### Linux/macOS

> **Note:** The script automatically detects and supports pyenv. See [PYENV_GUIDE.md](PYENV_GUIDE.md) if you encounter issues.

```bash
./setup.sh
```

The script will:
- ✅ Check for Python 3.13+
- ✅ Initialize pyenv if present
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Show next steps

### Windows

```cmd
setup.bat
```

Or double-click `setup.bat` in File Explorer.

---

## Manual Installation

### 1. Create Virtual Environment

```bash
# Linux/macOS
python3.13 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

### 1. Create Environment File

```bash
# Linux/macOS
cp .env.example .env

# Windows
copy .env.example .env
```

### 2. Edit `.env` File

Add your API keys:

```env
# API Keys (Required)
DEEPGRAM_API_KEY=your_deepgram_api_key_here
DEEPL_API_KEY=your_deepl_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Logging
LOG_LEVEL=INFO
DEBUG=False
```

---

## Running the Application

### Development Mode

```bash
# Activate virtual environment first
# Linux/macOS: source venv/bin/activate
# Windows: venv\Scripts\activate

uvicorn app.main:app --reload
```

**Access:** http://localhost:8000

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Production Deployment

**Using systemd (Linux):**

Create `/etc/systemd/system/emotion-ai.service`:

```ini
[Unit]
Description=FastAPI Speech Translation API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/emotion-ai
Environment="PATH=/opt/emotion-ai/venv/bin"
ExecStart=/opt/emotion-ai/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable emotion-ai
sudo systemctl start emotion-ai
```

---

## Verification

### 1. Check API Health

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{
  "status": "healthy",
  "redis": "connected"
}
```

### 2. View API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Test the API

```bash
curl -X POST "http://localhost:8000/api/process-audio" \
  -F "audio=@your_audio.wav" \
  -o response.json
```

---

## Troubleshooting

### pyenv Issues

**Error:** `pyenv: python3.13: command not found`

**Solution:**
```bash
# Initialize pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# Set version
pyenv local 3.13.0

# Run setup again
./setup.sh
```

> See [PYENV_GUIDE.md](PYENV_GUIDE.md) for complete pyenv documentation

### Python Not Found

**Error:** `Python 3.13 or higher is required but not found!`

**Solutions:**
- Install with pyenv: `pyenv install 3.13.0 && pyenv global 3.13.0`
- Install from [python.org](https://www.python.org/downloads/)
- Ensure Python is in PATH (Windows)

### Redis Connection Failed

**Error:** `Connection to Redis failed`

**Solutions:**
1. Check if running: `redis-cli ping`
2. Start Redis:
   - macOS: `brew services start redis`
   - Linux: `sudo service redis-server start`
   - Windows: Run `redis-server.exe`

### Permission Denied (setup.sh)

**Error:** `Permission denied: './setup.sh'`

**Solution:**
```bash
chmod +x setup.sh
./setup.sh
```

### Virtual Environment Issues

**Solution:**
```bash
# Remove and recreate
rm -rf venv
python3.13 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### OpenSmile Installation Failed

**Note:** OpenSmile is optional. The API will use mock emotion detection if unavailable.

**For full functionality:**
- macOS: `xcode-select --install`
- Linux: `sudo apt-get install build-essential`
- Windows: Install Visual Studio Build Tools

### Invalid API Keys

**Solutions:**
- Verify keys in `.env` (no extra spaces or quotes)
- Check API quotas and remaining credits
- Ensure keys are active in respective dashboards

---

## Additional Resources

- **[README.md](README.md)** - Project overview and quick reference
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation  
- **[PYENV_GUIDE.md](PYENV_GUIDE.md)** - Python version management
- **[Postman Collection](postman_collection.json)** - API testing

---

## Need Help?

1. Check logs for error messages
2. Verify all prerequisites are installed
3. Ensure API keys are correctly configured
4. Test Redis: `redis-cli ping`
5. Check Python version: `python --version`

For API service documentation:
- [Deepgram Docs](https://developers.deepgram.com/)
- [DeepL API Docs](https://www.deepl.com/docs-api)
- [ElevenLabs Docs](https://docs.elevenlabs.io/)

