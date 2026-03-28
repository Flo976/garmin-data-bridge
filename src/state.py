"""Track sync state to avoid re-uploading and enable backfill."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SyncState:
    """Simple file-based state tracker."""

    def __init__(self, state_dir: str):
        self._path = Path(state_dir) / "sync_state.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def mark_synced(self, date_str: str) -> None:
        """Record a successful sync for a given date."""
        self._data[date_str] = {
            "synced_at": datetime.now().isoformat(),
        }
        self._save()
        logger.debug("State: marked %s as synced", date_str)

    def last_synced(self) -> str | None:
        """Return the most recent synced date, or None."""
        if not self._data:
            return None
        return max(self._data.keys())

    def is_synced(self, date_str: str) -> bool:
        """Check if a date has already been synced."""
        return date_str in self._data
