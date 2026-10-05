import json
from pathlib import Path

import pytest

from toppertrail.collect import Collector, manifest_path
from toppertrail.data import load_exam, load_independent, load_registry, load_roster
from toppertrail.evidence import EvidenceStore
from toppertrail.extract.courses import Lexicon
from toppertrail.fetch.images import ReplayImageReader
from toppertrail.fetch.pages import ReplayPageFetcher
from toppertrail.serp.replay import ReplaySerpClient

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.parametrize("exam_id", ["upsc-cse-2025", "jee-adv-2026", "neet-ug-2026"])
def test_replay_matches_recorded_manifest(exam_id, tmp_path):
    path = manifest_path(FIXTURES, exam_id)
    if not path.exists():
        pytest.skip("no recorded fixtures yet")
    recorded = json.loads(path.read_text(encoding="utf-8"))
    exam = load_exam(exam_id)
    toppers = load_roster(exam, recorded.get("top") or exam.default_top)
    col = Collector(exam, toppers, load_registry(), load_independent(), Lexicon.load(),
                    ReplaySerpClient(FIXTURES), ReplayPageFetcher(FIXTURES),
                    ReplayImageReader(FIXTURES), EvidenceStore(tmp_path))
    run = col.run()
    assert run.manifest_root() == recorded["manifest_root"]


def test_fixtures_contain_no_keys():
    if not FIXTURES.exists():
        pytest.skip("no fixtures")
    for p in FIXTURES.rglob("*.json"):
        text = p.read_text(encoding="utf-8")
        assert "json_endpoint" not in text, p
        assert "api_key=" not in text.replace("api_key=REDACTED", ""), p
