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
    r"|(?<!\d)(?!(?:19|20)\d\d(?!\d))(\d{1,4})\s*(?:st|nd|rd|th)?\s*rank(?![a-z])"
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
        m = re.compile(r"\s").search(text, start)
        start = m.end() if m and m.start() < end else start
    if end < len(text):
        cuts = [m.start() for m in re.finditer(r"\s", text[start:end])]
        end = start + cuts[-1] if cuts and cuts[-1] > 0 else end
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


SQUASH_MIN = 10  # shorter squashed terms or names would match inside unrelated words


# Words in OCR text: spaces are often dropped, so a change from lower to upper case or between
# letters and digits also ends a word ("2025TOPPER", "OnlineClassroomProgram").
_OCR_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+|[\u0900-\u097f]+")


def ocr_words(text: str) -> str:
    """Image text as normalized words joined by '|'."""
    words = _OCR_WORD.findall(unicodedata.normalize("NFC", text))
    return "|".join(normalize(w) for w in words)


MERGED_RUN = 15  # an OCR "word" this long is several words run together


def ocr_pattern(term: str) -> re.Pattern[str]:
    """`term` with its spaces optional, for searching ocr_words() output with ocr_find()."""
    return re.compile(r"\|?".join(re.escape(c) for c in squash(term)))


def ocr_find(pattern: re.Pattern[str], flat: str, whole: bool) -> re.Match[str] | None:
    """First match that starts a word, or starts anywhere inside a long merged run (whose real
    word starts are unknown). With `whole` (names) it must start and end a word, so a name
    never matches inside a longer name."""
    for m in pattern.finditer(flat):
        begin = flat.rfind("|", 0, m.start()) + 1
        stop = flat.find("|", m.start())
        word = flat[begin:stop if stop >= 0 else len(flat)]
        starts = m.start() == begin
        if whole:
            if starts and (m.end() == len(flat) or flat[m.end()] == "|"):
                return m
        elif starts or len(word) >= MERGED_RUN:
            return m
    return None


def squash(text: str) -> str:
    """Letters and digits only. OCR of a poster often drops the spaces between words."""
    return re.sub(r"[^a-z0-9\u0900-\u097f]", "", normalize(text))


def ranks_in(text: str) -> set[int]:
    """Every rank number printed in the text."""
    return {int(next(g for g in m.groups() if g)) for m in _RANK.finditer(normalize(text))}


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


def mentions(text: str, toppers: Sequence[Topper], squashed: bool = False) -> list[Mention]:
    """Toppers named in the text. With `squashed` (image text), a full name whose words OCR
    ran together also counts, and only the official rank is read for it: with the layout gone,
    any other printed rank may belong to someone else."""
    norm = normalize(text)
    out = []
    flat = ocr_words(text) if squashed else ""
    for topper in toppers:
        spans = find_name(text, topper.name)
        if (not spans and squashed and len(name_tokens(topper.name)) >= 2
                and len(squash(topper.name)) >= SQUASH_MIN
                and ocr_find(ocr_pattern(topper.name), flat, whole=True)):
            claimed = topper.rank if topper.rank in ranks_in(text) else None
            out.append(Mention(topper, 0, 0, claimed))
            continue
        for span in spans:
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
