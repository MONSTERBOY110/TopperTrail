from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
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
    out.append(Planned("google_images",
                       {"q": exam.images_query.format(**fmt), "gl": "in", "hl": "en"},
                       "images", t.rank))
    out.append(Planned("youtube",
                       {"search_query": exam.youtube_query.format(**fmt), "gl": "in", "hl": "en"},
                       "youtube", t.rank))
    out.append(Planned("google_ai_mode",
                       {"q": exam.ai_mode_query.format(**fmt), "gl": "in", "hl": "en"},
                       "ai_mode", t.rank))
    return out


def ads_queries(exam: Exam, registry: Registry) -> list[Planned]:
    targets = sorted(registry.ads_for(exam.tag), key=lambda p: (p[0].id, p[1]))
    return [
        Planned(
            "google_ads_transparency_center",
            {
                "text": domain,
                "region": "2356",
                "start_date": exam.result_date.strftime("%Y%m%d"),
                "end_date": exam.ads_end_date.strftime("%Y%m%d"),
                "num": "100",
            },
            "ads",
            None,
            inst.id,
        )
        for inst, domain in targets
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


def _epoch(d: date) -> int:
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
        if any(find_name(text, t.name) for t in self.toppers):
            return True
        return self.lexicon.signal_terms(text)

    def _missing(self, run: Run, what: str, reason: str) -> None:
        self.missing += 1
        sha = self.store.put({"what": what})  # the reason varies by run; keep it in meta
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
        doc = {
            "engine": p.engine,
            "params": canonical_params(p.engine, p.params),
            "purpose": p.purpose,
            "rank": p.rank,
            "institute_id": p.institute_id,
            "response": result.data,
            **(extra or {}),
        }
        meta = {"engine": p.engine, "purpose": p.purpose, "rank": p.rank,
                "institute_id": p.institute_id}
        run.add(ArtifactRef("serp", key, self.store.put(doc), meta))
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
        if it.error == "missing_fixture":
            return  # replay of a run that did not read this image (for example OCR was off)
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
            limit = self.exam.video_details_per_topper
            for vid, iid in hosted_videos(videos, t, self.registry, limit):
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


def export_fixtures(run: Run, store: EvidenceStore, fixtures: Path,
                    top: int | None = None) -> int:
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
    tops = {a.meta.get("rank") for a in run.artifacts if a.meta.get("rank")}
    _write(manifest_path(fixtures, run.exam_id), {
        "exam": run.exam_id,
        "manifest_root": run.manifest_root(),
        "artifacts": len(run.artifacts),
        "top": top if top is not None else max(tops, default=0),
    })
    return n
