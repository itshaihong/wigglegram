#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f config.json ]; then
  cp config.example.json config.json
fi

echo "Setup complete. Edit pi/config.json, then run ./run_once.sh"
