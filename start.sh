#!/usr/bin/env bash

# Convenience script to start the brick-geometry-engine API locally.
#
# Usage:
#   ./start.sh
#
# This script:
#   1) Creates/activates a Python venv at ./brick-geometry-engine/.venv
#   2) Installs dependencies (only first run or after changes)
#   3) Runs the FastAPI server via uvicorn

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR/brick-geometry-engine"

# Create venv if missing
if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

# Activate venv (works in bash/zsh)
# shellcheck disable=SC1091
source .venv/bin/activate

# Install dependencies if not already installed
pip install -r requirements.txt
pip install -e .

# Ensure the database is ready (uses SQLITE local file by default)
# This is a no-op if already up to date.
python -m alembic upgrade head

# Run the API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
