# Garmin Playwright Sync

Sync your Garmin Connect health data by intercepting the web app's own API calls via a real browser.

## Why?

Since March 2026, Garmin hardened authentication via Cloudflare — Python libraries (`garminconnect`, `garth`) are blocked (429/403). Headless browsers are detected. Only a **real Chrome browser** from a **residential IP** works.

This tool uses [patchright](https://github.com/AuroraWright/patchright) (undetected Playwright fork) with a real Chrome browser to:
1. Navigate Garmin Connect like a normal user
2. Intercept the HTTP responses that Garmin's own React app makes
3. Parse health metrics and POST them to your webhook endpoint

If Garmin changes their API endpoints, their own app adapts — and so do we.

## How it works

```
Chrome (xvfb, persistent context, residential IP)
  → Navigates connect.garmin.com
    → Garmin's JS loads data (GraphQL, REST)
      → Patchright intercepts HTTP responses
        → Parsed and POSTed to your webhook
```

## Data synced

**Daily summary:** steps, calories, resting HR, VO2max, stress, Body Battery, HRV, sleep (score + phases)

**Activities:** type, name, duration, distance, HR, calories, training effect, VO2max update

## Setup

```bash
git clone https://github.com/Flo976/garmin-playwright-sync.git
cd garmin-playwright-sync
chmod +x setup.sh run.sh
./setup.sh
```

Edit `config.env`:
```env
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-password
WEBHOOK_URL=https://your-server.com
WEBHOOK_API_KEY=your-api-key
```

## Usage

```bash
# First run — log in and save session
./run.sh --login-only

# Sync today (preview without uploading)
./run.sh --dry-run

# Sync today (upload to webhook)
./run.sh

# Sync a specific date
./run.sh --date 2026-03-25

# Backfill the last 7 days
./run.sh --range 7

# Verbose logging
./run.sh -v --dry-run
```

## Scheduling

### Systemd (recommended)

```bash
sudo cp systemd/garmin-sync.* /etc/systemd/system/
# Edit paths in .service if needed
sudo systemctl daemon-reload
sudo systemctl enable --now garmin-sync.timer
```

### Cron

```cron
*/15 * * * * /home/you/garmin-playwright-sync/run.sh >> ~/.garmin-sync/logs/cron.log 2>&1
```

## Webhook format

**POST `{WEBHOOK_URL}/ingest/daily-summary`**
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
  "vo2max": null
}
```

**POST `{WEBHOOK_URL}/ingest/activity`**
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

Both include `Authorization: Bearer {WEBHOOK_API_KEY}` header.

## Raspberry Pi

Works on **Pi 4** (2 GB+) and **Pi 5** with Raspberry Pi OS 64-bit. Uses system Chromium automatically when available at `/usr/bin/chromium-browser`.

## Debugging

On auth failure, screenshots are saved to `~/.garmin-sync/debug/`. Sync state is tracked in `~/.garmin-sync/logs/sync_state.json`.

```bash
# Check sync state
cat ~/.garmin-sync/logs/sync_state.json

# Check logs
tail -50 ~/.garmin-sync/logs/sync.log

# View debug screenshots
ls ~/.garmin-sync/debug/
```

## How it bypasses Cloudflare

- **patchright** instead of vanilla Playwright — removes automation fingerprints that Cloudflare Turnstile detects
- **Not headless**: `xvfb` (virtual display) runs Chrome in headed mode without a physical screen
- **Persistent context**: cookies and Cloudflare clearance tokens saved to disk between runs
- **Normal browsing pattern**: visits 3 pages per sync — looks like a regular user

## License

MIT
