"""Upload parsed Garmin data to a configurable webhook endpoint."""

from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)


class Uploader:
    def __init__(self, webhook_url: str, api_key: str, max_retries: int = 3):
        self.webhook_url = webhook_url
        self.api_key = api_key
        self.max_retries = max_retries

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _post(self, path: str, data: dict) -> None:
        url = f"{self.webhook_url}{path}"
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(url, json=data, headers=self._headers(), timeout=30)
                resp.raise_for_status()
                logger.info("Upload OK: %s", path)
                return
            except Exception as e:
                logger.warning("Upload attempt %d/%d failed for %s: %s", attempt, self.max_retries, path, e)
                if attempt < self.max_retries:
                    time.sleep(2 * attempt)
        logger.error("Upload failed after %d attempts: %s", self.max_retries, path)

    def upload_daily_summary(self, data: dict) -> None:
        self._post("/ingest/daily-summary", data)

    def upload_activity(self, data: dict) -> None:
        self._post("/ingest/activity", data)
