from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

_TRUE = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    replay: bool
    home: Path
    fixtures: Path
    budget_cap: int


def load_settings(env: Mapping[str, str] | None = None, cwd: Path | None = None) -> Settings:
    cwd = Path(cwd or Path.cwd())
    from_file = {k: v for k, v in dotenv_values(cwd / ".env").items() if v is not None}
    merged = {**from_file, **dict(os.environ if env is None else env)}
    key = (merged.get("SERPAPI_API_KEY") or "").strip() or None
    return Settings(
        api_key=key,
        replay=merged.get("TOPPERTRAIL_REPLAY", "").strip().lower() in _TRUE,
        home=Path(merged.get("TOPPERTRAIL_HOME") or cwd / ".toppertrail"),
        fixtures=Path(merged.get("TOPPERTRAIL_FIXTURES") or cwd / "fixtures"),
        budget_cap=int(merged.get("TOPPERTRAIL_BUDGET") or 230),
    )
