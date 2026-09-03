#!/usr/bin/env bash
# Sets up a local Python virtual environment for PDF Pro development.
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

echo "Dev environment ready. Activate with: source .venv/bin/activate"
