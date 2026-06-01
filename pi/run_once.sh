#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate
python wigglegram_phase1.py --config config.json
