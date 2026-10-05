from toppertrail.data import load_exam, load_registry
from toppertrail.models import Claim, Interview, SelfReport, Signal
from toppertrail.rules import RULES, apply_rules

EXAM = load_exam("upsc-cse-2025")
BANNED = ("false", "fake", "fraud", "lie", "misleading")


def c(cid, iid, rank, types=(), url="u1", source="web_page", claimed=None, paid=False,
      dur=False, vague=False):
    return Claim(cid, EXAM.id, rank, iid, source, url, "t", "w", types, (), paid, dur, vague,
                 claimed, None, (), "2026-10-06")


def rules_for(flags, cid):
    return sorted(f.rule_id for f in flags if f.claim_id == cid)


def test_claim_level_rules():
    claims = [
        c("a", "vajiram-ravi", 1, ("interview_only",), claimed=2),
        c("b", "allen", 1, (), source="ad_creative", vague=True, url="u2"),
    ]
    flags = apply_rules(EXAM, claims, [], [], [], load_registry())
    assert rules_for(flags, "a") == ["TT-02", "TT-04", "TT-05", "TT-08", "TT-12"]
    assert rules_for(flags, "b") == ["TT-01", "TT-03", "TT-04", "TT-05", "TT-12", "TT-13",
                                     "TT-14"]


def test_cross_rules_inconsistent_labels_and_selective_page():
    claims = [
        c("a", "next-ias", 1, ("current_affairs",), url="p1"),
        c("b", "next-ias", 1, ("current_affairs", "interview_only"), url="v1",
          source="youtube_description"),
        c("x", "vision-ias", 1, ("test_series",), url="list"),
        c("y", "vision-ias", 2, (), url="list"),
    ]
    flags = apply_rules(EXAM, claims, [], [], [], load_registry())
    assert "TT-06" in rules_for(flags, "a") and "TT-06" in rules_for(flags, "b")
    assert "TT-07" in rules_for(flags, "y") and "TT-07" not in rules_for(flags, "x")


def test_signal_rules_and_own_words():
    claims = [c("a", "vajiram-ravi", 1, ("interview_only",))]
    signals = [
        Signal("vajiram-ravi", "TT-11", "top 10 out of 10", "u1", ()),
        Signal("vajiram-ravi", "TT-11", "top 10 out of 10", "u9", ()),
    ]
    interviews = [Interview(1, "KIr6dWSqspI", "Delhi Knowledge Track", "t", "hi")]
    reports = [SelfReport(1, "KIr6dWSqspI", "DKT", 1807000, "मैंने नेक्स्ट आईएएस का मॉक",
                          "next-ias", ("interview_only",), "affirm")]
    flags = apply_rules(EXAM, claims, signals, reports, interviews, load_registry())
    tt11 = [f for f in flags if f.rule_id == "TT-11"]
    assert len(tt11) == 1 and "1 name only an interview programme" in tt11[0].detail
    tt12 = [f for f in flags if f.rule_id == "TT-12"]
    assert tt12[0].code == "not_mentioned"


def test_wording_never_accuses():
    claims = [c("a", "vajiram-ravi", 1, ("interview_only",), claimed=3)]
    signals = [
        Signal("vajiram-ravi", "TT-09", "best ias", "u", ()),
        Signal("vajiram-ravi", "TT-10", "pakka", "u", ()),
    ]
    flags = apply_rules(EXAM, claims, signals, [], [], load_registry())
    texts = [t for t, _ in RULES.values()] + [f.detail for f in flags]
    assert not [t for t in texts if any(b in t.lower() for b in BANNED)]


def test_details_use_plain_course_names():
    claims = [c("a", "next-ias", 1, ("current_affairs",), url="p1"),
              c("b", "next-ias", 1, ("current_affairs", "interview_only"), url="v1",
                source="youtube_description")]
    flags = apply_rules(EXAM, claims, [], [], [], load_registry())
    details = " ".join(f.detail for f in flags)
    assert "interview_only" not in details and "current_affairs" not in details
    assert "interview programme" in details and "current affairs course" in details
