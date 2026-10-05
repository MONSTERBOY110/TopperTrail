from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz

from toppertrail.models import Topper

_ZERO_WIDTH = dict.fromkeys(map(ord, "‌‍﻿"), None)
_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
_NUKTA = "़"
_TOKEN = re.compile(r"[a-z0-9]+")
_ASCII = re.compile(r"^[\x00-\x7f]+$")
_RANK = re.compile(
    r"(?<![a-z])(?:all india rank|air|rank|crl)\s*[-:#]?\s*(\d{1,4})(?!\d)"
    r"|रैंक\s*[-:#]?\s*(\d{1,4})(?!\d)"
    r"|(?<!\d)(\d{1,4})\s*(?:st|nd|rd|th)?\s*rank(?![a-z])"
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
    # Devanagari: the term must start a word (so "मोशन" never matches inside "इमोशन"),
    # but may carry a suffix (so "मॉक इंटरव्यू" still matches "मॉक इंटरव्यूज").
    return re.compile(rf"(?<![ऀ-ॿ]){esc}")


def name_tokens(name: str) -> list[str]:
    return [tok for tok in _TOKEN.findall(normalize(name)) if len(tok) > 1]


def name_regex(name: str) -> re.Pattern[str] | None:
    """Case-insensitive pattern for a name in original text, tolerant of dotted initials."""
    tokens = [t for t in re.findall(r"[A-Za-z0-9]+", name) if len(t) > 1]
    if not tokens:
        return None
    joined = r"\W+(?:[A-Za-z]\W+)*".join(map(re.escape, tokens))
    return re.compile(r"\b" + joined + r"\b", re.IGNORECASE)


def snap_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Move a cut inward to whitespace so no word is split."""
    if start > 0:
        space = text.find(" ", start)
        start = space + 1 if 0 <= space < end else start
    if end < len(text):
        space = text.rfind(" ", start, end)
        end = space if space > start else end
    return start, end


def trim_around(text: str, name: str, limit: int) -> str:
    """Keep at most `limit` characters around the first match of the name, cut at words."""
    if len(text) <= limit:
        return text
    pattern = name_regex(name)
    m = pattern.search(text) if pattern else None
    room = limit - 6  # space for the two "..." marks
    start = 0 if not m else max(0, min(m.start() - room // 3, len(text) - room))
    start, end = snap_span(text, start, start + room)
    return ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")


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
            if topper.rank in tight:
                claimed = topper.rank  # a list sentence may put a neighbour's rank closer
            else:
                claimed = tight[0] if tight else None
            out.append(Mention(topper, span[0], span[1], claimed))
            break
    return out


def context_ok(text: str, year: int, terms: Sequence[str], require_year: bool = True) -> bool:
    norm = normalize(text)
    if require_year and str(year) not in norm:
        return False
    return any(term_pattern(term).search(norm) for term in terms)
