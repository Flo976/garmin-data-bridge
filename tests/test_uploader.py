from unittest.mock import MagicMock, patch

import pytest

from src.uploader import Uploader, UploadError


def _mock_response(status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def test_upload_daily_summary():
    with patch("src.uploader.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200)

        uploader = Uploader("https://my-server.com", "key123")
        data = {"date": "2026-03-28", "steps": 8000}
        uploader.upload_daily_summary(data)

        mock_post.assert_called_once_with(
            "https://my-server.com/ingest/daily-summary",
            json=data,
            headers={"Authorization": "Bearer key123"},
            timeout=30,
        )


def test_upload_activity():
    with patch("src.uploader.requests.post") as mock_post:
        mock_post.return_value = _mock_response(200)

        uploader = Uploader("https://my-server.com", "key123")
        data = {"garminActivityId": "123", "type": "running", "durationS": 3600, "date": "2026-03-28"}
        uploader.upload_activity(data)

        mock_post.assert_called_once_with(
            "https://my-server.com/ingest/activity",
            json=data,
            headers={"Authorization": "Bearer key123"},
            timeout=30,
        )


def test_upload_retries_on_failure():
    with patch("src.uploader.requests.post") as mock_post:
        mock_post.side_effect = [
            _mock_response(500),
            _mock_response(200),
        ]

        uploader = Uploader("https://my-server.com", "key123", max_retries=2)
        data = {"date": "2026-03-28", "steps": 100}
        uploader.upload_daily_summary(data)

        assert mock_post.call_count == 2


def test_upload_raises_after_exhausted_retries():
    with patch("src.uploader.requests.post") as mock_post:
        mock_post.side_effect = [
            _mock_response(500),
            _mock_response(500),
        ]

        uploader = Uploader("https://my-server.com", "key123", max_retries=2)
        data = {"date": "2026-03-28", "steps": 100}

        with pytest.raises(UploadError, match="Upload failed after 2 attempts"):
            uploader.upload_daily_summary(data)
