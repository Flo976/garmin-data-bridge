import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    garmin_email: str
    garmin_password: str
    webhook_url: str
    webhook_api_key: str
    browser_data_dir: str
    log_dir: str


def load_config(env_file: str | None = None) -> Config:
    """Load configuration from environment variables (and optional .env file)."""
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv("config.env", override=False)

    required = ["GARMIN_EMAIL", "GARMIN_PASSWORD", "WEBHOOK_URL", "WEBHOOK_API_KEY"]
    for var in required:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")

    home = Path.home()
    return Config(
        garmin_email=os.environ["GARMIN_EMAIL"],
        garmin_password=os.environ["GARMIN_PASSWORD"],
        webhook_url=os.environ["WEBHOOK_URL"].rstrip("/"),
        webhook_api_key=os.environ["WEBHOOK_API_KEY"],
        browser_data_dir=os.getenv(
            "BROWSER_DATA_DIR", str(home / ".garmin-sync" / "browser-data")
        ),
        log_dir=os.getenv("LOG_DIR", str(home / ".garmin-sync" / "logs")),
    )
