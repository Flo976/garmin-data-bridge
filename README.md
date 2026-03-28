<p align="center">
  <img src="https://img.shields.io/badge/Garmin-Data%20Bridge-000000?style=for-the-badge&logo=garmin&logoColor=white" alt="Garmin Data Bridge" />
</p>

<p align="center">
  <b>Sync your Garmin Connect health data to any webhook — automatically, from a Raspberry Pi or any Linux machine.</b>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" /></a>
  <a href="https://www.raspberrypi.com/"><img src="https://img.shields.io/badge/Raspberry%20Pi-4%20%2F%205-C51A4A?style=flat-square&logo=raspberrypi&logoColor=white" /></a>
  <img src="https://img.shields.io/badge/platform-Linux-FCC624?style=flat-square&logo=linux&logoColor=black" />
  <img src="https://img.shields.io/badge/Cloudflare-bypassed-F38020?style=flat-square&logo=cloudflare&logoColor=white" />
  <a href="https://github.com/Flo976/garmin-data-bridge/actions/workflows/ci.yml"><img src="https://github.com/Flo976/garmin-data-bridge/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/Flo976/garmin-data-bridge/releases/latest"><img src="https://img.shields.io/github/v/release/Flo976/garmin-data-bridge?style=flat-square&label=release" alt="Release" /></a>
</p>

<p align="center">
  <code>Garmin watch</code> → <code>Garmin Connect</code> → <code>Garmin Data Bridge</code> → <code>Your server</code>
</p>

---

> 💡 **Coming from [python-garminconnect#337](https://github.com/cyberjunky/python-garminconnect/issues/337) or [garth#217](https://github.com/matin/garth/issues/217)?**
>
> Those libraries stopped working in March 2026 when Garmin added Cloudflare Turnstile protection. This tool takes a completely different approach — it doesn't call Garmin's API at all. Instead, it opens a real browser, lets Garmin's own React app load the data, and intercepts the responses. [Read more →](#-how-it-works)

---

## 📊 What it syncs

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  DAILY HEALTH    │  SLEEP           │  FITNESS           │  BODY            │
│──────────────────│──────────────────│────────────────────│──────────────────│
│  Steps           │  Sleep score     │  VO2max            │  Weight          │
│  Calories        │  Total minutes   │  Training          │  Body fat %      │
│  Resting HR      │  Deep sleep      │    Readiness       │  BMI             │
│  Stress avg      │  REM sleep       │  Training Status   │  Muscle mass     │
│  Body Battery    │  Light sleep     │  Endurance score   │  Bone mass       │
│  HRV             │  Awake time      │  Hill score        │  Body water %    │
│  Respiration     │                  │  Fitness age       │                  │
│  SpO2            │  ACTIVITIES      │  Race predictions  │  RECORDS         │
│  Intensity mins  │──────────────────│                    │──────────────────│
│  Floors climbed  │  Type & name     │                    │  Personal bests  │
│                  │  Duration        │                    │  (5K, 10K, etc.) │
│                  │  Distance        │                    │                  │
│                  │  HR avg / max    │                    │                  │
│                  │  Training effect │                    │                  │
│                  │  VO2max update   │                    │                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

All metrics included — even Garmin-proprietary ones (**Body Battery**, **Training Readiness**, **HRV**) that aren't available via Health Connect or third-party APIs.

## 🔧 How it works

Instead of calling Garmin's API directly (blocked by Cloudflare), this tool opens a **real Chrome browser** and lets Garmin's own app do the work:

```
┌──────────────────────────────────────────────────────┐
│  Chrome (xvfb + patchright, residential IP)          │
│                                                      │
│  1. Navigate to connect.garmin.com                   │
│  2. Garmin's React app loads health data             │
│  3. Patchright intercepts HTTP responses             │
│  4. Parse into clean JSON                            │
│  5. POST to your webhook                             │
└──────────────────────────────────────────────────────┘
```

| | Traditional libraries | Garmin Data Bridge |
|---|---|---|
| **Approach** | Call Garmin API directly | Let Garmin's app call its own API, intercept responses |
| **Cloudflare** | ❌ Blocked (429/403) | ✅ Bypassed via [patchright](https://github.com/AuroraWright/patchright) |
| **Headless** | ❌ Detected | ✅ Headed mode via `xvfb` (virtual display) |
| **API changes** | ❌ Breaks | ✅ Garmin's app adapts, we follow |
| **Session** | ❌ Tokens expire in ~2h | ✅ Persistent browser profile, days/weeks |

## 🚀 Quick start

```bash
git clone https://github.com/Flo976/garmin-data-bridge.git
cd garmin-data-bridge
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

```bash
./run.sh --login-only    # First run: save session
./run.sh --dry-run       # Preview data without uploading
./run.sh                 # Sync for real
```

## 📖 Usage

| Command | Description |
|---------|-------------|
| `./run.sh` | Sync today |
| `./run.sh --dry-run` | Preview JSON, don't upload |
| `./run.sh --login-only` | Log in, save session, exit |
| `./run.sh --date 2026-03-25` | Sync a specific date |
| `./run.sh --range 7` | Backfill the last 7 days |
| `./run.sh --force` | Re-sync even if already synced |
| `./run.sh -v` | Verbose / debug logging |

## ⏰ Scheduling

<details>
<summary><b>systemd</b> (recommended)</summary>

```bash
# setup.sh auto-generates garmin-sync.service.local with your user/path
sudo cp systemd/garmin-sync.service.local /etc/systemd/system/garmin-sync.service
sudo cp systemd/garmin-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now garmin-sync.timer
```
</details>

<details>
<summary><b>cron</b></summary>

```cron
*/15 * * * * /path/to/garmin-data-bridge/run.sh >> ~/.garmin-sync/logs/cron.log 2>&1
```
</details>

## 📡 Webhook format

JSON is POSTed with `Authorization: Bearer {API_KEY}` header.

<details>
<summary><b>POST /ingest/daily-summary</b></summary>

```json
{
  "date": "2026-03-28",
  "steps": 8432,
  "calories": 2150,
  "restingHr": 52,
  "floorsClimbed": 12,
  "stressAvg": 32,
  "bodyBattery": 85,
  "bodyBatteryMin": 38,
  "trainingReadiness": 62,
  "trainingStatus": "PRODUCTIVE",
  "trainingLoad7d": 524.5,
  "hrvGarmin": 42.0,
  "hrvWeeklyAvg": 45.0,
  "hrvBaseline": 35.0,
  "respirationAvgWaking": 16.0,
  "respirationAvgSleep": 14.5,
  "respirationMin": 12.0,
  "respirationMax": 22.0,
  "spo2Avg": 96.0,
  "spo2Min": 92.0,
  "spo2Latest": 97.0,
  "intensityMinModerate": 15,
  "intensityMinVigorous": 10,
  "intensityMinWeeklyTotal": 135,
  "sleepScore": 81,
  "sleepTotalMin": 450,
  "sleepDeepMin": 90,
  "sleepRemMin": 90,
  "sleepLightMin": 240,
  "sleepAwakeMin": 30,
  "vo2max": 52.0,
  "enduranceScore": 72.0,
  "hillScore": 58.0,
  "fitnessAge": 28,
  "racePrediction5k": 1380.0,
  "racePrediction10k": 2940.0,
  "racePredictionHalf": 6600.0,
  "racePredictionMarathon": 14100.0
}
```

All fields are nullable — only fields with available data are non-null.
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

<details>
<summary><b>POST /ingest/body-composition</b></summary>

```json
{
  "weightKg": 75.4,
  "bodyFatPct": 18.5,
  "bmi": 23.8,
  "muscleMassKg": 34.2,
  "boneMassKg": 3.2,
  "bodyWaterPct": 55.2
}
```
</details>

<details>
<summary><b>POST /ingest/personal-records</b></summary>

```json
{
  "records": [
    {"type": "pr_fastest_5k", "value": 1380.0, "date": "2026-02-15 08:00:00", "activityId": 123},
    {"type": "pr_longest_run", "value": 21100.0, "date": "2026-01-10 07:00:00", "activityId": 456}
  ]
}
```
</details>

## 🍓 Raspberry Pi

Works on **Pi 4** (2 GB+) and **Pi 5** with Raspberry Pi OS 64-bit. System Chromium is auto-detected at `/usr/bin/chromium-browser`.

Memory: ~300-400 MB during sync. Power: ~3W idle. Set it up, plug it in, forget about it.

## 🔍 Troubleshooting

<details>
<summary><b>Cloudflare CAPTCHA / "Just a moment..."</b></summary>

Patchright handles Turnstile automatically. If it fails, reset the browser profile:
```bash
rm -rf ~/.garmin-sync/browser-data
./run.sh --login-only
```
</details>

<details>
<summary><b>MFA / Two-factor auth</b></summary>

Not currently supported. Disable MFA on your Garmin account, or use a secondary account without it.
</details>

<details>
<summary><b>xvfb errors</b></summary>

```bash
sudo apt-get install -y xvfb
```
On desktop Linux with a real display, skip xvfb: `python3 -m src.sync --dry-run`
</details>

<details>
<summary><b>429 Too Many Requests</b></summary>

This tool shouldn't trigger 429 (it doesn't call the API directly). If you see it, reduce sync frequency. Default 15-min interval is safe. Don't run multiple instances.
</details>

<details>
<summary><b>"AN UNEXPECTED ERROR HAS OCCURRED"</b></summary>

Garmin SSO returns this intermittently. The tool retries (2 attempts, 30s delay). If persistent, wait a few hours.
</details>

<details>
<summary><b>Debug info</b></summary>

```bash
ls ~/.garmin-sync/debug/                      # Auth failure screenshots
tail -50 ~/.garmin-sync/logs/sync.log         # Recent logs
cat ~/.garmin-sync/logs/sync_state.json       # Last sync per date
```
</details>

## ⚠️ Limitations

| Limitation | Details |
|------------|---------|
| **Linux only** | Requires `xvfb`. macOS/Windows not yet supported |
| **Residential IP** | Cloudflare blocks datacenter/cloud IPs |
| **No MFA** | Accounts with 2FA cannot be used |
| **Not real-time** | Page navigation approach; ~10 min minimum interval |
| **Single account** | One `config.env` per instance |
| **Browser footprint** | Needs full Chrome (~300 MB) |

## 🤝 Contributing

PRs welcome! Some ideas:

| Area | Description |
|------|-------------|
| 🍎 **macOS support** | Adapt or replace xvfb for macOS |
| 🐳 **Docker image** | Chrome + xvfb in a container |
| ⚖️ **Body composition** | Weight, body fat %, muscle mass |
| 👥 **Multi-account** | Config-driven multiple Garmin accounts |
| 🔔 **Failure alerts** | Slack / Discord / email on repeated failures |
| 📈 **Prometheus exporter** | Expose metrics for Grafana dashboards |

## 🔗 Related projects

| Project | Status (March 2026) |
|---------|-------------------|
| [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) | ⚠️ Blocked by Cloudflare — see [#337](https://github.com/cyberjunky/python-garminconnect/issues/337) |
| [garth](https://github.com/matin/garth) | ⚠️ Blocked by Cloudflare — see [#217](https://github.com/matin/garth/issues/217) |
| [garminexport](https://github.com/petergardfjall/garminexport) | Different goal (file export, not webhook sync) |
| [HA Garmin Connect](https://www.home-assistant.io/integrations/garmin_connect/) | ⚠️ Also affected by auth changes |

## 📋 Requirements

- Linux (Ubuntu 24.04 / WSL2 / Raspberry Pi OS Bookworm)
- Python 3.11+
- Google Chrome or Chromium
- xvfb
- Residential / home IP

## License

[MIT](LICENSE)
