import pytest

from toppertrail.data import load_exam, load_registry, load_roster
from toppertrail.extract.claims import ClaimExtractor
from toppertrail.extract.courses import Lexicon
from toppertrail.fetch.pages import html_to_blocks


@pytest.fixture(scope="module")
def ex():
    exam = load_exam("upsc-cse-2025")
    return ClaimExtractor(exam, load_roster(exam, 20), load_registry(), Lexicon.load())


def run(ex, blocks, inst="vajiram-ravi", url="https://vajiramandravi.com/x",
        title="UPSC CSE 2025 toppers", source="web_page"):
    reg = load_registry()
    return ex.from_blocks(reg.get(inst), url, title, blocks, source, "sid1", ("sha1",),
                          "2026-10-06")


def test_menu_page_without_course_gets_no_course(ex):
    page = (
        "<nav><li>GS Foundation Course</li><li>IGP</li></nav>"
        "<main><p>Congratulations Anuj Agnihotri, AIR 1 in UPSC CSE 2025.</p></main>"
    )
    claims, _, _ = run(ex, html_to_blocks(page))
    assert len(claims) == 1
    assert claims[0].course_types == ()
    assert claims[0].claimed_rank == 1


def test_neighbour_block_naming_another_topper_is_not_in_window(ex):
    blocks = [(0, "AIR 1 Anuj Agnihotri, our student"), (1, "AIR 2 Rajeshwari Suve M (IGP)")]
    claims, _, _ = run(ex, blocks)
    by_rank = {c.rank: c for c in claims}
    assert by_rank[1].course_types == ()
    assert by_rank[2].course_types == ("interview_only",)


def test_neighbour_block_without_topper_joins_window(ex):
    blocks = [(0, "Anuj Agnihotri AIR 1 UPSC CSE 2025"), (1, "Courses joined: CA-VA Program, IGP")]
    claims, _, _ = run(ex, blocks)
    assert claims[0].course_types == ("current_affairs", "interview_only")


def test_context_missing_year_is_unresolved(ex):
    claims, _, unresolved = run(ex, [(0, "Anuj Agnihotri spoke at our event")], title="Event")
    assert claims == [] and unresolved[0]["rank"] == 1


def test_signals_and_claim_id_stability(ex):
    blocks = [
        (0, "Top 10 Out of 10 Rankers in UPSC CSE 2025 From Vajiram & Ravi's Various Courses"),
        (1, "Anuj Agnihotri AIR 1"),
    ]
    claims, signals, _ = run(ex, blocks)
    assert {s.rule_id for s in signals} == {"TT-11"}
    again, _, _ = run(ex, blocks)
    assert claims[0].claim_id == again[0].claim_id
    assert claims[0].vague_label is True


def test_cross_exam_name_collision_rejected():
    exam = load_exam("jee-adv-2026")
    ex = ClaimExtractor(exam, load_roster(exam, 5), load_registry(), Lexicon.load())
    reg = load_registry()
    claims, _, unresolved = ex.from_blocks(
        reg.get("vision-ias"), "https://visionias.in/x", "UPSC CSE 2020 result",
        [(0, "Shubham Kumar AIR 1 UPSC CSE 2020")], "web_page", None, (), "2026-10-06",
    )
    assert claims == [] and unresolved


def test_news_style_listing_is_not_a_claim(ex):
    text = "In the UPSC CSE Final Result 2025, Anuj Agnihotri has secured All India Rank 1."
    blocks = [(0, text)]
    claims, _, unresolved = run(ex, blocks, inst="vision-ias", url="https://visionias.in/blog/x")
    assert claims == []
    assert unresolved[0]["reason"] == "named without claiming the topper"


def test_association_words_make_a_claim(ex):
    for text in ("Congratulations to our student Anuj Agnihotri, AIR 1, UPSC CSE 2025",
                 "ALLEN Kota Alumni Anuj Agnihotri Tops UPSC 2025",
                 "Anuj Agnihotri AIR 1 UPSC CSE 2025 joined our Interview Guidance Programme"):
        claims, _, _ = run(ex, [(0, text)], inst="allen", url="https://news.allen.in/x")
        assert len(claims) == 1, text


def test_hosted_video_is_always_a_claim(ex):
    blocks = [(0, "UPSC CSE 2025 AIR 1 Anuj Agnihotri strategy talk")]
    claims, _, _ = run(ex, blocks, source="youtube_hosted", url="https://www.youtube.com/watch?v=x")
    assert len(claims) == 1


def test_long_window_is_trimmed_around_the_name(ex):
    filler = "The UPSC Civil Services Examination is conducted annually. " * 20
    text = filler + "Congratulations to our student Anuj Agnihotri, AIR 1, UPSC CSE 2025."
    claims, _, _ = run(ex, [(0, text)])
    assert "Anuj Agnihotri" in claims[0].window
    assert len(claims[0].window) <= 600
