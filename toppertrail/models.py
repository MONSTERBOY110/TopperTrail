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
