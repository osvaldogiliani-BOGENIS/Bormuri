"""Caricamento di config/bormuri.yaml con accesso a punti (cfg.audio.sample_rate)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "config" / "bormuri.yaml"


class Section(dict):
    """Dizionario leggibile anche come attributi."""

    def __getattr__(self, name: str) -> Any:
        try:
            value = self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc
        return Section(value) if isinstance(value, dict) else value


def load(path: str | Path | None = None) -> Section:
    with open(path or DEFAULT_PATH, encoding="utf-8") as f:
        return Section(yaml.safe_load(f))


def resolve(relative: str) -> Path:
    """Percorsi nel config (modelli, persona) sono relativi alla radice del repo."""
    p = Path(relative)
    return p if p.is_absolute() else ROOT / p
