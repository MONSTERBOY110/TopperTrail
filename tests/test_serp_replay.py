import json
from pathlib import Path

import pytest

from toppertrail.serp.base import MissingFixture
from toppertrail.serp.replay import ReplaySerpClient, fixture_path


def test_replay_reads_fixture(tmp_path: Path):
    path = fixture_path(tmp_path, "google", {"q": "x", "gl": "in"})
    path.parent.mkdir(parents=True)
    doc = {
        "engine": "google",
        "params": {"engine": "google", "gl": "in", "q": "x"},
        "response": {"search_metadata": {"id": "s1"}, "organic_results": []},
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    r = ReplaySerpClient(tmp_path).search("google", {"gl": "in", "q": "x"})
    assert r.source == "replay"
    assert r.search_id == "s1"


def test_replay_missing_fixture_raises(tmp_path: Path):
    with pytest.raises(MissingFixture):
        ReplaySerpClient(tmp_path).search("google", {"q": "nothing"})
