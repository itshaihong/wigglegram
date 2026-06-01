#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
python web_gallery.py --host 0.0.0.0 --port 8080 --config config.json --output-dir captures
