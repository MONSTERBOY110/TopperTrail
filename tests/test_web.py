import json

from fastapi.testclient import TestClient

from toppertrail.web.app import create_app
from toppertrail.web.export import export_site

LEDGER = {
    "exam": "upsc-cse-2025", "label": "UPSC CSE 2025", "manifest_root": "m",
    "toppers": [{"rank": 1, "name": "ANUJ AGNIHOTRI", "display": "Anuj Agnihotri"}],
    "claims": [{
        "claim_id": "a", "exam_id": "upsc-cse-2025", "rank": 1, "institute_id": "vajiram-ravi",
        "source_type": "web_page", "url": "https://vajiramandravi.com/a", "title": "t",
        "window": "<script>alert(1)</script> AIR 1 (IGP)", "course_types": ["interview_only"],
        "course_terms": ["igp"], "paid_free_stated": False, "duration_stated": False,
        "vague_label": False, "claimed_rank": 1, "search_id": "g1", "evidence": ["e1"],
        "observed_at": "2026-10-06",
    }],
    "flags": [{"rule_id": "TT-02", "claim_id": "a", "institute_id": "vajiram-ravi", "rank": 1,
               "detail": "Only an interview programme is named: igp.", "code": ""}],
    "signals": [], "selfreports": [], "interviews": [], "ai_answers": [], "unresolved": [],
    "missing": [],
}


def home(tmp_path):
    (tmp_path / "ledgers").mkdir()
    (tmp_path / "ledgers" / "upsc-cse-2025.json").write_text(json.dumps(LEDGER), encoding="utf-8")
    return tmp_path


def test_pages_render_and_escape(tmp_path):
    client = TestClient(create_app(home(tmp_path)))
    for path in ("/", "/exam/upsc-cse-2025", "/exam/upsc-cse-2025/topper/1",
                 "/exam/upsc-cse-2025/institute/vajiram-ravi", "/methodology"):
        r = client.get(path)
        assert r.status_code == 200, path
    page = client.get("/exam/upsc-cse-2025/topper/1").text
    assert "&lt;script&gt;" in page and "<script>alert" not in page
    assert "Only the CCPA decides" in page
    assert client.get("/exam/nope").status_code == 404


def test_static_export_writes_pages(tmp_path):
    files = export_site(home(tmp_path), tmp_path / "site", "/TopperTrail/")
    names = {p.relative_to(tmp_path / "site").as_posix() for p in files}
    assert "index.html" in names and "exam/upsc-cse-2025/topper/1/index.html" in names
    html = (tmp_path / "site" / "exam" / "upsc-cse-2025" / "index.html").read_text(encoding="utf-8")
    assert 'href="/TopperTrail/exam/upsc-cse-2025/topper/1/"' in html


def test_inr_and_mdlite_filters():
    from toppertrail.web.render import inr, mdlite
    assert inr(700000) == "₹7,00,000"
    assert inr(1100000) == "₹11,00,000"
    assert inr(50000) == "₹50,000"
    html = str(mdlite("## Heading\n\nA <b>line</b>.\n- one\n- two"))
    assert "<h3>Heading</h3>" in html and "&lt;b&gt;" in html and "<li>one</li>" in html


def test_excerpt_centres_on_the_topper_and_labels_image_text():
    from toppertrail.web.render import excerpt
    window = ("Akansh Dhull has achieved AIR 3 in the UPSC CSE 2025. " * 6
              + "Anuj Agnihotri topped with AIR 1 after the Interview Guidance Programme.")
    html = str(excerpt(window, "ANUJ AGNIHOTRI", ["interview guidance programme"]))
    assert '<strong class="who">Anuj Agnihotri</strong>' in html
    assert "<mark>Interview Guidance Programme</mark>" in html
    assert html.startswith("...")
    alt_text = "image: banner\nimage: UPSC Topper 2025 Anuj Agnihotri Rank 1"
    html = str(excerpt(alt_text, "ANUJ AGNIHOTRI", []))
    assert "banner" not in html and "Image text:" in html


def test_notice_never_puts_false_next_to_claim():
    from toppertrail.web.render import NOTICE
    assert "false" not in NOTICE.lower() and "Only the CCPA decides" in NOTICE


def test_excerpt_does_not_cut_words():
    from toppertrail.web.render import excerpt
    window = "preparation " * 60 + "Anuj Agnihotri AIR 1 UPSC CSE 2025 " + "examination " * 60
    text = str(excerpt(window, "ANUJ AGNIHOTRI", []))
    body = text.replace('<strong class="who">', "").replace("</strong>", "").strip(".")
    allowed = {"preparation", "examination", "Anuj", "Agnihotri", "AIR", "1", "UPSC", "CSE", "2025"}
    assert all(w in allowed for w in body.split())
