from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import parse_qs, urlsplit

from toppertrail.data import IndependentChannels, Registry
from toppertrail.extract.courses import GENERIC, Lexicon, course_names
from toppertrail.extract.text import find_name, normalize
from toppertrail.models import Claim, SelfReport, Topper

NEAR_MS = 15_000  # caption segments further apart than this are not one statement


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
    """The topper's own interview: an independent channel, not an institute's mock interview."""
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
        if not inst or not vid or inst.id in seen:
            continue
        if not find_name(v.get("title") or "", topper.name):
            continue
        seen.add(inst.id)
        out.append((vid, inst.id))
        if len(out) >= limit:
            break
    return out


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


def own_words_status(claim: Claim, reports: Sequence[SelfReport],
                     has_interview: bool) -> tuple[str, str]:
    if not has_interview:
        return "no_interview", "No independent interview with a transcript was found."
    affirm = [r for r in reports if r.institute_id == claim.institute_id and r.polarity == "affirm"]
    if affirm:
        said = sorted({c for r in affirm for c in r.course_types if c != GENERIC})
        what = course_names(said) if said else "course not said"
        when = _clock(affirm[0].start_ms)
        return "mentioned", f"The topper mentions this institute ({what}) at {when}."
    claimed = set(claim.course_types)
    affirmed = {c for r in reports if r.polarity == "affirm" for c in r.course_types} - {GENERIC}
    for r in reports:
        if r.polarity != "deny" or r.institute_id not in (None, claim.institute_id):
            continue
        types = set(r.course_types)
        if r.institute_id is None and types - {GENERIC} and types - {GENERIC} <= affirmed:
            continue  # elsewhere the topper says they did take this kind of course
        if claimed & types or (GENERIC in types and "foundation_classroom" in claimed):
            return "denied", (f"At {_clock(r.start_ms)} the topper's own words may not match "
                              f"the course this claim names; check the quote.")
    return "not_mentioned", "The topper does not mention this institute in the interview."
