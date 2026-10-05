from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

import yaml

from toppertrail.data import Registry, read_data
from toppertrail.extract.courses import INTERVIEW_ONLY, Lexicon, course_names
from toppertrail.extract.selfreport import own_words_status
from toppertrail.models import Claim, Exam, Flag, Interview, SelfReport, Signal

RULES: dict[str, tuple[str, str]] = {
    "TT-01": ("Course not stated next to the claim",
              "Guidelines 2024, cl. 4(1)(a); CCPA directions in the NEXT IAS order of 07.09.2026"),
    "TT-02": ("Interview-only programme",
              "CCPA findings in the Vajiram & Ravi, KSG, Chahal, Drishti and StudyIQ orders"),
    "TT-03": ("Vague course label", "CCPA order against Career Line Coaching, Sikar, 09.04.2026"),
    "TT-04": ("Paid or free not stated", "Guidelines 2024, cl. 4(1)(a)"),
    "TT-05": ("Course duration not stated", "Guidelines 2024, cl. 4(1)(a)"),
    "TT-06": ("Different course labels across the institute's own sources",
              "Guidelines 2024, cl. 4(1)(e)"),
    "TT-07": ("Selective disclosure on one page",
              "CCPA orders against Vision IAS (18.12.2025) and Narayana (11.06.2026)"),
    "TT-08": ("Rank differs from the official result",
              "Guidelines 2024, cl. 3(b); CCPA order against Narayana (11.06.2026)"),
    "TT-09": ("Unsubstantiated superlative",
              "2022 Guidelines, cl. 12(a); CCPA orders against Chahal, Rau's and Sriram's"),
    "TT-10": ("Guarantee language",
              "Guidelines 2024, cl. 3(c); CCPA orders against Motion and StudyIQ"),
    "TT-11": ("Aggregate count claim", "Guidelines 2024, cl. 3(b)"),
    "TT-12": ("Topper's own words", "The topper's independent interview transcript (YouTube)"),
    "TT-13": ("Claimed for a different exam", "Informational"),
    "TT-14": ("Featured in a paid Google ad in India",
              "Google Ads Transparency Center, region India"),
}


def _interview_only(types: Sequence[str]) -> bool:
    return bool(types) and set(types) <= {INTERVIEW_ONLY}


def claim_flags(c: Claim, exam: Exam, registry: Registry) -> list[Flag]:
    out: list[Flag] = []

    def add(rule: str, detail: str) -> None:
        out.append(Flag(rule, c.institute_id, c.claim_id, c.rank, detail))

    if not c.course_types:
        add("TT-01", "No course name appears next to this claim.")
    elif _interview_only(c.course_types):
        add("TT-02", "Only an interview programme is named: " + ", ".join(c.course_terms) + ".")
    if c.vague_label:
        add("TT-03", "The label used does not name a course.")
    if not c.paid_free_stated:
        add("TT-04", "Whether the course was paid or free is not stated.")
    if not c.duration_stated:
        add("TT-05", "The course duration is not stated.")
    if c.claimed_rank is not None and c.claimed_rank != c.rank:
        add("TT-08", f"Shows rank {c.claimed_rank}; the official {exam.rank_label} is {c.rank}.")
    if exam.tag not in registry.get(c.institute_id).exams:
        add("TT-13", f"This institute's registered exams do not include {exam.label}.")
    if c.source_type == "ad_creative":
        add("TT-14", "This claim appeared in a Google ad shown in India after the result.")
    return out


def cross_flags(claims: Sequence[Claim]) -> list[Flag]:
    out: list[Flag] = []
    groups: dict[tuple[str, int], list[Claim]] = defaultdict(list)
    for c in claims:
        groups[(c.institute_id, c.rank)].append(c)
    for (iid, rank), cs in sorted(groups.items()):
        sets = sorted({c.course_types for c in cs if c.course_types})
        if len(sets) > 1:
            labels = "; ".join(course_names(s) for s in sets)
            for c in cs:
                if c.course_types:
                    out.append(Flag("TT-06", iid, c.claim_id, rank,
                                    f"This institute's own sources name different courses: "
                                    f"{labels}."))
    pages: dict[str, list[Claim]] = defaultdict(list)
    for c in claims:
        pages[c.url].append(c)
    for _, cs in sorted(pages.items()):
        if len({c.rank for c in cs}) < 2:
            continue
        stated = [c for c in cs if c.course_types]
        for c in cs:
            if stated and not c.course_types:
                out.append(Flag("TT-07", c.institute_id, c.claim_id, c.rank,
                                f"On this page the course is stated for {len(stated)} "
                                f"topper(s) but not for this one."))
    return out


def signal_flags(signals: Sequence[Signal], claims: Sequence[Claim]) -> list[Flag]:
    named: dict[str, list[Claim]] = defaultdict(list)
    for c in claims:
        named[c.institute_id].append(c)
    out: list[Flag] = []
    seen: set[tuple[str, str, str]] = set()
    for s in sorted(signals, key=lambda s: (s.institute_id, s.rule_id, s.text, s.url)):
        key = (s.institute_id, s.rule_id, s.text)
        if key in seen:
            continue
        seen.add(key)
        if s.rule_id == "TT-11":
            mine = named.get(s.institute_id, [])
            io = sum(1 for c in mine if _interview_only(c.course_types))
            detail = (f'Count claim "{s.text}". Of this institute\'s {len(mine)} named '
                      f"claim(s) in this ledger, {io} name only an interview programme.")
        elif s.rule_id == "TT-09":
            detail = f'Superlative "{s.text}" appears in this institute\'s material.'
        else:
            detail = f'Outcome wording "{s.text}" appears in this institute\'s material.'
        out.append(Flag(s.rule_id, s.institute_id, None, None, detail))
    return out


def own_words_flags(claims: Sequence[Claim], reports: Sequence[SelfReport],
                    interviews: Sequence[Interview]) -> list[Flag]:
    has = {i.rank for i in interviews}
    by_rank: dict[int, list[SelfReport]] = defaultdict(list)
    for r in reports:
        by_rank[r.rank].append(r)
    out = []
    for c in claims:
        code, detail = own_words_status(c, by_rank.get(c.rank, []), c.rank in has)
        out.append(Flag("TT-12", c.institute_id, c.claim_id, c.rank, detail, code))
    return out


def apply_rules(exam: Exam, claims: Sequence[Claim], signals: Sequence[Signal],
                reports: Sequence[SelfReport], interviews: Sequence[Interview],
                registry: Registry) -> list[Flag]:
    flags = [f for c in claims for f in claim_flags(c, exam, registry)]
    flags += cross_flags(claims)
    flags += signal_flags(signals, claims)
    flags += own_words_flags(claims, reports, interviews)
    return sorted(flags, key=lambda f: (f.rule_id, f.institute_id, f.rank or 0,
                                        f.claim_id or "", f.detail))


def load_orders() -> dict:
    return yaml.safe_load(read_data("ccpa/orders.yaml"))


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 3), "recall": round(r, 3)}


def score_orders(data: dict, lexicon: Lexicon) -> dict:
    counts = {rule: [0, 0, 0] for rule in ("TT-09", "TT-10", "TT-11")}
    for order in data["orders"]:
        for claim in order["claims"]:
            predicted = set()
            if lexicon.superlatives(claim["text"]):
                predicted.add("TT-09")
            if lexicon.guarantees(claim["text"]):
                predicted.add("TT-10")
            if lexicon.aggregates(claim["text"]):
                predicted.add("TT-11")
            expected = set(claim.get("expected") or [])
            for rule, cell in counts.items():
                cell[0] += rule in predicted and rule in expected
                cell[1] += rule in predicted and rule not in expected
                cell[2] += rule not in predicted and rule in expected
    out: dict = {rule: _prf(*cell) for rule, cell in counts.items()}
    labels = data.get("course_labels") or []
    exact = 0
    for item in labels:
        m = lexicon.classify(item["label"])
        exact += (
            set(m.course_types) == set(item["types"])
            and m.paid_free == bool(item.get("paid_free"))
            and m.duration == bool(item.get("duration"))
            and (m.vague and not m.course_types) == bool(item.get("vague"))
        )
    share = round(exact / len(labels), 3) if labels else 1.0
    out["course_labels"] = {"n": len(labels), "exact": share}
    return out
