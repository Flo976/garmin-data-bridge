#!/bin/bash
set -e

echo "=== Garmin Playwright Sync — Setup ==="

# System deps
sudo apt-get update
sudo apt-get install -y python3 python3-venv xvfb

# Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Chromium (skip on Raspberry Pi where it's system-provided)
if [ ! -f /usr/bin/chromium-browser ]; then
    python3 -m playwright install chromium
    python3 -m playwright install-deps chromium
else
    echo "System Chromium detected at /usr/bin/chromium-browser — skipping Playwright install"
fi

# Create dirs
mkdir -p ~/.garmin-sync/browser-data
mkdir -p ~/.garmin-sync/logs

# Config
if [ ! -f config.env ]; then
    cp config.example.env config.env
    echo ">>> Edit config.env with your credentials"
fi

echo "=== Setup complete ==="
echo "Test: ./run.sh"
