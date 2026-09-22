#!/usr/bin/env bash
set -e

echo "=== GenAI Data Assistant Setup Script ==="

# Check for Python 3.12
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check for uv package manager
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Copy .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please update GEMINI_API_KEY in .env before running LLM operations."
else
    echo ".env file already exists."
fi

# Create virtual environment if not present
if [ ! -d .venv ]; then
    echo "Creating Python 3.12 virtual environment using uv..."
    uv venv .venv --python 3.12
fi

echo "Installing project dependencies via uv..."
uv sync || uv pip install -e . -r apps/api/pyproject.toml

# Make scripts executable
chmod +x scripts/*.sh 2>/dev/null || true

echo "=== Setup complete! ==="
echo "Run 'make up' or 'docker compose -f infra/docker-compose.yml up --build' to start services."
