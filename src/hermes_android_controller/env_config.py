"""Local environment configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path


def load_local_env(path: str | Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from a local .env without overriding env vars."""

    env_path = _resolve_env_path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def env_value(name: str, default: str = "", *, env_path: str | Path | None = None) -> str:
    load_local_env(env_path)
    return os.getenv(name, default).strip()


def require_env_value(name: str, *, env_path: str | Path | None = None) -> str:
    value = env_value(name, env_path=env_path)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}.")
    return value


def _resolve_env_path(path: str | Path | None) -> Path:
    if path:
        return Path(path)
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env
    return Path(__file__).resolve().parents[2] / ".env"
