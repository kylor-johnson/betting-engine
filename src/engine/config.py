"""Paths, settings and secrets. Secrets are read from .env and never printed."""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.nosync"
LOGS = ROOT / "logs.nosync"
DB = DATA / "engine.duckdb"
ENV_FILE = ROOT / ".env"


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def unit_for(cfg: dict, sport: str | None) -> float:
    """Dollars per unit for a sport (`units_by_sport`, Kylor 2026-11-23: NFL $50, NBA $25), else the default `unit`."""
    return float(((cfg.get("units_by_sport") or {}).get(sport)) or cfg.get("unit", 25))


def units_text(units: float, dollars: float) -> str:
    """Units first, dollars after (decision 0036): "½ unit ($12.50)", "1 unit ($50)", "0 units ($0)"."""
    u = float(units or 0)
    word = "½ unit" if abs(u - 0.5) < 1e-9 else "1 unit" if abs(u - 1) < 1e-9 else f"{u:g} units"
    d = float(dollars or 0)
    return f"{word} (${d:,.2f})" if d and d != int(d) else f"{word} (${d:,.0f})"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    for k in ("WAGERHOUSE_USER", "WAGERHOUSE_PASSWORD", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ODDS_API_KEY", "CFBD_API_KEY"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def set_env_value(key: str, value: str) -> None:
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    out, done = [], False
    for line in lines:
        if line.startswith(key + "="):
            out.append(f"{key}={value}")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(out) + "\n")
    ENV_FILE.chmod(0o600)


def display_tz(cfg: dict | None = None) -> ZoneInfo:
    return ZoneInfo((cfg or load_config())["timezone_display"])
