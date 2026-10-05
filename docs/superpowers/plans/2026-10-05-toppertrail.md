# TopperTrail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build TopperTrail, a Python CLI and local dashboard that collects public "our topper" claims by Indian coaching institutes through SerpApi, checks each claim with deterministic rules grounded in CCPA's 2024 coaching guidelines and orders, and publishes an evidence ledger that judges can replay with no API key.

**Architecture:** A collection stage (SerpApi through a live or replay client, page snapshots, optional OCR) writes content-addressed evidence plus a run manifest. A pure analysis stage turns that evidence into claims, self-reports, AI-answer records and rule flags, producing a canonical JSON ledger whose hash is stable. A FastAPI + Jinja2 dashboard and a static exporter render the ledger.

**Tech Stack:** Python 3.11, `serpapi` (official SDK), httpx, selectolax, rapidfuzz, PyYAML, Typer, FastAPI, Jinja2, uvicorn, python-dotenv, optional `rapidocr-onnxruntime`; pytest and ruff for quality.

**Spec:** `docs/superpowers/specs/2026-10-05-toppertrail-design.md`

## Global Constraints

- Python `>=3.11`. Development venv is created with `py -3.11 -m venv .venv` at `D:\Projects\TopperTrail\.venv`. All commands below run from `D:\Projects\TopperTrail` in Git Bash and use `.venv/Scripts/python`.
- No LLM anywhere in the code path. No model API keys are read.
- **Claude never runs `git commit` or `git push`.** Every task ends with an "Owner checkpoint" step that lists the files and a suggested commit message; the owner commits.
- All file I/O is UTF-8 with `newline="\n"` on writes. CLI output must not crash on a cp1252 Windows console.
- The SerpApi key is read only from the environment or `.env`; it is never printed, logged, stored in evidence, or written to fixtures.
- Total SerpApi spend for the recorded demo run is at most 230 credits; `collect` must refuse to start when the estimate exceeds the cap or the account's remaining searches.
- Flag titles and details never use the words "false", "fake", "fraud", "lie" or "misleading". They describe disclosure: "not stated", "differs", "not mentioned".
- Claims are counted only from sources an institute controls: a registered domain, a registered YouTube channel, or that institute's own Google ads. Third-party news pages are not claims.
- House style for docs and UI copy: no em dashes or en dashes.
- Exam ids: `upsc-cse-2025`, `jee-adv-2026`, `neet-ug-2026`.
- Working directory for runtime state: `.toppertrail/` (gitignored). Committed replay data: `fixtures/`.

## Review Focus

1. An institute page whose navigation menu lists every course ("GS Foundation", "Test Series", "IGP") near a topper block that names no course must still get TT-01 "Course not stated". Pinned in Task 9 (block extraction drops menus) and Task 10 (claim window ignores far blocks).
2. A sponsor read at the start of an independent interview ("10 out of top 10 are from various courses of Vajiram & Ravi") must not become a self-report by the topper. Pinned in Task 11 (first-person requirement).
3. A SerpApi HTTP error whose message contains the request URL with `api_key=` must not leak the key in the raised error text or its chained traceback. Pinned in Task 4.
4. A replay run with a missing fixture must never call the network, must record the gap as a `missing` artifact, must continue, and must report the missing count. Pinned in Task 13.
5. Names with dotted initials ("A.R. Rajah Mohaideen"), printed misspellings ("Pakshal Secretry" vs "Secretary"), single-token names ("Hemant", "Ruhani") and cross-exam collisions ("Shubham Kumar" is JEE Advanced 2026 CRL 1 and UPSC CSE 2020 AIR 1) must be matched or rejected correctly. Pinned in Task 6 and Task 10.

---

## File structure

```
pyproject.toml, .gitignore, .env.example, LICENSE, README.md
toppertrail/
  __init__.py, __main__.py, cli.py, config.py, hashing.py, models.py, data.py, evidence.py,
  collect.py, analyze.py, report.py, rules.py
  serp/__init__.py, serp/base.py, serp/replay.py, serp/live.py, serp/budget.py
  fetch/__init__.py, fetch/pages.py, fetch/images.py
  extract/__init__.py, extract/text.py, extract/courses.py, extract/claims.py,
  extract/selfreport.py, extract/aianswer.py
  web/__init__.py, web/app.py, web/render.py, web/export.py, web/templates/*.html, web/static/style.css
  data/exams.yaml, data/institutes.yaml, data/independent_channels.yaml, data/lexicon.yaml,
  data/results/upsc-cse-2025.csv, data/results/jee-adv-2026.csv, data/results/neet-ug-2026.csv,
  data/ccpa/orders.yaml, data/ccpa/guidelines-2024.md
scripts/spike.py, scripts/build_orders.py
tests/ (one test module per source module)
fixtures/ (recorded, trimmed, scrubbed evidence for replay), fixtures/manifests/<exam>.json
docs/ (spec, plan, VALIDATION.md, METHODOLOGY.md, DEMO-SCRIPT.md, SUBMISSION.md, notes/spike.md)
.github/workflows/ci.yml
```

---

### Task 1: Project scaffold, settings, hashing, CLI shell

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`, `LICENSE`, `README.md`
- Create: `toppertrail/__init__.py`, `toppertrail/__main__.py`, `toppertrail/cli.py`, `toppertrail/config.py`, `toppertrail/hashing.py`
- Test: `tests/test_config.py`, `tests/test_hashing.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `Settings(api_key: str | None, replay: bool, home: Path, fixtures: Path, budget_cap: int)`; `load_settings(env: Mapping[str, str] | None = None, cwd: Path | None = None) -> Settings`; `sha256_bytes(b) -> str`, `sha256_text(s) -> str`, `canonical_json(obj) -> str`, `short_hash(s, n=16) -> str`; Typer `app` with a `version` command; `_utf8_stdio()`.

- [ ] **Step 1: Write packaging and repo files**

`pyproject.toml`:
```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "toppertrail"
version = "0.1.0"
description = "Evidence ledger of coaching institutes' topper claims, built on SerpApi"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
  "serpapi>=1.1,<2",
  "httpx>=0.27",
  "typer>=0.12",
  "fastapi>=0.115",
  "uvicorn>=0.30",
  "jinja2>=3.1",
  "pyyaml>=6.0",
  "selectolax>=0.3.21",
  "rapidfuzz>=3.9",
  "python-dotenv>=1.0",
]

[project.optional-dependencies]
ocr = ["rapidocr-onnxruntime>=1.3"]
dev = ["pytest>=8", "ruff>=0.6"]

[project.scripts]
toppertrail = "toppertrail.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["toppertrail"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.toppertrail/
.env
site/
dist/
build/
*.egg-info/
```

`.env.example`:
```
SERPAPI_API_KEY=
# TOPPERTRAIL_REPLAY=1
# TOPPERTRAIL_BUDGET=230
```

`LICENSE`: the standard MIT text with the line `Copyright (c) 2026 TopperTrail contributors`.

`README.md` (replaced in Task 17):
```markdown
# TopperTrail

One rank. Many claims. Follow the trail.

Work in progress for the SerpApi India Hackathon 2026.
```

- [ ] **Step 2: Write the failing tests**

`tests/test_hashing.py`:
```python
from toppertrail.hashing import canonical_json, sha256_text, short_hash


def test_canonical_json_is_order_independent_and_keeps_unicode():
    a = canonical_json({"b": 1, "a": "अनुज"})
    b = canonical_json({"a": "अनुज", "b": 1})
    assert a == b == '{"a":"अनुज","b":1}'


def test_hashes_are_stable():
    assert sha256_text("x") == "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"
    assert short_hash("x") == "2d711642b726b044"
```

`tests/test_config.py`:
```python
from pathlib import Path

from toppertrail.config import load_settings


def test_env_overrides_dotenv(tmp_path: Path):
    (tmp_path / ".env").write_text("SERPAPI_API_KEY=fromfile\nTOPPERTRAIL_BUDGET=50\n", encoding="utf-8")
    s = load_settings(env={"SERPAPI_API_KEY": "fromenv"}, cwd=tmp_path)
    assert s.api_key == "fromenv"
    assert s.budget_cap == 50
    assert s.replay is False
    assert s.home == tmp_path / ".toppertrail"
    assert s.fixtures == tmp_path / "fixtures"


def test_replay_flag_and_missing_key(tmp_path: Path):
    s = load_settings(env={"TOPPERTRAIL_REPLAY": "1"}, cwd=tmp_path)
    assert s.replay is True
    assert s.api_key is None
    assert s.budget_cap == 230
```

`tests/test_cli.py`:
```python
import io
import sys

from typer.testing import CliRunner

from toppertrail.cli import _utf8_stdio, app


def test_version():
    r = CliRunner().invoke(app, ["version"])
    assert r.exit_code == 0
    assert "toppertrail 0.1.0" in r.output


def test_utf8_stdio_survives_cp1252_console(monkeypatch):
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stream)
    _utf8_stdio()
    print("अनुज अग्निहोत्री")
    stream.flush()
    assert "अनुज".encode() in raw.getvalue()
```

- [ ] **Step 3: Create the venv and run tests to verify they fail**

Run:
```bash
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```
Expected: the install fails or tests fail with `ModuleNotFoundError: No module named 'toppertrail'` (package files do not exist yet).

- [ ] **Step 4: Write the implementation**

`toppertrail/__init__.py`:
```python
__version__ = "0.1.0"
```

`toppertrail/__main__.py`:
```python
from toppertrail.cli import app

app()
```

`toppertrail/hashing.py`:
```python
from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def short_hash(text: str, n: int = 16) -> str:
    return sha256_text(text)[:n]
```

`toppertrail/config.py`:
```python
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
```

`toppertrail/cli.py`:
```python
from __future__ import annotations

import sys

import typer

from toppertrail import __version__

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="TopperTrail: one rank, many claims. Follow the trail.",
)


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


@app.callback()
def _main() -> None:
    _utf8_stdio()


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(f"toppertrail {__version__}")
```

- [ ] **Step 5: Install and run tests to verify they pass**

Run:
```bash
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check .
```
Expected: `5 passed`; ruff reports no errors.

- [ ] **Step 6: Owner checkpoint**

Files: `pyproject.toml .gitignore .env.example LICENSE README.md toppertrail/ tests/`. Suggested message: `chore: scaffold toppertrail package, settings and CLI shell`.

---

### Task 2: Evidence store and run manifest

**Files:**
- Create: `toppertrail/evidence.py`
- Test: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `canonical_json`, `sha256_text` (Task 1).
- Produces: `ArtifactRef(kind: str, key: str, sha256: str, meta: dict)`; `EvidenceStore(root: Path)` with `put(obj) -> str`, `get(sha) -> Any`, `is_intact(sha) -> bool`; `Run(exam_id: str, artifacts: list[ArtifactRef])` with `add`, `of_kind(kind)`, `manifest_root() -> str`, `save(path)`, `Run.load(path)`; `damaged(run, store) -> list[str]`.

- [ ] **Step 1: Write the failing test**

`tests/test_evidence.py`:
```python
from pathlib import Path

from toppertrail.evidence import ArtifactRef, EvidenceStore, Run, damaged


def test_put_get_roundtrip_and_dedupe(tmp_path: Path):
    store = EvidenceStore(tmp_path)
    a = store.put({"x": "अनुज", "n": 1})
    b = store.put({"n": 1, "x": "अनुज"})
    assert a == b
    assert store.get(a) == {"x": "अनुज", "n": 1}
    assert store.is_intact(a)


def test_manifest_root_is_order_independent(tmp_path: Path):
    r1 = Run("upsc-cse-2025", [ArtifactRef("serp", "k1", "aa"), ArtifactRef("page", "k2", "bb")])
    r2 = Run("upsc-cse-2025", [ArtifactRef("page", "k2", "bb"), ArtifactRef("serp", "k1", "aa")])
    assert r1.manifest_root() == r2.manifest_root()


def test_save_load_and_tamper_detection(tmp_path: Path):
    store = EvidenceStore(tmp_path / "ev")
    sha = store.put({"a": 1})
    run = Run("upsc-cse-2025")
    run.add(ArtifactRef("serp", "google_en:1", sha, {"rank": 1}))
    run.save(tmp_path / "run.json")
    loaded = Run.load(tmp_path / "run.json")
    assert loaded.manifest_root() == run.manifest_root()
    assert loaded.artifacts[0].meta == {"rank": 1}
    assert damaged(loaded, store) == []
    path = tmp_path / "ev" / sha[:2] / f"{sha}.json"
    path.write_text('{"a":2}', encoding="utf-8")
    assert damaged(loaded, store) == [sha]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_evidence.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.evidence'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/evidence.py`:
```python
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
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    @classmethod
    def load(cls, path: Path) -> Run:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return cls(doc["exam_id"], [ArtifactRef(**a) for a in doc["artifacts"]])


def damaged(run: Run, store: EvidenceStore) -> list[str]:
    return [a.sha256 for a in run.artifacts if not store.is_intact(a.sha256)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_evidence.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/evidence.py tests/test_evidence.py`. Suggested message: `feat: content-addressed evidence store and run manifest`.

---

### Task 3: SerpApi client protocol, scrubbing, trimming, replay client

**Files:**
- Create: `toppertrail/serp/__init__.py` (empty), `toppertrail/serp/base.py`, `toppertrail/serp/replay.py`
- Test: `tests/test_serp_base.py`, `tests/test_serp_replay.py`

**Interfaces:**
- Consumes: `canonical_json`, `short_hash` (Task 1).
- Produces:
  - `SerpResult(engine: str, params: dict, data: dict, source: str)` with property `search_id -> str | None`
  - `SerpClient` Protocol: `search(engine: str, params: dict) -> SerpResult`
  - `SerpError(message, status=None)`, `MissingFixture(SerpError)`
  - `canonical_params(engine, params) -> dict`, `params_hash(engine, params) -> str`
  - `redact(text, api_key) -> str`, `scrub(data, api_key) -> dict`, `trim(engine, data) -> dict`
  - `fixture_path(root, engine, params) -> Path`; `ReplaySerpClient(fixtures: Path)`

- [ ] **Step 1: Write the failing tests**

`tests/test_serp_base.py`:
```python
from toppertrail.serp.base import canonical_params, params_hash, redact, scrub, trim


def test_canonical_params_drop_transport_keys_and_stringify():
    p = canonical_params("google", {"q": "x", "num": 10, "api_key": "K", "no_cache": True, "hl": None})
    assert p == {"engine": "google", "num": "10", "q": "x"}
    assert params_hash("google", {"q": "x", "num": 10}) == params_hash("google", {"num": "10", "q": "x"})


def test_redact_removes_key_from_urls_and_plain_text():
    msg = "401 for url: https://serpapi.com/search?engine=google&api_key=SECRET123&q=a SECRET123"
    out = redact(msg, "SECRET123")
    assert "SECRET123" not in out
    assert "api_key=REDACTED" in out


def test_scrub_drops_account_urls_and_nested_key():
    data = {
        "search_metadata": {
            "id": "abc",
            "json_endpoint": "https://serpapi.com/searches/4f73/abc.json",
            "raw_html_file": "https://serpapi.com/searches/4f73/abc.html",
            "prettify_html_file": "https://serpapi.com/searches/4f73/abc.prettify",
        },
        "organic_results": [{"link": "https://x.test/?api_key=SECRET123"}],
    }
    out = scrub(data, "SECRET123")
    assert out["search_metadata"] == {"id": "abc"}
    assert "SECRET123" not in str(out)
    assert data["search_metadata"]["json_endpoint"]  # input not mutated


def test_trim_keeps_only_used_fields():
    data = {
        "search_metadata": {"id": "abc", "status": "Success", "created_at": "2026-10-06 10:00:00 UTC"},
        "search_parameters": {"engine": "google", "q": "x"},
        "organic_results": [{"title": "t", "link": "l", "snippet": "s", "rich_snippet": {"big": 1}}],
        "related_searches": [{"query": "y"}],
    }
    out = trim("google", data)
    assert set(out) == {"search_metadata", "search_parameters", "organic_results"}
    assert out["organic_results"] == [{"title": "t", "link": "l", "snippet": "s"}]
```

`tests/test_serp_replay.py`:
```python
import json
from pathlib import Path

import pytest

from toppertrail.serp.base import MissingFixture
from toppertrail.serp.replay import ReplaySerpClient, fixture_path


def test_replay_reads_fixture(tmp_path: Path):
    path = fixture_path(tmp_path, "google", {"q": "x", "gl": "in"})
    path.parent.mkdir(parents=True)
    doc = {"engine": "google", "params": {"engine": "google", "gl": "in", "q": "x"},
           "response": {"search_metadata": {"id": "s1"}, "organic_results": []}}
    path.write_text(json.dumps(doc), encoding="utf-8")
    r = ReplaySerpClient(tmp_path).search("google", {"gl": "in", "q": "x"})
    assert r.source == "replay"
    assert r.search_id == "s1"


def test_replay_missing_fixture_raises(tmp_path: Path):
    with pytest.raises(MissingFixture):
        ReplaySerpClient(tmp_path).search("google", {"q": "nothing"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_serp_base.py tests/test_serp_replay.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.serp'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/serp/base.py`:
```python
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from toppertrail.hashing import canonical_json, short_hash

DROP_PARAMS = {"api_key", "no_cache", "async", "output", "zero_trace"}
SCRUB_META = ("json_endpoint", "raw_html_file", "prettify_html_file")
_KEY_IN_URL = re.compile(r"(api_key=)[^&\s\"']+")

# Fields kept per engine. Everything else is dropped before evidence is stored, which keeps
# fixtures small and avoids redistributing third-party content we never use.
_KEEP_TOP = {"search_metadata", "search_parameters", "error"}
_KEEP: dict[str, dict[str, Any]] = {
    "google": {"organic_results": ("position", "title", "link", "displayed_link", "snippet",
                                   "date", "source")},
    "google_images": {"images_results": ("position", "title", "link", "source", "original")},
    "youtube": {"video_results": ("position_on_page", "title", "link", "channel",
                                  "published_date", "length", "description", "views")},
    "youtube_video": {"title": None, "description": None, "channel": None,
                      "published_date": None},
    "youtube_video_transcript": {"transcript": None, "available_transcripts": None},
    "google_ads_transparency_center": {"advertiser": None, "search_information": None,
                                       "ad_creatives": ("advertiser_id", "advertiser",
                                                        "ad_creative_id", "format", "image",
                                                        "width", "height", "first_shown",
                                                        "last_shown", "details_link")},
    "google_ai_mode": {"text_blocks": None, "references": None,
                       "reconstructed_markdown": None},
}
_META_KEEP = ("id", "status", "created_at", "processed_at")


class SerpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class MissingFixture(SerpError):
    pass


@dataclass(frozen=True)
class SerpResult:
    engine: str
    params: dict
    data: dict
    source: str  # "live" or "replay"

    @property
    def search_id(self) -> str | None:
        return (self.data.get("search_metadata") or {}).get("id")


class SerpClient(Protocol):
    def search(self, engine: str, params: dict) -> SerpResult: ...


def canonical_params(engine: str, params: dict) -> dict:
    clean = {k: str(v) for k, v in params.items() if k not in DROP_PARAMS and v is not None}
    clean["engine"] = engine
    return dict(sorted(clean.items()))


def params_hash(engine: str, params: dict) -> str:
    return short_hash(canonical_json(canonical_params(engine, params)))


def redact(text: str, api_key: str | None) -> str:
    out = _KEY_IN_URL.sub(r"\1REDACTED", text)
    if api_key:
        out = out.replace(api_key, "REDACTED")
    return out


def _walk(obj: Any, api_key: str | None) -> Any:
    if isinstance(obj, str):
        return redact(obj, api_key)
    if isinstance(obj, list):
        return [_walk(x, api_key) for x in obj]
    if isinstance(obj, dict):
        return {k: _walk(v, api_key) for k, v in obj.items()}
    return obj


def scrub(data: dict, api_key: str | None) -> dict:
    copy = json.loads(json.dumps(data))
    meta = copy.get("search_metadata")
    if isinstance(meta, dict):
        for k in SCRUB_META:
            meta.pop(k, None)
    return _walk(copy, api_key)


def trim(engine: str, data: dict) -> dict:
    spec = _KEEP.get(engine, {})
    out: dict[str, Any] = {}
    for key in _KEEP_TOP:
        if key in data:
            out[key] = data[key]
    if isinstance(out.get("search_metadata"), dict):
        out["search_metadata"] = {k: v for k, v in out["search_metadata"].items() if k in _META_KEEP}
    for key, fields in spec.items():
        if key not in data:
            continue
        value = data[key]
        if fields is None:
            out[key] = value
        elif isinstance(value, list):
            out[key] = [{f: item[f] for f in fields if f in item} for item in value
                        if isinstance(item, dict)]
    return out
```

`toppertrail/serp/replay.py`:
```python
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
            raise MissingFixture(f"no recorded response for {canonical_params(engine, params)}")
        doc = json.loads(path.read_text(encoding="utf-8"))
        return SerpResult(engine, canonical_params(engine, params), doc["response"], "replay")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_serp_base.py tests/test_serp_replay.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/serp/ tests/test_serp_base.py tests/test_serp_replay.py`. Suggested message: `feat: serp client protocol, scrubbing, trimming and replay`.

---

### Task 4: Live SerpApi client, credit budget, spend log, account check

**Files:**
- Create: `toppertrail/serp/budget.py`, `toppertrail/serp/live.py`
- Test: `tests/test_serp_live.py`

**Interfaces:**
- Consumes: `SerpResult`, `SerpError`, `canonical_params`, `params_hash`, `redact`, `scrub`, `trim` (Task 3).
- Produces: `Budget(cap: int, spent: int = 0)` with `ensure_available()`, `charge()`, `remaining`; `BudgetExceeded(SerpError)`; `append_spend(path, engine, phash, search_id)`, `spend_count(path) -> int`; `LiveSerpClient(api_key, budget, spend_log=None, sdk=None, sleep=time.sleep, max_retries=3, timeout=60)`; `account_searches_left(api_key, sdk=None) -> int`.

- [ ] **Step 1: Write the failing test**

`tests/test_serp_live.py`:
```python
import traceback

import pytest
import requests
import serpapi

from toppertrail.serp.budget import Budget, BudgetExceeded, spend_count
from toppertrail.serp.live import LiveSerpClient, account_searches_left

KEY = "SECRET123"


def http_error(status, url, body=b'{"error": "boom"}', retry_after=None):
    r = requests.Response()
    r.status_code = status
    r._content = body
    r.url = url
    if retry_after:
        r.headers["Retry-After"] = retry_after
    exc = requests.exceptions.HTTPError(f"{status} Client Error for url: {url}", response=r)
    return serpapi.HTTPError(exc)


class FakeSdk:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def search(self, params):
        self.calls.append(dict(params))
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return o

    def account(self):
        return {"total_searches_left": 212, "plan_searches_left": 212}


OK = {"search_metadata": {"id": "s1", "json_endpoint": "https://serpapi.com/searches/h/s1.json"},
      "organic_results": [{"title": "t", "link": "l", "extra": 1}]}


def test_success_charges_scrubs_trims_and_logs(tmp_path):
    budget = Budget(5)
    client = LiveSerpClient(KEY, budget, tmp_path / "spend.jsonl", sdk=FakeSdk([OK]))
    r = client.search("google", {"q": "x", "gl": "in"})
    assert r.search_id == "s1"
    assert "json_endpoint" not in r.data["search_metadata"]
    assert r.data["organic_results"] == [{"title": "t", "link": "l"}]
    assert budget.spent == 1
    assert spend_count(tmp_path / "spend.jsonl") == 1


def test_no_results_json_error_is_free():
    budget = Budget(5)
    sdk = FakeSdk([{"search_metadata": {"id": "s2"}, "error": "Google hasn't returned any results for this query."}])
    r = LiveSerpClient(KEY, budget, sdk=sdk).search("google", {"q": "zzz"})
    assert r.data["error"].startswith("Google hasn't")
    assert budget.spent == 0


def test_429_retries_with_retry_after_then_succeeds():
    slept = []
    sdk = FakeSdk([http_error(429, f"https://serpapi.com/search?api_key={KEY}", retry_after="2"), OK])
    client = LiveSerpClient(KEY, Budget(5), sdk=sdk, sleep=slept.append)
    r = client.search("google", {"q": "x"})
    assert r.search_id == "s1"
    assert slept == [2.0]
    assert len(sdk.calls) == 2


def test_error_text_and_traceback_never_contain_key():
    sdk = FakeSdk([http_error(401, f"https://serpapi.com/search?engine=google&api_key={KEY}",
                              body=b"not json")])
    client = LiveSerpClient(KEY, Budget(5), sdk=sdk)
    with pytest.raises(Exception) as info:
        client.search("google", {"q": "x"})
    text = "".join(traceback.format_exception(info.value))
    assert KEY not in text
    assert "HTTP 401" in str(info.value)


def test_budget_exceeded_before_any_call():
    sdk = FakeSdk([OK])
    with pytest.raises(BudgetExceeded):
        LiveSerpClient(KEY, Budget(0), sdk=sdk).search("google", {"q": "x"})
    assert sdk.calls == []


def test_account_searches_left():
    assert account_searches_left(KEY, sdk=FakeSdk([])) == 212
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_serp_live.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.serp.budget'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/serp/budget.py`:
```python
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
    row = {"at": datetime.now(UTC).isoformat(timespec="seconds"), "engine": engine,
           "params_hash": phash, "search_id": search_id}
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row) + "\n")


def spend_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
```

`toppertrail/serp/live.py`:
```python
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import serpapi

from toppertrail.serp.base import (
    SerpError,
    SerpResult,
    canonical_params,
    params_hash,
    redact,
    scrub,
    trim,
)
from toppertrail.serp.budget import Budget, append_spend

_RETRY_STATUS = {429, 500, 502, 503, -1}
_NO_RESULTS = "hasn't returned any results"


class LiveSerpClient:
    def __init__(self, api_key: str, budget: Budget, spend_log: Path | None = None, sdk=None,
                 sleep: Callable[[float], None] = time.sleep, max_retries: int = 3,
                 timeout: int = 60) -> None:
        if not api_key:
            raise SerpError("SERPAPI_API_KEY is not set")
        self._key = api_key
        self._sdk = sdk or serpapi.Client(api_key=api_key, timeout=timeout)
        self.budget = budget
        self.spend_log = spend_log
        self._sleep = sleep
        self.max_retries = max_retries

    @staticmethod
    def _wait(err: Exception, attempt: int) -> float:
        try:
            return min(float(err.response.headers.get("Retry-After")), 30.0)
        except (AttributeError, TypeError, ValueError):
            return min(2.0 ** attempt, 30.0)

    def _result(self, engine: str, params: dict, data: dict) -> SerpResult:
        clean = trim(engine, scrub(data, self._key))
        return SerpResult(engine, canonical_params(engine, params), clean, "live")

    def search(self, engine: str, params: dict) -> SerpResult:
        query = {"engine": engine, **params}
        for attempt in range(self.max_retries + 1):
            self.budget.ensure_available()
            try:
                raw = self._sdk.search(dict(query))
            except serpapi.TimeoutError:
                if attempt < self.max_retries:
                    self._sleep(self._wait(Exception(), attempt))
                    continue
                raise SerpError(f"SerpApi {engine} timed out") from None
            except serpapi.HTTPError as err:
                status = getattr(err, "status_code", None)
                message = getattr(err, "error", None)
                if message and _NO_RESULTS in message.lower():
                    return self._result(engine, params, {"error": message})
                if status in _RETRY_STATUS and attempt < self.max_retries:
                    self._sleep(self._wait(err, attempt))
                    continue
                detail = redact(str(message or err), self._key)
                raise SerpError(f"SerpApi {engine} failed (HTTP {status}): {detail}",
                                status=status) from None
            data = raw.as_dict() if hasattr(raw, "as_dict") else dict(raw)
            result = self._result(engine, params, data)
            if not result.data.get("error"):
                self.budget.charge()
                if self.spend_log is not None:
                    append_spend(self.spend_log, engine, params_hash(engine, params),
                                 result.search_id)
            return result
        raise SerpError(f"SerpApi {engine} failed after retries")


def account_searches_left(api_key: str, sdk=None) -> int:
    client = sdk or serpapi.Client(api_key=api_key)
    try:
        data = client.account()
    except serpapi.HTTPError as err:
        raise SerpError(redact(f"account check failed: {err}", api_key)) from None
    data = data.as_dict() if hasattr(data, "as_dict") else dict(data)
    return int(data.get("total_searches_left", data.get("plan_searches_left", 0)))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_serp_live.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/serp/budget.py toppertrail/serp/live.py tests/test_serp_live.py`. Suggested message: `feat: live SerpApi client with budget cap, retries and key redaction`.

---

### Task 5: Live spike on AIR 1 (needs the owner's key; about 8 credits)

This task confirms response shapes before the extractors are written. If the key is not ready yet, skip to Task 6 and return here before Task 10.

**Files:**
- Create: `scripts/spike.py`, `docs/notes/spike.md`
- Create (trimmed copies for tests): `tests/data/serp/*.json`

- [ ] **Step 1: Owner puts the key in `.env`**

The owner creates `D:\Projects\TopperTrail\.env` with one line `SERPAPI_API_KEY=<key>`. Claude never reads this file's contents aloud or prints the key.

- [ ] **Step 2: Write the spike script**

`scripts/spike.py`:
```python
"""Run the AIR 1 (UPSC CSE 2025) queries once and save trimmed, scrubbed responses.

Costs about 8 credits. Output: .toppertrail/spike/NN-<engine>.json
"""
from __future__ import annotations

import json
import sys

from toppertrail.config import load_settings
from toppertrail.serp.budget import Budget
from toppertrail.serp.live import LiveSerpClient, account_searches_left

QUERIES = [
    ("google", {"q": '"Anuj Agnihotri" UPSC CSE 2025 AIR 1', "gl": "in", "hl": "en"}),
    ("google_images", {"q": "Anuj Agnihotri AIR 1 UPSC 2025", "gl": "in", "hl": "en"}),
    ("youtube", {"search_query": "Anuj Agnihotri UPSC 2025 topper interview", "gl": "in", "hl": "en"}),
    ("youtube_video", {"v": "8X-e5cJ_L3M", "gl": "in", "hl": "en"}),
    ("youtube_video_transcript", {"v": "KIr6dWSqspI", "language_code": "hi"}),
    ("youtube_video_transcript", {"v": "KIr6dWSqspI", "language_code": "hi", "type": "asr"}),
    ("google_ads_transparency_center", {"text": "visionias.in", "region": "2356",
                                        "start_date": "20260306", "end_date": "20261005",
                                        "num": "100"}),
    ("google_ai_mode", {"q": "Which coaching institute did Anuj Agnihotri, UPSC CSE 2025 AIR 1, study at?",
                        "gl": "in", "hl": "en"}),
]


def main() -> None:
    s = load_settings()
    if not s.api_key:
        sys.exit("SERPAPI_API_KEY is not set in .env")
    left = account_searches_left(s.api_key)
    print("searches left before spike:", left)
    if left < len(QUERIES) + 5:
        sys.exit("not enough credits for the spike")
    client = LiveSerpClient(s.api_key, Budget(len(QUERIES)), s.home / "spend.jsonl")
    out = s.home / "spike"
    out.mkdir(parents=True, exist_ok=True)
    for i, (engine, params) in enumerate(QUERIES):
        r = client.search(engine, params)
        path = out / f"{i:02d}-{engine}.json"
        path.write_text(json.dumps(r.data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(f"{engine}: keys={sorted(r.data)} search_id={r.search_id}")
    print("searches left after spike:", account_searches_left(s.api_key))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the spike**

Run: `.venv/Scripts/python scripts/spike.py`
Expected: eight lines, one per engine, each with a `search_id`, and "searches left" drops by at most 8.

- [ ] **Step 4: Check shapes against the trim lists and record findings**

For each file in `.toppertrail/spike/` confirm and write the answer into `docs/notes/spike.md`:
1. `google`: `organic_results[].link/title/snippet` exist.
2. `google_images`: `images_results[].original/link/title/source` exist.
3. `youtube`: `video_results[].channel.link` and `channel.name`, `length`, `description` exist; note the `channel.link` form (`/channel/UC…`, `/@handle`, or `/user/…`).
4. `youtube_video`: the shape of `description` (string, or object with `content`) and `channel`.
5. `youtube_video_transcript`: whether the call without `type=asr` returned a transcript; which language came back. Decide the collection params (`language_code=hi` with or without `type=asr`) and record it.
6. `google_ads_transparency_center`: `ad_creatives[].image/last_shown/format` exist; count of creatives; whether `end_date` in the past or today is accepted.
7. `google_ai_mode`: the shape of `text_blocks` (nested `list` items, `snippet` keys) and `references`.

If any field name differs from Task 3's `_KEEP` table or from what Tasks 10 and 11 read, fix `_KEEP` now and note the change in `docs/notes/spike.md`.

- [ ] **Step 5: Save trimmed copies as test data**

Copy each spike file to `tests/data/serp/<engine>.json` (the second transcript call to `youtube_video_transcript_asr.json`), cutting list fields to their first 5 items. Then run a key check:

Run: `grep -rn "api_key=[^R]" tests/data || echo clean`
Expected: `clean`.

- [ ] **Step 6: Check OCR on Python 3.11**

Run:
```bash
.venv/Scripts/python -m pip install -e ".[ocr]"
.venv/Scripts/python -c "from rapidocr_onnxruntime import RapidOCR; print('rapidocr ok')"
```
Expected: `rapidocr ok`. If installation fails, record it in `docs/notes/spike.md`; OCR stays optional and posters fall back to titles.

- [ ] **Step 7: Owner checkpoint**

Files: `scripts/spike.py docs/notes/spike.md tests/data/serp/`. Suggested message: `chore: live spike confirms SerpApi response shapes`.

---

### Task 6: Models, text normalisation, name matching and context checks

**Files:**
- Create: `toppertrail/models.py`, `toppertrail/extract/__init__.py` (empty), `toppertrail/extract/text.py`
- Test: `tests/test_text.py`

**Interfaces:**
- Produces (models): `Exam`, `Topper` (with `display_name`), `Institute`, `Claim`, `Signal`, `SelfReport`, `Interview`, `AIAnswer`, `Flag` (fields exactly as below).
- Produces (text): `normalize(text) -> str`; `name_tokens(name) -> list[str]`; `find_name(text, name) -> list[tuple[int, int]]` (spans in normalized text); `ranks_near(norm_text, span, reach=80) -> list[tuple[int, int]]` (distance, rank) sorted; `Mention(topper, start, end, claimed_rank)`; `mentions(text, toppers) -> list[Mention]`; `context_ok(text, year, terms, require_year=True) -> bool`; `term_pattern(term) -> re.Pattern`.

- [ ] **Step 1: Write the failing test**

`tests/test_text.py`:
```python
from datetime import date

from toppertrail.extract.text import context_ok, find_name, mentions, normalize
from toppertrail.models import Topper


def t(rank, name, exam="upsc-cse-2025"):
    return Topper(exam, rank, name)


def test_normalize_folds_case_nukta_and_quotes():
    assert normalize("  Rau’s  IAS ") == "rau's ias"
    assert normalize("टेस्ट सीरीज़") == normalize("टेस्ट सीरीज")


def test_dotted_initials_and_possessive():
    assert find_name("Congrats to A.R. Rajah Mohaideen's success", "A R RAJAH MOHAIDEEN")
    assert find_name("Anuj Agnihotri's journey", "ANUJ AGNIHOTRI")


def test_printed_misspelling_matches_fuzzily_but_other_names_do_not():
    assert find_name("Pakshal Secretary AIR 8", "PAKSHAL SECRETRY")
    assert not find_name("Pakshal Sharma AIR 8", "PAKSHAL SECRETRY")


def test_single_token_name_needs_rank_nearby():
    hemant = t(13, "HEMANT", "upsc-cse-2024")
    assert mentions("Hemant secured AIR 13 in UPSC CSE 2024", [hemant])
    assert not mentions("Hemant Soren addressed a rally", [hemant])


def test_claimed_rank_is_the_nearest_rank():
    toppers = [t(1, "ANUJ AGNIHOTRI"), t(2, "RAJESHWARI SUVE M")]
    ms = {m.topper.rank: m.claimed_rank
          for m in mentions("AIR 1 Anuj Agnihotri | AIR 2 Rajeshwari Suve M", toppers)}
    assert ms == {1: 1, 2: 2}


def test_context_requires_exam_term_and_year():
    terms = ("jee", "iit")
    assert context_ok("Shubham Kumar CRL 1 JEE Advanced 2026", 2026, terms)
    assert not context_ok("Shubham Kumar AIR 1 UPSC CSE 2020", 2026, terms)
    assert context_ok("Shubham Kumar JEE topper ad", 2026, terms, require_year=False)
    assert not context_ok("bias in 2025 reports", 2025, ("ias",))


def test_topper_display_name():
    assert Topper("x", 7, "A R RAJAH MOHAIDEEN").display_name == "A R Rajah Mohaideen"
    _ = date(2026, 3, 6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_text.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.extract'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Exam:
    id: str
    label: str
    exam: str
    year: int
    tag: str
    rank_label: str
    result_date: date
    results_file: str
    context_terms: tuple[str, ...]
    default_top: int
    ads_end_date: date
    ads_creatives_cap: int
    google_query: str
    google_hi_top: int
    images_query: str
    youtube_query: str
    ai_mode_query: str
    video_details_top: int
    video_details_per_topper: int
    transcripts: bool
    transcript_params: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Topper:
    exam_id: str
    rank: int
    name: str
    extra: str = ""

    @property
    def display_name(self) -> str:
        return " ".join(p if len(p) == 1 else p.capitalize() for p in self.name.split())


@dataclass(frozen=True)
class Institute:
    id: str
    name: str
    exams: tuple[str, ...]
    domains: tuple[str, ...]
    channels: tuple[str, ...]
    handles: tuple[str, ...]
    aliases: tuple[str, ...]
    ads: tuple[tuple[str, tuple[str, ...]], ...] = ()
    legal_name: str = ""
    ccpa_orders: tuple[str, ...] = ()


@dataclass(frozen=True)
class Claim:
    claim_id: str
    exam_id: str
    rank: int
    institute_id: str
    source_type: str
    url: str
    title: str
    window: str
    course_types: tuple[str, ...]
    course_terms: tuple[str, ...]
    paid_free_stated: bool
    duration_stated: bool
    vague_label: bool
    claimed_rank: int | None
    search_id: str | None
    evidence: tuple[str, ...]
    observed_at: str


@dataclass(frozen=True)
class Signal:
    institute_id: str
    rule_id: str
    text: str
    url: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class SelfReport:
    rank: int
    video_id: str
    channel: str
    start_ms: int
    statement: str
    institute_id: str | None
    course_types: tuple[str, ...]
    polarity: str


@dataclass(frozen=True)
class Interview:
    rank: int
    video_id: str
    channel: str
    title: str
    language: str


@dataclass(frozen=True)
class AIAnswer:
    rank: int
    engine: str
    search_id: str | None
    institutes: tuple[str, ...]
    excerpt: str


@dataclass(frozen=True)
class Flag:
    rule_id: str
    institute_id: str
    claim_id: str | None
    rank: int | None
    detail: str
    code: str = ""
```

`toppertrail/extract/text.py`:
```python
from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz

from toppertrail.models import Topper

_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200c\u200d\ufeff"), None)
_QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'})
_NUKTA = "\u093c"
_TOKEN = re.compile(r"[a-z0-9]+")
_ASCII = re.compile(r"^[\x00-\x7f]+$")
_RANK = re.compile(
    r"(?<![a-z])(?:all india rank|air|rank|crl)\s*[-:#]?\s*(\d{1,4})(?!\d)"
    r"|रैंक\s*[-:#]?\s*(\d{1,4})(?!\d)"
    r"|(?<!\d)(\d{1,4})\s*(?:st|nd|rd|th)?\s*rank"
)


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "").translate(_ZERO_WIDTH).translate(_QUOTES)
    t = t.replace(_NUKTA, "").casefold()
    return re.sub(r"\s+", " ", t).strip()


def term_pattern(term: str) -> re.Pattern[str]:
    norm = normalize(term)
    esc = re.escape(norm)
    if _ASCII.match(norm):
        return re.compile(rf"(?<![a-z0-9]){esc}(?![a-z0-9])")
    return re.compile(esc)


def name_tokens(name: str) -> list[str]:
    return [tok for tok in _TOKEN.findall(normalize(name)) if len(tok) > 1]


def _same(a: str, b: str) -> bool:
    return a == b or (len(a) >= 5 and len(b) >= 5 and fuzz.ratio(a, b) >= 88)


def find_name(text: str, name: str) -> list[tuple[int, int]]:
    norm = normalize(text)
    toks = [(m.group(), m.start(), m.end()) for m in _TOKEN.finditer(norm) if len(m.group()) > 1]
    want = name_tokens(name)
    if not want:
        return []
    spans = []
    for i in range(len(toks) - len(want) + 1):
        if all(_same(toks[i + j][0], want[j]) for j in range(len(want))):
            spans.append((toks[i][1], toks[i + len(want) - 1][2]))
    return spans


def ranks_near(norm_text: str, span: tuple[int, int], reach: int = 80) -> list[tuple[int, int]]:
    start, end = span
    out = []
    for m in _RANK.finditer(norm_text):
        if m.end() < start - reach or m.start() > end + reach:
            continue
        value = int(next(g for g in m.groups() if g))
        if m.end() <= start:
            dist = start - m.end()
        elif m.start() >= end:
            dist = m.start() - end
        else:
            dist = 0
        out.append((dist, value))
    return sorted(out)


@dataclass(frozen=True)
class Mention:
    topper: Topper
    start: int
    end: int
    claimed_rank: int | None


def mentions(text: str, toppers: Sequence[Topper]) -> list[Mention]:
    norm = normalize(text)
    out = []
    for topper in toppers:
        for span in find_name(text, topper.name):
            near = ranks_near(norm, span)
            if len(name_tokens(topper.name)) < 2 and topper.rank not in {v for _, v in near}:
                continue
            tight = [v for d, v in near if d <= 25]
            out.append(Mention(topper, span[0], span[1], tight[0] if tight else None))
            break
    return out


def context_ok(text: str, year: int, terms: Sequence[str], require_year: bool = True) -> bool:
    norm = normalize(text)
    if require_year and str(year) not in norm:
        return False
    return any(term_pattern(term).search(norm) for term in terms)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_text.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/models.py toppertrail/extract/ tests/test_text.py`. Suggested message: `feat: models, normalisation and tolerant name matching`.

---

### Task 7: Ground-truth data, exam config, roster, institute registry

**Files:**
- Create: `toppertrail/data/exams.yaml`, `toppertrail/data/institutes.yaml`, `toppertrail/data/independent_channels.yaml`
- Create: `toppertrail/data/results/upsc-cse-2025.csv`, `toppertrail/data/results/jee-adv-2026.csv`, `toppertrail/data/results/neet-ug-2026.csv`
- Create: `toppertrail/data.py`
- Test: `tests/test_data.py`

**Interfaces:**
- Consumes: `Exam`, `Topper`, `Institute` (Task 6); `normalize`, `term_pattern` (Task 6).
- Produces: `load_exam(exam_id) -> Exam`; `exam_ids() -> list[str]`; `load_roster(exam, top) -> list[Topper]`; `Registry` with `get(iid)`, `all()`, `by_url(url)`, `by_channel(link, name)`, `find_aliases(text) -> list[str]`, `ads_for(tag) -> list[tuple[Institute, str]]`; `load_registry() -> Registry`; `IndependentChannels` with `match(link, name) -> bool`; `load_independent() -> IndependentChannels`; `read_data(rel) -> str`.

- [ ] **Step 1: Write the data files**

`toppertrail/data/results/upsc-cse-2025.csv` (official final result, 06.03.2026, names as printed):
```
rank,name,extra
1,ANUJ AGNIHOTRI,
2,RAJESHWARI SUVE M,
3,AKANSH DHULL,
4,RAGHAV JHUNJHUNWALA,
5,ISHAN BHATNAGAR,
6,ZINNIA AURORA,
7,A R RAJAH MOHAIDEEN,
8,PAKSHAL SECRETRY,
9,ASTHA JAIN,
10,UJJWAL PRIYANK,
11,YASHASWI RAJ VARDHAN,
12,AKSHIT BHARDWAJ,
13,ANANYA SHARMA,
14,SURABHI YADAV,
15,SIMRANDEEP KAUR,
16,MONIKA SRIVASTAVA,
17,CHITWAN JAIN,
18,SRUTHII R,
19,NISAR DISHANT AMRUTLAL,
20,RAVI RAAZ,
21,SHUBHAM SINGH,
22,GEETIKA ARORA,
23,JEENU SRI JASWANTH CHANDRA,
24,IFRA SHAMS ANSARI,
25,BHAVIKA CHOPRA,
```

`toppertrail/data/results/jee-adv-2026.csv` (IIT Roorkee press release, 01.06.2026):
```
rank,name,extra
1,SHUBHAM KUMAR,Delhi
2,KABEER CHHILLAR,Delhi
3,JATIN CHAHAR,Delhi
4,MOHIT SHEKHER SHUKLA,Madras
5,KUCHI SANDEEP,Madras
6,B JAYAKRISHNA SRINIVAS,Bombay
7,ARNAV GAUTAM,Delhi
8,KANISHK JAIN,Bombay
9,MEDISETTI NAGA SAHARSHA,Madras
10,DARSH SIKKA,Delhi
```

`toppertrail/data/results/neet-ug-2026.csv` (NTA re-exam result, 16.07.2026):
```
rank,name,extra
1,ARYAN GUPTA,Punjab
2,PANSHUL BANSAL,Haryana
3,UPLAKSHYA GOYAL,Rajasthan
4,AYUSH BHALOTIA,Bihar
5,KUDALE SHRAVANI KRISHNA,Maharashtra
6,RIYA RANJAN,Bihar
7,ARYAN DUBEY,Uttar Pradesh
8,GEETANSH SARIN,Punjab
9,GAURAV SINGH,Rajasthan
10,MOHANISH MARUTI BHOSALE,Maharashtra
```

`toppertrail/data/exams.yaml` (`transcript_params` comes from the spike decision in Task 5 Step 4; default shown):
```yaml
upsc-cse-2025:
  label: UPSC CSE 2025
  exam: UPSC Civil Services Examination
  year: 2025
  tag: upsc
  rank_label: AIR
  result_date: 2026-03-06
  results_file: results/upsc-cse-2025.csv
  sources:
    - https://www.upsc.gov.in/sites/default/files/CSE_2025_FR_Eng_06032026.pdf
  context_terms: [upsc, cse, civil services, ias]
  default_top: 20
  ads_end_date: 2026-10-05
  ads_creatives_cap: 25
  google_query: '"{name}" UPSC CSE {year} AIR {rank}'
  google_hi_top: 10
  images_query: '{name} AIR {rank} UPSC {year}'
  youtube_query: '{name} UPSC {year} topper interview'
  ai_mode_query: 'Which coaching institute did {name}, UPSC CSE {year} AIR {rank}, study at?'
  video_details_top: 10
  video_details_per_topper: 2
  transcripts: true
  transcript_params: {language_code: hi}
jee-adv-2026:
  label: JEE Advanced 2026
  exam: JEE Advanced
  year: 2026
  tag: jee
  rank_label: CRL
  result_date: 2026-06-01
  results_file: results/jee-adv-2026.csv
  sources:
    - https://jeeadv.ac.in/documents/Result2026PressRelease.pdf
  context_terms: [jee, iit]
  default_top: 5
  ads_end_date: 2026-10-05
  ads_creatives_cap: 25
  google_query: '"{name}" JEE Advanced {year} AIR {rank}'
  google_hi_top: 0
  images_query: '{name} JEE Advanced {year} AIR {rank}'
  youtube_query: '{name} JEE Advanced {year} topper'
  ai_mode_query: 'Which coaching institute did {name}, JEE Advanced {year} AIR {rank}, study at?'
  video_details_top: 0
  video_details_per_topper: 0
  transcripts: false
  transcript_params: {}
neet-ug-2026:
  label: NEET UG 2026
  exam: NEET UG (re-exam of 21 June 2026)
  year: 2026
  tag: neet
  rank_label: AIR
  result_date: 2026-07-16
  results_file: results/neet-ug-2026.csv
  sources:
    - https://cdnbbsr.s3waas.gov.in/s37bc1ec1d9c3426357e69acd5bf320061/uploads/2026/07/20260716477215762.pdf
  context_terms: [neet]
  default_top: 5
  ads_end_date: 2026-10-05
  ads_creatives_cap: 25
  google_query: '"{name}" NEET UG {year} AIR {rank}'
  google_hi_top: 0
  images_query: '{name} NEET {year} AIR {rank}'
  youtube_query: '{name} NEET {year} topper'
  ai_mode_query: 'Which coaching institute did {name}, NEET UG {year} AIR {rank}, study at?'
  video_details_top: 0
  video_details_per_topper: 0
  transcripts: false
  transcript_params: {}
```

`toppertrail/data/independent_channels.yaml` (media and interview channels that are not coaching institutes; handles other than Delhi Knowledge Track are matched by name until verified):
```yaml
- {name: Delhi Knowledge Track, channel_id: UCuHW2abZ-K0SKGhXfkyOY6w, handle: DelhiKnowledgeTrack}
- {name: The Lallantop}
- {name: Josh Talks}
- {name: Aaj Tak}
- {name: NDTV}
- {name: Dainik Bhaskar}
- {name: News18 India}
- {name: ABP NEWS}
- {name: Indian Masterminds}
- {name: ThePrint}
- {name: The Better India}
```

`toppertrail/data/institutes.yaml` (registry; channel IDs verified from the institutes' own pages or channel pages on 5 Oct 2026; aliases avoid common Hindi words such as दृष्टि or विजन on their own):
```yaml
# UPSC
- id: vision-ias
  name: Vision IAS
  legal_name: AjayVision Education Pvt Ltd
  exams: [upsc]
  domains: [visionias.in]
  channels: [UCw4wosjC-DKq95xI5klz92w, UCRr_ix2-7Z6EjfVopOAc4aA]
  handles: [VisionIASdelhi, VisionIASHindi]
  aliases: [vision ias, visionias, विजन आईएएस, विज़न आईएएस, विजन आईएस]
  ads: [{domain: visionias.in, exams: [upsc]}]
  ccpa_orders: [VISION_IAS_CSE2022_2023, VISION_IAS_CSE2020]
- id: vajiram-ravi
  name: Vajiram & Ravi
  legal_name: Vajiram and Ravi IAS Study Centre LLP
  exams: [upsc]
  domains: [vajiramandravi.com, vajiramias.com]
  channels: [UCzelA5kqD9v6k6drK44l4_g, UCe6aCM8xudXv3rlBc5C75Wg]
  handles: [VajiramandRaviOfficial, VajiramAndRaviHindi]
  aliases: [vajiram, vajiram & ravi, vajiram and ravi, वाजीराम, वाजिराम, वाजराम]
  ads: [{domain: vajiramandravi.com, exams: [upsc]}]
  ccpa_orders: [VAJIRAM_RAVI_CSE2023]
- id: vajirao-reddy
  name: Vajirao & Reddy Institute
  exams: [upsc]
  domains: [vajiraoinstitute.com]
  channels: [UCQgWK91IvWlYdNeTTw3LZVw]
  handles: [Vajiraoreddyinstitute]
  aliases: [vajirao, vajirao & reddy, vajirao and reddy, वाजीराव, वाजिराव]
  ads: [{domain: vajiraoinstitute.com, exams: [upsc]}]
  ccpa_orders: [VAJIRAO_REDDY_CSE2022, VAJIRAO_REDDY_CSE2023]
- id: drishti-ias
  name: Drishti IAS
  legal_name: VDK Eduventures
  exams: [upsc]
  domains: [drishtiias.com]
  channels: [UCzLqOSZPtUKrmSEnlH4LAvw, UCafpueX9hFLls24ed6UddEQ]
  handles: [DrishtiIASvideos, DrishtiIASEnglish]
  aliases: [drishti ias, drishtiias, दृष्टि आईएएस, दृष्टि आईएस]
  ads: [{domain: drishtiias.com, exams: [upsc]}]
  ccpa_orders: [DRISHTI_CSE2021, DRISHTI_CSE2022]
- id: studyiq
  name: StudyIQ IAS
  exams: [upsc]
  domains: [studyiq.com]
  channels: [UCrC8mOqJQpoB7NuIMKIS6rQ, UCKSGmEx5nKZCgjRny-9LaWQ, UCtKv7_z4rh37OCSEfkZuGow]
  handles: [StudyIQEducationLtd, studyiqiasHindi, upscprepbystudyiq]
  aliases: [studyiq, study iq, स्टडी आईक्यू, स्टडीआईक्यू]
  ads: [{domain: studyiq.com, exams: [upsc]}]
  ccpa_orders: [STUDYIQ_CSE2023]
- id: next-ias
  name: NEXT IAS
  legal_name: Made Easy Learnings
  exams: [upsc]
  domains: [nextias.com]
  channels: [UCgKgAaGbKS-XWUJGWqP5W0A, UCAW-rpG882FJA-1EvWueTCg]
  handles: [nextias, NEXTIASHindi]
  aliases: [next ias, nextias, नेक्स्ट आईएएस, नेक्स्ट आईएस]
  ads: [{domain: nextias.com, exams: [upsc]}]
  ccpa_orders: [NEXT_IAS_CSE2021]
- id: forum-ias
  name: ForumIAS
  exams: [upsc]
  domains: [forumias.com]
  channels: [UCzuYmh_kQUpJpguQCwLKoPg, UCrUVBvitIKjZ3EUZ89hwFzg]
  handles: [ForumIASOfficial, ForumiasHindi]
  aliases: [forumias, forum ias, फोरम आईएएस]
  ads: [{domain: forumias.com, exams: [upsc]}]
- id: shankar-ias
  name: Shankar IAS Academy
  exams: [upsc]
  domains: [shankariasacademy.com]
  channels: [UCj0t9VmB-FNrXuVJJCW7etw]
  handles: [ShankarIASAcademyVideos]
  aliases: [shankar ias, शंकर आईएएस]
  ads: [{domain: shankariasacademy.com, exams: [upsc]}]
  ccpa_orders: [SHANKAR_CSE2022]
- id: raus-ias
  name: Rau's IAS Study Circle
  exams: [upsc]
  domains: [rauias.com]
  channels: [UCWdeyiTcwjboM3qLcBPJThQ]
  handles: [rausias1953]
  aliases: [rau's ias, raus ias, rau ias, राउज आईएएस]
  ads: [{domain: rauias.com, exams: [upsc]}]
  ccpa_orders: [RAUS_CSE2021]
- id: srirams-ias
  name: Sriram's IAS
  exams: [upsc]
  domains: [sriramsias.com]
  channels: [UCbiWt_Ckrd4dqESbsXGBX6Q]
  handles: [sriramsiasofficial]
  aliases: [sriram's ias, srirams ias, sriram ias, श्रीराम आईएएस, श्रीराम्स आईएएस]
  ads: [{domain: sriramsias.com, exams: [upsc]}]
  ccpa_orders: [SRIRAMS_CSE2022]
- id: chahal-academy
  name: Chahal Academy
  exams: [upsc]
  domains: [chahalacademy.com]
  channels: [UCi73-p09as4fkn4HK_Xrywg]
  handles: [chahalacademy]
  aliases: [chahal academy, चहल एकेडमी, चहल अकादमी]
  ads: [{domain: chahalacademy.com, exams: [upsc]}]
  ccpa_orders: [CHAHAL_CSE2022]
- id: physics-wallah
  name: Physics Wallah (PW, PW OnlyIAS)
  legal_name: Physicswallah Ltd
  exams: [upsc, jee, neet]
  domains: [pw.live, pwonlyias.com, physicswallah.live]
  channels: [UCiGyWN6DEbnj2alu7iapuKQ, UCh4f3NyOzqGwZfwTSX78QfQ, UC9fQuR3XRALjaIZtKGSNJcQ,
             UCqOy6oOu6RPJNHYQ8f_Ybvg, UC17PM-3GiJIeIUogU2Y1t1Q, UCVJU_IChPMOe8RWkdVQjtfQ,
             UCD16eo98AXl-9T61Xd711kQ, UCGw8iWmsw1cPlfcrww-3C0g, UCctEsQirgs3hCmq5S7A7ToA,
             UCWEmndu9aCunQAVCjxsP7jg, UChbgwNStwEW8CdeuRl-JaXQ, UC2ynjdzhmROVYmDaF1KrvEA,
             UC8rsRDBBE1aUEzVETfHtCvQ]
  handles: [PhysicsWallah, OnlyIasnothingelse, PWOnlyIASUPSCEnglish, PWOnlyIASUPSC,
            OnlyIASPrarambh, PW-JEEWallah, PW-NEETWallah, PWNEET-Official, Class11th-JEE,
            class11th-neet, class12th-jee, class12th-neet, PW.Yoddha123]
  aliases: [physics wallah, physicswallah, pw onlyias, pw only ias, onlyias, पीडब्ल्यू, फिजिक्स वाला, फिजिक्सवाला]
  ads: [{domain: pwonlyias.com, exams: [upsc]}, {domain: pw.live, exams: [jee, neet]}]
- id: unacademy
  name: Unacademy
  legal_name: Sorting Hat Technologies
  exams: [upsc, jee, neet]
  domains: [unacademy.com]
  channels: [UCABe2FgVNv2hgBeMu2mySVg, UCPhY4iS6NNoQwlRLcUYu_tw, UC7Q0EfPzTwtanMVSWuK_QXA,
             UCV1lbzgZNcYFAT3VHKOb7Cg, UCVOyyXupdtEblFbno_4ibLQ, UCZNNx4KYmCkwxCLdsHyWqQA,
             UCdQwYksctqqiRwqp3PiJMWA, UCwJjrP7jG-PVJqToYUSfb2w]
  handles: [unacademyupscprep, UnacademyUPSCHindi, UnacademyIASEnglish, UnacademyUPSC101,
            upscunstoppables, Unacademy_JEE, UnacademyNEET, jeemastersbyunacademy]
  aliases: [unacademy, अनएकेडमी, अनअकैडमी, अनअकडमी, अनएकडमी]
  ads: [{domain: unacademy.com, exams: [upsc]}]
  ccpa_orders: [UNACADEMY_CSE2021]
- id: ksg
  name: Khan Study Group (KSG)
  exams: [upsc]
  domains: [ksgindia.com]
  channels: [UC6sOW5RX9miothdP0MteJvQ]
  handles: [ksg_ias]
  aliases: [ksg, khan study group, केएसजी]
  ads: [{domain: ksgindia.com, exams: [upsc]}]
  ccpa_orders: [KSG_CSE2022]
- id: khan-global-studies
  name: Khan Global Studies
  exams: [upsc]
  domains: [khanglobalstudies.com]
  channels: [UC7krt1E6XvrywJBu0ZOyq3Q, UC8yuaNBUMgttmcteh6W84OA]
  handles: [khanglobalstudies, KGS-IASHindi]
  aliases: [khan global studies, kgs ias, खान ग्लोबल स्टडीज]
- id: dhyeya-ias
  name: Dhyeya IAS
  exams: [upsc]
  domains: [dhyeyaias.com]
  channels: [UCMXdi-xFPcZV2tDXlHuZHgw]
  handles: [DhyeyaTV]
  aliases: [dhyeya ias, ध्येय आईएएस]
  ads: [{domain: dhyeyaias.com, exams: [upsc]}]
- id: dikshant-ias
  name: Dikshant IAS
  exams: [upsc]
  domains: [dikshantias.com]
  channels: [UCL2kVTYj7_cPGlsoTV_mmLQ]
  handles: [DikshantIAS]
  aliases: [dikshant ias, दीक्षांत आईएएस]
  ccpa_orders: [DIKSHANT_CSE2021]
- id: sanskriti-ias
  name: Sanskriti IAS
  exams: [upsc]
  domains: [sanskritiias.com]
  channels: [UC58IAk1i-6d5XgHZG4NnffA]
  handles: [SANSKRITIIAS]
  aliases: [sanskriti ias, संस्कृति आईएएस]
- id: edukemy
  name: Edukemy
  exams: [upsc]
  domains: [edukemy.com]
  channels: [UCwhJ_VtIAeeiCC50yKMMcnA]
  handles: [EdukemyforIAS]
  aliases: [edukemy]
- id: shubhra-ranjan
  name: Shubhra Ranjan IAS
  exams: [upsc]
  domains: [shubhraranjan.com]
  channels: [UCn7lUEF9AzgF_BJaRMsHRjQ]
  handles: [shubhraranjan]
  aliases: [shubhra ranjan, शुभ्रा रंजन]
  ccpa_orders: [SHUBHRA_RANJAN_CSE2023]
- id: plutus-ias
  name: Plutus IAS
  exams: [upsc]
  domains: [plutusias.com]
  channels: [UCpYZAdWAvgtQKHqQjzqdYqw]
  handles: [plutusias]
  aliases: [plutus ias]
  ccpa_orders: [PLUTUS_YOJANA_CSE2021]
- id: abhimanu-ias
  name: Abhimanu IAS
  exams: [upsc]
  domains: [abhimanu.com, abhimanuias.com]
  channels: [UCAmsQW4PJXzbcqiUCvHgKJQ]
  handles: [abhimanuiasofficial]
  aliases: [abhimanu ias, abhimanu's ias]
  ccpa_orders: [ABHIMANU_IAS]
- id: insights-ias
  name: Insights IAS
  exams: [upsc]
  domains: [insightsonindia.com, insightsias.com]
  channels: [UCpoccbCX9GEIwaiIe4HLjwA]
  handles: [Insights_IAS]
  aliases: [insights ias, insightsias]
- id: iasbaba
  name: IASbaba
  exams: [upsc]
  domains: [iasbaba.com]
  channels: [UChvbVdio9Wgj7Z3nQz1Q0ZQ]
  handles: [IASbaba_Official]
  aliases: [iasbaba, ias baba]
- id: lukmaan-ias
  name: Lukmaan IAS
  exams: [upsc]
  domains: [lukmaanias.com]
  channels: [UCDiKI-0k4CY7IZOrGbDY69g]
  handles: [LukmanIAS]
  aliases: [lukmaan ias, लुकमान आईएएस]
- id: legacy-ias
  name: Legacy IAS Academy
  exams: [upsc]
  domains: [legacyias.com]
  channels: []
  handles: []
  aliases: [legacy ias]
- id: clearias
  name: ClearIAS
  exams: [upsc]
  domains: [clearias.com]
  channels: []
  handles: []
  aliases: [clearias]
- id: gs-score
  name: GS SCORE
  exams: [upsc]
  domains: [iasscore.in]
  channels: [UCf31eCPlIbv-2dOTakELxOg]
  handles: [gsscoreofficial]
  aliases: [gs score, iasscore]
- id: sleepy-classes
  name: Sleepy Classes
  exams: [upsc]
  domains: [sleepyclasses.com]
  channels: [UCgRf62bnK3uX4N-YEhG4Jog]
  handles: [SleepyClassesIAS]
  aliases: [sleepy classes]
- id: byjus-ias
  name: BYJU'S IAS
  legal_name: Think & Learn Pvt Ltd
  exams: [upsc]
  domains: [byjus.com]
  channels: [UC1pfsmDBnMQB8sOuQvmTvRQ]
  handles: [BYJUSIAS]
  aliases: [byju's ias, byjus ias]
  ccpa_orders: [BYJUS_IAS]
- id: als-ias
  name: ALS IAS
  legal_name: Alternative Learning Systems
  exams: [upsc]
  domains: [alsedunation.com]
  channels: [UC4Cvh6Rf3i5fb9xCV962dIA]
  handles: [ALSIASOfficial]
  aliases: [als ias]
  ccpa_orders: [ALS_CSE2021_2022]
# JEE and NEET
- id: allen
  name: ALLEN Career Institute
  exams: [jee, neet]
  domains: [allen.in, allen.ac.in]
  channels: [UCgUeJ2Gv7rJtMBkQF2Ppn4A, UCkUI45drrKTWLxy3q3voJRw, UCySvBtI4jMLXp0BT9osvASw,
             UCcPauQfd9drEEC8_PoZ6Wpw]
  handles: [ALLENCareerInstituteofficial, ALLENJEE, ALLENNEET, ALLENOnlineOfficial]
  aliases: [allen career institute, allen kota, allen online, एलन कोटा, एलन करियर]
  ads: [{domain: allen.in, exams: [jee, neet]}]
- id: aakash
  name: Aakash Educational Services
  exams: [jee, neet]
  domains: [aakash.ac.in]
  channels: [UCDA-O-rNN0IKFaQUgWcb67A, UCAPDuc6Kfpe1mKjMX367qmA, UCfRxSp1qtic_q06e9HwhxJw]
  handles: [AakashEducation, Aakash_NEET, JEEatAakash]
  aliases: [aakash institute, aakash educational, aakash byju's, आकाश इंस्टीट्यूट]
  ads: [{domain: aakash.ac.in, exams: [jee, neet]}]
- id: motion
  name: Motion Education
  exams: [jee, neet]
  domains: [motion.ac.in]
  channels: [UCVUjsfIErUfWI57ep1L7B6Q, UC8UzfGlCDh-Q8WDJfrJ6XoA, UC2MLg_YHD4i6sJE0J07NgDw]
  handles: [MotionNVSir, MotionNEET, MotionEducation]
  aliases: [motion education, motion kota, मोशन]
  ads: [{domain: motion.ac.in, exams: [jee, neet]}]
  ccpa_orders: [MOTION_JEE_NEET_2025]
- id: resonance
  name: Resonance Eduventures
  exams: [jee, neet]
  domains: [resonance.ac.in]
  channels: [UC_bdItm01JN2xXRz5hXJwTQ]
  handles: [ResonanceEdu]
  aliases: [resonance eduventures, resonance kota, रेजोनेंस]
- id: fiitjee
  name: FIITJEE
  exams: [jee]
  domains: [fiitjee.com]
  channels: [UCx9JBiEB9oOsfTEtakjzn8w]
  handles: [fiitjee]
  aliases: [fiitjee, फिटजी]
- id: narayana
  name: Narayana Educational Institutions
  exams: [jee, neet]
  domains: [narayanagroup.com]
  channels: [UCQBYyVyxKzWHDVGIKxfC0vA, UCIcITe_6aIe98_jjkjyaf8Q, UCyfQ0mYvoP-2JiGuoNHhQuQ]
  handles: [thenarayanagroup, narayanajee, Narayananeet]
  aliases: [narayana group, narayana educational, narayana jee, नारायणा]
  ccpa_orders: [NARAYANA_JEEADV2024]
- id: sri-chaitanya
  name: Sri Chaitanya Educational Institutions
  exams: [jee, neet]
  domains: [srichaitanya.net]
  channels: [UCG31O2eprG8EAJkv9kMWVDg, UC6DoFLtBiqMV9DZKAIGM0EA]
  handles: [SriChaitanyaEdu, InfinityLearnEdu]
  aliases: [sri chaitanya, infinity learn, श्री चैतन्य]
- id: vibrant
  name: Vibrant Academy
  exams: [jee, neet]
  domains: [vibrantacademy.com]
  channels: [UCiGpAU6F3DeBmLbs6J8pvjg]
  handles: [vibrantacademyofficial]
  aliases: [vibrant academy]
- id: clc-sikar
  name: Career Line Coaching, Sikar
  exams: [jee, neet]
  domains: [clcsikar.com]
  channels: [UCDOAygE2Smt9jWB7xpQo6iQ]
  handles: [clcsikar]
  aliases: [clc sikar, career line coaching]
  ccpa_orders: [CLC_SIKAR_NEET2024]
- id: vmc
  name: Vidyamandir Classes
  exams: [jee]
  domains: [vidyamandir.com]
  channels: [UConPUBSiB7UkdMH2nkYzxAA]
  handles: [VMCJEE]
  aliases: [vidyamandir classes]
- id: vedantu
  name: Vedantu
  exams: [jee, neet]
  domains: [vedantu.com]
  channels: [UClaQJq84XMtMkL44zDmL-Tg, UCqaq3Cwa7m_EsqlvfZh6uyw]
  handles: [JEEVedantu, vedantuneet]
  aliases: [vedantu]
- id: esaral
  name: eSaral
  exams: [jee, neet]
  domains: [esaral.com]
  channels: [UCddnJhXMUxzHoH8AZkZSd8w, UCD7O0ABXcFzKPTAuUTNCE3A]
  handles: [eSaral, NEETeSaral]
  aliases: [esaral]
- id: career-point
  name: Career Point Kota
  exams: [jee, neet]
  domains: [careerpoint.ac.in]
  channels: [UCLNYhA7rnXfdaFh-W6hJTSg]
  handles: [cpkota]
  aliases: [career point kota]
- id: matrix-sikar
  name: Matrix Academy Sikar
  exams: [jee, neet]
  domains: []
  channels: [UC3lu2YmeqASw775BVBg5Ejw]
  handles: [matrixacademysikar]
  aliases: [matrix sikar]
- id: goal-institute
  name: Goal Institute
  exams: [neet]
  domains: []
  channels: [UCrmzFVr1z6l6bzqQKhTOQIA]
  handles: [GOALINSTITUTEOFFICIAL]
  aliases: [goal institute]
```

- [ ] **Step 2: Write the failing test**

`tests/test_data.py`:
```python
from datetime import date

from toppertrail.data import exam_ids, load_exam, load_independent, load_registry, load_roster


def test_exams_and_roster():
    assert exam_ids() == ["jee-adv-2026", "neet-ug-2026", "upsc-cse-2025"]
    exam = load_exam("upsc-cse-2025")
    assert exam.result_date == date(2026, 3, 6)
    assert exam.transcript_params == (("language_code", "hi"),)
    roster = load_roster(exam, 3)
    assert [(t.rank, t.name) for t in roster] == [
        (1, "ANUJ AGNIHOTRI"), (2, "RAJESHWARI SUVE M"), (3, "AKANSH DHULL")]


def test_registry_urls_and_lookalikes():
    reg = load_registry()
    assert reg.by_url("https://news.allen.in/allen-kota-alumni").id == "allen"
    assert reg.by_url("https://www.vajiraoinstitute.com/x.aspx").id == "vajirao-reddy"
    assert reg.by_url("https://vajiramandravi.com/ias-selections-from-vajiram/").id == "vajiram-ravi"
    assert reg.by_url("https://onlyias.com/anything") is None
    assert reg.by_url("https://thebetterindia.com/upsc/x") is None


def test_registry_channels():
    reg = load_registry()
    assert reg.by_channel("https://www.youtube.com/channel/UCgKgAaGbKS-XWUJGWqP5W0A", None).id == "next-ias"
    assert reg.by_channel("https://www.youtube.com/@NEXTIAS", None).id == "next-ias"
    assert reg.by_channel(None, "NEXT IAS").id == "next-ias"
    assert reg.by_channel(None, "NEXT IAS Fans Club") is None


def test_aliases_avoid_common_hindi_words():
    reg = load_registry()
    assert reg.find_aliases("मेरी दृष्टि से यह विजन सही था") == []
    assert reg.find_aliases("मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया") == ["next-ias"]
    assert reg.find_aliases("Vajiram & Ravi and Vajirao & Reddy") == ["vajiram-ravi", "vajirao-reddy"]


def test_ads_targets_and_independent_channels():
    reg = load_registry()
    upsc = reg.ads_for("upsc")
    assert len(upsc) == 15
    assert ("physics-wallah", "pwonlyias.com") in {(i.id, d) for i, d in upsc}
    assert len(reg.ads_for("jee")) == 4 and len(reg.ads_for("neet")) == 4
    ind = load_independent()
    assert ind.match("https://www.youtube.com/channel/UCuHW2abZ-K0SKGhXfkyOY6w", None)
    assert ind.match(None, "The Lallantop")
    assert not ind.match(None, "Vision IAS")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_data.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.data'` (the YAML exists but the loader does not).

- [ ] **Step 4: Write the implementation**

`toppertrail/data.py`:
```python
from __future__ import annotations

import csv
import io
import re
from functools import lru_cache
from importlib.resources import files
from urllib.parse import urlsplit

import yaml

from toppertrail.extract.text import normalize, term_pattern
from toppertrail.models import Exam, Institute, Topper

_CHANNEL_ID = re.compile(r"/channel/(UC[\w-]{22})")
_HANDLE = re.compile(r"/@([\w.\-]+)")
_USER = re.compile(r"/(?:user|c)/([\w.\-]+)")


def read_data(rel: str) -> str:
    return files("toppertrail").joinpath(f"data/{rel}").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _exams() -> dict:
    return yaml.safe_load(read_data("exams.yaml"))


def exam_ids() -> list[str]:
    return sorted(_exams())


def load_exam(exam_id: str) -> Exam:
    raw = _exams()[exam_id]
    return Exam(
        id=exam_id, label=raw["label"], exam=raw["exam"], year=int(raw["year"]), tag=raw["tag"],
        rank_label=raw["rank_label"], result_date=raw["result_date"],
        results_file=raw["results_file"], context_terms=tuple(raw["context_terms"]),
        default_top=int(raw["default_top"]), ads_end_date=raw["ads_end_date"],
        ads_creatives_cap=int(raw["ads_creatives_cap"]), google_query=raw["google_query"],
        google_hi_top=int(raw["google_hi_top"]), images_query=raw["images_query"],
        youtube_query=raw["youtube_query"], ai_mode_query=raw["ai_mode_query"],
        video_details_top=int(raw["video_details_top"]),
        video_details_per_topper=int(raw["video_details_per_topper"]),
        transcripts=bool(raw["transcripts"]),
        transcript_params=tuple(sorted((k, str(v)) for k, v in (raw.get("transcript_params") or {}).items())),
    )


def load_roster(exam: Exam, top: int) -> list[Topper]:
    rows = csv.DictReader(io.StringIO(read_data(exam.results_file)))
    toppers = [Topper(exam.id, int(r["rank"]), r["name"].strip(), (r.get("extra") or "").strip())
               for r in rows]
    return sorted((t for t in toppers if t.rank <= top), key=lambda t: t.rank)


def _host(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


class Registry:
    def __init__(self, institutes: list[Institute]) -> None:
        self._by_id = {i.id: i for i in institutes}
        self._domains = {d.lower(): i for i in institutes for d in i.domains}
        self._channels = {c: i for i in institutes for c in i.channels}
        self._handles = {h.casefold(): i for i in institutes for h in i.handles}
        self._names = {normalize(n): i for i in institutes for n in (i.name, *i.aliases)}
        self._aliases = [(term_pattern(a), i.id) for i in institutes for a in i.aliases]

    def get(self, iid: str) -> Institute:
        return self._by_id[iid]

    def all(self) -> list[Institute]:
        return list(self._by_id.values())

    def by_url(self, url: str) -> Institute | None:
        parts = _host(url).split(".")
        for k in range(len(parts) - 1):
            hit = self._domains.get(".".join(parts[k:]))
            if hit:
                return hit
        return None

    def by_channel(self, link: str | None, name: str | None) -> Institute | None:
        link = link or ""
        m = _CHANNEL_ID.search(link)
        if m and m.group(1) in self._channels:
            return self._channels[m.group(1)]
        for pattern in (_HANDLE, _USER):
            m = pattern.search(link)
            if m and m.group(1).casefold() in self._handles:
                return self._handles[m.group(1).casefold()]
        if name:
            return self._names.get(normalize(name))
        return None

    def find_aliases(self, text: str) -> list[str]:
        norm = normalize(text)
        return sorted({iid for pattern, iid in self._aliases if pattern.search(norm)})

    def ads_for(self, tag: str) -> list[tuple[Institute, str]]:
        out = []
        for inst in self._by_id.values():
            for domain, exams in inst.ads:
                if tag in exams:
                    out.append((inst, domain))
        return out


@lru_cache(maxsize=1)
def load_registry() -> Registry:
    raw = yaml.safe_load(read_data("institutes.yaml"))
    institutes = [
        Institute(
            id=r["id"], name=r["name"], exams=tuple(r["exams"]), domains=tuple(r.get("domains") or ()),
            channels=tuple(r.get("channels") or ()), handles=tuple(r.get("handles") or ()),
            aliases=tuple(r.get("aliases") or ()),
            ads=tuple((a["domain"], tuple(a["exams"])) for a in r.get("ads") or ()),
            legal_name=r.get("legal_name", ""), ccpa_orders=tuple(r.get("ccpa_orders") or ()),
        )
        for r in raw
    ]
    return Registry(institutes)


class IndependentChannels:
    def __init__(self, rows: list[dict]) -> None:
        self._ids = {r["channel_id"] for r in rows if r.get("channel_id")}
        self._handles = {r["handle"].casefold() for r in rows if r.get("handle")}
        self._names = {normalize(r["name"]) for r in rows}

    def match(self, link: str | None, name: str | None) -> bool:
        link = link or ""
        m = _CHANNEL_ID.search(link)
        if m and m.group(1) in self._ids:
            return True
        m = _HANDLE.search(link)
        if m and m.group(1).casefold() in self._handles:
            return True
        return bool(name) and normalize(name) in self._names


@lru_cache(maxsize=1)
def load_independent() -> IndependentChannels:
    return IndependentChannels(yaml.safe_load(read_data("independent_channels.yaml")))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_data.py -q`
Expected: `5 passed`. If the `ads_for("upsc")` count is not 15, recount the `ads:` entries tagged `upsc` in `institutes.yaml` (vision, vajiram, vajirao, drishti, studyiq, next, forum, shankar, raus, srirams, chahal, pw, unacademy, ksg, dhyeya).

- [ ] **Step 6: Owner checkpoint**

Files: `toppertrail/data/ toppertrail/data.py tests/test_data.py`. Suggested message: `feat: official result rosters, exam config and institute registry`.

---

### Task 8: Lexicon and course classification

**Files:**
- Create: `toppertrail/data/lexicon.yaml`, `toppertrail/extract/courses.py`
- Test: `tests/test_courses.py`

**Interfaces:**
- Consumes: `normalize`, `term_pattern` (Task 6); `read_data` (Task 7).
- Produces: `CourseMatch(course_types, terms, vague, paid_free, duration)`; `Lexicon.load()`; `Lexicon.classify(text, include_generic=False) -> CourseMatch`; `superlatives(text) -> list[str]`; `guarantees(text) -> list[str]`; `aggregates(text) -> list[str]`; `first_person(text) -> bool`; `negated(text) -> bool`; `signal_terms(text) -> bool`; constants `INTERVIEW_ONLY = "interview_only"`, `GENERIC = "coaching_generic"`.

- [ ] **Step 1: Write the lexicon**

`toppertrail/data/lexicon.yaml`:
```yaml
course_types:
  interview_only:
    - interview guidance programme
    - interview guidance program
    - interview guidance
    - interview training program
    - interview program
    - igp
    - mock interview programme
    - mock interviews
    - mock interview
    - personality test
    - personality development programme
    - daf analysis
    - last mile
    - इंटरव्यू गाइडेंस प्रोग्राम
    - इंटरव्यू गाइडेंस
    - मॉक इंटरव्यू
    - साक्षात्कार मार्गदर्शन
  foundation_classroom:
    - gs foundation
    - foundation course
    - foundation batch
    - foundation
    - classroom programme
    - classroom program
    - classroom course
    - classroom student
    - full time classroom
    - full-time classroom
    - prelims cum mains
    - pcm
    - mains advance course
    - gs mac
    - residential programme
    - two year integrated
    - integrated classroom
    - nurture
    - enthuse
    - leader course
    - dropper batch
    - target course
    - one year classroom
    - फाउंडेशन कोर्स
    - फाउंडेशन
    - क्लासरूम प्रोग्राम
    - क्लासरूम
  test_series:
    - all india test series
    - prelims test series
    - mains test series
    - test series
    - abhyaas
    - aiats
    - mock test
    - open test
    - टेस्ट सीरीज
    - अभ्यास टेस्ट
  optional:
    - optional
    - psir
    - sociology
    - anthropology
    - वैकल्पिक
  crash_course:
    - crash course
    - क्रैश कोर्स
  mentorship:
    - mentorship
    - mentoring
    - मेंटरशिप
  current_affairs:
    - ca-va
    - current affairs
    - करेंट अफेयर्स
  essay_ethics:
    - ethics enhancer
    - answer writing
    - essay
    - ethics
  online_distance:
    - online course
    - online learner
    - online program
    - distance learning
    - postal course
    - plus subscription
    - i-eklavya
    - dlp
    - ऑनलाइन कोर्स
    - डिस्टेंस लर्निंग
generic_coaching:
  - coaching
  - कोचिंग
vague_labels:
  - our student
  - our students
  - from various courses
  - various courses
  - various programs
  - various programmes
  - associated with
  - student of
  - fresher
  - with xii
  - repeater
  - repeaters
  - हमारे छात्र
  - हमारा छात्र
paid_free:
  - free of cost
  - free
  - paid
  - fee
  - fees
  - scholarship
  - "₹"
  - rs.
  - inr
  - निःशुल्क
  - नि:शुल्क
  - मुफ्त
  - फ्री
  - शुल्क
  - फीस
duration_patterns:
  - '(?<![\d.])\d{1,2}\s*[- ]?\s*(?:day|days|week|weeks|month|months|year|years|yr|yrs)\b'
  - '\b(?:one|two|three|six|ten)[- ](?:day|week|month|year)s?\b'
  - '\d{1,2}\s*(?:दिन|सप्ताह|माह|महीने|महीना|वर्ष|साल)'
superlatives:
  - best ias coaching
  - best ias academy
  - best upsc coaching
  - best ias
  - best coaching
  - best institute
  - no. 1
  - no.1
  - number 1
  - number one
  - "#1"
  - india's top
  - india's best
  - india's premier
  - top upsc coaching
  - ranked at 1st position
  - we are the best
  - सर्वश्रेष्ठ
  - नंबर 1
  - नंबर वन
  - बेस्ट
guarantees:
  - guaranteed selection
  - guaranteed
  - guarantee
  - 100% selection
  - 100 % selection
  - assured selection
  - selection assured
  - sure shot selection
  - success pakka
  - pakka
  - पक्का
  - गारंटी
  - है तो सिलेक्शन है
aggregate_patterns:
  - '(?<![\d.])(?!(?:19|20)\d\d\b)\d{1,4}\s*(?:\+|plus)?\s*(?:rank holders?|rankers?|selections?|students?|candidates?|achievers)?\s*(?:in|out of|of)\s*(?:the\s*)?top\s*[- ]?\d{1,4}\b'
  - '\ball\s*top\s*\d{1,3}\b'
  - '\btop\s*\d{1,3}\s*out of\s*(?:top\s*)?\d{1,3}\b'
  - '(?<![\d.])(?!(?:19|20)\d\d\b)\d{1,5}\s*(?:\+|plus)?\s*(?:selections?|selected|results?|achievers)\b'
  - '\btotal\s*selections?\s*[:\-]?\s*\d{1,5}\b'
  - '(?<![\d.])(?!(?:19|20)\d\d\b)\d{1,5}\s*out of\s*\d{2,5}\b'
  - '(?<![\d.])\d{1,3}(?:\.\d+)?\s*%\s*of\s*(?:all\s*)?(?:\w+\s*){0,2}?(?:selections?|rankers|officers|selected|toppers)\b'
first_person:
  - i
  - i've
  - i'm
  - my
  - me
  - myself
  - मैंने
  - मैं
  - मेरा
  - मेरी
  - मेरे
  - मुझे
negations:
  - didn't
  - did not
  - never
  - not join
  - not joined
  - haven't
  - have not
  - no coaching
  - without coaching
  - self study
  - self-study
  - नहीं
  - नही
  - बिना कोचिंग
  - सेल्फ स्टडी
```

- [ ] **Step 2: Write the failing test**

`tests/test_courses.py`:
```python
import pytest

from toppertrail.extract.courses import Lexicon


@pytest.fixture(scope="module")
def lex():
    return Lexicon.load()


def test_mock_interview_vs_mock_test_vs_topper_interview(lex):
    assert lex.classify("Anuj Agnihotri AIR 1 | CSE Topper's Mock Interview").course_types == ("interview_only",)
    assert lex.classify("Prelims mock test series").course_types == ("test_series",)
    assert lex.classify("UPSC Topper Interview with Anuj").course_types == ()


def test_ccpa_course_labels(lex):
    assert lex.classify("GS FOUNDATION BATCH CLASSROOM STUDENT").course_types == ("foundation_classroom",)
    m = lex.classify("Mock Interview / Free of cost")
    assert m.course_types == ("interview_only",) and m.paid_free
    m = lex.classify("free 5-day Interview Training Program")
    assert m.course_types == ("interview_only",) and m.paid_free and m.duration
    assert lex.classify("GS Mains Test Series 2020").course_types == ("test_series",)
    assert lex.classify("I-Eklavya (Online)").course_types == ("online_distance",)
    assert lex.classify("PSIR optional").course_types == ("optional",)


def test_vague_labels_and_hindi(lex):
    m = lex.classify("Our student Anuj Agnihotri, AIR 1")
    assert m.course_types == () and m.vague
    assert lex.classify("टेस्ट सीरीज़ और इंटरव्यू गाइडेंस प्रोग्राम").course_types == ("interview_only", "test_series")
    assert lex.classify("कोई कोचिंग नहीं ली", include_generic=True).course_types == ("coaching_generic",)
    assert lex.classify("Best IAS Coaching in Delhi").course_types == ()


def test_signals_from_ccpa_claim_texts(lex):
    assert lex.aggregates("8 Rank Holders in the Top 10 are from Vajiram & Ravi")
    assert lex.aggregates("120+ selections in UPSC CSE 2023")
    assert lex.aggregates("26% of all UPSC rankers are Unacademy learners")
    assert lex.aggregates("All TOP 5 Successful Candidates of UPSC Civil Services Exam 2022 are from KSG.")
    assert lex.aggregates("682 out of 933 selected students are from KSG.")
    assert not lex.aggregates("UPSC 2025 results announced")
    assert lex.superlatives("We are India's No. 1 Prestigious UPSC/IAS Coaching Institute")
    assert lex.superlatives("Best IAS Coaching Institute for General Studies and CSAT in India.") == ["best ias coaching"]
    assert lex.guarantees("Success Pakka Offer")
    assert lex.guarantees("मोशन है तो सिलेक्शन है")
    assert lex.guarantees("Guaranteed Prelims & Mains")


def test_first_person_and_negation(lex):
    assert lex.first_person("मॉक इंटरव्यूज में मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया")
    assert not lex.first_person("10 आउट ऑफ टॉप 10 आर फ्रॉम वेरियस कोर्सेज ऑफ वाजराम एंड रवि")
    assert lex.negated("मैंने टेस्ट सीरीज शायद कभी जॉइ नहीं करी")
    assert not lex.negated("I joined the test series")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_courses.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.extract.courses'`.

- [ ] **Step 4: Write the implementation**

`toppertrail/extract/courses.py`:
```python
from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from toppertrail.data import read_data
from toppertrail.extract.text import normalize, term_pattern

INTERVIEW_ONLY = "interview_only"
GENERIC = "coaching_generic"


@dataclass(frozen=True)
class CourseMatch:
    course_types: tuple[str, ...]
    terms: tuple[str, ...]
    vague: bool
    paid_free: bool
    duration: bool


def _compile(terms: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    pairs = [(normalize(t), term_pattern(t)) for t in terms]
    return sorted(pairs, key=lambda p: (-len(p[0]), p[0]))


def _masked_hits(text: str, pats: list[tuple[str, str, re.Pattern[str]]]) -> list[tuple[str, str]]:
    masked = normalize(text)
    hits = []
    for label, term, pattern in pats:
        if pattern.search(masked):
            hits.append((label, term))
            masked = pattern.sub(lambda m: " " * len(m.group()), masked)
    return hits


class Lexicon:
    def __init__(self, raw: dict) -> None:
        course = [(ctype, normalize(t), term_pattern(t))
                  for ctype, terms in raw["course_types"].items() for t in terms]
        generic = [(GENERIC, normalize(t), term_pattern(t)) for t in raw["generic_coaching"]]
        order = lambda p: (-len(p[1]), p[1])  # noqa: E731
        self._course = sorted(course, key=order)
        self._with_generic = sorted(course + generic, key=order)
        self._vague = [p for _, p in _compile(raw["vague_labels"])]
        self._paid = [p for _, p in _compile(raw["paid_free"])]
        self._duration = [re.compile(p) for p in raw["duration_patterns"]]
        self._sup = [(t, t, p) for t, p in _compile(raw["superlatives"])]
        self._guar = [(t, t, p) for t, p in _compile(raw["guarantees"])]
        self._agg = [re.compile(p) for p in raw["aggregate_patterns"]]
        self._first = [p for _, p in _compile(raw["first_person"])]
        self._neg = [p for _, p in _compile(raw["negations"])]

    @classmethod
    def load(cls) -> Lexicon:
        return cls(yaml.safe_load(read_data("lexicon.yaml")))

    def classify(self, text: str, include_generic: bool = False) -> CourseMatch:
        norm = normalize(text)
        hits = _masked_hits(text, self._with_generic if include_generic else self._course)
        types = tuple(sorted({label for label, _ in hits}))
        terms = tuple(sorted({term for _, term in hits}))
        return CourseMatch(
            course_types=types,
            terms=terms,
            vague=any(p.search(norm) for p in self._vague),
            paid_free=any(p.search(norm) for p in self._paid),
            duration=any(p.search(norm) for p in self._duration),
        )

    def superlatives(self, text: str) -> list[str]:
        return sorted({term for _, term in _masked_hits(text, self._sup)})

    def guarantees(self, text: str) -> list[str]:
        return sorted({term for _, term in _masked_hits(text, self._guar)})

    def aggregates(self, text: str) -> list[str]:
        norm = normalize(text)
        found = []
        for pattern in self._agg:
            found.extend(m.group().strip() for m in pattern.finditer(norm))
        return sorted(set(found))

    def signal_terms(self, text: str) -> bool:
        return bool(self.superlatives(text) or self.guarantees(text) or self.aggregates(text))

    def first_person(self, text: str) -> bool:
        norm = normalize(text)
        return any(p.search(norm) for p in self._first)

    def negated(self, text: str) -> bool:
        norm = normalize(text)
        return any(p.search(norm) for p in self._neg)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_courses.py -q`
Expected: `5 passed`. If one CCPA string fails, adjust the lexicon entry (not the test); the CCPA strings are verbatim from the orders.

- [ ] **Step 6: Owner checkpoint**

Files: `toppertrail/data/lexicon.yaml toppertrail/extract/courses.py tests/test_courses.py`. Suggested message: `feat: English and Hindi course, superlative, guarantee and count lexicon`.

---

### Task 9: Page snapshots, HTML blocks, image text, replay readers

**Files:**
- Create: `toppertrail/fetch/__init__.py` (empty), `toppertrail/fetch/pages.py`, `toppertrail/fetch/images.py`
- Test: `tests/test_pages.py`, `tests/test_images.py`

**Interfaces:**
- Consumes: `sha256_bytes`, `short_hash` (Task 1).
- Produces:
  - `PageSnapshot(url, status, fetched_at, html_sha256, blocks: tuple[tuple[int, str], ...], error)`; `html_to_blocks(html) -> list[tuple[int, str]]`; `filter_blocks(blocks, relevant: Callable[[str], bool]) -> list[tuple[int, str]]`
  - `LivePageFetcher(client=None, min_interval=1.0, max_bytes=2_000_000, timeout=10.0, sleep=time.sleep, clock=time.monotonic, today=None)` with `fetch(url) -> PageSnapshot`; `ReplayPageFetcher(fixtures)`; `page_fixture_path(root, url) -> Path`; `snapshot_from_dict(d) -> PageSnapshot`
  - `ImageText(url, image_sha256, text, error)`; `LiveImageReader(ocr, client=None, max_bytes=5_000_000)` with `read(url) -> ImageText`; `ReplayImageReader(fixtures)`; `image_fixture_path(root, url) -> Path`; `load_rapidocr() -> Callable[[bytes], str] | None`

- [ ] **Step 1: Write the failing tests**

`tests/test_pages.py`:
```python
import json

import httpx

from toppertrail.fetch.pages import (
    LivePageFetcher,
    ReplayPageFetcher,
    filter_blocks,
    html_to_blocks,
    page_fixture_path,
)

PAGE = """<html><body>
<header><nav><ul><li>GS Foundation Course</li><li>Test Series</li><li>IGP</li></ul></nav></header>
<div class="mega-menu"><a>Mains Test Series</a></div>
<main><h1>Anuj Agnihotri UPSC AIR 1 2025</h1>
<p>Congratulations Anuj Agnihotri, AIR 1 in UPSC CSE 2025.</p>
<img alt="Anuj Agnihotri poster" src="x.jpg">
<ul><li>Rajeshwari Suve M AIR 2 (IGP)</li></ul></main>
<footer><p>Best IAS coaching in Delhi</p></footer>
<script>var courses = "Test Series";</script></body></html>"""


def test_blocks_drop_menus_footer_and_scripts():
    texts = [t for _, t in html_to_blocks(PAGE)]
    assert "Congratulations Anuj Agnihotri, AIR 1 in UPSC CSE 2025." in texts
    assert "image: Anuj Agnihotri poster" in texts
    joined = " ".join(texts)
    assert "GS Foundation Course" not in joined
    assert "Mains Test Series" not in joined
    assert "Best IAS coaching" not in joined
    assert "var courses" not in joined


def test_filter_keeps_relevant_blocks_and_neighbours():
    blocks = [(0, "a"), (1, "b"), (2, "Anuj"), (3, "c"), (4, "d")]
    assert filter_blocks(blocks, lambda t: t == "Anuj") == [(1, "b"), (2, "Anuj"), (3, "c")]


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    if request.url.path == "/report.pdf":
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
    return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=PAGE)


def fetcher():
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LivePageFetcher(client=client, min_interval=0, today="2026-10-06")


def test_live_fetch_ok_robots_and_non_html():
    f = fetcher()
    ok = f.fetch("https://inst.test/anuj")
    assert ok.error is None and ok.fetched_at == "2026-10-06" and ok.html_sha256
    assert f.fetch("https://inst.test/private/x").error == "robots_disallowed"
    assert f.fetch("https://inst.test/report.pdf").error == "not_html"


def test_replay_page(tmp_path):
    path = page_fixture_path(tmp_path, "https://inst.test/anuj")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"url": "https://inst.test/anuj", "status": 200, "fetched_at": "2026-10-06",
                                "html_sha256": "ab", "blocks": [[2, "Anuj"]], "error": None}), encoding="utf-8")
    snap = ReplayPageFetcher(tmp_path).fetch("https://inst.test/anuj")
    assert snap.blocks == ((2, "Anuj"),)
    assert ReplayPageFetcher(tmp_path).fetch("https://inst.test/other").error == "missing_fixture"
```

`tests/test_images.py`:
```python
import httpx

from toppertrail.fetch.images import LiveImageReader, ReplayImageReader


def test_live_image_reader_runs_ocr_and_hashes():
    def handler(request):
        if request.url.path == "/a.png":
            return httpx.Response(200, headers={"content-type": "image/png"}, content=b"PNGDATA")
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html></html>")

    reader = LiveImageReader(ocr=lambda data: "AIR 1 ANUJ AGNIHOTRI" if data == b"PNGDATA" else "",
                             client=httpx.Client(transport=httpx.MockTransport(handler)))
    it = reader.read("https://img.test/a.png")
    assert it.text == "AIR 1 ANUJ AGNIHOTRI" and it.image_sha256 and it.error is None
    assert reader.read("https://img.test/page").error == "not_image"


def test_replay_image_missing(tmp_path):
    assert ReplayImageReader(tmp_path).read("https://img.test/a.png").error == "missing_fixture"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_pages.py tests/test_images.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.fetch'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/fetch/pages.py`:
```python
from __future__ import annotations

import json
import re
import time
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from selectolax.parser import HTMLParser, Node

from toppertrail.hashing import sha256_bytes, short_hash

USER_AGENT = "TopperTrail/0.1 (+https://github.com/; research on public coaching claims)"
_REMOVE = (
    "script", "style", "noscript", "template", "svg", "iframe", "form", "nav", "aside",
    "body > header", "body > footer", "footer", "header nav", "[role=navigation]",
    "[role=banner]", "[role=contentinfo]", "[aria-hidden=true]", "[class*=menu]", "[id*=menu]",
    "[class*=navbar]", "[class*=footer]", "[id*=footer]", "[class*=breadcrumb]",
    "[class*=sidebar]", "[class*=cookie]",
)
_BLOCKS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "figcaption",
           "blockquote", "dt", "dd", "caption", "div", "section", "article"}


@dataclass(frozen=True)
class PageSnapshot:
    url: str
    status: int
    fetched_at: str
    html_sha256: str | None
    blocks: tuple[tuple[int, str], ...]
    error: str | None


def snapshot_from_dict(d: dict) -> PageSnapshot:
    return PageSnapshot(d["url"], int(d["status"]), d["fetched_at"], d.get("html_sha256"),
                        tuple((int(i), t) for i, t in d.get("blocks") or ()), d.get("error"))


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _walk(node: Node, out: list[str]) -> bool:
    """Append leaf block texts in document order; return True if the subtree holds a block."""
    contains = False
    child = node.child
    while child is not None:
        if child.tag not in ("-text", "-comment") and _walk(child, out):
            contains = True
        child = child.next
    if node.tag == "img":
        alt = _clean(node.attributes.get("alt") or "")
        if alt:
            out.append(f"image: {alt}")
        return False
    if node.tag in _BLOCKS:
        if not contains:
            text = _clean(node.text(deep=True, separator=" "))
            if len(text) > 1:
                out.append(text)
        return True
    return contains


def html_to_blocks(html: str) -> list[tuple[int, str]]:
    tree = HTMLParser(html)
    for selector in _REMOVE:
        for node in tree.css(selector):
            node.decompose()
    root = tree.body or tree.root
    texts: list[str] = []
    if root is not None:
        _walk(root, texts)
    deduped = [t for i, t in enumerate(texts) if i == 0 or t != texts[i - 1]]
    return list(enumerate(deduped))


def filter_blocks(blocks: list[tuple[int, str]], relevant: Callable[[str], bool]) -> list[tuple[int, str]]:
    keep: set[int] = set()
    index = {i for i, _ in blocks}
    for i, text in blocks:
        if relevant(text):
            keep.update(j for j in (i - 1, i, i + 1) if j in index)
    return [(i, t) for i, t in blocks if i in keep]


def page_fixture_path(root: Path, url: str) -> Path:
    return Path(root) / "pages" / f"{short_hash(url)}.json"


class LivePageFetcher:
    def __init__(self, client: httpx.Client | None = None, min_interval: float = 1.0,
                 max_bytes: int = 2_000_000, timeout: float = 10.0,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, today: str | None = None) -> None:
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True,
                                              headers={"User-Agent": USER_AGENT})
        self.min_interval = min_interval
        self.max_bytes = max_bytes
        self._sleep, self._clock = sleep, clock
        self._today = today
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last: dict[str, float] = {}

    def _date(self) -> str:
        return self._today or datetime.now(UTC).date().isoformat()

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self._client.get(base + "/robots.txt")
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                rp.parse([])
            self._robots[base] = rp
        return rp.can_fetch(USER_AGENT, url)

    def _throttle(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            wait = self.min_interval - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        self._last[host] = self._clock()

    def fetch(self, url: str) -> PageSnapshot:
        day = self._date()
        if not self._allowed(url):
            return PageSnapshot(url, 0, day, None, (), "robots_disallowed")
        self._throttle(urlsplit(url).netloc)
        try:
            with self._client.stream("GET", url) as r:
                if "html" not in r.headers.get("content-type", ""):
                    return PageSnapshot(url, r.status_code, day, None, (), "not_html")
                if r.status_code >= 400:
                    return PageSnapshot(url, r.status_code, day, None, (), f"http_{r.status_code}")
                body = b""
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > self.max_bytes:
                        return PageSnapshot(url, r.status_code, day, None, (), "too_large")
                encoding = r.encoding or "utf-8"
                status = r.status_code
        except httpx.HTTPError as err:
            return PageSnapshot(url, 0, day, None, (), f"fetch_error:{type(err).__name__}")
        html = body.decode(encoding, errors="replace")
        return PageSnapshot(url, status, day, sha256_bytes(body), tuple(html_to_blocks(html)), None)


class ReplayPageFetcher:
    def __init__(self, fixtures: Path) -> None:
        self.fixtures = Path(fixtures)

    def fetch(self, url: str) -> PageSnapshot:
        path = page_fixture_path(self.fixtures, url)
        if not path.exists():
            return PageSnapshot(url, 0, "", None, (), "missing_fixture")
        return snapshot_from_dict(json.loads(path.read_text(encoding="utf-8")))
```

`toppertrail/fetch/images.py`:
```python
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from toppertrail.fetch.pages import USER_AGENT
from toppertrail.hashing import sha256_bytes, short_hash


@dataclass(frozen=True)
class ImageText:
    url: str
    image_sha256: str | None
    text: str
    error: str | None


def image_fixture_path(root: Path, url: str) -> Path:
    return Path(root) / "images" / f"{short_hash(url)}.json"


class LiveImageReader:
    def __init__(self, ocr: Callable[[bytes], str], client: httpx.Client | None = None,
                 max_bytes: int = 5_000_000) -> None:
        self._ocr = ocr
        self._client = client or httpx.Client(timeout=15.0, follow_redirects=True,
                                              headers={"User-Agent": USER_AGENT})
        self.max_bytes = max_bytes

    def read(self, url: str) -> ImageText:
        try:
            r = self._client.get(url)
        except httpx.HTTPError as err:
            return ImageText(url, None, "", f"fetch_error:{type(err).__name__}")
        if r.status_code >= 400:
            return ImageText(url, None, "", f"http_{r.status_code}")
        if not r.headers.get("content-type", "").startswith("image/"):
            return ImageText(url, None, "", "not_image")
        if len(r.content) > self.max_bytes:
            return ImageText(url, None, "", "too_large")
        try:
            text = self._ocr(r.content)
        except Exception as err:  # OCR engines raise many types on odd images
            return ImageText(url, sha256_bytes(r.content), "", f"ocr_error:{type(err).__name__}")
        return ImageText(url, sha256_bytes(r.content), text, None)


class ReplayImageReader:
    def __init__(self, fixtures: Path) -> None:
        self.fixtures = Path(fixtures)

    def read(self, url: str) -> ImageText:
        path = image_fixture_path(self.fixtures, url)
        if not path.exists():
            return ImageText(url, None, "", "missing_fixture")
        d = json.loads(path.read_text(encoding="utf-8"))
        return ImageText(d["url"], d.get("image_sha256"), d.get("text", ""), d.get("error"))


def load_rapidocr() -> Callable[[bytes], str] | None:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    engine = RapidOCR()

    def run(data: bytes) -> str:
        result, _ = engine(data)
        if not result:
            return ""
        rows = sorted(result, key=lambda r: (round(r[0][0][1] / 12), r[0][0][0]))
        return "\n".join(r[1] for r in rows)

    return run
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_pages.py tests/test_images.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/fetch/ tests/test_pages.py tests/test_images.py`. Suggested message: `feat: polite page snapshots, menu-free blocks and image text readers`.

---

### Task 10: Claim extraction

**Files:**
- Create: `toppertrail/extract/claims.py`
- Test: `tests/test_claims.py`

**Interfaces:**
- Consumes: `Exam`, `Topper`, `Institute`, `Claim`, `Signal` (Task 6); `mentions`, `context_ok` (Task 6); `Registry` (Task 7); `Lexicon` (Task 8); `short_hash` (Task 1).
- Produces: `ClaimExtractor(exam, toppers, registry, lexicon)` with `from_blocks(inst, url, title, blocks, source_type, search_id, evidence, observed_at, require_year=True) -> tuple[list[Claim], list[Signal], list[dict]]`.

- [ ] **Step 1: Write the failing test**

`tests/test_claims.py`:
```python
from datetime import date

import pytest

from toppertrail.data import load_exam, load_registry, load_roster
from toppertrail.extract.claims import ClaimExtractor
from toppertrail.extract.courses import Lexicon
from toppertrail.fetch.pages import html_to_blocks


@pytest.fixture(scope="module")
def ex():
    exam = load_exam("upsc-cse-2025")
    return ClaimExtractor(exam, load_roster(exam, 20), load_registry(), Lexicon.load())


def run(ex, blocks, inst="vajiram-ravi", url="https://vajiramandravi.com/x", title="UPSC CSE 2025 toppers",
        source="web_page"):
    reg = load_registry()
    return ex.from_blocks(reg.get(inst), url, title, blocks, source, "sid1", ("sha1",), "2026-10-06")


def test_menu_page_without_course_gets_no_course(ex):
    page = ("<nav><li>GS Foundation Course</li><li>IGP</li></nav>"
            "<main><p>Congratulations Anuj Agnihotri, AIR 1 in UPSC CSE 2025.</p></main>")
    claims, _, _ = run(ex, html_to_blocks(page))
    assert len(claims) == 1
    assert claims[0].course_types == ()
    assert claims[0].claimed_rank == 1


def test_neighbour_block_naming_another_topper_is_not_in_window(ex):
    blocks = [(0, "AIR 1 Anuj Agnihotri"), (1, "AIR 2 Rajeshwari Suve M (IGP)")]
    claims, _, _ = run(ex, blocks)
    by_rank = {c.rank: c for c in claims}
    assert by_rank[1].course_types == ()
    assert by_rank[2].course_types == ("interview_only",)


def test_neighbour_block_without_topper_joins_window(ex):
    blocks = [(0, "Anuj Agnihotri AIR 1 UPSC CSE 2025"), (1, "Courses joined: CA-VA Program, IGP")]
    claims, _, _ = run(ex, blocks)
    assert claims[0].course_types == ("current_affairs", "interview_only")


def test_context_missing_year_is_unresolved(ex):
    claims, _, unresolved = run(ex, [(0, "Anuj Agnihotri spoke at our event")], title="Event")
    assert claims == [] and unresolved[0]["rank"] == 1


def test_signals_and_claim_id_stability(ex):
    blocks = [(0, "Top 10 Out of 10 Rankers in UPSC CSE 2025 From Vajiram & Ravi's Various Courses"),
              (1, "Anuj Agnihotri AIR 1")]
    claims, signals, _ = run(ex, blocks)
    assert {s.rule_id for s in signals} == {"TT-11"}
    again, _, _ = run(ex, blocks)
    assert claims[0].claim_id == again[0].claim_id
    assert claims[0].vague_label is True


def test_cross_exam_name_collision_rejected():
    exam = load_exam("jee-adv-2026")
    ex = ClaimExtractor(exam, load_roster(exam, 5), load_registry(), Lexicon.load())
    reg = load_registry()
    claims, _, unresolved = ex.from_blocks(
        reg.get("vision-ias"), "https://visionias.in/x", "UPSC CSE 2020 result",
        [(0, "Shubham Kumar AIR 1 UPSC CSE 2020")], "web_page", None, (), "2026-10-06")
    assert claims == [] and unresolved
    _ = date
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_claims.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.extract.claims'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/extract/claims.py`:
```python
from __future__ import annotations

from collections.abc import Sequence

from toppertrail.data import Registry
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.text import context_ok, mentions
from toppertrail.hashing import short_hash
from toppertrail.models import Claim, Exam, Institute, Signal, Topper

WINDOW_LIMIT = 600


class ClaimExtractor:
    """Turns institute-controlled text blocks into claim observations and institute signals."""

    def __init__(self, exam: Exam, toppers: Sequence[Topper], registry: Registry,
                 lexicon: Lexicon) -> None:
        self.exam = exam
        self.toppers = list(toppers)
        self.registry = registry
        self.lexicon = lexicon

    def _claim(self, topper: Topper, inst: Institute, source_type: str, url: str, title: str,
               window: str, claimed_rank: int | None, search_id: str | None,
               evidence: tuple[str, ...], observed_at: str) -> Claim:
        cm = self.lexicon.classify(window)
        cid = short_hash(f"{self.exam.id}|{topper.rank}|{inst.id}|{source_type}|{url}")
        return Claim(
            claim_id=cid, exam_id=self.exam.id, rank=topper.rank, institute_id=inst.id,
            source_type=source_type, url=url, title=title, window=window[:WINDOW_LIMIT],
            course_types=cm.course_types, course_terms=cm.terms,
            paid_free_stated=cm.paid_free, duration_stated=cm.duration,
            vague_label=cm.vague and not cm.course_types, claimed_rank=claimed_rank,
            search_id=search_id, evidence=tuple(evidence), observed_at=observed_at,
        )

    def _signals(self, inst: Institute, text: str, url: str,
                 evidence: tuple[str, ...]) -> list[Signal]:
        out = [Signal(inst.id, "TT-09", t, url, evidence) for t in self.lexicon.superlatives(text)]
        out += [Signal(inst.id, "TT-10", t, url, evidence) for t in self.lexicon.guarantees(text)]
        out += [Signal(inst.id, "TT-11", t, url, evidence) for t in self.lexicon.aggregates(text)]
        return out

    def from_blocks(self, inst: Institute, url: str, title: str,
                    blocks: Sequence[tuple[int, str]], source_type: str, search_id: str | None,
                    evidence: tuple[str, ...], observed_at: str,
                    require_year: bool = True) -> tuple[list[Claim], list[Signal], list[dict]]:
        index = dict(blocks)
        found = {i: mentions(text, self.toppers) for i, text in blocks}
        claims: list[Claim] = []
        unresolved: list[dict] = []
        done: set[int] = set()
        for i, text in blocks:
            for m in found[i]:
                if m.topper.rank in done:
                    continue
                parts = [text]
                if i - 1 in index and not found.get(i - 1):
                    parts.insert(0, index[i - 1])
                if i + 1 in index and not found.get(i + 1):
                    parts.append(index[i + 1])
                window = "\n".join(parts)
                context = f"{window} {title} {url}"
                if not context_ok(context, self.exam.year, self.exam.context_terms, require_year):
                    unresolved.append({"rank": m.topper.rank, "institute_id": inst.id, "url": url,
                                       "reason": "exam or year not stated near the name"})
                    continue
                done.add(m.topper.rank)
                claims.append(self._claim(m.topper, inst, source_type, url, title, window,
                                          m.claimed_rank, search_id, evidence, observed_at))
        unresolved = [u for u in unresolved if u["rank"] not in done]
        signal_text = "\n".join(t for _, t in blocks)
        return claims, self._signals(inst, signal_text, url, evidence), unresolved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_claims.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/extract/claims.py tests/test_claims.py`. Suggested message: `feat: claim extraction with menu-safe windows and exam context`.

---

### Task 11: Independent interview pick, self-reports, AI Mode answers

**Files:**
- Create: `toppertrail/extract/selfreport.py`, `toppertrail/extract/aianswer.py`
- Test: `tests/test_selfreport.py`, `tests/test_aianswer.py`

**Interfaces:**
- Consumes: `Registry`, `IndependentChannels` (Task 7); `Lexicon`, `GENERIC` (Task 8); `find_name`, `normalize` (Task 6); `SelfReport`, `AIAnswer`, `Claim`, `Topper` (Task 6).
- Produces: `video_id(link) -> str | None`; `parse_length(text) -> int`; `pick_interview(video_results, topper, registry, independent) -> dict | None` (keys `id`, `channel`, `title`); `hosted_videos(video_results, topper, registry, limit) -> list[tuple[str, str]]` (video id, institute id); `self_reports(transcript, rank, video_id, channel, registry, lexicon) -> list[SelfReport]`; `own_words_status(claim, reports, has_interview) -> tuple[str, str]`; `ai_answer(response, rank, registry) -> AIAnswer`; `flatten_text_blocks(blocks) -> str`.

- [ ] **Step 1: Write the failing tests**

`tests/test_selfreport.py`:
```python
import pytest

from toppertrail.data import load_independent, load_registry
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.selfreport import (
    hosted_videos,
    own_words_status,
    parse_length,
    pick_interview,
    self_reports,
)
from toppertrail.models import Claim, Topper

ANUJ = Topper("upsc-cse-2025", 1, "ANUJ AGNIHOTRI")
VIDEOS = [
    {"title": "Anuj Agnihotri AIR 1 | CSE Topper's Mock Interview | NEXT IAS", "link": "https://www.youtube.com/watch?v=8X-e5cJ_L3M",
     "channel": {"name": "NEXT IAS", "link": "https://www.youtube.com/@nextias"}, "length": "27:39"},
    {"title": "Anuj Agnihotri AIR 1 Mock Interview", "link": "https://www.youtube.com/watch?v=uSgHZWfcfvQ",
     "channel": {"name": "Vajiram and Ravi Official", "link": "https://www.youtube.com/channel/UCzelA5kqD9v6k6drK44l4_g"}, "length": "45:39"},
    {"title": "Anuj Agnihotri AIR 1 full story", "link": "https://www.youtube.com/watch?v=KIr6dWSqspI",
     "channel": {"name": "Delhi Knowledge Track", "link": "https://www.youtube.com/@DelhiKnowledgeTrack"}, "length": "1:31:05"},
    {"title": "Anuj Agnihotri strategy", "link": "https://www.youtube.com/watch?v=zzzzzzzzzzz",
     "channel": {"name": "Random Prep", "link": "https://www.youtube.com/@randomprep"}, "length": "2:01:00"},
]

TRANSCRIPT = [
    {"start_ms": 0, "snippet": "इन द लेटेस्ट यूपीएससी रिजल्ट 2025, टॉप"},
    {"start_ms": 3000, "snippet": "10 आउट ऑफ टॉप 10 आर फ्रॉम वेरियस कोर्सेज"},
    {"start_ms": 6000, "snippet": "ऑफ वाजराम एंड रवि विद ऑल इंडिया रैंक वन"},
    {"start_ms": 1402000, "snippet": "उस समय Unacademy का मुझे लगा था"},
    {"start_ms": 1505000, "snippet": "इसके अलावा मैंने उसके बाद कोई कोचिंग नहीं ली"},
    {"start_ms": 1807000, "snippet": "मॉक इंटरव्यूज में मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया"},
    {"start_ms": 1810000, "snippet": "पीडब्ल्यू का मॉक दिया"},
    {"start_ms": 4045000, "snippet": "मैंने टेस्ट सीरीज शायद कभी जॉइ नहीं करी"},
]


@pytest.fixture(scope="module")
def reports():
    return self_reports(TRANSCRIPT, 1, "KIr6dWSqspI", "Delhi Knowledge Track", load_registry(), Lexicon.load())


def claim(iid, types):
    return Claim("c", "upsc-cse-2025", 1, iid, "web_page", "u", "t", "w", types, (), False, False, False,
                 1, None, (), "2026-10-06")


def test_parse_length():
    assert parse_length("1:31:05") == 5465 and parse_length("27:39") == 1659 and parse_length("") == 0


def test_pick_interview_prefers_allowlisted_independent_channel():
    pick = pick_interview(VIDEOS, ANUJ, load_registry(), load_independent())
    assert pick == {"id": "KIr6dWSqspI", "channel": "Delhi Knowledge Track", "title": "Anuj Agnihotri AIR 1 full story"}


def test_hosted_videos_one_per_institute():
    assert hosted_videos(VIDEOS, ANUJ, load_registry(), 2) == [("8X-e5cJ_L3M", "next-ias"), ("uSgHZWfcfvQ", "vajiram-ravi")]


def test_sponsor_read_is_not_a_self_report(reports):
    assert all(r.institute_id != "vajiram-ravi" for r in reports)


def test_self_reports_capture_affirm_and_deny(reports):
    got = {(r.institute_id, r.polarity) for r in reports}
    assert ("unacademy", "affirm") in got
    assert ("next-ias", "affirm") in got
    assert ("physics-wallah", "affirm") in got
    deny = [r for r in reports if r.polarity == "deny" and "test_series" in r.course_types]
    assert deny and deny[0].start_ms == 4045000


def test_own_words_status(reports):
    assert own_words_status(claim("next-ias", ("current_affairs",)), reports, True)[0] == "mentioned"
    assert own_words_status(claim("vision-ias", ("test_series",)), reports, True)[0] == "denied"
    assert own_words_status(claim("vajiram-ravi", ("interview_only",)), reports, True)[0] == "not_mentioned"
    assert own_words_status(claim("vajiram-ravi", ()), [], False)[0] == "no_interview"
```

`tests/test_aianswer.py`:
```python
from toppertrail.data import load_registry
from toppertrail.extract.aianswer import ai_answer


def test_ai_answer_lists_named_institutes():
    resp = {
        "search_metadata": {"id": "ai1"},
        "text_blocks": [
            {"type": "paragraph", "snippet": "Anuj Agnihotri prepared largely through self-study."},
            {"type": "list", "list": [{"snippet": "He attended mock interviews at NEXT IAS."},
                                      {"snippet": "Vajiram & Ravi lists him under its Interview Guidance Programme."}]},
        ],
    }
    a = ai_answer(resp, 1, load_registry())
    assert a.institutes == ("next-ias", "vajiram-ravi")
    assert a.search_id == "ai1"
    assert a.excerpt.startswith("Anuj Agnihotri prepared")


def test_ai_answer_empty_response():
    a = ai_answer({"error": "no answer"}, 3, load_registry())
    assert a.institutes == () and a.excerpt == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_selfreport.py tests/test_aianswer.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.extract.selfreport'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/extract/selfreport.py`:
```python
from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import parse_qs, urlsplit

from toppertrail.data import IndependentChannels, Registry
from toppertrail.extract.courses import GENERIC, Lexicon
from toppertrail.extract.text import find_name, normalize
from toppertrail.models import Claim, SelfReport, Topper


def video_id(link: str) -> str | None:
    parts = urlsplit(link or "")
    if parts.hostname and parts.hostname.endswith("youtu.be"):
        return parts.path.strip("/") or None
    return (parse_qs(parts.query).get("v") or [None])[0]


def parse_length(text: str) -> int:
    try:
        nums = [int(x) for x in (text or "").split(":")]
    except ValueError:
        return 0
    total = 0
    for n in nums:
        total = total * 60 + n
    return total


def pick_interview(video_results: Sequence[dict], topper: Topper, registry: Registry,
                   independent: IndependentChannels) -> dict | None:
    candidates = []
    for pos, v in enumerate(video_results):
        title = v.get("title") or ""
        ch = v.get("channel") or {}
        vid = video_id(v.get("link") or "")
        if not vid or not find_name(title, topper.name) or "mock" in normalize(title):
            continue
        if registry.by_channel(ch.get("link"), ch.get("name")):
            continue
        listed = independent.match(ch.get("link"), ch.get("name"))
        candidates.append((0 if listed else 1, -parse_length(v.get("length") or ""), pos,
                           {"id": vid, "channel": ch.get("name") or "", "title": title}))
    return min(candidates, key=lambda c: c[:3])[3] if candidates else None


def hosted_videos(video_results: Sequence[dict], topper: Topper, registry: Registry,
                  limit: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for v in video_results:
        ch = v.get("channel") or {}
        inst = registry.by_channel(ch.get("link"), ch.get("name"))
        vid = video_id(v.get("link") or "")
        if not inst or not vid or inst.id in seen or not find_name(v.get("title") or "", topper.name):
            continue
        seen.add(inst.id)
        out.append((vid, inst.id))
        if len(out) >= limit:
            break
    return out


NEAR_MS = 15_000  # caption segments further apart than this are not one statement


def self_reports(transcript: Sequence[dict], rank: int, vid: str, channel: str,
                 registry: Registry, lexicon: Lexicon) -> list[SelfReport]:
    segs = [(int(s.get("start_ms") or 0), s.get("snippet") or "") for s in transcript]
    out: list[SelfReport] = []
    seen: set[tuple] = set()

    def near(lo: int, hi: int, start: int) -> str:
        return " ".join(t for s, t in segs[max(0, lo): hi] if abs(s - start) <= NEAR_MS)

    for i, (start, text) in enumerate(segs):
        insts = registry.find_aliases(text)
        anchor = lexicon.classify(text, include_generic=True)
        if not insts and not anchor.course_types:
            continue
        around = near(i - 1, i + 2, start)
        if not lexicon.first_person(around):
            continue
        tail = near(i, i + 2, start)
        polarity = "deny" if lexicon.negated(tail) else "affirm"
        types = lexicon.classify(tail, include_generic=True).course_types
        for iid in insts or [None]:
            key = (iid, types, polarity)
            if key in seen:
                continue
            seen.add(key)
            out.append(SelfReport(rank, vid, channel, start, around[:300], iid, types, polarity))
    return out


def _clock(ms: int) -> str:
    s = ms // 1000
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def own_words_status(claim: Claim, reports: Sequence[SelfReport], has_interview: bool) -> tuple[str, str]:
    if not has_interview:
        return "no_interview", "No independent interview with a transcript was found."
    affirm = [r for r in reports if r.institute_id == claim.institute_id and r.polarity == "affirm"]
    if affirm:
        said = sorted({c for r in affirm for c in r.course_types if c != GENERIC})
        what = ", ".join(said) if said else "course not said"
        return "mentioned", f"The topper mentions this institute ({what}) at {_clock(affirm[0].start_ms)}."
    claimed = set(claim.course_types)
    for r in reports:
        if r.polarity != "deny" or r.institute_id not in (None, claim.institute_id):
            continue
        types = set(r.course_types)
        if claimed & types or (GENERIC in types and "foundation_classroom" in claimed):
            return "denied", (f"At {_clock(r.start_ms)} the topper's own words do not match the "
                              f"course this claim names.")
    return "not_mentioned", "The topper does not mention this institute in the interview."
```

`toppertrail/extract/aianswer.py`:
```python
from __future__ import annotations

from typing import Any

from toppertrail.data import Registry
from toppertrail.models import AIAnswer


def flatten_text_blocks(blocks: Any) -> str:
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("snippet"), str):
                parts.append(node["snippet"])
            for key, value in node.items():
                if key != "snippet":
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(blocks)
    return " ".join(p.strip() for p in parts if p.strip())


def ai_answer(response: dict, rank: int, registry: Registry) -> AIAnswer:
    text = flatten_text_blocks(response.get("text_blocks") or [])
    if not text and isinstance(response.get("reconstructed_markdown"), str):
        text = response["reconstructed_markdown"]
    sid = (response.get("search_metadata") or {}).get("id")
    return AIAnswer(rank, "google_ai_mode", sid, tuple(registry.find_aliases(text)), text[:500])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_selfreport.py tests/test_aianswer.py -q`
Expected: `9 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/extract/selfreport.py toppertrail/extract/aianswer.py tests/test_selfreport.py tests/test_aianswer.py`. Suggested message: `feat: topper's own words from transcripts and AI Mode attributions`.

---

### Task 12: Rule engine, CCPA order suite, validate command

**Files:**
- Create: `toppertrail/rules.py`, `scripts/build_orders.py`, `toppertrail/data/ccpa/orders.yaml`, `toppertrail/data/ccpa/guidelines-2024.md`, `docs/VALIDATION.md`
- Modify: `toppertrail/cli.py` (add `validate`)
- Test: `tests/test_rules.py`, `tests/test_validation.py`

**Interfaces:**
- Consumes: models (Task 6); `Registry` (Task 7); `Lexicon`, `INTERVIEW_ONLY` (Task 8); `own_words_status` (Task 11).
- Produces: `RULES: dict[str, tuple[str, str]]` (title, basis); `claim_flags(claim, exam, registry) -> list[Flag]`; `cross_flags(claims) -> list[Flag]`; `signal_flags(signals, claims) -> list[Flag]`; `own_words_flags(claims, reports, interviews) -> list[Flag]`; `apply_rules(exam, claims, signals, reports, interviews, registry) -> list[Flag]`; `load_orders() -> list[dict]`; `score_orders(orders, lexicon) -> dict`.

- [ ] **Step 1: Build `orders.yaml` from the research file, then annotate expected flags before any scoring**

`scripts/build_orders.py`:
```python
"""Convert the research case file into toppertrail/data/ccpa/orders.yaml (claims without labels).

Usage: python scripts/build_orders.py <path to ccpa_coaching_cases.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

src = Path(sys.argv[1])
cases = json.loads(src.read_text(encoding="utf-8"))
out = []
for c in cases:
    out.append({
        "id": c["id"], "institute": c["institute"], "domain": c.get("domain"),
        "exam": c["exam"], "exam_year": c.get("exam_year"), "order_date": c["order_date"],
        "penalty_inr": c.get("penalty_inr"), "order_pdf": c.get("order_pdf"), "pib": c.get("pib"),
        "claims": [{"text": t, "expected": []} for t in c.get("claims", [])],
    })
dest = Path("toppertrail/data/ccpa/orders.yaml")
dest.parent.mkdir(parents=True, exist_ok=True)
doc = {"orders": out, "course_labels": []}
dest.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=120),
                encoding="utf-8", newline="\n")
print(f"wrote {len(out)} orders, {sum(len(o['claims']) for o in out)} claim texts")
```

Run:
```bash
.venv/Scripts/python scripts/build_orders.py "C:/Users/MONSTER/AppData/Local/Temp/claude/C--Users-MONSTER--local-bin/479b2c98-bcd3-4dbd-a93c-a580e3026e3c/scratchpad/toppertrail/ccpa_coaching_cases.json"
```
Expected: `wrote 33 orders, 9x claim texts` (about 92).

Then annotate each claim's `expected` list by reading the text only, never by running the engine, using these definitions:
- `TT-11` if the text states a count, share or top-N position of selections ("8 Rank Holders in the Top 10", "120+ selections", "26% of all UPSC rankers", "All TOP 5 ...").
- `TT-09` if the text uses a superlative about the institute ("Best", "No. 1", "India's top", "1st position").
- `TT-10` if the text promises an outcome ("guaranteed", "pakka", "100% selection", "है तो सिलेक्शन है").

Replace the empty `course_labels: []` at the end of the file with this list (labels quoted in CCPA findings, with expected types):
```yaml
course_labels:
  - {label: "GS FOUNDATION BATCH CLASSROOM STUDENT", types: [foundation_classroom]}
  - {label: "Mock Interview / Free of cost", types: [interview_only], paid_free: true}
  - {label: "Interview Guidance Programme", types: [interview_only]}
  - {label: "IGP (DAF Analysis)", types: [interview_only]}
  - {label: "IGP [WhatsApp Group]", types: [interview_only]}
  - {label: "Last Mile", types: [interview_only]}
  - {label: "free 5-day Interview Training Program", types: [interview_only], paid_free: true, duration: true}
  - {label: "Mock Interview Programme / 1 Day / 0", types: [interview_only], duration: true}
  - {label: "GS Mains Test Series 2020", types: [test_series]}
  - {label: "Abhyaas 2020", types: [test_series]}
  - {label: "Ethics & Essay Crash", types: [essay_ethics]}
  - {label: "PSIR optional", types: [optional]}
  - {label: "Mains Mentorship", types: [mentorship]}
  - {label: "GS Prelims cum Mains", types: [foundation_classroom]}
  - {label: "General Studies PCM 10-Month Course", types: [foundation_classroom], duration: true}
  - {label: "I-Eklavya (Online)", types: [online_distance]}
  - {label: "DLP", types: [online_distance]}
  - {label: "Target Course", types: [foundation_classroom]}
  - {label: "fresher", types: [], vague: true}
  - {label: "With XII", types: [], vague: true}
  - {label: "repeaters", types: [], vague: true}
```

Freeze: compute the hash and write it to `docs/VALIDATION.md` before Step 5.

Run: `.venv/Scripts/python -c "import hashlib;print(hashlib.sha256(open('toppertrail/data/ccpa/orders.yaml','rb').read()).hexdigest())"`

`docs/VALIDATION.md` (initial):
```markdown
# Validation

## CCPA order suite

The claim texts of 33 CCPA coaching orders (2023 to 2026) and 21 course labels quoted in CCPA findings were labelled by the author from the text alone, before the rule engine was scored.

Frozen file: `toppertrail/data/ccpa/orders.yaml`, SHA-256 `<paste hash>`, frozen on 2026-10-07.

Results are pasted below exactly as printed by `toppertrail validate`. The frozen file is not edited after scoring.
```

Also write `toppertrail/data/ccpa/guidelines-2024.md` with the verbatim clauses 1(3), 2(1)(c), 2(1)(d), 3(a) to 3(f), 4(1)(a) to 4(1)(f), 4(2) of the 2024 Guidelines, section 2(28) of the Consumer Protection Act 2019, and clauses 11, 12(a), 12(c), 13(1), 14 of the 2022 Guidelines, each with the source URL from the spec (text available in the research notes, section 1).

- [ ] **Step 2: Write the failing tests**

`tests/test_rules.py`:
```python
from toppertrail.data import load_exam, load_registry
from toppertrail.models import Claim, Interview, SelfReport, Signal
from toppertrail.rules import RULES, apply_rules

EXAM = load_exam("upsc-cse-2025")
BANNED = ("false", "fake", "fraud", "lie", "misleading")


def c(cid, iid, rank, types=(), url="u1", source="web_page", claimed=None, paid=False, dur=False, vague=False):
    return Claim(cid, EXAM.id, rank, iid, source, url, "t", "w", types, (), paid, dur, vague, claimed,
                 None, (), "2026-10-06")


def rules_for(flags, cid):
    return sorted(f.rule_id for f in flags if f.claim_id == cid)


def test_claim_level_rules():
    claims = [c("a", "vajiram-ravi", 1, ("interview_only",), claimed=2),
              c("b", "allen", 1, (), source="ad_creative", vague=True, url="u2")]
    flags = apply_rules(EXAM, claims, [], [], [], load_registry())
    assert rules_for(flags, "a") == ["TT-02", "TT-04", "TT-05", "TT-08", "TT-12"]
    assert rules_for(flags, "b") == ["TT-01", "TT-03", "TT-04", "TT-05", "TT-12", "TT-13", "TT-14"]


def test_cross_rules_inconsistent_labels_and_selective_page():
    claims = [c("a", "next-ias", 1, ("current_affairs",), url="p1"),
              c("b", "next-ias", 1, ("current_affairs", "interview_only"), url="v1", source="youtube_description"),
              c("x", "vision-ias", 1, ("test_series",), url="list"),
              c("y", "vision-ias", 2, (), url="list")]
    flags = apply_rules(EXAM, claims, [], [], [], load_registry())
    assert "TT-06" in rules_for(flags, "a") and "TT-06" in rules_for(flags, "b")
    assert "TT-07" in rules_for(flags, "y") and "TT-07" not in rules_for(flags, "x")


def test_signal_rules_and_own_words():
    claims = [c("a", "vajiram-ravi", 1, ("interview_only",))]
    signals = [Signal("vajiram-ravi", "TT-11", "top 10 out of 10", "u1", ()),
               Signal("vajiram-ravi", "TT-11", "top 10 out of 10", "u9", ())]
    interviews = [Interview(1, "KIr6dWSqspI", "Delhi Knowledge Track", "t", "hi")]
    reports = [SelfReport(1, "KIr6dWSqspI", "DKT", 1807000, "मैंने नेक्स्ट आईएएस का मॉक", "next-ias", ("interview_only",), "affirm")]
    flags = apply_rules(EXAM, claims, signals, reports, interviews, load_registry())
    tt11 = [f for f in flags if f.rule_id == "TT-11"]
    assert len(tt11) == 1 and "1 name only an interview programme" in tt11[0].detail
    tt12 = [f for f in flags if f.rule_id == "TT-12"]
    assert tt12[0].code == "not_mentioned"


def test_wording_never_accuses():
    claims = [c("a", "vajiram-ravi", 1, ("interview_only",), claimed=3)]
    signals = [Signal("vajiram-ravi", "TT-09", "best ias", "u", ()), Signal("vajiram-ravi", "TT-10", "pakka", "u", ())]
    flags = apply_rules(EXAM, claims, signals, [], [], load_registry())
    texts = [t for t, _ in RULES.values()] + [f.detail for f in flags]
    assert not [t for t in texts if any(b in t.lower() for b in BANNED)]
```

`tests/test_validation.py`:
```python
from toppertrail.extract.courses import Lexicon
from toppertrail.rules import load_orders, score_orders


def test_orders_file_is_complete_and_scores():
    data = load_orders()
    assert len(data["orders"]) == 33
    assert sum(len(o["claims"]) for o in data["orders"]) >= 80
    assert len(data["course_labels"]) == 21
    scores = score_orders(data, Lexicon.load())
    for rule in ("TT-09", "TT-10", "TT-11"):
        assert set(scores[rule]) == {"tp", "fp", "fn", "precision", "recall"}
    assert 0.0 <= scores["course_labels"]["exact"] <= 1.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_rules.py tests/test_validation.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.rules'`.

- [ ] **Step 4: Write the implementation**

`toppertrail/rules.py`:
```python
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

import yaml

from toppertrail.data import Registry, read_data
from toppertrail.extract.courses import INTERVIEW_ONLY, Lexicon
from toppertrail.extract.selfreport import own_words_status
from toppertrail.models import Claim, Exam, Flag, Interview, SelfReport, Signal

RULES: dict[str, tuple[str, str]] = {
    "TT-01": ("Course not stated next to the claim",
              "Guidelines 2024, cl. 4(1)(a); CCPA directions in the NEXT IAS order of 07.09.2026"),
    "TT-02": ("Interview-only programme",
              "CCPA findings in the Vajiram & Ravi, KSG, Chahal, Drishti and StudyIQ orders"),
    "TT-03": ("Vague course label", "CCPA order against Career Line Coaching, Sikar, 09.04.2026"),
    "TT-04": ("Paid or free not stated", "Guidelines 2024, cl. 4(1)(a)"),
    "TT-05": ("Course duration not stated", "Guidelines 2024, cl. 4(1)(a)"),
    "TT-06": ("Different course labels across the institute's own sources",
              "Guidelines 2024, cl. 4(1)(e)"),
    "TT-07": ("Selective disclosure on one page",
              "CCPA orders against Vision IAS (18.12.2025) and Narayana (11.06.2026)"),
    "TT-08": ("Rank differs from the official result",
              "Guidelines 2024, cl. 3(b); CCPA order against Narayana (11.06.2026)"),
    "TT-09": ("Unsubstantiated superlative",
              "2022 Guidelines, cl. 12(a); CCPA orders against Chahal, Rau's and Sriram's"),
    "TT-10": ("Guarantee language", "Guidelines 2024, cl. 3(c); CCPA orders against Motion and StudyIQ"),
    "TT-11": ("Aggregate count claim", "Guidelines 2024, cl. 3(b)"),
    "TT-12": ("Topper's own words", "The topper's independent interview transcript (YouTube)"),
    "TT-13": ("Claimed for a different exam", "Informational"),
    "TT-14": ("Featured in a paid Google ad in India", "Google Ads Transparency Center, region India"),
}


def _interview_only(types: Sequence[str]) -> bool:
    return bool(types) and set(types) <= {INTERVIEW_ONLY}


def claim_flags(c: Claim, exam: Exam, registry: Registry) -> list[Flag]:
    out: list[Flag] = []

    def add(rule: str, detail: str) -> None:
        out.append(Flag(rule, c.institute_id, c.claim_id, c.rank, detail))

    if not c.course_types:
        add("TT-01", "No course name appears next to this claim.")
    elif _interview_only(c.course_types):
        add("TT-02", "Only an interview programme is named: " + ", ".join(c.course_terms) + ".")
    if c.vague_label:
        add("TT-03", "The label used does not name a course.")
    if not c.paid_free_stated:
        add("TT-04", "Whether the course was paid or free is not stated.")
    if not c.duration_stated:
        add("TT-05", "The course duration is not stated.")
    if c.claimed_rank is not None and c.claimed_rank != c.rank:
        add("TT-08", f"Shows rank {c.claimed_rank}; the official {exam.rank_label} is {c.rank}.")
    if exam.tag not in registry.get(c.institute_id).exams:
        add("TT-13", f"This institute's registered exams do not include {exam.label}.")
    if c.source_type == "ad_creative":
        add("TT-14", "This claim appeared in a Google ad shown in India after the result.")
    return out


def cross_flags(claims: Sequence[Claim]) -> list[Flag]:
    out: list[Flag] = []
    groups: dict[tuple[str, int], list[Claim]] = defaultdict(list)
    for c in claims:
        groups[(c.institute_id, c.rank)].append(c)
    for (iid, rank), cs in sorted(groups.items()):
        sets = sorted({c.course_types for c in cs if c.course_types})
        if len(sets) > 1:
            labels = "; ".join(", ".join(s) for s in sets)
            for c in cs:
                if c.course_types:
                    out.append(Flag("TT-06", iid, c.claim_id, rank,
                                    f"This institute's own sources name different courses: {labels}."))
    pages: dict[str, list[Claim]] = defaultdict(list)
    for c in claims:
        pages[c.url].append(c)
    for _, cs in sorted(pages.items()):
        if len({c.rank for c in cs}) < 2:
            continue
        stated = [c for c in cs if c.course_types]
        for c in cs:
            if stated and not c.course_types:
                out.append(Flag("TT-07", c.institute_id, c.claim_id, c.rank,
                                f"On this page the course is stated for {len(stated)} topper(s) "
                                f"but not for this one."))
    return out


def signal_flags(signals: Sequence[Signal], claims: Sequence[Claim]) -> list[Flag]:
    named: dict[str, list[Claim]] = defaultdict(list)
    for c in claims:
        named[c.institute_id].append(c)
    out: list[Flag] = []
    seen: set[tuple[str, str, str]] = set()
    for s in sorted(signals, key=lambda s: (s.institute_id, s.rule_id, s.text, s.url)):
        key = (s.institute_id, s.rule_id, s.text)
        if key in seen:
            continue
        seen.add(key)
        if s.rule_id == "TT-11":
            mine = named.get(s.institute_id, [])
            io = sum(1 for c in mine if _interview_only(c.course_types))
            detail = (f'Count claim "{s.text}". Of this institute\'s {len(mine)} named claim(s) '
                      f"in this ledger, {io} name only an interview programme.")
        elif s.rule_id == "TT-09":
            detail = f'Superlative "{s.text}" appears in this institute\'s material.'
        else:
            detail = f'Outcome wording "{s.text}" appears in this institute\'s material.'
        out.append(Flag(s.rule_id, s.institute_id, None, None, detail))
    return out


def own_words_flags(claims: Sequence[Claim], reports: Sequence[SelfReport],
                    interviews: Sequence[Interview]) -> list[Flag]:
    has = {i.rank for i in interviews}
    by_rank: dict[int, list[SelfReport]] = defaultdict(list)
    for r in reports:
        by_rank[r.rank].append(r)
    out = []
    for c in claims:
        code, detail = own_words_status(c, by_rank.get(c.rank, []), c.rank in has)
        out.append(Flag("TT-12", c.institute_id, c.claim_id, c.rank, detail, code))
    return out


def apply_rules(exam: Exam, claims: Sequence[Claim], signals: Sequence[Signal],
                reports: Sequence[SelfReport], interviews: Sequence[Interview],
                registry: Registry) -> list[Flag]:
    flags = [f for c in claims for f in claim_flags(c, exam, registry)]
    flags += cross_flags(claims)
    flags += signal_flags(signals, claims)
    flags += own_words_flags(claims, reports, interviews)
    return sorted(flags, key=lambda f: (f.rule_id, f.institute_id, f.rank or 0, f.claim_id or "",
                                        f.detail))


def load_orders() -> dict:
    return yaml.safe_load(read_data("ccpa/orders.yaml"))


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 3), "recall": round(r, 3)}


def score_orders(data: dict, lexicon: Lexicon) -> dict:
    counts = {rule: [0, 0, 0] for rule in ("TT-09", "TT-10", "TT-11")}
    for order in data["orders"]:
        for claim in order["claims"]:
            predicted = set()
            if lexicon.superlatives(claim["text"]):
                predicted.add("TT-09")
            if lexicon.guarantees(claim["text"]):
                predicted.add("TT-10")
            if lexicon.aggregates(claim["text"]):
                predicted.add("TT-11")
            expected = set(claim.get("expected") or [])
            for rule, cell in counts.items():
                cell[0] += rule in predicted and rule in expected
                cell[1] += rule in predicted and rule not in expected
                cell[2] += rule not in predicted and rule in expected
    out = {rule: _prf(*cell) for rule, cell in counts.items()}
    labels = data.get("course_labels") or []
    exact = 0
    for item in labels:
        m = lexicon.classify(item["label"])
        exact += (set(m.course_types) == set(item["types"])
                  and m.paid_free == bool(item.get("paid_free"))
                  and m.duration == bool(item.get("duration"))
                  and (m.vague and not m.course_types) == bool(item.get("vague")))
    out["course_labels"] = {"n": len(labels), "exact": round(exact / len(labels), 3) if labels else 1.0}
    return out
```

Add to `toppertrail/cli.py` (below `version`):
```python
@app.command()
def validate() -> None:
    """Score the rules against the frozen CCPA order suite and print a Markdown table."""
    from toppertrail.extract.courses import Lexicon
    from toppertrail.rules import load_orders, score_orders

    scores = score_orders(load_orders(), Lexicon.load())
    typer.echo("| Rule | TP | FP | FN | Precision | Recall |")
    typer.echo("|---|---|---|---|---|---|")
    for rule in ("TT-09", "TT-10", "TT-11"):
        s = scores[rule]
        typer.echo(f"| {rule} | {s['tp']} | {s['fp']} | {s['fn']} | {s['precision']} | {s['recall']} |")
    cl = scores["course_labels"]
    typer.echo(f"\nCourse labels classified exactly: {cl['exact']} of {cl['n']} labels (share).")
```

- [ ] **Step 5: Run tests, then score and paste results**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_rules.py tests/test_validation.py -q
.venv/Scripts/python -m toppertrail validate
```
Expected: `5 passed`, then a Markdown table. Paste the table unchanged into `docs/VALIDATION.md` under a heading `## Results (2026-10-07)`. Do not edit `orders.yaml` afterwards; lexicon changes made after this point must be reported as a second, dated results table.

- [ ] **Step 6: Owner checkpoint**

Files: `toppertrail/rules.py toppertrail/cli.py toppertrail/data/ccpa/ scripts/build_orders.py docs/VALIDATION.md tests/test_rules.py tests/test_validation.py`. Suggested message: `feat: deterministic rule engine validated on 33 CCPA orders`.

---

### Task 13: Collection planner, estimator, collector, fixture export, CLI

**Files:**
- Create: `toppertrail/collect.py`
- Modify: `toppertrail/cli.py` (add `estimate`, `collect`, `budget`)
- Test: `tests/test_collect.py`

**Interfaces:**
- Consumes: everything from Tasks 2 to 11.
- Produces: `Planned(engine, params, purpose, rank=None, institute_id=None)`; `topper_queries(exam, topper) -> list[Planned]`; `ads_queries(exam, registry) -> list[Planned]`; `estimate(exam, toppers, registry) -> dict[str, int]`; `Collector(exam, toppers, registry, independent, lexicon, serp, pages, images, store)` with `run() -> Run` and attribute `missing: int`; `export_fixtures(run, store, fixtures) -> int`; `manifest_path(fixtures, exam_id) -> Path`.

- [ ] **Step 1: Write the failing test**

`tests/test_collect.py`:
```python
import json

from toppertrail.collect import Collector, ads_queries, estimate, export_fixtures, topper_queries
from toppertrail.data import load_exam, load_independent, load_registry, load_roster
from toppertrail.evidence import EvidenceStore
from toppertrail.extract.courses import Lexicon
from toppertrail.fetch.images import ImageText
from toppertrail.fetch.pages import PageSnapshot
from toppertrail.serp.base import MissingFixture, SerpResult
from toppertrail.serp.replay import ReplaySerpClient

EXAM = load_exam("upsc-cse-2025")


def test_estimate_matches_spec_budget():
    est = estimate(EXAM, load_roster(EXAM, 20), load_registry())
    assert est == {"google": 30, "google_ads_transparency_center": 15, "google_ai_mode": 20,
                   "google_images": 20, "youtube": 20, "youtube_video": 20,
                   "youtube_video_transcript": 20}
    assert sum(est.values()) == 145


def test_queries_are_formatted():
    q = topper_queries(EXAM, load_roster(EXAM, 1)[0])
    assert q[0].params == {"q": '"Anuj Agnihotri" UPSC CSE 2025 AIR 1', "gl": "in", "hl": "en"}
    ads = ads_queries(EXAM, load_registry())
    assert ads[0].params["region"] == "2356" and ads[0].params["start_date"] == "20260306"


class FakeSerp:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def search(self, engine, params):
        self.calls.append((engine, params))
        key = (engine, params.get("q") or params.get("search_query") or params.get("v") or params.get("text"))
        if key not in self.responses:
            raise MissingFixture(str(key))
        return SerpResult(engine, params, self.responses[key], "replay")


class FakePages:
    def fetch(self, url):
        blocks = ((0, "Anuj Agnihotri AIR 1 UPSC CSE 2025"), (1, "menu"), (2, "unrelated"), (3, "far away"))
        return PageSnapshot(url, 200, "2026-10-06", "h", blocks, None)


class FakeImages:
    def read(self, url):
        return ImageText(url, "i", "AIR 1 ANUJ AGNIHOTRI UPSC CSE 2025", None)


def test_collector_records_missing_and_continues(tmp_path):
    roster = load_roster(EXAM, 1)
    responses = {("google", '"Anuj Agnihotri" UPSC CSE 2025 AIR 1'): {
        "search_metadata": {"id": "g1"},
        "organic_results": [{"link": "https://vajiramandravi.com/a", "title": "t"},
                            {"link": "https://thebetterindia.com/b", "title": "t"}]}}
    serp = FakeSerp(responses)
    store = EvidenceStore(tmp_path / "ev")
    col = Collector(EXAM, roster, load_registry(), load_independent(), Lexicon.load(), serp,
                    FakePages(), FakeImages(), store)
    run = col.run()
    kinds = sorted({a.kind for a in run.artifacts})
    assert kinds == ["missing", "page", "serp"]
    assert col.missing >= 4
    page = [a for a in run.artifacts if a.kind == "page"]
    assert [a.key for a in page] == ["https://vajiramandravi.com/a"]
    assert store.get(page[0].sha256)["blocks"] == [[0, "Anuj Agnihotri AIR 1 UPSC CSE 2025"], [1, "menu"]]


def test_export_then_replay_reproduces_manifest(tmp_path):
    roster = load_roster(EXAM, 1)
    responses = {("google", '"Anuj Agnihotri" UPSC CSE 2025 AIR 1'): {"search_metadata": {"id": "g1"}, "organic_results": []}}
    store = EvidenceStore(tmp_path / "ev")
    args = (EXAM, roster, load_registry(), load_independent(), Lexicon.load())
    first = Collector(*args, FakeSerp(responses), FakePages(), FakeImages(), store).run()
    export_fixtures(first, store, tmp_path / "fx")
    second = Collector(*args, ReplaySerpClient(tmp_path / "fx"), FakePages(), FakeImages(),
                       EvidenceStore(tmp_path / "ev2")).run()
    serp_keys = lambda r: sorted((a.key, a.sha256) for a in r.artifacts if a.kind == "serp")  # noqa: E731
    assert serp_keys(first) == serp_keys(second)
    manifest = json.loads((tmp_path / "fx" / "manifests" / f"{EXAM.id}.json").read_text(encoding="utf-8"))
    assert manifest["manifest_root"] == first.manifest_root()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_collect.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.collect'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/collect.py`:
```python
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from toppertrail.data import IndependentChannels, Registry
from toppertrail.evidence import ArtifactRef, EvidenceStore, Run
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.selfreport import hosted_videos, pick_interview
from toppertrail.extract.text import find_name
from toppertrail.fetch.images import image_fixture_path
from toppertrail.fetch.pages import filter_blocks, page_fixture_path
from toppertrail.models import Exam, Topper
from toppertrail.serp.base import SerpError, canonical_params, params_hash
from toppertrail.serp.budget import BudgetExceeded
from toppertrail.serp.replay import fixture_path


@dataclass(frozen=True)
class Planned:
    engine: str
    params: dict = field(hash=False)
    purpose: str = ""
    rank: int | None = None
    institute_id: str | None = None


def topper_queries(exam: Exam, t: Topper) -> list[Planned]:
    fmt = {"name": t.display_name, "rank": t.rank, "year": exam.year}
    q = exam.google_query.format(**fmt)
    out = [Planned("google", {"q": q, "gl": "in", "hl": "en"}, "google_en", t.rank)]
    if t.rank <= exam.google_hi_top:
        out.append(Planned("google", {"q": q, "gl": "in", "hl": "hi"}, "google_hi", t.rank))
    out.append(Planned("google_images", {"q": exam.images_query.format(**fmt), "gl": "in",
                                         "hl": "en"}, "images", t.rank))
    out.append(Planned("youtube", {"search_query": exam.youtube_query.format(**fmt), "gl": "in",
                                   "hl": "en"}, "youtube", t.rank))
    out.append(Planned("google_ai_mode", {"q": exam.ai_mode_query.format(**fmt), "gl": "in",
                                          "hl": "en"}, "ai_mode", t.rank))
    return out


def ads_queries(exam: Exam, registry: Registry) -> list[Planned]:
    return [
        Planned("google_ads_transparency_center",
                {"text": domain, "region": "2356",
                 "start_date": exam.result_date.strftime("%Y%m%d"),
                 "end_date": exam.ads_end_date.strftime("%Y%m%d"), "num": "100"},
                "ads", None, inst.id)
        for inst, domain in sorted(registry.ads_for(exam.tag), key=lambda p: (p[0].id, p[1]))
    ]


def estimate(exam: Exam, toppers: list[Topper], registry: Registry) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for t in toppers:
        for p in topper_queries(exam, t):
            counts[p.engine] += 1
        if t.rank <= exam.video_details_top:
            counts["youtube_video"] += exam.video_details_per_topper
        if exam.transcripts:
            counts["youtube_video_transcript"] += 1
    for p in ads_queries(exam, registry):
        counts[p.engine] += 1
    return dict(sorted(counts.items()))


def _epoch(d) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp())


class Collector:
    def __init__(self, exam: Exam, toppers: list[Topper], registry: Registry,
                 independent: IndependentChannels, lexicon: Lexicon, serp, pages, images,
                 store: EvidenceStore, log=lambda msg: None) -> None:
        self.exam, self.toppers, self.registry = exam, toppers, registry
        self.independent, self.lexicon = independent, lexicon
        self.serp, self.pages, self.images, self.store = serp, pages, images, store
        self.log = log
        self.missing = 0
        self._fetched: set[str] = set()
        self._read: set[str] = set()

    def _relevant(self, text: str) -> bool:
        return any(find_name(text, t.name) for t in self.toppers) or self.lexicon.signal_terms(text)

    def _missing(self, run: Run, what: str, reason: str) -> None:
        self.missing += 1
        sha = self.store.put({"what": what, "reason": reason})
        run.add(ArtifactRef("missing", what, sha, {"reason": reason}))

    def _search(self, run: Run, p: Planned, extra: dict | None = None) -> dict | None:
        key = f"{p.purpose}:{p.rank}:{p.institute_id}:{params_hash(p.engine, p.params)}"
        try:
            result = self.serp.search(p.engine, dict(p.params))
        except BudgetExceeded:
            raise
        except SerpError as err:
            self._missing(run, key, str(err))
            return None
        doc = {"engine": p.engine, "params": canonical_params(p.engine, p.params),
               "purpose": p.purpose, "rank": p.rank, "institute_id": p.institute_id,
               "response": result.data, **(extra or {})}
        run.add(ArtifactRef("serp", key, self.store.put(doc),
                            {"engine": p.engine, "purpose": p.purpose, "rank": p.rank,
                             "institute_id": p.institute_id}))
        self.log(f"  {p.engine} {p.purpose} rank={p.rank} inst={p.institute_id}")
        return result.data

    def _page(self, run: Run, url: str) -> None:
        if url in self._fetched:
            return
        self._fetched.add(url)
        snap = self.pages.fetch(url)
        doc = asdict(snap)
        doc["blocks"] = [list(b) for b in filter_blocks(list(snap.blocks), self._relevant)]
        run.add(ArtifactRef("page", url, self.store.put(doc), {"error": snap.error}))

    def _image(self, run: Run, url: str) -> None:
        if not url or url in self._read or self.images is None:
            return
        self._read.add(url)
        it = self.images.read(url)
        run.add(ArtifactRef("image", url, self.store.put(asdict(it)), {"error": it.error}))

    def run(self) -> Run:
        run = Run(self.exam.id)
        for t in self.toppers:
            for p in topper_queries(self.exam, t):
                data = self._search(run, p)
                if data is None:
                    continue
                if p.purpose in ("google_en", "google_hi"):
                    for r in data.get("organic_results") or []:
                        if self.registry.by_url(r.get("link") or ""):
                            self._page(run, r["link"])
                elif p.purpose == "images":
                    for r in data.get("images_results") or []:
                        if self.registry.by_url(r.get("link") or ""):
                            self._image(run, r.get("original") or "")
                elif p.purpose == "youtube":
                    self._video_followups(run, t, data.get("video_results") or [])
        floor = _epoch(self.exam.result_date)
        for p in ads_queries(self.exam, self.registry):
            data = self._search(run, p)
            creatives = [c for c in (data or {}).get("ad_creatives") or []
                         if int(c.get("last_shown") or 0) >= floor]
            for c in creatives[: self.exam.ads_creatives_cap]:
                self._image(run, c.get("image") or "")
        return run

    def _video_followups(self, run: Run, t: Topper, videos: list[dict]) -> None:
        if t.rank <= self.exam.video_details_top:
            for vid, iid in hosted_videos(videos, t, self.registry,
                                          self.exam.video_details_per_topper):
                self._search(run, Planned("youtube_video", {"v": vid, "gl": "in", "hl": "en"},
                                          "youtube_video", t.rank, iid))
        if self.exam.transcripts:
            pick = pick_interview(videos, t, self.registry, self.independent)
            if pick is None:
                return
            params = {"v": pick["id"], **dict(self.exam.transcript_params)}
            self._search(run, Planned("youtube_video_transcript", params, "transcript", t.rank),
                         extra={"video": pick})


def manifest_path(fixtures: Path, exam_id: str) -> Path:
    return Path(fixtures) / "manifests" / f"{exam_id}.json"


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True),
                    encoding="utf-8", newline="\n")


def export_fixtures(run: Run, store: EvidenceStore, fixtures: Path) -> int:
    n = 0
    for a in run.artifacts:
        obj = store.get(a.sha256)
        if a.kind == "serp":
            _write(fixture_path(fixtures, obj["engine"], obj["params"]), obj)
        elif a.kind == "page":
            _write(page_fixture_path(fixtures, a.key), obj)
        elif a.kind == "image":
            _write(image_fixture_path(fixtures, a.key), obj)
        else:
            continue
        n += 1
    _write(manifest_path(fixtures, run.exam_id),
           {"exam": run.exam_id, "manifest_root": run.manifest_root(),
            "artifacts": len(run.artifacts)})
    return n
```

Note for replay parity: `ReplaySerpClient` returns the stored `response`; the collector rebuilds the same `doc`, so serp artifact hashes match. Page and image artifacts match because replay readers return the stored dicts.

Add to `toppertrail/cli.py`:
```python
from pathlib import Path


def _context(exam_id: str, top: int | None):
    from toppertrail.data import load_exam, load_registry, load_roster

    exam = load_exam(exam_id)
    return exam, load_roster(exam, top or exam.default_top), load_registry()


@app.command()
def estimate(exam_id: str, top: int | None = typer.Option(None, help="Top N ranks")) -> None:
    """Show the SerpApi credits a collection run would spend, per engine."""
    from toppertrail.collect import estimate as plan

    exam, toppers, registry = _context(exam_id, top)
    counts = plan(exam, toppers, registry)
    typer.echo(f"{exam.label}, top {len(toppers)}")
    for engine, n in counts.items():
        typer.echo(f"  {engine:<34}{n:>5}")
    typer.echo(f"  {'total credits':<34}{sum(counts.values()):>5}")


@app.command()
def collect(exam_id: str, top: int | None = typer.Option(None), record: bool = False,
            ocr: bool = True) -> None:
    """Collect evidence (live, or replay when TOPPERTRAIL_REPLAY=1)."""
    from toppertrail.collect import Collector, estimate as plan, export_fixtures
    from toppertrail.config import load_settings
    from toppertrail.data import load_independent
    from toppertrail.evidence import EvidenceStore
    from toppertrail.extract.courses import Lexicon
    from toppertrail.fetch.images import LiveImageReader, ReplayImageReader, load_rapidocr
    from toppertrail.fetch.pages import LivePageFetcher, ReplayPageFetcher
    from toppertrail.serp.budget import Budget, BudgetExceeded
    from toppertrail.serp.live import LiveSerpClient, account_searches_left
    from toppertrail.serp.replay import ReplaySerpClient

    s = load_settings()
    exam, toppers, registry = _context(exam_id, top)
    if s.replay:
        serp, pages, images = (ReplaySerpClient(s.fixtures), ReplayPageFetcher(s.fixtures),
                               ReplayImageReader(s.fixtures))
        budget = None
        typer.echo("Replay mode: no network calls, no credits.")
    else:
        if not s.api_key:
            raise typer.BadParameter("SERPAPI_API_KEY is not set (or use TOPPERTRAIL_REPLAY=1).")
        need = sum(plan(exam, toppers, registry).values())
        left = account_searches_left(s.api_key)
        cap = min(s.budget_cap, left)
        if need > cap:
            typer.echo(f"Estimated {need} credits exceed the available {cap}. Lower --top.", err=True)
            raise typer.Exit(1)
        budget = Budget(cap)
        serp = LiveSerpClient(s.api_key, budget, s.home / "spend.jsonl")
        pages = LivePageFetcher()
        reader = load_rapidocr() if ocr else None
        images = LiveImageReader(reader) if reader else None
        typer.echo(f"Live mode: estimate {need} credits, cap {cap}, OCR {'on' if images else 'off'}.")
    store = EvidenceStore(s.home / "evidence")
    col = Collector(exam, toppers, registry, load_independent(), Lexicon.load(), serp, pages,
                    images, store, log=typer.echo)
    try:
        run = col.run()
    except BudgetExceeded as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(1) from None
    run.save(s.home / "runs" / f"{exam.id}.json")
    typer.echo(f"Artifacts: {len(run.artifacts)}, missing: {col.missing}, "
               f"credits spent: {budget.spent if budget else 0}")
    typer.echo(f"Manifest root: {run.manifest_root()}")
    if record:
        n = export_fixtures(run, store, s.fixtures)
        typer.echo(f"Exported {n} fixtures to {s.fixtures}")


@app.command()
def budget() -> None:
    """Show remaining SerpApi searches and this machine's spend log."""
    from toppertrail.config import load_settings
    from toppertrail.serp.budget import spend_count
    from toppertrail.serp.live import account_searches_left

    s = load_settings()
    typer.echo(f"Spend log: {spend_count(s.home / 'spend.jsonl')} paid searches")
    if s.api_key and not s.replay:
        typer.echo(f"Account searches left: {account_searches_left(s.api_key)}")
```

Move `from pathlib import Path` to the top of `cli.py` with the other imports.

- [ ] **Step 4: Run tests and a dry estimate**

Run:
```bash
.venv/Scripts/python -m pytest tests/test_collect.py -q
.venv/Scripts/python -m toppertrail estimate upsc-cse-2025
PYTHONIOENCODING=cp1252 .venv/Scripts/python -m toppertrail estimate neet-ug-2026
```
Expected: `4 passed`; the first estimate prints a total of 145; the cp1252 run prints without a UnicodeEncodeError (total 24).

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/collect.py toppertrail/cli.py tests/test_collect.py`. Suggested message: `feat: budgeted collector with replay parity and fixture export`.

---

### Task 14: Analysis, ledger hash, report, CLI analyze and verify

**Files:**
- Create: `toppertrail/analyze.py`, `toppertrail/report.py`
- Modify: `toppertrail/cli.py` (add `analyze`, `verify`)
- Test: `tests/test_analyze.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: all extractors (Tasks 10, 11), rules (Task 12), evidence (Task 2).
- Produces: `analyze(exam, toppers, registry, lexicon, run, store) -> dict` (ledger with keys `exam`, `label`, `manifest_root`, `toppers`, `claims`, `signals`, `selfreports`, `interviews`, `ai_answers`, `flags`, `unresolved`, `missing`); `ledger_hash(ledger) -> str`; `headline(ledger) -> dict`; `topper_view(ledger, rank) -> dict`; `institute_rows(ledger, registry) -> list[dict]`; `institute_view(ledger, iid, registry) -> dict`; `ai_findings(ledger) -> dict`.

- [ ] **Step 1: Write the failing tests**

`tests/test_analyze.py`:
```python
from toppertrail.analyze import analyze, ledger_hash
from toppertrail.data import load_exam, load_registry, load_roster
from toppertrail.evidence import ArtifactRef, EvidenceStore, Run
from toppertrail.extract.courses import Lexicon

EXAM = load_exam("upsc-cse-2025")


def build(tmp_path):
    store = EvidenceStore(tmp_path)
    run = Run(EXAM.id)

    def serp(purpose, rank, response, iid=None, extra=None):
        doc = {"engine": "x", "params": {"engine": "x"}, "purpose": purpose, "rank": rank,
               "institute_id": iid, "response": response, **(extra or {})}
        run.add(ArtifactRef("serp", f"{purpose}:{rank}:{iid}", store.put(doc), {}))

    serp("google_en", 1, {"search_metadata": {"id": "g1", "created_at": "2026-10-06 09:00:00 UTC"},
                          "organic_results": [{"link": "https://vajiramandravi.com/a", "title": "Anuj Agnihotri UPSC AIR 1 2025", "snippet": "IGP"}]})
    page = {"url": "https://vajiramandravi.com/a", "status": 200, "fetched_at": "2026-10-06", "html_sha256": "h",
            "blocks": [[0, "Anuj Agnihotri AIR 1 - UPSC CSE 2025 (IGP)"]], "error": None}
    run.add(ArtifactRef("page", page["url"], store.put(page), {}))
    serp("youtube", 1, {"video_results": [{"title": "Anuj Agnihotri AIR 1 | Mock Interview | NEXT IAS",
                                           "link": "https://www.youtube.com/watch?v=8X-e5cJ_L3M",
                                           "channel": {"name": "NEXT IAS", "link": "https://www.youtube.com/@nextias"},
                                           "description": "UPSC CSE 2025"}]})
    serp("transcript", 1, {"transcript": [{"start_ms": 1807000, "snippet": "मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया"}]},
         extra={"video": {"id": "KIr6dWSqspI", "channel": "Delhi Knowledge Track", "title": "t"}})
    serp("ai_mode", 1, {"search_metadata": {"id": "a1"}, "text_blocks": [{"snippet": "He took Vajiram & Ravi's IGP."}]})
    return run, store


def test_analyze_builds_ledger_and_is_deterministic(tmp_path):
    run, store = build(tmp_path)
    args = (EXAM, load_roster(EXAM, 3), load_registry(), Lexicon.load(), run, store)
    ledger = analyze(*args)
    by_inst = {c["institute_id"]: c for c in ledger["claims"]}
    assert set(by_inst) == {"vajiram-ravi", "next-ias"}
    assert by_inst["vajiram-ravi"]["course_types"] == ["interview_only"]
    assert by_inst["vajiram-ravi"]["observed_at"] == "2026-10-06"
    assert ledger["ai_answers"][0]["institutes"] == ["vajiram-ravi"]
    tt12 = {f["institute_id"]: f["code"] for f in ledger["flags"] if f["rule_id"] == "TT-12"}
    assert tt12 == {"next-ias": "mentioned", "vajiram-ravi": "not_mentioned"}
    assert ledger_hash(ledger) == ledger_hash(analyze(*args))
```

`tests/test_report.py`:
```python
from toppertrail.data import load_registry
from toppertrail.report import ai_findings, headline, institute_rows, topper_view

LEDGER = {
    "exam": "upsc-cse-2025", "label": "UPSC CSE 2025", "manifest_root": "m",
    "toppers": [{"rank": 1, "name": "ANUJ AGNIHOTRI", "display": "Anuj Agnihotri"},
                {"rank": 2, "name": "RAJESHWARI SUVE M", "display": "Rajeshwari Suve M"}],
    "claims": [
        {"claim_id": "a", "rank": 1, "institute_id": "vajiram-ravi", "course_types": ["interview_only"], "source_type": "web_page"},
        {"claim_id": "b", "rank": 1, "institute_id": "next-ias", "course_types": [], "source_type": "youtube_hosted"},
        {"claim_id": "c", "rank": 1, "institute_id": "legacy-ias", "course_types": [], "source_type": "web_page"},
        {"claim_id": "d", "rank": 2, "institute_id": "vajiram-ravi", "course_types": ["test_series"], "source_type": "poster"},
    ],
    "flags": [
        {"rule_id": "TT-01", "claim_id": "b", "institute_id": "next-ias", "rank": 1, "detail": "", "code": ""},
        {"rule_id": "TT-01", "claim_id": "c", "institute_id": "legacy-ias", "rank": 1, "detail": "", "code": ""},
        {"rule_id": "TT-02", "claim_id": "a", "institute_id": "vajiram-ravi", "rank": 1, "detail": "", "code": ""},
        {"rule_id": "TT-04", "claim_id": "a", "institute_id": "vajiram-ravi", "rank": 1, "detail": "", "code": ""},
        {"rule_id": "TT-12", "claim_id": "a", "institute_id": "vajiram-ravi", "rank": 1, "detail": "", "code": "not_mentioned"},
        {"rule_id": "TT-11", "claim_id": None, "institute_id": "vajiram-ravi", "rank": None, "detail": "", "code": ""},
    ],
    "selfreports": [], "interviews": [], "signals": [], "unresolved": [], "missing": [],
    "ai_answers": [{"rank": 1, "institutes": ["vajiram-ravi"], "excerpt": "x", "search_id": "s", "engine": "google_ai_mode"},
                   {"rank": 2, "institutes": [], "excerpt": "", "search_id": "t", "engine": "google_ai_mode"}],
}


def test_headline_numbers():
    h = headline(LEDGER)
    assert h["claims"] == 4 and h["toppers"] == 2 and h["institutes"] == 3
    assert h["avg_claimants"] == 2.0 and h["max_claimants"] == 3
    assert h["course_stated_pct"] == 50 and h["interview_only_pct_of_stated"] == 50
    assert h["paid_free_stated_pct"] == 75
    assert h["own_words"] == {"not_mentioned": 1}


def test_views():
    v = topper_view(LEDGER, 1)
    assert [c["institute_id"] for c in v["claims"]] == ["legacy-ias", "next-ias", "vajiram-ravi"]
    rows = institute_rows(LEDGER, load_registry())
    assert rows[0]["institute_id"] == "vajiram-ravi" and rows[0]["toppers"] == 2
    ai = ai_findings(LEDGER)
    assert ai == {"toppers_named": 1, "toppers_total": 2,
                  "named_with_weak_claims": 1, "named_without_claims": 0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_analyze.py tests/test_report.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.analyze'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/analyze.py`:
```python
from __future__ import annotations

from dataclasses import asdict

from toppertrail.data import Registry
from toppertrail.evidence import EvidenceStore, Run
from toppertrail.extract.aianswer import ai_answer
from toppertrail.extract.claims import ClaimExtractor
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.selfreport import self_reports
from toppertrail.hashing import canonical_json, sha256_text
from toppertrail.models import Claim, Exam, Interview, Signal, Topper
from toppertrail.rules import apply_rules


def _day(response: dict) -> str:
    created = (response.get("search_metadata") or {}).get("created_at") or ""
    return created[:10]


def _desc(value) -> str:
    if isinstance(value, dict):
        return str(value.get("content") or "")
    return str(value or "")


def analyze(exam: Exam, toppers: list[Topper], registry: Registry, lexicon: Lexicon, run: Run,
            store: EvidenceStore) -> dict:
    ex = ClaimExtractor(exam, toppers, registry, lexicon)
    pages = {a.key: (a.sha256, store.get(a.sha256)) for a in run.of_kind("page")}
    images = {a.key: (a.sha256, store.get(a.sha256)) for a in run.of_kind("image")}
    claims: list[Claim] = []
    signals: list[Signal] = []
    unresolved: list[dict] = []
    reports, interviews, answers = [], [], []

    def take(result) -> None:
        c, s, u = result
        claims.extend(c)
        signals.extend(s)
        unresolved.extend(u)

    for a in sorted(run.of_kind("serp"), key=lambda a: a.key):
        doc = store.get(a.sha256)
        resp, purpose, rank = doc["response"], doc["purpose"], doc["rank"]
        sid, day = (resp.get("search_metadata") or {}).get("id"), _day(resp)
        if purpose in ("google_en", "google_hi"):
            for r in resp.get("organic_results") or []:
                inst = registry.by_url(r.get("link") or "")
                if not inst:
                    continue
                url, title = r["link"], r.get("title") or ""
                page_sha, page = pages.get(url, (None, None))
                if page and page.get("blocks") and not page.get("error"):
                    blocks = [(int(i), t) for i, t in page["blocks"]]
                    before = len(claims)
                    take(ex.from_blocks(inst, url, title, blocks, "web_page", sid,
                                        (a.sha256, page_sha), page["fetched_at"] or day))
                    if any(c.rank == rank for c in claims[before:]):
                        continue
                take(ex.from_blocks(inst, url, title, [(0, title), (1, r.get("snippet") or "")],
                                    "snippet_only", sid, (a.sha256,), day))
        elif purpose == "images":
            for r in resp.get("images_results") or []:
                inst = registry.by_url(r.get("link") or "")
                if not inst:
                    continue
                img_sha, img = images.get(r.get("original") or "", (None, None))
                text = img["text"] if img and not img.get("error") else ""
                ev = (a.sha256, img_sha) if img_sha else (a.sha256,)
                take(ex.from_blocks(inst, r["link"], r.get("title") or "",
                                    [(0, r.get("title") or ""), (1, text)], "poster", sid, ev, day))
        elif purpose == "youtube":
            for v in resp.get("video_results") or []:
                ch = v.get("channel") or {}
                inst = registry.by_channel(ch.get("link"), ch.get("name"))
                if inst:
                    take(ex.from_blocks(inst, v.get("link") or "", v.get("title") or "",
                                        [(0, v.get("title") or ""), (1, _desc(v.get("description")))],
                                        "youtube_hosted", sid, (a.sha256,), day))
        elif purpose == "youtube_video":
            inst = registry.get(doc["institute_id"])
            url = f"https://www.youtube.com/watch?v={doc['params'].get('v', '')}"
            title = resp.get("title") or ""
            take(ex.from_blocks(inst, url, title, [(0, title), (1, _desc(resp.get("description")))],
                                "youtube_description", sid, (a.sha256,), day))
        elif purpose == "transcript":
            video = doc.get("video") or {}
            transcript = resp.get("transcript") or []
            if transcript:
                lang = doc["params"].get("language_code", "")
                interviews.append(Interview(rank, video.get("id", ""), video.get("channel", ""),
                                            video.get("title", ""), lang))
                reports.extend(self_reports(transcript, rank, video.get("id", ""),
                                            video.get("channel", ""), registry, lexicon))
        elif purpose == "ads":
            inst = registry.get(doc["institute_id"])
            for cr in resp.get("ad_creatives") or []:
                img_sha, img = images.get(cr.get("image") or "", (None, None))
                if not img or img.get("error"):
                    continue
                take(ex.from_blocks(inst, cr.get("details_link") or "", f"Google ad by {inst.name}",
                                    [(0, img["text"])], "ad_creative", sid, (a.sha256, img_sha),
                                    day, require_year=False))
        elif purpose == "ai_mode":
            answers.append(ai_answer(resp, rank, registry))

    unique = {c.claim_id: c for c in sorted(claims, key=lambda c: (c.claim_id, c.evidence))}
    claims = sorted(unique.values(), key=lambda c: (c.rank, c.institute_id, c.source_type, c.url))
    flags = apply_rules(exam, claims, signals, reports, interviews, registry)
    sig = sorted({(s.institute_id, s.rule_id, s.text, s.url): s for s in signals}.values(),
                 key=lambda s: (s.institute_id, s.rule_id, s.text, s.url))
    return {
        "exam": exam.id,
        "label": exam.label,
        "manifest_root": run.manifest_root(),
        "toppers": [{"rank": t.rank, "name": t.name, "display": t.display_name} for t in toppers],
        "claims": [asdict(c) for c in claims],
        "signals": [asdict(s) for s in sig],
        "selfreports": [asdict(r) for r in sorted(reports, key=lambda r: (r.rank, r.start_ms))],
        "interviews": [asdict(i) for i in sorted(interviews, key=lambda i: i.rank)],
        "ai_answers": [asdict(x) for x in sorted(answers, key=lambda x: x.rank)],
        "flags": [asdict(f) for f in flags],
        "unresolved": sorted(unresolved, key=lambda u: (u["rank"], u["institute_id"], u["url"])),
        "missing": sorted(a.key for a in run.of_kind("missing")),
    }


def ledger_hash(ledger: dict) -> str:
    return sha256_text(canonical_json(ledger))
```

`asdict` turns tuples into lists, so the ledger is plain JSON. `canonical_json` sorts keys.

`toppertrail/report.py`:
```python
from __future__ import annotations

from collections import Counter, defaultdict

from toppertrail.data import Registry
from toppertrail.rules import RULES, load_orders


def _pct(a: int, b: int) -> int:
    return round(100 * a / b) if b else 0


def _flags_by_claim(ledger: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for f in ledger["flags"]:
        if f["claim_id"]:
            out[f["claim_id"]].add(f["rule_id"])
    return out


def headline(ledger: dict) -> dict:
    claims, toppers = ledger["claims"], ledger["toppers"]
    by_rank: dict[int, set[str]] = defaultdict(set)
    for c in claims:
        by_rank[c["rank"]].add(c["institute_id"])
    counts = [len(by_rank.get(t["rank"], ())) for t in toppers]
    fl = _flags_by_claim(ledger)
    stated = [c for c in claims if "TT-01" not in fl[c["claim_id"]]]
    interview_only = [c for c in stated if "TT-02" in fl[c["claim_id"]]]
    paid_missing = sum(1 for c in claims if "TT-04" in fl[c["claim_id"]])
    own = Counter(f["code"] for f in ledger["flags"] if f["rule_id"] == "TT-12")
    return {
        "toppers": len(toppers),
        "claims": len(claims),
        "institutes": len({c["institute_id"] for c in claims}),
        "avg_claimants": round(sum(counts) / len(counts), 1) if counts else 0.0,
        "max_claimants": max(counts, default=0),
        "toppers_3plus": sum(1 for n in counts if n >= 3),
        "course_stated_pct": _pct(len(stated), len(claims)),
        "interview_only_pct_of_stated": _pct(len(interview_only), len(stated)),
        "paid_free_stated_pct": _pct(len(claims) - paid_missing, len(claims)),
        "own_words": dict(sorted(own.items())),
    }


def topper_view(ledger: dict, rank: int) -> dict:
    topper = next(t for t in ledger["toppers"] if t["rank"] == rank)
    flags: dict[str, list[dict]] = defaultdict(list)
    for f in ledger["flags"]:
        if f["claim_id"]:
            flags[f["claim_id"]].append(f)
    claims = sorted((c for c in ledger["claims"] if c["rank"] == rank),
                    key=lambda c: (c["institute_id"], c["source_type"], c["url"]))
    return {
        "topper": topper,
        "claims": [{**c, "flags": flags.get(c["claim_id"], [])} for c in claims],
        "selfreports": [r for r in ledger["selfreports"] if r["rank"] == rank],
        "interview": next((i for i in ledger["interviews"] if i["rank"] == rank), None),
        "ai": next((a for a in ledger["ai_answers"] if a["rank"] == rank), None),
    }


def institute_rows(ledger: dict, registry: Registry) -> list[dict]:
    fl = _flags_by_claim(ledger)
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in ledger["claims"]:
        groups[c["institute_id"]].append(c)
    signals = Counter(f["institute_id"] for f in ledger["flags"] if f["claim_id"] is None)
    rows = []
    for iid, cs in groups.items():
        stated = [c for c in cs if "TT-01" not in fl[c["claim_id"]]]
        rows.append({
            "institute_id": iid,
            "name": registry.get(iid).name,
            "toppers": len({c["rank"] for c in cs}),
            "claims": len(cs),
            "course_stated_pct": _pct(len(stated), len(cs)),
            "interview_only": sum(1 for c in cs if "TT-02" in fl[c["claim_id"]]),
            "signals": signals.get(iid, 0),
            "ads": sum(1 for c in cs if c["source_type"] == "ad_creative"),
            "ccpa_orders": len(registry.get(iid).ccpa_orders),
        })
    return sorted(rows, key=lambda r: (-r["toppers"], -r["claims"], r["institute_id"]))


def institute_view(ledger: dict, iid: str, registry: Registry) -> dict:
    orders = {o["id"]: o for o in load_orders()["orders"]}
    inst = registry.get(iid)
    return {
        "institute": inst,
        "claims": [c for c in ledger["claims"] if c["institute_id"] == iid],
        "signals": [f for f in ledger["flags"] if f["institute_id"] == iid and f["claim_id"] is None],
        "orders": [orders[o] for o in inst.ccpa_orders if o in orders],
        "rules": RULES,
    }


def ai_findings(ledger: dict) -> dict:
    fl = _flags_by_claim(ledger)
    own = {f["claim_id"]: f["code"] for f in ledger["flags"] if f["rule_id"] == "TT-12"}
    named = [a for a in ledger["ai_answers"] if a["institutes"]]
    weak = without = 0
    for a in named:
        for iid in a["institutes"]:
            cs = [c for c in ledger["claims"] if c["rank"] == a["rank"] and c["institute_id"] == iid]
            if not cs:
                without += 1
            elif all("TT-02" in fl[c["claim_id"]] or own.get(c["claim_id"]) in ("not_mentioned", "denied")
                     for c in cs):
                weak += 1
    return {"toppers_named": len(named), "toppers_total": len(ledger["ai_answers"]),
            "named_with_weak_claims": weak, "named_without_claims": without}
```

Add to `toppertrail/cli.py`:
```python
@app.command()
def analyze(exam_id: str, top: int | None = typer.Option(None)) -> None:
    """Build the ledger from collected evidence and print the headline numbers."""
    import json

    from toppertrail.analyze import analyze as build, ledger_hash
    from toppertrail.config import load_settings
    from toppertrail.evidence import EvidenceStore, Run
    from toppertrail.extract.courses import Lexicon
    from toppertrail.report import ai_findings, headline

    s = load_settings()
    exam, toppers, registry = _context(exam_id, top)
    run = Run.load(s.home / "runs" / f"{exam.id}.json")
    ledger = build(exam, toppers, registry, Lexicon.load(), run, EvidenceStore(s.home / "evidence"))
    out = s.home / "ledgers" / f"{exam.id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    for k, v in {**headline(ledger), **{"ai_" + k: v for k, v in ai_findings(ledger).items()}}.items():
        typer.echo(f"  {k:<30}{v}")
    typer.echo(f"Ledger hash: {ledger_hash(ledger)}")


@app.command()
def verify(exam_id: str) -> None:
    """Check evidence integrity and compare the run with the recorded fixture manifest."""
    import json

    from toppertrail.collect import manifest_path
    from toppertrail.config import load_settings
    from toppertrail.evidence import EvidenceStore, Run, damaged

    s = load_settings()
    run = Run.load(s.home / "runs" / f"{exam_id}.json")
    bad = damaged(run, EvidenceStore(s.home / "evidence"))
    typer.echo(f"Evidence files checked: {len(run.artifacts)}, damaged: {len(bad)}")
    path = manifest_path(s.fixtures, exam_id)
    if path.exists():
        recorded = json.loads(path.read_text(encoding="utf-8"))["manifest_root"]
        same = recorded == run.manifest_root()
        typer.echo("Manifest root matches the recorded run." if same else
                   f"Manifest root differs: recorded {recorded}, this run {run.manifest_root()}")
        if not same or bad:
            raise typer.Exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_analyze.py tests/test_report.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/analyze.py toppertrail/report.py toppertrail/cli.py tests/test_analyze.py tests/test_report.py`. Suggested message: `feat: deterministic ledger, headline findings, verify command`.

---

### Task 15: Dashboard and static export

Use the `frontend-design` skill (or `impeccable`) for the visual pass in Step 4; the structure below is fixed, the styling is the skill's job.

**Files:**
- Create: `toppertrail/web/__init__.py` (empty), `toppertrail/web/render.py`, `toppertrail/web/app.py`, `toppertrail/web/export.py`
- Create: `toppertrail/web/templates/base.html`, `index.html`, `exam.html`, `topper.html`, `institute.html`, `methodology.html`, `evidence.html`
- Create: `toppertrail/web/static/style.css`
- Modify: `toppertrail/cli.py` (add `serve`, `export`)
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `headline`, `topper_view`, `institute_rows`, `institute_view`, `ai_findings`, `RULES` (Tasks 12, 14); `load_registry`, `read_data` (Task 7).
- Produces: `Renderer(base="/", static=False)` with `page(name, **ctx) -> str` and `link(path) -> str`; `load_ledgers(home) -> dict[str, dict]`; `create_app(home: Path) -> FastAPI`; `export_site(home: Path, out: Path, base: str) -> list[Path]`.

- [ ] **Step 1: Write the failing test**

`tests/test_web.py`:
```python
import json

from fastapi.testclient import TestClient

from toppertrail.web.app import create_app
from toppertrail.web.export import export_site

LEDGER = {
    "exam": "upsc-cse-2025", "label": "UPSC CSE 2025", "manifest_root": "m",
    "toppers": [{"rank": 1, "name": "ANUJ AGNIHOTRI", "display": "Anuj Agnihotri"}],
    "claims": [{"claim_id": "a", "exam_id": "upsc-cse-2025", "rank": 1, "institute_id": "vajiram-ravi",
                "source_type": "web_page", "url": "https://vajiramandravi.com/a", "title": "t",
                "window": "<script>alert(1)</script> AIR 1 (IGP)", "course_types": ["interview_only"],
                "course_terms": ["igp"], "paid_free_stated": False, "duration_stated": False,
                "vague_label": False, "claimed_rank": 1, "search_id": "g1", "evidence": ["e1"],
                "observed_at": "2026-10-06"}],
    "flags": [{"rule_id": "TT-02", "claim_id": "a", "institute_id": "vajiram-ravi", "rank": 1,
               "detail": "Only an interview programme is named: igp.", "code": ""}],
    "signals": [], "selfreports": [], "interviews": [], "ai_answers": [], "unresolved": [], "missing": [],
}


def home(tmp_path):
    (tmp_path / "ledgers").mkdir()
    (tmp_path / "ledgers" / "upsc-cse-2025.json").write_text(json.dumps(LEDGER), encoding="utf-8")
    return tmp_path


def test_pages_render_and_escape(tmp_path):
    client = TestClient(create_app(home(tmp_path)))
    for path in ("/", "/exam/upsc-cse-2025", "/exam/upsc-cse-2025/topper/1",
                 "/exam/upsc-cse-2025/institute/vajiram-ravi", "/methodology"):
        r = client.get(path)
        assert r.status_code == 200, path
    page = client.get("/exam/upsc-cse-2025/topper/1").text
    assert "&lt;script&gt;" in page and "<script>alert" not in page
    assert "does not decide whether a claim is" in page
    assert client.get("/exam/nope").status_code == 404


def test_static_export_writes_pages(tmp_path):
    files = export_site(home(tmp_path), tmp_path / "site", "/TopperTrail/")
    names = {p.relative_to(tmp_path / "site").as_posix() for p in files}
    assert "index.html" in names and "exam/upsc-cse-2025/topper/1/index.html" in names
    html = (tmp_path / "site" / "exam" / "upsc-cse-2025" / "index.html").read_text(encoding="utf-8")
    assert 'href="/TopperTrail/exam/upsc-cse-2025/topper/1/"' in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_web.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'toppertrail.web'`.

- [ ] **Step 3: Write the implementation**

`toppertrail/web/render.py`:
```python
from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from toppertrail.rules import RULES

NOTICE = ("TopperTrail records what institutes publicly claim and what they disclose next to "
          "the claim. It does not decide whether a claim is false or misleading; that is for "
          "the CCPA.")
SOURCE_LABELS = {"web_page": "Web page", "snippet_only": "Search snippet only", "poster": "Poster",
                 "ad_creative": "Google ad (India)", "youtube_hosted": "YouTube video",
                 "youtube_description": "YouTube description"}


def load_ledgers(home: Path) -> dict[str, dict]:
    folder = Path(home) / "ledgers"
    if not folder.exists():
        return {}
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))}


class Renderer:
    def __init__(self, base: str = "/", static: bool = False) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.static = static
        folder = str(files("toppertrail").joinpath("web/templates"))
        self.env = Environment(loader=FileSystemLoader(folder),
                               autoescape=select_autoescape(["html"]))
        self.env.globals.update(link=self.link, NOTICE=NOTICE, RULES=RULES,
                                SOURCE_LABELS=SOURCE_LABELS, static_mode=static)

    def link(self, path: str) -> str:
        path = path.lstrip("/")
        if self.static and path and not path.endswith((".css", ".html")):
            path = path.rstrip("/") + "/"
        return self.base + path

    def page(self, name: str, **ctx) -> str:
        return self.env.get_template(name).render(**ctx)
```

`toppertrail/web/app.py`:
```python
from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from toppertrail.data import load_registry, read_data
from toppertrail.evidence import EvidenceStore
from toppertrail.report import ai_findings, headline, institute_rows, institute_view, topper_view
from toppertrail.web.render import Renderer, load_ledgers


def create_app(home: Path) -> FastAPI:
    app = FastAPI(title="TopperTrail", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(files("toppertrail").joinpath("web/static"))),
              name="static")
    r = Renderer("/")
    registry = load_registry()
    store = EvidenceStore(Path(home) / "evidence")

    def ledger(exam_id: str) -> dict:
        found = load_ledgers(home).get(exam_id)
        if not found:
            raise HTTPException(404, "No ledger for this exam. Run collect and analyze first.")
        return found

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        ledgers = load_ledgers(home)
        return r.page("index.html", exams=[(k, v["label"], headline(v)) for k, v in ledgers.items()])

    @app.get("/exam/{exam_id}", response_class=HTMLResponse)
    def exam(exam_id: str) -> str:
        led = ledger(exam_id)
        return r.page("exam.html", led=led, h=headline(led), ai=ai_findings(led),
                      rows=institute_rows(led, registry),
                      claimants={t["rank"]: len({c["institute_id"] for c in led["claims"]
                                                 if c["rank"] == t["rank"]}) for t in led["toppers"]})

    @app.get("/exam/{exam_id}/topper/{rank}", response_class=HTMLResponse)
    def topper(exam_id: str, rank: int) -> str:
        led = ledger(exam_id)
        if not any(t["rank"] == rank for t in led["toppers"]):
            raise HTTPException(404, "Rank not in this ledger.")
        return r.page("topper.html", led=led, v=topper_view(led, rank), registry=registry)

    @app.get("/exam/{exam_id}/institute/{iid}", response_class=HTMLResponse)
    def institute(exam_id: str, iid: str) -> str:
        led = ledger(exam_id)
        try:
            view = institute_view(led, iid, registry)
        except KeyError:
            raise HTTPException(404, "Unknown institute.") from None
        return r.page("institute.html", led=led, v=view)

    @app.get("/methodology", response_class=HTMLResponse)
    def methodology() -> str:
        return r.page("methodology.html", guidelines=read_data("ccpa/guidelines-2024.md"))

    @app.get("/evidence/{sha}", response_class=HTMLResponse)
    def evidence(sha: str) -> str:
        if len(sha) != 64 or not all(ch in "0123456789abcdef" for ch in sha):
            raise HTTPException(404, "Not an evidence id.")
        try:
            obj = store.get(sha)
        except FileNotFoundError:
            raise HTTPException(404, "Evidence not found on this machine.") from None
        return r.page("evidence.html", sha=sha, body=json.dumps(obj, ensure_ascii=False, indent=1),
                      intact=store.is_intact(sha))

    return app
```

`toppertrail/web/export.py`:
```python
from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

from toppertrail.data import load_registry, read_data
from toppertrail.report import ai_findings, headline, institute_rows, institute_view, topper_view
from toppertrail.web.render import Renderer, load_ledgers


def _write(path: Path, html: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8", newline="\n")
    return path


def export_site(home: Path, out: Path, base: str = "/") -> list[Path]:
    r = Renderer(base, static=True)
    registry = load_registry()
    ledgers = load_ledgers(home)
    out = Path(out)
    written = [_write(out / "index.html",
                      r.page("index.html", exams=[(k, v["label"], headline(v)) for k, v in ledgers.items()]))]
    written.append(_write(out / "methodology" / "index.html",
                          r.page("methodology.html", guidelines=read_data("ccpa/guidelines-2024.md"))))
    for exam_id, led in ledgers.items():
        claimants = {t["rank"]: len({c["institute_id"] for c in led["claims"] if c["rank"] == t["rank"]})
                     for t in led["toppers"]}
        written.append(_write(out / "exam" / exam_id / "index.html",
                              r.page("exam.html", led=led, h=headline(led), ai=ai_findings(led),
                                     rows=institute_rows(led, registry), claimants=claimants)))
        for t in led["toppers"]:
            written.append(_write(out / "exam" / exam_id / "topper" / str(t["rank"]) / "index.html",
                                  r.page("topper.html", led=led, v=topper_view(led, t["rank"]),
                                         registry=registry)))
        for iid in sorted({c["institute_id"] for c in led["claims"]}):
            written.append(_write(out / "exam" / exam_id / "institute" / iid / "index.html",
                                  r.page("institute.html", led=led, v=institute_view(led, iid, registry))))
    static = Path(str(files("toppertrail").joinpath("web/static")))
    shutil.copytree(static, out / "static", dirs_exist_ok=True)
    return written
```

Templates (Jinja2; every dynamic value goes through autoescape; no `|safe` anywhere):

`toppertrail/web/templates/base.html`:
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}TopperTrail{% endblock %}</title>
  <link rel="stylesheet" href="{{ link('static/style.css') }}">
</head>
<body>
  <header class="site">
    <a class="brand" href="{{ link('') }}">TopperTrail</a>
    <span class="tag">One rank. Many claims. Follow the trail.</span>
    <nav><a href="{{ link('methodology') }}">Methodology</a></nav>
  </header>
  <main>{% block main %}{% endblock %}</main>
  <footer class="site"><p class="notice">{{ NOTICE }}</p></footer>
</body>
</html>
```

`toppertrail/web/templates/index.html`:
```html
{% extends "base.html" %}
{% block main %}
<h1>Exams</h1>
{% if not exams %}<p>No ledgers yet. Run <code>toppertrail collect</code> then <code>toppertrail analyze</code>.</p>{% endif %}
<ul class="cards">
{% for id, label, h in exams %}
  <li><a href="{{ link('exam/' ~ id) }}"><strong>{{ label }}</strong>
    <span>{{ h.toppers }} toppers, {{ h.claims }} claims, {{ h.institutes }} institutes</span>
    <span>On average {{ h.avg_claimants }} institutes claim each topper</span></a></li>
{% endfor %}
</ul>
{% endblock %}
```

`toppertrail/web/templates/exam.html`:
```html
{% extends "base.html" %}
{% block title %}{{ led.label }} · TopperTrail{% endblock %}
{% block main %}
<h1>{{ led.label }}</h1>
<section class="headline">
  <div><b>{{ h.avg_claimants }}</b><span>institutes claim each topper on average (max {{ h.max_claimants }})</span></div>
  <div><b>{{ h.course_stated_pct }}%</b><span>of claims name a course next to the claim</span></div>
  <div><b>{{ h.interview_only_pct_of_stated }}%</b><span>of those name only an interview programme</span></div>
  <div><b>{{ h.paid_free_stated_pct }}%</b><span>say whether the course was paid or free</span></div>
  <div><b>{{ ai.toppers_named }} of {{ ai.toppers_total }}</b><span>Google AI Mode answers name a coaching institute</span></div>
</section>
<h2>Toppers</h2>
<table class="data"><thead><tr><th>Rank</th><th>Name</th><th>Institutes claiming</th></tr></thead><tbody>
{% for t in led.toppers %}
<tr><td>{{ t.rank }}</td><td><a href="{{ link('exam/' ~ led.exam ~ '/topper/' ~ t.rank) }}">{{ t.display }}</a></td><td>{{ claimants[t.rank] }}</td></tr>
{% endfor %}</tbody></table>
<h2>Institutes</h2>
<table class="data"><thead><tr><th>Institute</th><th>Toppers</th><th>Claims</th><th>Course stated</th><th>Interview-only</th><th>Wording signals</th><th>Ads</th><th>CCPA orders</th></tr></thead><tbody>
{% for r in rows %}
<tr><td><a href="{{ link('exam/' ~ led.exam ~ '/institute/' ~ r.institute_id) }}">{{ r.name }}</a></td><td>{{ r.toppers }}</td><td>{{ r.claims }}</td><td>{{ r.course_stated_pct }}%</td><td>{{ r.interview_only }}</td><td>{{ r.signals }}</td><td>{{ r.ads }}</td><td>{{ r.ccpa_orders }}</td></tr>
{% endfor %}</tbody></table>
<p class="meta">Manifest root <code>{{ led.manifest_root }}</code>. Counts are lower bounds: only registered institutes are counted.</p>
{% endblock %}
```

`toppertrail/web/templates/topper.html`:
```html
{% extends "base.html" %}
{% block title %}{{ v.topper.display }} · {{ led.label }}{% endblock %}
{% block main %}
<p><a href="{{ link('exam/' ~ led.exam) }}">{{ led.label }}</a></p>
<h1>{{ v.topper.display }} <small>rank {{ v.topper.rank }}</small></h1>
<p>{{ v.claims|length }} claims by {{ v.claims|map(attribute='institute_id')|unique|list|length }} institutes.</p>
{% for c in v.claims %}
<article class="claim">
  <h3>{{ registry.get(c.institute_id).name }} <span class="src">{{ SOURCE_LABELS[c.source_type] }}</span></h3>
  <blockquote>{{ c.window }}</blockquote>
  <p class="meta">Course named: {{ c.course_terms|join(', ') if c.course_terms else 'none' }} · observed {{ c.observed_at }}
    · <a href="{{ c.url }}" rel="noopener noreferrer nofollow">source</a>
    {% if c.search_id %} · SerpApi search {{ c.search_id }}{% endif %}
    {% if not static_mode %}{% for e in c.evidence %} · <a href="{{ link('evidence/' ~ e) }}">evidence {{ loop.index }}</a>{% endfor %}{% endif %}</p>
  <ul class="flags">{% for f in c.flags %}<li class="{{ f.rule_id }}"><b>{{ RULES[f.rule_id][0] }}</b> {{ f.detail }}</li>{% endfor %}</ul>
</article>
{% endfor %}
<h2>The topper's own words</h2>
{% if v.interview %}
<p>From <a href="https://www.youtube.com/watch?v={{ v.interview.video_id }}" rel="noopener noreferrer nofollow">{{ v.interview.title }}</a> ({{ v.interview.channel }}).</p>
<ul>{% for s in v.selfreports %}<li><a href="https://www.youtube.com/watch?v={{ s.video_id }}&t={{ (s.start_ms // 1000) }}s" rel="noopener noreferrer nofollow">{{ s.start_ms // 60000 }} min</a> {{ s.statement }} <em>({{ s.polarity }})</em></li>{% endfor %}</ul>
{% else %}<p>No independent interview with a transcript was found.</p>{% endif %}
<h2>What Google AI Mode says</h2>
{% if v.ai %}<blockquote>{{ v.ai.excerpt }}</blockquote><p class="meta">Institutes named: {{ v.ai.institutes|join(', ') or 'none' }} · SerpApi search {{ v.ai.search_id }}</p>{% else %}<p>Not collected.</p>{% endif %}
{% endblock %}
```

`toppertrail/web/templates/institute.html`:
```html
{% extends "base.html" %}
{% block title %}{{ v.institute.name }} · {{ led.label }}{% endblock %}
{% block main %}
<p><a href="{{ link('exam/' ~ led.exam) }}">{{ led.label }}</a></p>
<h1>{{ v.institute.name }}</h1>
<p>{{ v.claims|length }} claims about {{ v.claims|map(attribute='rank')|unique|list|length }} toppers in this ledger.</p>
<h2>Wording found in its material</h2>
<ul>{% for f in v.signals %}<li><b>{{ RULES[f.rule_id][0] }}</b> {{ f.detail }}</li>{% else %}<li>None found.</li>{% endfor %}</ul>
<h2>Claims</h2>
<table class="data"><thead><tr><th>Rank</th><th>Source</th><th>Course named</th></tr></thead><tbody>
{% for c in v.claims %}<tr><td><a href="{{ link('exam/' ~ led.exam ~ '/topper/' ~ c.rank) }}">{{ c.rank }}</a></td><td>{{ SOURCE_LABELS[c.source_type] }}</td><td>{{ c.course_terms|join(', ') or 'none' }}</td></tr>{% endfor %}
</tbody></table>
<h2>CCPA orders on record</h2>
<ul>{% for o in v.orders %}<li>{{ o.order_date }}: {{ o.exam }} {{ o.exam_year or '' }}, penalty Rs {{ o.penalty_inr }} · <a href="{{ o.pib or o.order_pdf }}" rel="noopener noreferrer nofollow">source</a></li>{% else %}<li>None in the register for this institute.</li>{% endfor %}</ul>
{% endblock %}
```

`toppertrail/web/templates/methodology.html`:
```html
{% extends "base.html" %}
{% block title %}Methodology · TopperTrail{% endblock %}
{% block main %}
<h1>Methodology</h1>
<p>Claims come only from sources an institute controls: its registered website, its YouTube channels and its own Google ads in India. Every verdict below is a fixed rule; no AI model decides anything.</p>
<table class="data"><thead><tr><th>Rule</th><th>What it means</th><th>Basis</th></tr></thead><tbody>
{% for id, pair in RULES.items() %}<tr><td>{{ id }}</td><td>{{ pair[0] }}</td><td>{{ pair[1] }}</td></tr>{% endfor %}
</tbody></table>
<h2>The text these rules rest on</h2>
<pre class="source">{{ guidelines }}</pre>
<h2>Request a correction</h2>
<p>If an institute discloses a course next to a claim and we missed it, open an issue on the repository with the page link. We re-run the page and publish the change.</p>
{% endblock %}
```

`toppertrail/web/templates/evidence.html`:
```html
{% extends "base.html" %}
{% block title %}Evidence {{ sha[:12] }} · TopperTrail{% endblock %}
{% block main %}
<h1>Evidence <code>{{ sha[:16] }}</code></h1>
<p>{{ 'Integrity check passed: the file hash matches its name.' if intact else 'Integrity check failed.' }}</p>
<pre class="source">{{ body }}</pre>
{% endblock %}
```

`toppertrail/web/static/style.css` (starting point; Step 4 refines it):
```css
:root { --ink:#1b1f24; --muted:#5b6470; --line:#e3e6ea; --bg:#fbfaf7; --accent:#a63d2a; }
* { box-sizing:border-box; }
body { margin:0; font:16px/1.55 system-ui, "Segoe UI", "Noto Sans Devanagari", sans-serif; color:var(--ink); background:var(--bg); }
header.site, footer.site, main { max-width:1080px; margin:0 auto; padding:16px; }
header.site { display:flex; gap:16px; align-items:baseline; flex-wrap:wrap; border-bottom:1px solid var(--line); }
.brand { font-weight:800; color:var(--accent); text-decoration:none; font-size:20px; }
.tag { color:var(--muted); }
header.site nav { margin-left:auto; }
.headline { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin:16px 0; }
.headline div { border:1px solid var(--line); background:#fff; padding:14px; border-radius:8px; }
.headline b { display:block; font-size:28px; }
.headline span { color:var(--muted); font-size:14px; }
table.data { width:100%; border-collapse:collapse; margin:8px 0 24px; }
table.data th, table.data td { text-align:left; padding:8px; border-bottom:1px solid var(--line); }
.claim { border:1px solid var(--line); background:#fff; border-radius:8px; padding:12px 16px; margin:12px 0; }
.claim blockquote { margin:8px 0; padding-left:12px; border-left:3px solid var(--line); white-space:pre-wrap; }
.src { font-size:13px; color:var(--muted); font-weight:400; }
.meta, .notice { color:var(--muted); font-size:14px; }
.flags li { margin:4px 0; }
pre.source { white-space:pre-wrap; background:#fff; border:1px solid var(--line); padding:12px; overflow-x:auto; }
@media (max-width:640px) { table.data { font-size:14px; } .headline b { font-size:22px; } }
```

Add to `toppertrail/cli.py`:
```python
@app.command()
def serve(port: int = 8765, host: str = "127.0.0.1") -> None:
    """Open the local dashboard."""
    import uvicorn

    from toppertrail.config import load_settings
    from toppertrail.web.app import create_app

    typer.echo(f"Dashboard: http://{host}:{port}/")
    uvicorn.run(create_app(load_settings().home), host=host, port=port, log_level="warning")


@app.command()
def export(out: Path = Path("site"), base: str = "/") -> None:
    """Write the static findings site."""
    from toppertrail.config import load_settings
    from toppertrail.web.export import export_site

    files_written = export_site(load_settings().home, out, base)
    typer.echo(f"Wrote {len(files_written)} pages to {out}")
```

- [ ] **Step 4: Run tests, then do the visual pass**

Run: `.venv/Scripts/python -m pytest tests/test_web.py -q`
Expected: `2 passed`.

Then invoke the `frontend-design` skill to refine `style.css` and template markup for a calm, evidence-first reading experience (claims as cards, rule flags as compact labelled chips, Devanagari rendered with a Noto Devanagari fallback, readable at 360 px width). Re-run the test after the pass; it must still pass, and no template may use `|safe`.

- [ ] **Step 5: Owner checkpoint**

Files: `toppertrail/web/ toppertrail/cli.py tests/test_web.py`. Suggested message: `feat: local dashboard and static findings export`.

---

### Task 16: Recorded runs and headline findings (live; about 193 credits)

**Files:**
- Create: `fixtures/` (exported), `docs/FINDINGS.md`, `docs/LABELLED-SAMPLE.md`

- [ ] **Step 1: Full test suite and estimates before spending**

Run:
```bash
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m toppertrail budget
.venv/Scripts/python -m toppertrail estimate upsc-cse-2025
.venv/Scripts/python -m toppertrail estimate jee-adv-2026
.venv/Scripts/python -m toppertrail estimate neet-ug-2026
```
Expected: all tests pass; estimates 145, 24, 24; account searches left at least 200. If fewer are left, run UPSC with `--top 15` and JEE/NEET with `--top 3`, and note it in `docs/FINDINGS.md`.

- [ ] **Step 2: Record UPSC first, check, then JEE and NEET**

Run:
```bash
.venv/Scripts/python -m toppertrail collect upsc-cse-2025 --record
.venv/Scripts/python -m toppertrail analyze upsc-cse-2025
```
Expected: "credits spent" at most 145, a manifest root, and headline numbers. Open `.toppertrail/ledgers/upsc-cse-2025.json` and spot check AIR 1: claims from at least Vajiram, NEXT IAS, PW and Unacademy; NEXT IAS should show `mentioned`; Vajiram `not_mentioned`. If a parser misses an obvious field, fix the code and re-run `analyze` (no new credits; evidence is stored).

Then:
```bash
.venv/Scripts/python -m toppertrail collect jee-adv-2026 --record
.venv/Scripts/python -m toppertrail analyze jee-adv-2026
.venv/Scripts/python -m toppertrail collect neet-ug-2026 --record
.venv/Scripts/python -m toppertrail analyze neet-ug-2026
```

- [ ] **Step 3: Replay parity from fixtures**

Run:
```bash
rm -rf .toppertrail/runs .toppertrail/evidence .toppertrail/ledgers
TOPPERTRAIL_REPLAY=1 .venv/Scripts/python -m toppertrail collect upsc-cse-2025
TOPPERTRAIL_REPLAY=1 .venv/Scripts/python -m toppertrail verify upsc-cse-2025
TOPPERTRAIL_REPLAY=1 .venv/Scripts/python -m toppertrail analyze upsc-cse-2025
```
Expected: `missing: 0`, "Manifest root matches the recorded run.", and the same ledger hash as Step 2.

- [ ] **Step 4: Fixture key and size check**

Run:
```bash
grep -rn "api_key=[^R]" fixtures || echo clean
grep -rln "json_endpoint" fixtures || echo clean
du -sh fixtures
```
Expected: `clean`, `clean`, and a size under 25 MB. Also search fixtures for the literal key value from `.env` with a one-off command the owner runs (`grep -rc "$(grep SERPAPI_API_KEY .env | cut -d= -f2)" fixtures | grep -v ':0' || echo clean`).

- [ ] **Step 5: Hand-labelled sample (owner, about 40 minutes)**

Run a one-off sampler and give the owner the list to label before showing rule output:
```bash
.venv/Scripts/python -c "import json,random;L=json.load(open('.toppertrail/ledgers/upsc-cse-2025.json',encoding='utf-8'));random.seed(20261009);S=random.sample(L['claims'],min(40,len(L['claims'])));open('docs/LABELLED-SAMPLE.md','w',encoding='utf-8').write('# Labelled sample\n\nseed 20261009\n\n'+'\n'.join(f\"{i+1}. {c['claim_id']} | {c['institute_id']} | rank {c['rank']} | {c['window'][:200].replace(chr(10),' ')} | course stated (y/n): __ | course type: __\" for i,c in enumerate(S)))"
```
The owner fills the blanks. Then compare their answers with the ledger's `course_types` and TT-01 and add the agreement (count and share) to `docs/VALIDATION.md` under `## Hand-labelled sample`.

- [ ] **Step 6: Write `docs/FINDINGS.md`**

Copy the printed headline numbers for each exam, the AI Mode numbers, the three strongest topper examples (with links and the topper's own quote), and the date "as observed on 2026-10-0X". Every number must come from `analyze` output; nothing is typed by hand.

- [ ] **Step 7: Owner checkpoint**

Files: `fixtures/ docs/FINDINGS.md docs/LABELLED-SAMPLE.md docs/VALIDATION.md` plus any code fixes. Suggested message: `data: recorded UPSC, JEE and NEET runs with replay fixtures`.

---

### Task 17: README, methodology, demo script, submission text, CI

**Files:**
- Modify: `README.md`
- Create: `docs/METHODOLOGY.md`, `docs/DEMO-SCRIPT.md`, `docs/SUBMISSION.md`, `.github/workflows/ci.yml`
- Test: `tests/test_replay_parity.py`

- [ ] **Step 1: Write the replay parity test (runs in CI when fixtures exist)**

`tests/test_replay_parity.py`:
```python
import json
from pathlib import Path

import pytest

from toppertrail.collect import Collector, manifest_path
from toppertrail.data import load_exam, load_independent, load_registry, load_roster
from toppertrail.evidence import EvidenceStore
from toppertrail.extract.courses import Lexicon
from toppertrail.fetch.images import ReplayImageReader
from toppertrail.fetch.pages import ReplayPageFetcher
from toppertrail.serp.replay import ReplaySerpClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.parametrize("exam_id", ["upsc-cse-2025", "jee-adv-2026", "neet-ug-2026"])
def test_replay_matches_recorded_manifest(exam_id, tmp_path):
    path = manifest_path(FIXTURES, exam_id)
    if not path.exists():
        pytest.skip("no recorded fixtures yet")
    recorded = json.loads(path.read_text(encoding="utf-8"))
    exam = load_exam(exam_id)
    top = sum(1 for _ in load_roster(exam, exam.default_top))
    col = Collector(exam, load_roster(exam, top), load_registry(), load_independent(), Lexicon.load(),
                    ReplaySerpClient(FIXTURES), ReplayPageFetcher(FIXTURES), ReplayImageReader(FIXTURES),
                    EvidenceStore(tmp_path))
    run = col.run()
    assert col.missing == 0
    assert run.manifest_root() == recorded["manifest_root"]


def test_fixtures_contain_no_keys():
    if not FIXTURES.exists():
        pytest.skip("no fixtures")
    for p in FIXTURES.rglob("*.json"):
        text = p.read_text(encoding="utf-8")
        assert "json_endpoint" not in text, p
        assert "api_key=" not in text.replace("api_key=REDACTED", ""), p
```

If a run used a smaller `--top` than `default_top`, change the test to read `top` from the recorded manifest by adding a `"top"` field in `export_fixtures` (pass `top=len(toppers)` from the CLI) and use it here.

Run: `.venv/Scripts/python -m pytest tests/test_replay_parity.py -q`
Expected: `4 passed` after Task 16 (or skips before it).

- [ ] **Step 2: CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -q
      - name: Judge mode replay
        env: {TOPPERTRAIL_REPLAY: "1"}
        run: |
          toppertrail collect upsc-cse-2025
          toppertrail verify upsc-cse-2025
          toppertrail analyze upsc-cse-2025
```

- [ ] **Step 3: README**

Replace `README.md` with these sections, filling numbers only from `docs/FINDINGS.md`:
1. Title, tagline, one-paragraph problem (CCPA penalties with links), the headline finding in one sentence, a screenshot of the AIR 1 page.
2. **Try it in 60 seconds (no API key):**
   ```bash
   git clone <repo> && cd TopperTrail
   py -3.11 -m venv .venv && .venv/Scripts/python -m pip install -e .
   set TOPPERTRAIL_REPLAY=1   # PowerShell: $env:TOPPERTRAIL_REPLAY="1"; bash: export TOPPERTRAIL_REPLAY=1
   toppertrail collect upsc-cse-2025 && toppertrail analyze upsc-cse-2025 && toppertrail serve
   ```
3. **Run it live:** `.env` with `SERPAPI_API_KEY`, `toppertrail estimate`, `collect --record`, the credit table from the spec.
4. **Why this needs SerpApi:** the engine table from spec section 6, with the fields used.
5. **How a verdict is made:** rules TT-01 to TT-14 with their basis; "no AI model decides anything".
6. **Validation:** link `docs/VALIDATION.md` and paste its result table.
7. **Limitations:** registry is a lower bound; JS-only pages are snippet-only; English OCR only; auto-caption errors; observed dates.
8. **Ethics and corrections:** the notice text, people's data rules, correction process.
9. **AI tools disclosure:** "Code and docs written with Claude Code (Anthropic). Every number in this README is produced by the code from recorded evidence."
10. License (MIT).

- [ ] **Step 4: `docs/METHODOLOGY.md`, `docs/DEMO-SCRIPT.md`, `docs/SUBMISSION.md`**

`docs/METHODOLOGY.md`: pipeline steps from spec section 7, window definition (the mention block, plus an adjacent block only when that block names no other topper), interview pick rule, self-report rule (first person in the surrounding segments, negation in the anchor and next segment), claims-only-from-controlled-sources rule.

`docs/DEMO-SCRIPT.md` (target 2:45, recorded with replay so it is identical every take):
```markdown
0:00-0:20  Problem: CCPA fined Vajiram & Ravi Rs 7 lakh for "8 of top 10"; 7 had only a free interview programme. Parents pay Rs 1 to 3 lakh on these claims.
0:20-0:45  `toppertrail estimate upsc-cse-2025` (145 credits, per engine), then `collect` in replay mode and `verify` (manifest matches).
0:45-1:45  Dashboard, AIR 1: count of institutes; open three claims (Vajiram IGP, NEXT IAS CA-VA vs IGP, a poster); the flags; the topper's own words at 30:07 and 1:07:25.
1:45-2:15  Institute scorecard: course stated %, interview-only, count claims, CCPA orders on record.
2:15-2:35  AI Mode finding: how many answers name an institute, and how many of those claims are interview-only or not mentioned by the topper.
2:35-2:45  Close: "One rank. Many claims. Follow the trail." Repo link.
```

`docs/SUBMISSION.md`: project name "TopperTrail"; track "Knowledge & Public Interest"; description (what it does, who it helps); "How the project uses SerpApi" (engine table condensed to one paragraph per engine); AI tools used: "Claude Code (Anthropic) for code, tests and documentation; no AI model is used inside the product"; new project; repo and video links (filled on 10 Oct).

- [ ] **Step 5: Run everything**

Run:
```bash
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m ruff check .
```
Expected: all tests pass; ruff clean.

- [ ] **Step 6: Owner checkpoint**

Files: `README.md docs/ .github/workflows/ci.yml tests/test_replay_parity.py`. Suggested message: `docs: README, methodology, demo script, submission text and CI`.

---

### Task 18: Judge-mode dry run from a clean clone and submission checklist

- [ ] **Step 1: Clean-clone dry run (after the owner pushes)**

Run in a temporary folder:
```bash
cd "$(mktemp -d)" && git clone https://github.com/<owner>/TopperTrail.git && cd TopperTrail
py -3.11 -m venv .venv && .venv/Scripts/python -m pip install -e .
TOPPERTRAIL_REPLAY=1 .venv/Scripts/toppertrail collect upsc-cse-2025
TOPPERTRAIL_REPLAY=1 .venv/Scripts/toppertrail verify upsc-cse-2025
TOPPERTRAIL_REPLAY=1 .venv/Scripts/toppertrail analyze upsc-cse-2025
```
Expected: no errors, `missing: 0`, manifest matches, ledger hash equals `docs/FINDINGS.md`.

- [ ] **Step 2: Incognito checks (owner)**

Open the repo URL and the unlisted YouTube video in a private window; both open without sign-in. The video is under 3:00.

- [ ] **Step 3: Submission (owner, by 18:00 IST on 10 Oct)**

Paste `docs/SUBMISSION.md` into the form at https://serpapi.github.io/serpapi-india-hackathon-2026/submit.html, choose the "Knowledge & Public Interest" track, answer "How did you hear" truthfully, tick the three acknowledgements, press "Submit project" (not just save draft), and confirm the submitted state on the dashboard.
