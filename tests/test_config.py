import os
import tempfile

import pytest

from config.settings import ConfigError, load_config


def test_config_defaults(monkeypatch):
    # Setup standard environment mock
    monkeypatch.setenv("API_ID", "99999")
    monkeypatch.setenv("API_HASH", "1234567890abcdef1234567890abcdef")

    # Write a minimal config.ini to avoid ConfigError: No forwarding jobs defined
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
        f.write("[General]\n")
        f.write("[MyForward]\n")
        f.write("from = @src\n")
        f.write("to = @dst\n")
        temp_ini_path = f.name

    try:
        config = load_config(temp_ini_path)

        # Check defaults
        assert config.api_id == 99999
        assert config.api_hash == "1234567890abcdef1234567890abcdef"
        assert config.download_dir == "downloads"
        assert config.log_level == "INFO"
        assert config.keep_downloads is False
        assert config.max_retries == 3
        assert config.upload_delay == 3.0
        assert config.flood_wait_limit == 300

        # Check loaded jobs
        assert len(config.jobs) == 1
        assert config.jobs[0].name == "MyForward"
        assert config.jobs[0].from_chat == "@src"
        assert config.jobs[0].to_chat == "@dst"
        assert config.jobs[0].initial_offset == 0
    finally:
        os.remove(temp_ini_path)


def test_config_validation_failures(monkeypatch):
    # No API_ID/API_HASH
    monkeypatch.delenv("API_ID", raising=False)
    monkeypatch.delenv("API_HASH", raising=False)

    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as f:
        f.write("[General]\n")
        f.write("[Job]\n")
        f.write("from = @src\n")
        f.write("to = @dst\n")
        temp_ini_path = f.name

    try:
        # Should raise ConfigError because API_ID/API_HASH are not set
        with pytest.raises(ConfigError) as excinfo:
            load_config(temp_ini_path)
        assert "API_ID is required" in str(excinfo.value)

        # Bad API Hash length
        monkeypatch.setenv("API_ID", "123")
        monkeypatch.setenv("API_HASH", "short")
        with pytest.raises(ConfigError) as excinfo:
            load_config(temp_ini_path)
        assert "API_HASH must be exactly 32 characters long" in str(excinfo.value)
    finally:
        os.remove(temp_ini_path)
