"""Build a layout-review ledger from pages and video metadata saved during research.

This runs the real Collector and analyzer, but answers search queries from files saved on
5 Oct 2026 instead of SerpApi, so it spends no credits. The ledger is marked as a preview
and must never be presented as a SerpApi finding.

Usage: python scripts/research_preview.py <evidence dir> [--home .toppertrail-preview]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from toppertrail.analyze import analyze, ledger_hash
from toppertrail.collect import Collector
from toppertrail.data import load_exam, load_independent, load_registry, load_roster
from toppertrail.evidence import EvidenceStore
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.text import find_name, normalize, snap_span
from toppertrail.fetch.pages import PageSnapshot, html_to_blocks
from toppertrail.hashing import sha256_bytes
from toppertrail.serp.base import MissingFixture, SerpResult

PREVIEW_NOTE = (
    "Preview built from institute pages and YouTube metadata saved during research on "
    "5 Oct 2026. Not a SerpApi run; for layout review only."
)


def url_from_filename(name: str) -> str:
    stem = name[: -len(".html")]
    host, _, rest = stem.partition("_")
    return f"https://{host}/{rest.replace('_', '/')}"


def page_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def snippet(text: str, limit: int = 240) -> str:
    """Search-result style description: cut at a word, marked with an ellipsis."""
    if len(text) <= limit:
        return text
    start, end = snap_span(text, 0, limit)
    return text[start:end].rstrip() + "..."


def clock(seconds: int) -> str:
    h, rem = divmod(int(seconds or 0), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def load_transcript(folder: Path, vid: str) -> list[dict]:
    for lang in ("hi", "en"):
        path = next(folder.rglob(f"{vid}.{lang}-orig.json3"), None)
        if path:
            doc = json.loads(path.read_text(encoding="utf-8"))
            lines = []
            for ev in doc.get("events", []):
                text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).strip()
                if text:
                    lines.append({"start_ms": int(ev.get("tStartMs", 0)), "snippet": text})
            return lines
    return []


class SavedSerp:
    """Answers the collector's queries from saved files; everything else is 'not collected'."""

    def __init__(self, evidence: Path, toppers) -> None:
        self.evidence = evidence
        self.pages = {url_from_filename(p.name): p for p in evidence.glob("*.html")}
        self.videos = [json.loads(p.read_text(encoding="utf-8"))
                       for p in sorted(evidence.rglob("*.info.json"))]
        self.toppers = toppers

    def _topper(self, text: str):
        for t in self.toppers:
            if find_name(text, t.display_name):
                return t
        return None

    def search(self, engine: str, params: dict) -> SerpResult:
        meta = {"search_metadata": {"id": "research-preview",
                                    "created_at": "2026-10-05 00:00:00 UTC"}}
        if engine == "google" and params.get("hl") == "en":
            t = self._topper(params["q"])
            slug = "-".join(normalize(t.name).split()[:2]) if t else "\x00"
            results = []
            for url, path in sorted(self.pages.items()):
                if slug in normalize(path.name) or (t and t.rank == 1 and "toppers" in path.name):
                    html = path.read_text(encoding="utf-8", errors="replace")
                    results.append({"link": url, "title": page_title(html), "snippet": ""})
            return SerpResult(engine, params, {**meta, "organic_results": results}, "replay")
        if engine == "youtube":
            t = self._topper(params["search_query"])
            rows = []
            for v in self.videos:
                if t and find_name(v.get("title") or "", t.name):
                    rows.append({
                        "title": v.get("title"),
                        "link": f"https://www.youtube.com/watch?v={v['id']}",
                        "channel": {"name": v.get("channel"),
                                    "link": f"https://www.youtube.com/channel/{v.get('channel_id')}"},
                        "length": clock(v.get("duration")),
                        "description": snippet(v.get("description") or ""),
                        "published_date": v.get("upload_date"),
                    })
            return SerpResult(engine, params, {**meta, "video_results": rows}, "replay")
        if engine == "youtube_video":
            v = next((x for x in self.videos if x["id"] == params["v"]), None)
            if v:
                data = {**meta, "title": v.get("title"), "description": v.get("description") or "",
                        "channel": {"name": v.get("channel")}}
                return SerpResult(engine, params, data, "replay")
        if engine == "youtube_video_transcript":
            lines = load_transcript(self.evidence, params["v"])
            if lines:
                return SerpResult(engine, params, {**meta, "transcript": lines}, "replay")
        raise MissingFixture(f"not saved during research: {engine}")


class SavedPages:
    def __init__(self, serp: SavedSerp) -> None:
        self.serp = serp

    def fetch(self, url: str) -> PageSnapshot:
        path = self.serp.pages.get(url)
        if not path:
            return PageSnapshot(url, 0, "2026-10-05", None, (), "missing_fixture")
        raw = path.read_bytes()
        html = raw.decode("utf-8", errors="replace")
        blocks = tuple(html_to_blocks(html))
        return PageSnapshot(url, 200, "2026-10-05", sha256_bytes(raw), blocks, None)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence", type=Path)
    ap.add_argument("--home", type=Path, default=Path(".toppertrail-preview"))
    args = ap.parse_args()
    exam = load_exam("upsc-cse-2025")
    toppers = load_roster(exam, 20)
    registry, lexicon = load_registry(), Lexicon.load()
    serp = SavedSerp(args.evidence, toppers)
    store = EvidenceStore(args.home / "evidence")
    col = Collector(exam, toppers, registry, load_independent(), lexicon, serp, SavedPages(serp),
                    None, store)
    run = col.run()
    run.save(args.home / "runs" / f"{exam.id}.json")
    ledger = analyze(exam, toppers, registry, lexicon, run, store)
    ledger["preview"] = PREVIEW_NOTE
    out = args.home / "ledgers" / f"{exam.id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    institutes = len({c["institute_id"] for c in ledger["claims"]})
    print(f"claims {len(ledger['claims'])}, institutes {institutes}, "
          f"selfreports {len(ledger['selfreports'])}, missing {col.missing}, "
          f"hash {ledger_hash(ledger)[:12]}")


if __name__ == "__main__":
    main()
