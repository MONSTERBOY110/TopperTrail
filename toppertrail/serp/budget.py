from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from toppertrail.serp.base import SerpError


class BudgetExceeded(SerpError):
    pass


class Budget:
    def __init__(self, cap: int, spent: int = 0) -> None:
        self.cap = cap
        self.spent = spent

    @property
    def remaining(self) -> int:
        return max(self.cap - self.spent, 0)

    def ensure_available(self) -> None:
        if self.spent + 1 > self.cap:
            raise BudgetExceeded(f"credit cap of {self.cap} reached; nothing more will be spent")

    def charge(self) -> None:
        self.spent += 1


def append_spend(path: Path, engine: str, phash: str, search_id: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "engine": engine,
        "params_hash": phash,
        "search_id": search_id,
    }
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row) + "\n")


def spend_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
