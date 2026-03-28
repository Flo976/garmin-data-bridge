#!/bin/bash
set -e

echo "=== Garmin Data Bridge — Setup ==="

# System deps
sudo apt-get update
sudo apt-get install -y python3 python3-venv xvfb

# Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install browser: prefer system Chrome/Chromium, fallback to Playwright-managed
if command -v google-chrome-stable &>/dev/null || command -v google-chrome &>/dev/null; then
    echo "System Chrome detected — skipping browser install"
elif [ -f /usr/bin/chromium-browser ]; then
    echo "System Chromium detected — skipping browser install"
else
    echo "No system Chrome found — installing via patchright"
    python3 -m patchright install chromium
    python3 -m patchright install-deps chromium
fi

# Create dirs
mkdir -p ~/.garmin-sync/browser-data
mkdir -p ~/.garmin-sync/logs
mkdir -p ~/.garmin-sync/debug

# Config
if [ ! -f config.env ]; then
    cp config.example.env config.env
    echo ">>> Edit config.env with your Garmin credentials"
fi

# Prepare systemd files with actual user/path
INSTALL_DIR="$(pwd)"
INSTALL_USER="$(whoami)"
sed "s|%REPLACE_USER%|${INSTALL_USER}|g; s|%REPLACE_PATH%|${INSTALL_DIR}|g" \
    systemd/garmin-sync.service > systemd/garmin-sync.service.local
echo "Systemd service configured for user=${INSTALL_USER} path=${INSTALL_DIR}"
echo "  To install: sudo cp systemd/garmin-sync.service.local /etc/systemd/system/garmin-sync.service"
echo "              sudo cp systemd/garmin-sync.timer /etc/systemd/system/"
echo "              sudo systemctl daemon-reload && sudo systemctl enable --now garmin-sync.timer"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Usage:"
echo "  ./run.sh                    # Sync today"
echo "  ./run.sh --dry-run          # Preview without uploading"
echo "  ./run.sh --login-only       # Save session and exit"
echo "  ./run.sh --range 7          # Backfill last 7 days"
echo "  ./run.sh --date 2026-03-25  # Sync a specific date"
