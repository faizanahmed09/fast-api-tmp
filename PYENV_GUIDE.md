# 🐍 pyenv Quick Reference

If you're using **pyenv** to manage Python versions, here's what you need to know:

## Quick Fix for Setup Script

If you see an error like:
```
pyenv: python3.13: command not found
```

**Run these commands first, then run the setup script again:**

```bash
# Initialize pyenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# Set Python version for this project
pyenv local 3.13.0

# Now run setup
./setup.sh
```

> See [INSTALLATION.md](INSTALLATION.md) for general installation help.

## Understanding pyenv

pyenv is a Python version manager that allows multiple Python versions to coexist on your system.

### Check Available Python Versions

```bash
# List installed versions
pyenv versions

# List available versions to install
pyenv install --list | grep 3.13
```

### Install Python 3.13

```bash
# Install Python 3.13.0 (or latest 3.13.x)
pyenv install 3.13.0

# Or install the latest 3.13 version
pyenv install 3.13.9
```

### Set Python Version

**For this project only (recommended):**
```bash
cd /path/to/fast-api-tmp
pyenv local 3.13.0
```
This creates a `.python-version` file in the project directory.

**For all projects (global):**
```bash
pyenv global 3.13.0
```

**For current shell session only:**
```bash
pyenv shell 3.13.0
```

### Verify Python Version

```bash
python --version
# Should output: Python 3.13.x
```

## Make pyenv Permanent

To avoid initializing pyenv every time, add these lines to your shell config:

**For bash (`~/.bashrc` or `~/.bash_profile`):**
```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
```

**For zsh (`~/.zshrc`):**
```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
```

After editing, reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc for zsh
```

## The Setup Script Now Handles pyenv

The updated `setup.sh` script now:
- ✅ Automatically detects pyenv
- ✅ Initializes pyenv environment
- ✅ Sets local Python version
- ✅ Creates virtual environment correctly

Just run:
```bash
./setup.sh
```

## Alternative: Use pyenv-virtualenv

If you prefer using pyenv's built-in virtualenv:

```bash
# Install pyenv-virtualenv plugin
git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv

# Create a virtual environment
pyenv virtualenv 3.13.0 emotion-ai-env

# Activate it for this project
pyenv local emotion-ai-env

# Install dependencies
pip install -r requirements.txt
```

## Troubleshooting

### pyenv command not found

**Install pyenv:**
```bash
curl https://pyenv.run | bash
```

Then add to your `~/.bashrc` or `~/.zshrc`:
```bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
```

### Python build fails

Install build dependencies:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
  libffi-dev liblzma-dev
```

**macOS:**
```bash
brew install openssl readline sqlite3 xz zlib
```

## More Information

- pyenv GitHub: https://github.com/pyenv/pyenv
- pyenv commands: `pyenv commands`
- Get help: `pyenv help` or `pyenv help <command>`
