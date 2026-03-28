# Garmin Data Bridge

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4%20%2F%205-c51a4a.svg)](https://www.raspberrypi.com/)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)]()

Automatically sync your Garmin Connect health data to any webhook endpoint. Runs on any Linux machine (laptop, Raspberry Pi) as a cron job.

```
Garmin watch → Garmin Connect → Garmin Data Bridge → Your server
```

> **Coming from [garminconnect#337](https://github.com/cyberjunky/python-garminconnect/issues/337) or [garth#217](https://github.com/matin/garth/issues/217)?** Those libraries stopped working in March 2026 when Garmin added Cloudflare protection. This tool takes a completely different approach that bypasses the issue — see [How it works](#how-it-works).

---

## What it syncs

| Category | Metrics |
|----------|---------|
| **Daily** | Steps, calories, resting HR, VO2max, stress, Body Battery, Training Readiness, HRV |
| **Sleep** | Score, total/deep/REM/light/awake minutes |
| **Activities** | Type, name, duration, distance, HR avg/max, training effect (aerobic + anaerobic), VO2max update |

All metrics are included — even Garmin-proprietary ones (Body Battery, Training Readiness, HRV) that aren't available via Health Connect or third-party APIs.

## How it works

Instead of calling Garmin's API directly (which gets blocked by Cloudflare), this tool opens a **real Chrome browser**, navigates Garmin Connect like a normal user, and **intercepts the data that Garmin's own React app loads**.

```
Chrome (xvfb, persistent session, residential IP)
  → Navigates connect.garmin.com
    → Garmin's own JavaScript loads health data
      → Patchright intercepts the HTTP responses
        → Parsed and POSTed to your webhook
```

**Why this works when libraries don't:**
- No API reverse-engineering — if Garmin changes their endpoints, their own app adapts, and so do we
- Uses [patchright](https://github.com/AuroraWright/patchright) (undetected Playwright fork) to bypass Cloudflare Turnstile
- Runs Chrome in headed mode via `xvfb` (virtual display) — indistinguishable from a real user
- Persistent browser session — cookies saved to disk, login only happens when the session expires

## Quick start

```bash
git clone https://github.com/Flo976/garmin-data-bridge.git
cd garmin-data-bridge
chmod +x setup.sh run.sh
./setup.sh
```

Edit `config.env` with your credentials:

```env
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-password
WEBHOOK_URL=https://your-server.com
WEBHOOK_API_KEY=your-api-key
```

First run — save your session:

```bash
./run.sh --login-only
```

Preview data without uploading:

```bash
./run.sh --dry-run
```

## Usage

```bash
./run.sh                      # Sync today
./run.sh --dry-run             # Preview JSON output, don't upload
./run.sh --login-only          # Log in, save session, exit
./run.sh --date 2026-03-25     # Sync a specific date
./run.sh --range 7             # Backfill the last 7 days
./run.sh -v                    # Verbose logging
```

## Scheduling

### systemd (recommended)

```bash
sudo cp systemd/garmin-sync.* /etc/systemd/system/
# Edit WorkingDirectory and User in garmin-sync.service
sudo systemctl daemon-reload
sudo systemctl enable --now garmin-sync.timer
```

### cron

```cron
*/15 * * * * /path/to/garmin-data-bridge/run.sh >> ~/.garmin-sync/logs/cron.log 2>&1
```

## Webhook format

The tool POSTs JSON to two endpoints with an `Authorization: Bearer {API_KEY}` header.

<details>
<summary><b>POST /ingest/daily-summary</b></summary>

```json
{
  "date": "2026-03-28",
  "steps": 8432,
  "calories": 2150,
  "restingHr": 52,
  "stressAvg": 32,
  "bodyBattery": 85,
  "trainingReadiness": 62,
  "hrvGarmin": 42.0,
  "sleepScore": 81,
  "sleepTotalMin": 450,
  "sleepDeepMin": 90,
  "sleepRemMin": 90,
  "sleepLightMin": 240,
  "sleepAwakeMin": 30,
  "vo2max": 52.0
}
```
</details>

<details>
<summary><b>POST /ingest/activity</b></summary>

```json
{
  "garminActivityId": "17234567890",
  "date": "2026-03-28 07:30:00",
  "type": "trail_running",
  "name": "Trail Morning",
  "durationS": 3845,
  "distanceM": 8234.5,
  "hrAvg": 148,
  "hrMax": 172,
  "calories": 680,
  "trainingEffectAerobic": 3.8,
  "trainingEffectAnaerobic": 1.2,
  "vo2maxUpdate": 52.0
}
```
</details>

## Raspberry Pi

Works on **Pi 4** (2 GB+ RAM) and **Pi 5** with Raspberry Pi OS 64-bit (Bookworm). The tool automatically detects and uses system Chromium at `/usr/bin/chromium-browser`.

Memory usage is ~300-400 MB during sync (Chrome + xvfb), well within Pi 4 limits.

## Troubleshooting

### Cloudflare CAPTCHA / "Just a moment..."

Patchright handles Cloudflare Turnstile automatically. If it fails persistently, your browser profile may be flagged. Reset it:

```bash
rm -rf ~/.garmin-sync/browser-data
./run.sh --login-only
```

### MFA / Two-factor authentication

MFA is **not currently supported**. If your Garmin account has MFA enabled, the tool will fail at login. Disable MFA on your Garmin account, or use a secondary account without MFA.

### xvfb errors

If you see `xvfb-run: error: Xvfb failed to start`, install xvfb:

```bash
sudo apt-get install -y xvfb
```

On systems with a real display (desktop Linux), you can skip xvfb and run directly:

```bash
python3 -m src.sync --dry-run
```

### 429 Too Many Requests

This tool should not trigger 429 errors because it doesn't call Garmin's API directly. If you see 429 in the logs, you're likely running syncs too frequently. The default 15-minute interval is safe. Avoid running multiple instances in parallel.

### "AN UNEXPECTED ERROR HAS OCCURRED"

Garmin's SSO returns this intermittently. The tool retries automatically (2 attempts, 30s delay). If it persists, wait a few hours — Garmin's servers may be under load.

### Debug screenshots

On any auth failure, screenshots are saved to `~/.garmin-sync/debug/`:

```bash
ls ~/.garmin-sync/debug/
```

### Logs and state

```bash
tail -50 ~/.garmin-sync/logs/sync.log        # Recent logs
cat ~/.garmin-sync/logs/sync_state.json       # Last sync per date
```

## Limitations

- **Linux only** — requires xvfb for headless display. macOS and Windows are not supported yet.
- **Residential IP required** — Cloudflare blocks datacenter and cloud IPs. Must run from a home network (laptop, Raspberry Pi, home server).
- **No MFA support** — accounts with two-factor authentication enabled cannot be used.
- **Session expiry** — Garmin sessions expire after some time (hours to days). The tool re-logs in automatically, but this can occasionally fail if Cloudflare is aggressive.
- **No real-time sync** — data is fetched by navigating pages; minimum practical interval is ~10 minutes.
- **Browser dependency** — requires a full Chrome/Chromium installation (~300 MB). Lightweight environments (Alpine, minimal containers) need extra setup.
- **Single account** — one config.env per instance. For multiple Garmin accounts, run separate instances with different data directories.

## Contributing

PRs are welcome! Here are some areas where help would be appreciated:

- **macOS support** — adapt xvfb approach or use a native alternative
- **Docker image** — containerized setup with Chrome and xvfb included
- **Body composition data** — weight, body fat %, muscle mass from Garmin's scale integration
- **Training Readiness / Status** — intercept additional health stats pages
- **Multi-account support** — config-driven support for syncing multiple accounts
- **Notification on failure** — Slack/Discord/email alert when sync fails repeatedly
- **Prometheus/Grafana exporter** — expose metrics instead of (or in addition to) webhook POST

## Related projects

If Garmin Data Bridge doesn't fit your use case, these projects tackle the same problem:

- **[python-garminconnect](https://github.com/cyberjunky/python-garminconnect)** — the original Python library. Works when Garmin's auth isn't blocking your IP. See [#337](https://github.com/cyberjunky/python-garminconnect/issues/337) for current status.
- **[garth](https://github.com/matin/garth)** — Garmin SSO + OAuth token library. Also affected by the March 2026 Cloudflare changes. See [#217](https://github.com/matin/garth/issues/217).
- **[garminexport](https://github.com/petergardfjall/garminexport)** — export Garmin activities to files (GPX, TCX, FIT). Different goal (file export vs. webhook sync).
- **[Home Assistant Garmin Connect](https://www.home-assistant.io/integrations/garmin_connect/)** — HA integration, also affected by the auth changes.

## Requirements

- Linux (tested on Ubuntu 24.04, WSL2, Raspberry Pi OS Bookworm)
- Python 3.11+
- Google Chrome or Chromium
- xvfb
- Residential/home IP

## License

MIT
