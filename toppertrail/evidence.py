from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from toppertrail.hashing import canonical_json, sha256_text


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    key: str
    sha256: str
    meta: dict = field(default_factory=dict, hash=False)


class EvidenceStore:
    """Content-addressed JSON store: the file name is the SHA-256 of its canonical JSON."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, sha: str) -> Path:
        return self.root / sha[:2] / f"{sha}.json"

    def put(self, obj: Any) -> str:
        text = canonical_json(obj)
        sha = sha256_text(text)
        path = self._path(sha)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        return sha

    def get(self, sha: str) -> Any:
        return json.loads(self._path(sha).read_text(encoding="utf-8"))

    def is_intact(self, sha: str) -> bool:
        path = self._path(sha)
        return path.exists() and sha256_text(path.read_text(encoding="utf-8")) == sha


@dataclass
class Run:
    exam_id: str
    artifacts: list[ArtifactRef] = field(default_factory=list)

    def add(self, ref: ArtifactRef) -> None:
        self.artifacts.append(ref)

    def of_kind(self, kind: str) -> list[ArtifactRef]:
        return [a for a in self.artifacts if a.kind == kind]

    def manifest_root(self) -> str:
        lines = sorted(f"{a.kind}|{a.key}|{a.sha256}" for a in self.artifacts)
        return sha256_text("\n".join(lines))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = {"exam_id": self.exam_id, "artifacts": [asdict(a) for a in self.artifacts]}
        path.write_text(
            json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
        )

    @classmethod
    def load(cls, path: Path) -> Run:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return cls(doc["exam_id"], [ArtifactRef(**a) for a in doc["artifacts"]])


def damaged(run: Run, store: EvidenceStore) -> list[str]:
    return [a.sha256 for a in run.artifacts if not store.is_intact(a.sha256)]
