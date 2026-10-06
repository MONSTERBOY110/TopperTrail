from __future__ import annotations

import json
from dataclasses import asdict

from toppertrail.data import Registry
from toppertrail.evidence import EvidenceStore, Run
from toppertrail.extract.aianswer import ai_answer
from toppertrail.extract.claims import ClaimExtractor
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.selfreport import self_reports
from toppertrail.hashing import canonical_json, sha256_text
from toppertrail.models import AIAnswer, Claim, Exam, Interview, SelfReport, Signal, Topper
from toppertrail.rules import apply_rules


def _day(response: dict) -> str:
    created = (response.get("search_metadata") or {}).get("created_at") or ""
    return created[:10]


def _desc(value) -> str:
    if isinstance(value, dict):
        return str(value.get("content") or "")
    return str(value or "")


class _Builder:
    def __init__(self, ex: ClaimExtractor, registry: Registry, lexicon: Lexicon, pages: dict,
                 images: dict) -> None:
        self.ex, self.registry, self.lexicon = ex, registry, lexicon
        self.pages, self.images = pages, images
        self.claims: list[Claim] = []
        self.signals: list[Signal] = []
        self.unresolved: list[dict] = []
        self.reports: list[SelfReport] = []
        self.interviews: list[Interview] = []
        self.answers: list[AIAnswer] = []

    def take(self, result) -> list[Claim]:
        claims, signals, unresolved = result
        self.claims.extend(claims)
        self.signals.extend(signals)
        self.unresolved.extend(unresolved)
        return claims

    def organic(self, sha: str, resp: dict, rank: int, sid, day: str) -> None:
        for r in resp.get("organic_results") or []:
            inst = self.registry.by_url(r.get("link") or "")
            if not inst:
                continue
            url, title = r["link"], r.get("title") or ""
            page_sha, page = self.pages.get(url, (None, None))
            if page and page.get("blocks") and not page.get("error"):
                blocks = [(int(i), t) for i, t in page["blocks"]]
                got = self.take(self.ex.from_blocks(inst, url, title, blocks, "web_page", sid,
                                                    (sha, page_sha), page["fetched_at"] or day))
                if any(c.rank == rank for c in got):
                    continue
            blocks = [(0, title), (1, r.get("snippet") or "")]
            self.take(self.ex.from_blocks(inst, url, title, blocks, "snippet_only", sid, (sha,),
                                          day))

    def posters(self, sha: str, resp: dict, sid, day: str) -> None:
        for r in resp.get("images_results") or []:
            inst = self.registry.by_url(r.get("link") or "")
            if not inst:
                continue
            title = r.get("title") or ""
            page_sha, page = self.pages.get(r["link"], (None, None))
            if page and page.get("blocks") and not page.get("error"):
                blocks = [(int(i), t) for i, t in page["blocks"]]
                self.take(self.ex.from_blocks(inst, r["link"], title, blocks, "web_page", sid,
                                              (sha, page_sha), page["fetched_at"] or day))
            img_sha, img = self.images.get(r.get("original") or "", (None, None))
            text = img["text"] if img and not img.get("error") else ""
            if not text.strip():
                continue  # without image text the poster adds nothing beyond its page
            self.take(self.ex.from_blocks(inst, r["link"], title, [(0, title), (1, text)],
                                          "poster", sid, (sha, img_sha), day))

    def videos(self, sha: str, resp: dict, sid, day: str) -> None:
        for v in resp.get("video_results") or []:
            ch = v.get("channel") or {}
            inst = self.registry.by_channel(ch.get("link"), ch.get("name"))
            if not inst:
                continue
            title = v.get("title") or ""
            blocks = [(0, title), (1, _desc(v.get("description")))]
            self.take(self.ex.from_blocks(inst, v.get("link") or "", title, blocks,
                                          "youtube_hosted", sid, (sha,), day))

    def video_detail(self, sha: str, doc: dict, resp: dict, sid, day: str) -> None:
        inst = self.registry.get(doc["institute_id"])
        url = f"https://www.youtube.com/watch?v={doc['params'].get('v', '')}"
        title = resp.get("title") or ""
        blocks = [(0, title), (1, _desc(resp.get("description")))]
        self.take(self.ex.from_blocks(inst, url, title, blocks, "youtube_description", sid,
                                      (sha,), day))

    def transcript(self, doc: dict, resp: dict, rank: int) -> None:
        video = doc.get("video") or {}
        lines = resp.get("transcript") or []
        if not lines:
            return
        vid, channel = video.get("id", ""), video.get("channel", "")
        lang = doc["params"].get("language_code", "")
        self.interviews.append(Interview(rank, vid, channel, video.get("title", ""), lang))
        self.reports.extend(self_reports(lines, rank, vid, channel, self.registry,
                                         self.lexicon))

    def ads(self, sha: str, doc: dict, resp: dict, sid, day: str) -> None:
        inst = self.registry.get(doc["institute_id"])
        for cr in resp.get("ad_creatives") or []:
            img_sha, img = self.images.get(cr.get("image") or "", (None, None))
            if not img or img.get("error"):
                continue
            self.take(self.ex.from_blocks(inst, cr.get("details_link") or "",
                                          f"Google ad by {inst.name}", [(0, img["text"])],
                                          "ad_creative", sid, (sha, img_sha), day,
                                          require_year=False))


def analyze(exam: Exam, toppers: list[Topper], registry: Registry, lexicon: Lexicon, run: Run,
            store: EvidenceStore) -> dict:
    pages = {a.key: (a.sha256, store.get(a.sha256)) for a in run.of_kind("page")}
    images = {a.key: (a.sha256, store.get(a.sha256)) for a in run.of_kind("image")}
    b = _Builder(ClaimExtractor(exam, toppers, registry, lexicon), registry, lexicon, pages,
                 images)
    for a in sorted(run.of_kind("serp"), key=lambda a: a.key):
        doc = store.get(a.sha256)
        resp, purpose, rank = doc["response"], doc["purpose"], doc["rank"]
        sid, day = (resp.get("search_metadata") or {}).get("id"), _day(resp)
        if purpose in ("google_en", "google_hi"):
            b.organic(a.sha256, resp, rank, sid, day)
        elif purpose == "images":
            b.posters(a.sha256, resp, sid, day)
        elif purpose == "youtube":
            b.videos(a.sha256, resp, sid, day)
        elif purpose == "youtube_video":
            b.video_detail(a.sha256, doc, resp, sid, day)
        elif purpose == "transcript":
            b.transcript(doc, resp, rank)
        elif purpose == "ads":
            b.ads(a.sha256, doc, resp, sid, day)
        elif purpose == "ai_mode":
            b.answers.append(ai_answer(resp, rank, registry))

    unique = {c.claim_id: c for c in sorted(b.claims, key=lambda c: (c.claim_id, c.evidence))}
    # One image published on several pages is one advertisement: keep it once, at its first URL.
    images: set[tuple] = set()
    kept = []
    for c in sorted(unique.values(), key=lambda c: (c.url, c.claim_id)):
        if c.source_type in ("poster", "ad_creative"):
            key = (c.rank, c.institute_id, c.source_type, " ".join(c.window.split()))
            if key in images:
                continue
            images.add(key)
        kept.append(c)
    claims = sorted(kept, key=lambda c: (c.rank, c.institute_id, c.source_type, c.url))
    flags = apply_rules(exam, claims, b.signals, b.reports, b.interviews, registry)
    signals = sorted({(s.institute_id, s.rule_id, s.text, s.url): s for s in b.signals}.values(),
                     key=lambda s: (s.institute_id, s.rule_id, s.text, s.url))
    claimed = {(c.rank, c.institute_id, c.url) for c in claims}
    unresolved = {(u["rank"], u["institute_id"], u["url"]): u for u in b.unresolved
                  if (u["rank"], u["institute_id"], u["url"]) not in claimed}
    ledger = {
        "exam": exam.id,
        "label": exam.label,
        "manifest_root": run.manifest_root(),
        "toppers": [{"rank": t.rank, "name": t.name, "display": t.display_name} for t in toppers],
        "claims": [asdict(c) for c in claims],
        "signals": [asdict(s) for s in signals],
        "selfreports": [asdict(r) for r in sorted(b.reports, key=lambda r: (r.rank, r.start_ms))],
        "interviews": [asdict(i) for i in sorted(b.interviews, key=lambda i: i.rank)],
        "ai_answers": [asdict(x) for x in sorted(b.answers, key=lambda x: x.rank)],
        "flags": [asdict(f) for f in flags],
        "unresolved": [unresolved[k] for k in sorted(unresolved)],
        "missing": sorted(a.key for a in run.of_kind("missing")),
    }
    # Plain JSON (tuples become lists) so the in-memory ledger equals the one read from disk.
    return json.loads(canonical_json(ledger))


def ledger_hash(ledger: dict) -> str:
    return sha256_text(canonical_json(ledger))
