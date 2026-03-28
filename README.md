# Garmin Connect Sync

Automatically sync your Garmin Connect health data to any webhook endpoint. Runs on any Linux machine (laptop, Raspberry Pi) as a cron job.

```
Garmin watch → Garmin Connect → This tool → Your server
```

## What it syncs

| Category | Metrics |
|----------|---------|
| **Daily** | Steps, calories, resting HR, VO2max, stress, Body Battery, HRV |
| **Sleep** | Score, total/deep/REM/light/awake minutes |
| **Activities** | Type, name, duration, distance, HR avg/max, training effect |

All metrics are included, even Garmin-proprietary ones (Body Battery, Training Readiness) that aren't available via Health Connect or third-party APIs.

## How it works

Most Garmin libraries stopped working in March 2026 when Garmin added Cloudflare protection. This tool takes a different approach: it opens a **real Chrome browser**, navigates Garmin Connect like a normal user, and intercepts the data that Garmin's own app loads.

- No API reverse-engineering — if Garmin changes their endpoints, their app adapts, and so do we
- No headless browser — runs Chrome in headed mode via `xvfb` (virtual display), indistinguishable from a real user
- Persistent session — cookies are saved to disk, login happens only when the session expires
- Residential IP required — runs on your home machine, not a server

## Quick start

```bash
git clone https://github.com/Flo976/garmin-playwright-sync.git
cd garmin-playwright-sync
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
./run.sh                     # Sync today
./run.sh --dry-run            # Preview JSON output, don't upload
./run.sh --login-only         # Log in, save session, exit
./run.sh --date 2026-03-25    # Sync a specific date
./run.sh --range 7            # Backfill the last 7 days
./run.sh -v                   # Verbose logging
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
*/15 * * * * /path/to/garmin-playwright-sync/run.sh >> ~/.garmin-sync/logs/cron.log 2>&1
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

Works on **Pi 4** (2 GB+) and **Pi 5** with Raspberry Pi OS 64-bit (Bookworm). The tool automatically uses system Chromium when available at `/usr/bin/chromium-browser`.

## Troubleshooting

**Cloudflare "Just a moment" / CAPTCHA**
The tool handles Cloudflare Turnstile automatically via patchright. If it fails persistently, delete the browser profile and re-login:
```bash
rm -rf ~/.garmin-sync/browser-data
./run.sh --login-only
```

**"AN UNEXPECTED ERROR HAS OCCURRED"**
Garmin's SSO sometimes returns this transiently. The tool retries automatically (up to 2 attempts with 30s delay).

**Session expired**
The persistent browser context usually keeps sessions alive for days. When it expires, the tool re-logs in automatically. If it fails, run `--login-only` manually.

**Debug screenshots**
On any auth failure, screenshots are saved to `~/.garmin-sync/debug/`.

**Logs and state**
```bash
tail -50 ~/.garmin-sync/logs/sync.log       # Recent logs
cat ~/.garmin-sync/logs/sync_state.json      # Last sync per date
ls ~/.garmin-sync/debug/                     # Auth failure screenshots
```

## Requirements

- Linux (tested on Ubuntu 24.04 / WSL2, Raspberry Pi OS Bookworm)
- Python 3.11+
- Google Chrome or Chromium
- xvfb
- Residential IP (datacenter/cloud IPs are blocked by Garmin/Cloudflare)

## License

MIT
