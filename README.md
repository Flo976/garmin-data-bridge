# Garmin Playwright Sync

Sync your Garmin Connect health data by intercepting the web app's own API calls via Playwright.

## Why?

Since March 2026, Garmin hardened authentication via Cloudflare — Python libraries (`garminconnect`, `garth`) are blocked (429/403). Headless browsers are detected. Only a **real Chromium browser** from a **residential IP** works.

This tool uses Playwright with a real (non-headless) Chromium browser to:
1. Navigate Garmin Connect like a normal user
2. Intercept the HTTP responses that Garmin's own React app makes
3. Parse health metrics and POST them to your webhook endpoint

If Garmin changes their API endpoints, their own app adapts — and so do we.

## How it works

```
Chromium (xvfb, persistent context, residential IP)
  → Navigates connect.garmin.com
    → Garmin's JS loads data (GraphQL, REST)
      → Playwright intercepts HTTP responses
        → Parsed and POSTed to your webhook
```

## Data synced

**Daily summary:**
- Steps, calories, resting HR, VO2max
- Stress (average level)
- Body Battery (max/min)
- HRV (last night average)
- Sleep: score, total/deep/REM/light/awake minutes

**Activities:**
- Type, name, duration, distance
- HR (avg/max), calories, elevation gain
- Training effect (aerobic/anaerobic)
- VO2max update

## Setup

```bash
git clone https://github.com/your-user/garmin-playwright-sync.git
cd garmin-playwright-sync
./setup.sh
```

Edit `config.env`:
```env
GARMIN_EMAIL=your-email@example.com
GARMIN_PASSWORD=your-password
WEBHOOK_URL=https://your-server.com
WEBHOOK_API_KEY=your-api-key
```

Test:
```bash
./run.sh
```

## Webhook format

The tool POSTs JSON to two endpoints:

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

## Raspberry Pi

Works on **Pi 4** (2 GB+) and **Pi 5** with Raspberry Pi OS 64-bit. Uses system Chromium automatically when available at `/usr/bin/chromium-browser`.

## How it stays undetected

- **Not headless**: Uses `xvfb` (virtual display) so Chromium runs in headed mode without a physical screen
- **Persistent context**: Cookies and session data are saved to disk between runs — no re-login every time
- **Normal browsing pattern**: Visits 3 pages every 15 min — looks like a regular user
- **No API reverse-engineering**: We don't call Garmin APIs directly — we let their React app do it and intercept the responses

## License

MIT
