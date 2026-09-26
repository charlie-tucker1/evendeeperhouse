"""Configuration loading for deephouse.

Single YAML file at the repo root (``deephouse.yaml``). Access is through
``load()`` which returns a ``Config`` object with attribute-style access and a
``root`` path so all relative paths resolve against the repo, not the CWD.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ENV_VAR = "DEEPHOUSE_CONFIG"


class _Node:
    """Read-only attribute access over a nested dict."""

    def __init__(self, data: dict[str, Any]):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str) -> Any:
        data = object.__getattribute__(self, "_data")
        if name not in data:
            raise AttributeError(f"config has no key {name!r}")
        val = data[name]
        return _Node(val) if isinstance(val, dict) else val

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(name)

    def get(self, name: str, default: Any = None) -> Any:
        return object.__getattribute__(self, "_data").get(name, default)

    def as_dict(self) -> dict[str, Any]:
        return dict(object.__getattribute__(self, "_data"))

    def __repr__(self) -> str:
        return f"_Node({object.__getattribute__(self, '_data')!r})"


@dataclass
class Config:
    root: Path
    raw: dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, name: str) -> Any:
        if name in ("root", "raw"):
            raise AttributeError(name)
        if name not in self.raw:
            raise AttributeError(f"config has no key {name!r}")
        val = self.raw[name]
        return _Node(val) if isinstance(val, dict) else val

    def path(self, key: str) -> Path:
        """Resolve a key under ``paths:`` against the repo root."""
        p = Path(self.raw["paths"][key])
        return p if p.is_absolute() else (self.root / p)


def find_config(start: Path | None = None) -> Path:
    """Locate deephouse.yaml: env var, then walk up from ``start`` (default CWD)."""
    env = os.environ.get(_ENV_VAR)
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        cfg = candidate / "deephouse.yaml"
        if cfg.exists():
            return cfg
    raise FileNotFoundError(
        "deephouse.yaml not found walking up from "
        f"{here}; set {_ENV_VAR} or run from inside the repo."
    )


def load(path: Path | None = None) -> Config:
    cfg_path = Path(path).resolve() if path else find_config()
    with cfg_path.open() as f:
        raw = yaml.safe_load(f) or {}
    return Config(root=cfg_path.parent, raw=raw)
