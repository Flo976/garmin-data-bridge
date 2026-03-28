#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
export $(grep -v '^#' config.env | grep -v '^\s*$' | xargs)

# xvfb-run launches a virtual display for headed Chromium
xvfb-run --auto-servernum python3 -m src.sync "$@" 2>&1 | tee -a ~/.garmin-sync/logs/sync.log
