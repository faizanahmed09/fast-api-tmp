#!/bin/bash

# FastAPI Speech Translation API - Setup Script
# For Linux and macOS

set -e  # Exit on error

echo "=========================================="
echo "FastAPI Speech Translation API Setup"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Initialize pyenv if it exists
if command -v pyenv &> /dev/null; then
    print_info "Initializing pyenv..."
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init --path 2>/dev/null || true)"
    eval "$(pyenv init - 2>/dev/null || true)"
fi

# Check for Python 3.13
print_info "Checking for Python 3.13..."

# Try different Python commands
PYTHON_CMD=""
PYTHON_VERSION=""
for cmd in python3.13 python3 python; do
    if command -v $cmd &> /dev/null; then
        # Get version, handling different output formats
        version=$($cmd --version 2>&1 | grep -oP '\d+\.\d+(\.\d+)?' | head -1)
        if [ -n "$version" ]; then
            major=$(echo $version | cut -d. -f1)
            minor=$(echo $version | cut -d. -f2)
            
            if [ "$major" -eq 3 ] && [ "$minor" -ge 13 ]; then
                PYTHON_CMD=$cmd
                PYTHON_VERSION=$version
                print_success "Found Python $version at $(which $cmd)"
                break
            fi
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    print_error "Python 3.13 or higher is required but not found!"
    echo ""
    echo "Please install Python 3.13+ from:"
    echo "  - pyenv: pyenv install 3.13.0 && pyenv global 3.13.0"
    echo "  - macOS: brew install python@3.13"
    echo "  - Ubuntu/Debian: sudo apt install python3.13"
    echo "  - Or download from: https://www.python.org/downloads/"
    exit 1
fi

# For pyenv users, set the local version to ensure consistency
if command -v pyenv &> /dev/null; then
    print_info "Setting pyenv local version to $PYTHON_VERSION..."
    pyenv local $PYTHON_VERSION 2>/dev/null || true
fi

echo ""

# Check if virtual environment already exists
if [ -d "venv" ]; then
    print_info "Virtual environment already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing virtual environment..."
        rm -rf venv
    else
        print_info "Using existing virtual environment."
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
fi

echo ""

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip --quiet

echo ""

# Install dependencies
print_info "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

print_success "All dependencies installed successfully!"

echo ""
echo "=========================================="
echo "Setup Complete! 🎉"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Configure your environment variables:"
echo "     cp .env.example .env"
echo "     Then edit .env with your API keys"
echo ""
echo "  3. Make sure Redis is running:"
echo "     redis-cli ping (should return PONG)"
echo ""
echo "  4. Start the application:"
echo "     uvicorn app.main:app --reload"
echo ""
echo "  5. Visit the API documentation:"
echo "     http://localhost:8000/docs"
echo ""
