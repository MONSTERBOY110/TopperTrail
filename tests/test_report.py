from toppertrail.data import load_registry
from toppertrail.report import ai_findings, headline, institute_rows, topper_view


def claim(cid, rank, iid, types, source="web_page"):
    return {"claim_id": cid, "rank": rank, "institute_id": iid, "course_types": types,
            "source_type": source}


def flag(rule, cid, iid, rank, code=""):
    return {"rule_id": rule, "claim_id": cid, "institute_id": iid, "rank": rank, "detail": "",
            "code": code}


LEDGER = {
    "exam": "upsc-cse-2025", "label": "UPSC CSE 2025", "manifest_root": "m",
    "toppers": [{"rank": 1, "name": "ANUJ AGNIHOTRI", "display": "Anuj Agnihotri"},
                {"rank": 2, "name": "RAJESHWARI SUVE M", "display": "Rajeshwari Suve M"}],
    "claims": [
        claim("a", 1, "vajiram-ravi", ["interview_only"]),
        claim("b", 1, "next-ias", [], "youtube_hosted"),
        claim("c", 1, "legacy-ias", []),
        claim("d", 2, "vajiram-ravi", ["test_series"], "poster"),
    ],
    "flags": [
        flag("TT-01", "b", "next-ias", 1),
        flag("TT-01", "c", "legacy-ias", 1),
        flag("TT-02", "a", "vajiram-ravi", 1),
        flag("TT-04", "a", "vajiram-ravi", 1),
        flag("TT-12", "a", "vajiram-ravi", 1, "not_mentioned"),
        flag("TT-11", None, "vajiram-ravi", None),
    ],
    "selfreports": [], "interviews": [], "signals": [], "unresolved": [], "missing": [],
    "ai_answers": [
        {"rank": 1, "institutes": ["vajiram-ravi"], "excerpt": "x", "search_id": "s",
         "engine": "google_ai_mode"},
        {"rank": 2, "institutes": [], "excerpt": "", "search_id": "t",
         "engine": "google_ai_mode"},
    ],
}


def test_headline_numbers():
    h = headline(LEDGER)
    assert h["claims"] == 4 and h["toppers"] == 2 and h["institutes"] == 3
    assert h["avg_claimants"] == 2.0 and h["max_claimants"] == 3
    assert h["course_stated_pct"] == 50 and h["interview_only_pct_of_stated"] == 50
    assert h["paid_free_stated_pct"] == 75
    assert h["own_words"] == {"not_mentioned": 1}


def test_views():
    v = topper_view(LEDGER, 1)
    assert [c["institute_id"] for c in v["claims"]] == ["legacy-ias", "next-ias", "vajiram-ravi"]
    rows = institute_rows(LEDGER, load_registry())
    assert rows[0]["institute_id"] == "vajiram-ravi" and rows[0]["toppers"] == 2
    assert ai_findings(LEDGER) == {"toppers_named": 1, "toppers_total": 2,
                                   "named_with_weak_claims": 1, "named_without_claims": 0}


def test_institute_slots_follow_claim_counts():
    from toppertrail.report import institute_slots
    slots = institute_slots(LEDGER)
    assert slots["vajiram-ravi"] == 1
    assert set(slots) == {"vajiram-ravi", "legacy-ias", "next-ias"}


def test_claimant_chips_encode_disclosure():
    from toppertrail.report import claimant_chips
    chips = {c["institute_id"]: c for c in claimant_chips(LEDGER, 1, load_registry())}
    assert chips["vajiram-ravi"]["state"] == "interview"
    assert chips["next-ias"]["state"] == "none"
    assert chips["vajiram-ravi"]["slot"] == 1


def test_tally_segments_sum_to_claims():
    from toppertrail.report import tally
    rows = tally(LEDGER, load_registry())
    vaj = next(r for r in rows if r["institute_id"] == "vajiram-ravi")
    assert (vaj["claims"], vaj["stated"], vaj["interview"], vaj["none"]) == (2, 1, 1, 0)
    assert sum(r["claims"] for r in rows) == 4


def test_headline_leads_with_the_most_claimed_rank():
    h = headline(LEDGER)
    assert (h["max_claimants"], h["max_rank"]) == (3, 1)
    assert (h["stated_claims"], h["interview_only_claims"]) == (2, 1)
