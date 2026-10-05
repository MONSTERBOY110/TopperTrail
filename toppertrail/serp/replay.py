from __future__ import annotations

import json
from pathlib import Path

from toppertrail.serp.base import MissingFixture, SerpResult, canonical_params, params_hash


def fixture_path(root: Path, engine: str, params: dict) -> Path:
    return Path(root) / "serp" / engine / f"{params_hash(engine, params)}.json"


class ReplaySerpClient:
    """Serves recorded responses. Has no network capability by construction."""

    def __init__(self, fixtures: Path) -> None:
        self.fixtures = Path(fixtures)

    def search(self, engine: str, params: dict) -> SerpResult:
        path = fixture_path(self.fixtures, engine, params)
        if not path.exists():
            raise MissingFixture(
                f"no recorded response for {canonical_params(engine, params)}"
            )
        doc = json.loads(path.read_text(encoding="utf-8"))
        return SerpResult(engine, canonical_params(engine, params), doc["response"], "replay")
