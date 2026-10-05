import pytest

from toppertrail.data import load_independent, load_registry
from toppertrail.extract.courses import Lexicon
from toppertrail.extract.selfreport import (
    hosted_videos,
    own_words_status,
    parse_length,
    pick_interview,
    self_reports,
)
from toppertrail.models import Claim, Topper

ANUJ = Topper("upsc-cse-2025", 1, "ANUJ AGNIHOTRI")
VIDEOS = [
    {
        "title": "Anuj Agnihotri AIR 1 | CSE Topper's Mock Interview | NEXT IAS",
        "link": "https://www.youtube.com/watch?v=8X-e5cJ_L3M",
        "channel": {"name": "NEXT IAS", "link": "https://www.youtube.com/@nextias"},
        "length": "27:39",
    },
    {
        "title": "Anuj Agnihotri AIR 1 Mock Interview",
        "link": "https://www.youtube.com/watch?v=uSgHZWfcfvQ",
        "channel": {
            "name": "Vajiram and Ravi Official",
            "link": "https://www.youtube.com/channel/UCzelA5kqD9v6k6drK44l4_g",
        },
        "length": "45:39",
    },
    {
        "title": "Anuj Agnihotri AIR 1 full story",
        "link": "https://www.youtube.com/watch?v=KIr6dWSqspI",
        "channel": {
            "name": "Delhi Knowledge Track",
            "link": "https://www.youtube.com/@DelhiKnowledgeTrack",
        },
        "length": "1:31:05",
    },
    {
        "title": "Anuj Agnihotri strategy",
        "link": "https://www.youtube.com/watch?v=zzzzzzzzzzz",
        "channel": {"name": "Random Prep", "link": "https://www.youtube.com/@randomprep"},
        "length": "2:01:00",
    },
]

TRANSCRIPT = [
    {"start_ms": 0, "snippet": "इन द लेटेस्ट यूपीएससी रिजल्ट 2025, टॉप"},
    {"start_ms": 3000, "snippet": "10 आउट ऑफ टॉप 10 आर फ्रॉम वेरियस कोर्सेज"},
    {"start_ms": 6000, "snippet": "ऑफ वाजराम एंड रवि विद ऑल इंडिया रैंक वन"},
    {"start_ms": 1402000, "snippet": "उस समय Unacademy का मुझे लगा था"},
    {"start_ms": 1505000, "snippet": "इसके अलावा मैंने उसके बाद कोई कोचिंग नहीं ली"},
    {"start_ms": 1807000, "snippet": "मॉक इंटरव्यूज में मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया"},
    {"start_ms": 1810000, "snippet": "पीडब्ल्यू का मॉक दिया"},
    {"start_ms": 4045000, "snippet": "मैंने टेस्ट सीरीज शायद कभी जॉइ नहीं करी"},
]


@pytest.fixture(scope="module")
def reports():
    return self_reports(TRANSCRIPT, 1, "KIr6dWSqspI", "Delhi Knowledge Track", load_registry(),
                        Lexicon.load())


def claim(iid, types):
    return Claim("c", "upsc-cse-2025", 1, iid, "web_page", "u", "t", "w", types, (), False,
                 False, False, 1, None, (), "2026-10-06")


def test_parse_length():
    assert parse_length("1:31:05") == 5465
    assert parse_length("27:39") == 1659
    assert parse_length("") == 0


def test_pick_interview_prefers_allowlisted_independent_channel():
    pick = pick_interview(VIDEOS, ANUJ, load_registry(), load_independent())
    assert pick == {
        "id": "KIr6dWSqspI",
        "channel": "Delhi Knowledge Track",
        "title": "Anuj Agnihotri AIR 1 full story",
    }


def test_hosted_videos_one_per_institute():
    assert hosted_videos(VIDEOS, ANUJ, load_registry(), 2) == [
        ("8X-e5cJ_L3M", "next-ias"),
        ("uSgHZWfcfvQ", "vajiram-ravi"),
    ]


def test_sponsor_read_is_not_a_self_report(reports):
    assert all(r.institute_id != "vajiram-ravi" for r in reports)


def test_self_reports_capture_affirm_and_deny(reports):
    got = {(r.institute_id, r.polarity) for r in reports}
    assert ("unacademy", "affirm") in got
    assert ("next-ias", "affirm") in got
    assert ("physics-wallah", "affirm") in got
    deny = [r for r in reports if r.polarity == "deny" and "test_series" in r.course_types]
    assert deny and deny[0].start_ms == 4045000


def test_own_words_status(reports):
    next_ias = own_words_status(claim("next-ias", ("current_affairs",)), reports, True)
    assert next_ias[0] == "mentioned"
    assert own_words_status(claim("vision-ias", ("test_series",)), reports, True)[0] == "denied"
    vajiram = own_words_status(claim("vajiram-ravi", ("interview_only",)), reports, True)
    assert vajiram[0] == "not_mentioned"
    assert own_words_status(claim("vajiram-ravi", ()), [], False)[0] == "no_interview"


def test_generic_denial_yields_to_an_affirmation_of_the_same_course():
    from toppertrail.models import SelfReport
    reports = [
        SelfReport(1, "v", "c", 100, "मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया", "next-ias",
                   ("interview_only",), "affirm"),
        SelfReport(1, "v", "c", 200, "पहले अटेम्प्ट में मैंने कोई मॉक इंटरव्यू नहीं दिया", None,
                   ("interview_only",), "deny"),
    ]
    status, _ = own_words_status(claim("vajiram-ravi", ("interview_only",)), reports, True)
    assert status == "not_mentioned"
