"""
config.py — loads DataTrust settings from configs/settings.yaml and secrets from .env.

Imports / uses: configs/settings.yaml, .env, PyYAML, python-dotenv
Used by: datatrust/collector/run_collect.py (and later every pipeline entry point)
"""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# The project's top folder (the one that holds README.md).
# __file__ is this file; parents[1] goes up two levels: datatrust/ -> project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_FILE = PROJECT_ROOT / "configs" / "settings.yaml"
ENV_FILE = PROJECT_ROOT / ".env"


# Reads settings.yaml and .env and returns everything as one dictionary.
# Inputs: settings_file — path to the YAML file (defaults to configs/settings.yaml).
# Returns: dict with "collect", "paths", "http" sections plus "hf_token" (text or None).
def load_settings(settings_file=SETTINGS_FILE):
    settings_file = Path(settings_file)
    if not settings_file.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_file}")

    with open(settings_file, encoding="utf-8") as file:
        settings = yaml.safe_load(file)

    # Copies values from .env into environment variables (does nothing if .env is missing).
    load_dotenv(ENV_FILE)

    # An empty HF_TOKEN= line counts as "no token".
    settings["hf_token"] = os.getenv("HF_TOKEN") or None

    max_from_env = os.getenv("MAX_DATASETS")
    if max_from_env:
        settings["collect"]["max_datasets"] = parse_positive_int(max_from_env, "MAX_DATASETS")

    return settings


# Turns text like "5000" into the number 5000, with a clear error if it is not valid.
# Inputs: text — the value to convert; name — setting name, used in the error message.
# Returns: a whole number greater than 0.
def parse_positive_int(text, name):
    try:
        number = int(text)
    except ValueError:
        raise ValueError(f"{name} must be a whole number, got: {text!r}") from None
    if number <= 0:
        raise ValueError(f"{name} must be greater than 0, got: {number}")
    return number


# Turns a relative path from settings (like "data/raw") into a full path in the project.
# Inputs: relative_path — text such as "data/raw".
# Returns: a pathlib.Path pointing inside the project folder.
def project_path(relative_path):
    return PROJECT_ROOT / relative_path
