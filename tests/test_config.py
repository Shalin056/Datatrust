"""
test_config.py — checks that settings load correctly and bad values give clear errors.

Imports / uses: datatrust/config.py
Used by: pytest
"""

import pytest

from datatrust.config import load_settings, parse_positive_int


def test_settings_file_loads():
    settings = load_settings()
    assert settings["collect"]["page_size"] == 1000
    assert "hf_token" in settings


def test_env_overrides_max_datasets(monkeypatch):
    monkeypatch.setenv("MAX_DATASETS", "42")
    assert load_settings()["collect"]["max_datasets"] == 42


def test_missing_settings_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "missing.yaml")


def test_parse_positive_int_rejects_bad_values():
    assert parse_positive_int("10", "X") == 10
    with pytest.raises(ValueError):
        parse_positive_int("ten", "X")
    with pytest.raises(ValueError):
        parse_positive_int("0", "X")
