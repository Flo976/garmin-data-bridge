import os
import pytest
from src.config import load_config


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "secret")
    monkeypatch.setenv("WEBHOOK_URL", "https://my-server.com")
    monkeypatch.setenv("WEBHOOK_API_KEY", "key123")

    cfg = load_config()

    assert cfg.garmin_email == "test@example.com"
    assert cfg.garmin_password == "secret"
    assert cfg.webhook_url == "https://my-server.com"
    assert cfg.webhook_api_key == "key123"


def test_load_config_defaults(monkeypatch):
    monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "secret")
    monkeypatch.setenv("WEBHOOK_URL", "https://my-server.com")
    monkeypatch.setenv("WEBHOOK_API_KEY", "key123")

    cfg = load_config()

    assert cfg.browser_data_dir.endswith("browser-data")
    assert cfg.log_dir.endswith("logs")


def test_load_config_missing_required(monkeypatch, tmp_path):
    monkeypatch.delenv("GARMIN_EMAIL", raising=False)
    monkeypatch.delenv("GARMIN_PASSWORD", raising=False)
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WEBHOOK_API_KEY", raising=False)

    # Use a non-existent env file to prevent dotenv from loading config.env
    with pytest.raises(ValueError, match="GARMIN_EMAIL"):
        load_config(env_file=str(tmp_path / "nonexistent.env"))
