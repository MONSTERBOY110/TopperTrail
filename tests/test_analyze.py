from toppertrail.analyze import analyze, ledger_hash
from toppertrail.data import load_exam, load_registry, load_roster
from toppertrail.evidence import ArtifactRef, EvidenceStore, Run
from toppertrail.extract.courses import Lexicon

EXAM = load_exam("upsc-cse-2025")


def build(tmp_path):
    store = EvidenceStore(tmp_path)
    run = Run(EXAM.id)

    def serp(purpose, rank, response, iid=None, extra=None):
        doc = {"engine": "x", "params": {"engine": "x"}, "purpose": purpose, "rank": rank,
               "institute_id": iid, "response": response, **(extra or {})}
        run.add(ArtifactRef("serp", f"{purpose}:{rank}:{iid}", store.put(doc), {}))

    serp("google_en", 1, {
        "search_metadata": {"id": "g1", "created_at": "2026-10-06 09:00:00 UTC"},
        "organic_results": [{"link": "https://vajiramandravi.com/a",
                             "title": "Anuj Agnihotri UPSC AIR 1 2025", "snippet": "IGP"}],
    })
    page = {"url": "https://vajiramandravi.com/a", "status": 200, "fetched_at": "2026-10-06",
            "html_sha256": "h", "blocks": [[0, "Anuj Agnihotri AIR 1 - UPSC CSE 2025 (IGP)"]],
            "error": None}
    run.add(ArtifactRef("page", page["url"], store.put(page), {}))
    serp("youtube", 1, {"video_results": [{
        "title": "Anuj Agnihotri AIR 1 | Mock Interview | NEXT IAS",
        "link": "https://www.youtube.com/watch?v=8X-e5cJ_L3M",
        "channel": {"name": "NEXT IAS", "link": "https://www.youtube.com/@nextias"},
        "description": "UPSC CSE 2025",
    }]})
    serp("transcript", 1,
         {"transcript": [{"start_ms": 1807000,
                          "snippet": "मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया"}]},
         extra={"video": {"id": "KIr6dWSqspI", "channel": "Delhi Knowledge Track", "title": "t"}})
    serp("ai_mode", 1, {"search_metadata": {"id": "a1"},
                        "text_blocks": [{"snippet": "He took Vajiram & Ravi's IGP."}]})
    return run, store


def test_analyze_builds_ledger_and_is_deterministic(tmp_path):
    run, store = build(tmp_path)
    args = (EXAM, load_roster(EXAM, 3), load_registry(), Lexicon.load(), run, store)
    ledger = analyze(*args)
    by_inst = {c["institute_id"]: c for c in ledger["claims"]}
    assert set(by_inst) == {"vajiram-ravi", "next-ias"}
    assert by_inst["vajiram-ravi"]["course_types"] == ["interview_only"]
    assert by_inst["vajiram-ravi"]["observed_at"] == "2026-10-06"
    assert ledger["ai_answers"][0]["institutes"] == ["vajiram-ravi"]
    tt12 = {f["institute_id"]: f["code"] for f in ledger["flags"] if f["rule_id"] == "TT-12"}
    assert tt12 == {"next-ias": "mentioned", "vajiram-ravi": "not_mentioned"}
    assert ledger_hash(ledger) == ledger_hash(analyze(*args))


def test_image_result_with_fetched_page_gives_a_page_claim_not_an_empty_poster(tmp_path):
    store = EvidenceStore(tmp_path)
    run = Run(EXAM.id)
    doc = {"engine": "google_images", "params": {"engine": "google_images"}, "purpose": "images",
           "rank": 1, "institute_id": None,
           "response": {"images_results": [{"link": "https://vajiramandravi.com/a",
                                             "original": "https://x/p.jpg", "title": "Anuj"}]}}
    run.add(ArtifactRef("serp", "images:1", store.put(doc), {}))
    page = {"url": "https://vajiramandravi.com/a", "status": 200, "fetched_at": "2026-10-06",
            "html_sha256": "h", "blocks": [[0, "Anuj Agnihotri AIR 1 UPSC CSE 2025 (IGP)"]],
            "error": None}
    run.add(ArtifactRef("page", page["url"], store.put(page), {}))
    ledger = analyze(EXAM, load_roster(EXAM, 1), load_registry(), Lexicon.load(), run, store)
    assert [c["source_type"] for c in ledger["claims"]] == ["web_page"]


def test_same_poster_on_several_pages_is_one_claim(tmp_path):
    store = EvidenceStore(tmp_path)
    run = Run(EXAM.id)
    links = ["https://vajiramandravi.com/b", "https://vajiramandravi.com/a"]
    doc = {"engine": "google_images", "params": {"engine": "google_images"}, "purpose": "images",
           "rank": 1, "institute_id": None,
           "response": {"images_results": [{"link": u, "original": "https://x/p.jpg",
                                             "title": "UPSC CSE 2025"} for u in links]}}
    run.add(ArtifactRef("serp", "images:1", store.put(doc), {}))
    img = {"url": "https://x/p.jpg", "text": "Congratulations Anuj Agnihotri AIR 1 UPSC CSE 2025",
           "error": None}
    run.add(ArtifactRef("image", img["url"], store.put(img), {}))
    ledger = analyze(EXAM, load_roster(EXAM, 1), load_registry(), Lexicon.load(), run, store)
    posters = [c for c in ledger["claims"] if c["source_type"] == "poster"]
    assert [c["url"] for c in posters] == ["https://vajiramandravi.com/a"]


def test_a_page_with_a_claim_is_not_also_listed_as_unclaimed(tmp_path):
    store = EvidenceStore(tmp_path)
    run = Run(EXAM.id)
    url = "https://vajiramandravi.com/a"
    doc = {"engine": "google_images", "params": {"engine": "google_images"}, "purpose": "images",
           "rank": 1, "institute_id": None,
           "response": {"images_results": [{"link": url, "original": "https://x/p.jpg",
                                             "title": "UPSC CSE 2025"}]}}
    run.add(ArtifactRef("serp", "images:1", store.put(doc), {}))
    page = {"url": url, "status": 200, "fetched_at": "2026-10-06", "html_sha256": "h",
            "blocks": [[0, "Anuj Agnihotri AIR 1 UPSC CSE 2025 strategy"]], "error": None}
    run.add(ArtifactRef("page", url, store.put(page), {}))
    img = {"url": "https://x/p.jpg", "text": "Congratulations Anuj Agnihotri AIR 1 UPSC CSE 2025",
           "error": None}
    run.add(ArtifactRef("image", img["url"], store.put(img), {}))
    ledger = analyze(EXAM, load_roster(EXAM, 1), load_registry(), Lexicon.load(), run, store)
    assert [c["source_type"] for c in ledger["claims"]] == ["poster"]
    assert ledger["unresolved"] == []
