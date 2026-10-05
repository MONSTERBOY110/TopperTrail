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
    params = raw.get("transcript_params") or {}
    return Exam(
        id=exam_id,
        label=raw["label"],
        exam=raw["exam"],
        year=int(raw["year"]),
        tag=raw["tag"],
        rank_label=raw["rank_label"],
        result_date=raw["result_date"],
        results_file=raw["results_file"],
        context_terms=tuple(raw["context_terms"]),
        default_top=int(raw["default_top"]),
        ads_end_date=raw["ads_end_date"],
        ads_creatives_cap=int(raw["ads_creatives_cap"]),
        google_query=raw["google_query"],
        google_hi_top=int(raw["google_hi_top"]),
        images_query=raw["images_query"],
        youtube_query=raw["youtube_query"],
        ai_mode_query=raw["ai_mode_query"],
        video_details_top=int(raw["video_details_top"]),
        video_details_per_topper=int(raw["video_details_per_topper"]),
        transcripts=bool(raw["transcripts"]),
        transcript_params=tuple(sorted((k, str(v)) for k, v in params.items())),
    )


def load_roster(exam: Exam, top: int) -> list[Topper]:
    rows = csv.DictReader(io.StringIO(read_data(exam.results_file)))
    toppers = [
        Topper(exam.id, int(r["rank"]), r["name"].strip(), (r.get("extra") or "").strip())
        for r in rows
    ]
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
            id=r["id"],
            name=r["name"],
            exams=tuple(r["exams"]),
            domains=tuple(r.get("domains") or ()),
            channels=tuple(r.get("channels") or ()),
            handles=tuple(r.get("handles") or ()),
            aliases=tuple(r.get("aliases") or ()),
            ads=tuple((a["domain"], tuple(a["exams"])) for a in r.get("ads") or ()),
            legal_name=r.get("legal_name", ""),
            ccpa_orders=tuple(r.get("ccpa_orders") or ()),
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
