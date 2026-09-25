"""Load project settings from config/settings.yaml and secrets from .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class Settings:
    raw: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def path(self, name: str) -> Path:
        """Absolute path for a key under `paths:` in settings.yaml."""
        return PROJECT_ROOT / self.raw["paths"][name]


def load_settings(path: Path = DEFAULT_CONFIG) -> Settings:
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:  # python-dotenv is optional
        pass
    with open(path, encoding="utf-8") as f:
        return Settings(yaml.safe_load(f))


def get_secret(name: str) -> str | None:
    """Read a secret from the environment. Returns None if unset or empty."""
    value = os.environ.get(name, "").strip()
    return value or None
