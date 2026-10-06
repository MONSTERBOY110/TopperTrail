import json

from toppertrail.collect import (
    Collector,
    ads_queries,
    estimate,
    export_fixtures,
    topper_queries,
)
from toppertrail.data import load_exam, load_independent, load_registry, load_roster
from toppertrail.evidence import EvidenceStore
from toppertrail.extract.courses import Lexicon
from toppertrail.fetch.images import ImageText
from toppertrail.fetch.pages import PageSnapshot
from toppertrail.serp.base import MissingFixture, SerpResult
from toppertrail.serp.replay import ReplaySerpClient

EXAM = load_exam("upsc-cse-2025")
QUERY = '"Anuj Agnihotri" UPSC CSE 2025 AIR 1'


def test_estimate_matches_spec_budget():
    est = estimate(EXAM, load_roster(EXAM, 20), load_registry())
    assert est == {
        "google": 30,
        "google_ads_transparency_center": 15,
        "google_ai_mode": 20,
        "google_images": 20,
        "youtube": 20,
        "youtube_video": 20,
        "youtube_video_transcript": 20,
    }
    assert sum(est.values()) == 145


def test_queries_are_formatted():
    q = topper_queries(EXAM, load_roster(EXAM, 1)[0])
    assert q[0].params == {"q": QUERY, "gl": "in", "hl": "en"}
    ads = ads_queries(EXAM, load_registry())
    assert ads[0].params["region"] == "2356" and ads[0].params["start_date"] == "20260306"


class FakeSerp:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def search(self, engine, params):
        self.calls.append((engine, params))
        key = (engine, params.get("q") or params.get("search_query") or params.get("v")
               or params.get("text"))
        if key not in self.responses:
            raise MissingFixture(str(key))
        return SerpResult(engine, params, self.responses[key], "replay")


class FakePages:
    def fetch(self, url):
        blocks = ((0, "Anuj Agnihotri AIR 1 UPSC CSE 2025"), (1, "menu"), (2, "unrelated"),
                  (3, "far away"))
        return PageSnapshot(url, 200, "2026-10-06", "h", blocks, None)


class FakeImages:
    def read(self, url):
        return ImageText(url, "i", "AIR 1 ANUJ AGNIHOTRI UPSC CSE 2025", None)


def args():
    return (EXAM, load_roster(EXAM, 1), load_registry(), load_independent(), Lexicon.load())


def test_collector_records_missing_and_continues(tmp_path):
    responses = {("google", QUERY): {
        "search_metadata": {"id": "g1"},
        "organic_results": [{"link": "https://vajiramandravi.com/a", "title": "t"},
                            {"link": "https://thebetterindia.com/b", "title": "t"}],
    }}
    store = EvidenceStore(tmp_path / "ev")
    col = Collector(*args(), FakeSerp(responses), FakePages(), FakeImages(), store)
    run = col.run()
    assert sorted({a.kind for a in run.artifacts}) == ["missing", "page", "serp"]
    assert col.missing >= 4
    page = [a for a in run.artifacts if a.kind == "page"]
    assert [a.key for a in page] == ["https://vajiramandravi.com/a"]
    blocks = store.get(page[0].sha256)["blocks"]
    assert blocks == [[0, "Anuj Agnihotri AIR 1 UPSC CSE 2025"], [1, "menu"]]


def test_export_then_replay_reproduces_manifest(tmp_path):
    responses = {("google", QUERY): {"search_metadata": {"id": "g1"}, "organic_results": []}}
    store = EvidenceStore(tmp_path / "ev")
    first = Collector(*args(), FakeSerp(responses), FakePages(), FakeImages(), store).run()
    export_fixtures(first, store, tmp_path / "fx")
    second = Collector(*args(), ReplaySerpClient(tmp_path / "fx"), FakePages(), FakeImages(),
                       EvidenceStore(tmp_path / "ev2")).run()

    def serp_keys(r):
        return sorted((a.key, a.sha256) for a in r.artifacts if a.kind == "serp")

    assert serp_keys(first) == serp_keys(second)
    path = tmp_path / "fx" / "manifests" / f"{EXAM.id}.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["manifest_root"] == first.manifest_root()
    assert manifest["top"] == 1


class FailingSerp:
    def __init__(self, message):
        self.message = message

    def search(self, engine, params):
        from toppertrail.serp.base import SerpError
        raise SerpError(self.message)


def test_missing_artifacts_hash_the_same_whatever_the_error_text(tmp_path):
    a = Collector(*args(), FailingSerp("HTTP 500 upstream"), FakePages(), FakeImages(),
                  EvidenceStore(tmp_path / "a")).run()
    b = Collector(*args(), FailingSerp("no recorded response"), FakePages(), FakeImages(),
                  EvidenceStore(tmp_path / "b")).run()
    assert a.manifest_root() == b.manifest_root()
    assert a.of_kind("missing")[0].meta["reason"] == "HTTP 500 upstream"


def test_replay_image_without_fixture_is_not_recorded(tmp_path):
    from toppertrail.fetch.images import ReplayImageReader
    responses = {("google_images", "Anuj Agnihotri AIR 1 UPSC 2025"): {
        "search_metadata": {"id": "i1"},
        "images_results": [{"link": "https://vajiramandravi.com/a", "original": "https://x/p.jpg"}]}}
    run = Collector(*args(), FakeSerp(responses), FakePages(), ReplayImageReader(tmp_path / "fx"),
                    EvidenceStore(tmp_path / "ev")).run()
    assert run.of_kind("image") == []


def test_image_results_on_institute_domains_also_fetch_the_page(tmp_path):
    responses = {("google_images", "Anuj Agnihotri AIR 1 UPSC 2025"): {
        "search_metadata": {"id": "i1"},
        "images_results": [{"link": "https://vajiramandravi.com/a", "original": "https://x/p.jpg"},
                           {"link": "https://www.instagram.com/p/x", "original": "https://x/q.jpg"}]}}
    run = Collector(*args(), FakeSerp(responses), FakePages(), FakeImages(),
                    EvidenceStore(tmp_path / "ev")).run()
    assert [a.key for a in run.of_kind("page")] == ["https://vajiramandravi.com/a"]
