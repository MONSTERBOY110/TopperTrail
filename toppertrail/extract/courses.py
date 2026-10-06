from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from toppertrail.data import read_data
from toppertrail.extract.text import (
    SQUASH_MIN,
    normalize,
    ocr_find,
    ocr_pattern,
    ocr_words,
    squash,
    term_pattern,
)

INTERVIEW_ONLY = "interview_only"
GENERIC = "coaching_generic"
COURSE_NAMES = {
    "interview_only": "interview programme",
    "foundation_classroom": "classroom or foundation course",
    "test_series": "test series",
    "optional": "optional subject course",
    "crash_course": "crash course",
    "mentorship": "mentorship",
    "current_affairs": "current affairs course",
    "essay_ethics": "essay or ethics course",
    "online_distance": "online or distance course",
    "coaching_generic": "coaching",
}


def course_names(types) -> str:
    return ", ".join(COURSE_NAMES.get(t, t) for t in types)


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


def _order(entry: tuple[str, str, re.Pattern[str]]) -> tuple[int, str]:
    return (-len(entry[1]), entry[1])


def _masked_hits(
    text: str, pats: list[tuple[str, str, re.Pattern[str]]]
) -> list[tuple[str, str]]:
    """Longest terms first; each match is blanked so shorter terms cannot re-match inside it."""
    masked = normalize(text)
    hits = []
    for label, term, pattern in pats:
        if pattern.search(masked):
            hits.append((label, term))
            masked = pattern.sub(lambda m: " " * len(m.group()), masked)
    return hits


class Lexicon:
    def __init__(self, raw: dict) -> None:
        course = [
            (ctype, normalize(t), term_pattern(t))
            for ctype, terms in raw["course_types"].items()
            for t in terms
        ]
        generic = [(GENERIC, normalize(t), term_pattern(t)) for t in raw["generic_coaching"]]
        self._course = sorted(course, key=_order)
        # Multi-word course names, spaces removed, for OCR text that ran the words together.
        self._squashed = [
            (ctype, term, ocr_pattern(term))
            for ctype, term, _ in sorted(course, key=lambda e: (-len(squash(e[1])), e[1]))
            if " " in term and len(squash(term)) >= SQUASH_MIN]
        self._with_generic = sorted(course + generic, key=_order)
        self._vague = [p for _, p in _compile(raw["vague_labels"])]
        self._paid = [p for _, p in _compile(raw["paid_free"])]
        self._duration = [re.compile(p) for p in raw["duration_patterns"]]
        self._sup = [(t, t, p) for t, p in _compile(raw["superlatives"])]
        self._guar = [(t, t, p) for t, p in _compile(raw["guarantees"])]
        self._agg = [re.compile(p) for p in raw["aggregate_patterns"]]
        self._assoc = [p for _, p in _compile(raw["association_cues"])]
        self._first = [p for _, p in _compile(raw["first_person"])]
        self._neg = [p for _, p in _compile(raw["negations"])]

    @classmethod
    def load(cls) -> Lexicon:
        return cls(yaml.safe_load(read_data("lexicon.yaml")))

    def classify(self, text: str, include_generic: bool = False,
                 squashed: bool = False) -> CourseMatch:
        norm = normalize(text)
        hits = _masked_hits(text, self._with_generic if include_generic else self._course)
        if squashed:
            flat = ocr_words(text)
            for label, term, pattern in self._squashed:
                m = ocr_find(pattern, flat, whole=False)
                if m:
                    hits.append((label, term))
                    flat = flat[:m.start()] + "#" * (m.end() - m.start()) + flat[m.end():]
        return CourseMatch(
            course_types=tuple(sorted({label for label, _ in hits})),
            terms=tuple(sorted({term for _, term in hits})),
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

    def associated(self, text: str) -> bool:
        """Words that tie a named topper to the institute publishing the text."""
        norm = normalize(text)
        return any(p.search(norm) for p in self._assoc)

    def first_person(self, text: str) -> bool:
        norm = normalize(text)
        return any(p.search(norm) for p in self._first)

    def negated(self, text: str) -> bool:
        norm = normalize(text)
        return any(p.search(norm) for p in self._neg)
