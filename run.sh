#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

# Load config safely (handles passwords with #, *, spaces, etc.)
set -a
source config.env
set +a

# xvfb-run launches a virtual display for headed Chromium
# Logging is handled by src/sync.py — no tee needed
xvfb-run --auto-servernum python3 -m src.sync "$@"
