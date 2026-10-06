from __future__ import annotations

from collections.abc import Sequence

from toppertrail.data import Registry
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.text import context_ok, mentions, ranks_in, trim_around
from toppertrail.hashing import short_hash
from toppertrail.models import Claim, Exam, Institute, Signal, Topper

WINDOW_LIMIT = 600
# Sources where publishing the topper is itself the association: the institute hosts the
# video or pays for the ad. A poster on the institute's site can be a news thumbnail, so it
# needs the same association words as a page, and its watermark name does not count.
ALWAYS_CLAIMS = {"youtube_hosted", "youtube_description", "ad_creative"}
# Image text (OCR) keeps the words but not the layout, so a rank printed beside one name in a
# grid of toppers may belong to another.
IMAGE_TEXT = {"poster", "ad_creative"}
URL_CUES = ("selection", "our-result", "results-disclosure", "our-topper", "achiever",
            "hall-of-fame", "success-stor", "associated")


def _joins(block: str, mentions_in_block) -> bool:
    """A neighbour block joins the window unless it names another topper or is image alt text
    (a banner's alt text next to a name is not a disclosure about that name)."""
    return not mentions_in_block and not block.lstrip().lower().startswith("image:")


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
        cm = self.lexicon.classify(window, squashed=source_type in IMAGE_TEXT)
        cid = short_hash(f"{self.exam.id}|{topper.rank}|{inst.id}|{source_type}|{url}")
        return Claim(
            claim_id=cid,
            exam_id=self.exam.id,
            rank=topper.rank,
            institute_id=inst.id,
            source_type=source_type,
            url=url,
            title=title,
            window=trim_around(window, topper.name, WINDOW_LIMIT),
            course_types=cm.course_types,
            course_terms=cm.terms,
            paid_free_stated=cm.paid_free,
            duration_stated=cm.duration,
            vague_label=cm.vague and not cm.course_types,
            claimed_rank=claimed_rank,
            search_id=search_id,
            evidence=tuple(evidence),
            observed_at=observed_at,
        )

    def _associated(self, window: str, inst: Institute, url: str, source_type: str) -> bool:
        if source_type in ALWAYS_CLAIMS:
            return True
        image = source_type in IMAGE_TEXT
        if self.lexicon.associated(window) or \
                self.lexicon.classify(window, squashed=image).course_types:
            return True
        if source_type != "poster" and inst.id in self.registry.find_aliases(window):
            return True
        return any(cue in url.lower() for cue in URL_CUES)

    def _signals(self, inst: Institute, text: str, url: str,
                 evidence: tuple[str, ...]) -> list[Signal]:
        lex = self.lexicon
        out = [Signal(inst.id, "TT-09", t, url, evidence) for t in lex.superlatives(text)]
        out += [Signal(inst.id, "TT-10", t, url, evidence) for t in lex.guarantees(text)]
        out += [Signal(inst.id, "TT-11", t, url, evidence) for t in lex.aggregates(text)]
        return out

    def from_blocks(self, inst: Institute, url: str, title: str,
                    blocks: Sequence[tuple[int, str]], source_type: str, search_id: str | None,
                    evidence: tuple[str, ...], observed_at: str,
                    require_year: bool = True) -> tuple[list[Claim], list[Signal], list[dict]]:
        index = dict(blocks)
        image = source_type in IMAGE_TEXT
        found = {i: mentions(text, self.toppers, squashed=image) for i, text in blocks}
        claims: list[Claim] = []
        unresolved: list[dict] = []
        done: set[int] = set()
        for i, text in blocks:
            for m in found[i]:
                if m.topper.rank in done:
                    continue
                parts = [text]
                if i - 1 in index and _joins(index[i - 1], found.get(i - 1)):
                    parts.insert(0, index[i - 1])
                if i + 1 in index and _joins(index[i + 1], found.get(i + 1)):
                    parts.append(index[i + 1])
                window = "\n".join(parts)
                context = f"{window} {title} {url}"
                if not context_ok(context, self.exam.year, self.exam.context_terms, require_year):
                    unresolved.append({
                        "rank": m.topper.rank,
                        "institute_id": inst.id,
                        "url": url,
                        "reason": "exam or year not stated near the name",
                    })
                    continue
                if not self._associated(window, inst, url, source_type):
                    unresolved.append({
                        "rank": m.topper.rank,
                        "institute_id": inst.id,
                        "url": url,
                        "reason": "named without claiming the topper",
                    })
                    continue
                done.add(m.topper.rank)
                claimed = m.claimed_rank
                if (source_type in IMAGE_TEXT and claimed != m.topper.rank
                        and (len(found[i]) > 1 or len(ranks_in(text)) > 1)):
                    claimed = None
                claims.append(self._claim(m.topper, inst, source_type, url, title, window,
                                          claimed, search_id, evidence, observed_at))
        unresolved = [u for u in unresolved if u["rank"] not in done]
        signal_text = "\n".join(t for _, t in blocks)
        return claims, self._signals(inst, signal_text, url, evidence), unresolved
