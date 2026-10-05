from __future__ import annotations

from collections import Counter, defaultdict

from toppertrail.data import Registry
from toppertrail.rules import RULES, load_orders


def _pct(a: int, b: int) -> int:
    return round(100 * a / b) if b else 0


def _flags_by_claim(ledger: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for f in ledger["flags"]:
        if f["claim_id"]:
            out[f["claim_id"]].add(f["rule_id"])
    return out


def claimants(ledger: dict) -> dict[int, int]:
    by_rank: dict[int, set[str]] = defaultdict(set)
    for c in ledger["claims"]:
        by_rank[c["rank"]].add(c["institute_id"])
    return {t["rank"]: len(by_rank.get(t["rank"], ())) for t in ledger["toppers"]}


def headline(ledger: dict) -> dict:
    claims = ledger["claims"]
    per_rank = claimants(ledger)
    counts = list(per_rank.values())
    top = min(per_rank, key=lambda r: (-per_rank[r], r)) if per_rank else None
    fl = _flags_by_claim(ledger)
    stated = [c for c in claims if "TT-01" not in fl[c["claim_id"]]]
    interview_only = [c for c in stated if "TT-02" in fl[c["claim_id"]]]
    paid_missing = sum(1 for c in claims if "TT-04" in fl[c["claim_id"]])
    own = Counter(f["code"] for f in ledger["flags"] if f["rule_id"] == "TT-12")
    return {
        "toppers": len(ledger["toppers"]),
        "claims": len(claims),
        "institutes": len({c["institute_id"] for c in claims}),
        "avg_claimants": round(sum(counts) / len(counts), 1) if counts else 0.0,
        "max_claimants": max(counts, default=0),
        "max_rank": top,
        "stated_claims": len(stated),
        "interview_only_claims": len(interview_only),
        "toppers_3plus": sum(1 for n in counts if n >= 3),
        "course_stated_pct": _pct(len(stated), len(claims)),
        "interview_only_pct_of_stated": _pct(len(interview_only), len(stated)),
        "paid_free_stated_pct": _pct(len(claims) - paid_missing, len(claims)),
        "own_words": dict(sorted(own.items())),
    }


def topper_view(ledger: dict, rank: int) -> dict:
    topper = next(t for t in ledger["toppers"] if t["rank"] == rank)
    flags: dict[str, list[dict]] = defaultdict(list)
    for f in ledger["flags"]:
        if f["claim_id"]:
            flags[f["claim_id"]].append(f)
    claims = sorted((c for c in ledger["claims"] if c["rank"] == rank),
                    key=lambda c: (c["institute_id"], c["source_type"], c.get("url", "")))
    return {
        "topper": topper,
        "claims": [{**c, "flags": flags.get(c["claim_id"], [])} for c in claims],
        "selfreports": [r for r in ledger["selfreports"] if r["rank"] == rank],
        "interview": next((i for i in ledger["interviews"] if i["rank"] == rank), None),
        "ai": next((a for a in ledger["ai_answers"] if a["rank"] == rank), None),
    }


def institute_rows(ledger: dict, registry: Registry) -> list[dict]:
    fl = _flags_by_claim(ledger)
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in ledger["claims"]:
        groups[c["institute_id"]].append(c)
    signals = Counter(f["institute_id"] for f in ledger["flags"] if f["claim_id"] is None)
    rows = []
    for iid, cs in groups.items():
        stated = [c for c in cs if "TT-01" not in fl[c["claim_id"]]]
        rows.append({
            "institute_id": iid,
            "name": registry.get(iid).name,
            "toppers": len({c["rank"] for c in cs}),
            "claims": len(cs),
            "course_stated_pct": _pct(len(stated), len(cs)),
            "interview_only": sum(1 for c in cs if "TT-02" in fl[c["claim_id"]]),
            "signals": signals.get(iid, 0),
            "ads": sum(1 for c in cs if c["source_type"] == "ad_creative"),
            "ccpa_orders": len(registry.get(iid).ccpa_orders),
        })
    return sorted(rows, key=lambda r: (-r["toppers"], -r["claims"], r["institute_id"]))


def institute_view(ledger: dict, iid: str, registry: Registry) -> dict:
    orders = {o["id"]: o for o in load_orders()["orders"]}
    inst = registry.get(iid)
    return {
        "institute": inst,
        "claims": [c for c in ledger["claims"] if c["institute_id"] == iid],
        "signals": [f for f in ledger["flags"]
                    if f["institute_id"] == iid and f["claim_id"] is None],
        "orders": [orders[o] for o in inst.ccpa_orders if o in orders],
        "rules": RULES,
    }


def ai_findings(ledger: dict) -> dict:
    fl = _flags_by_claim(ledger)
    own = {f["claim_id"]: f["code"] for f in ledger["flags"] if f["rule_id"] == "TT-12"}
    named = [a for a in ledger["ai_answers"] if a["institutes"]]
    weak = without = 0
    for a in named:
        for iid in a["institutes"]:
            cs = [c for c in ledger["claims"]
                  if c["rank"] == a["rank"] and c["institute_id"] == iid]
            if not cs:
                without += 1
            elif all("TT-02" in fl[c["claim_id"]]
                     or own.get(c["claim_id"]) in ("not_mentioned", "denied") for c in cs):
                weak += 1
    return {"toppers_named": len(named), "toppers_total": len(ledger["ai_answers"]),
            "named_with_weak_claims": weak, "named_without_claims": without}


SLOT_COUNT = 6  # validated categorical series; the rest fold into "other institutes"


def _state(course_types) -> str:
    if not course_types:
        return "none"
    if set(course_types) <= {"interview_only"}:
        return "interview"
    return "stated"


def short_name(name: str) -> str:
    return name.split(" (")[0]


def institute_slots(ledger: dict) -> dict[str, int]:
    """Colour slots by claim count within one ledger, fixed for every page of that exam."""
    counts = Counter(c["institute_id"] for c in ledger["claims"])
    ranked = sorted(counts, key=lambda iid: (-counts[iid], iid))
    return {iid: i + 1 for i, iid in enumerate(ranked[:SLOT_COUNT])}


def _alerts(ledger: dict) -> set[tuple[int, str]]:
    return {(f["rank"], f["institute_id"]) for f in ledger["flags"]
            if f["rule_id"] == "TT-08" or (f["rule_id"] == "TT-12" and f["code"] == "denied")}


def claimant_chips(ledger: dict, rank: int, registry: Registry) -> list[dict]:
    slots = institute_slots(ledger)
    alerts = _alerts(ledger)
    groups: dict[str, list[dict]] = defaultdict(list)
    for c in ledger["claims"]:
        if c["rank"] == rank:
            groups[c["institute_id"]].append(c)
    chips = []
    for iid, cs in groups.items():
        states = {_state(c["course_types"]) for c in cs}
        state = next(s for s in ("stated", "interview", "none") if s in states)
        chips.append({"institute_id": iid, "name": short_name(registry.get(iid).name),
                      "slot": slots.get(iid), "state": state, "claims": len(cs),
                      "alert": (rank, iid) in alerts})
    return sorted(chips, key=lambda c: (c["slot"] or 99, c["name"]))


def tally(ledger: dict, registry: Registry) -> list[dict]:
    slots = institute_slots(ledger)
    groups: dict[str, Counter] = defaultdict(Counter)
    for c in ledger["claims"]:
        groups[c["institute_id"]][_state(c["course_types"])] += 1
    rows = [{"institute_id": iid, "name": short_name(registry.get(iid).name),
             "slot": slots.get(iid), "claims": sum(n.values()), "stated": n["stated"],
             "interview": n["interview"], "none": n["none"]} for iid, n in groups.items()]
    return sorted(rows, key=lambda r: (-r["claims"], r["institute_id"]))
