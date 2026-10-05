from pathlib import Path

from toppertrail.evidence import ArtifactRef, EvidenceStore, Run, damaged


def test_put_get_roundtrip_and_dedupe(tmp_path: Path):
    store = EvidenceStore(tmp_path)
    a = store.put({"x": "अनुज", "n": 1})
    b = store.put({"n": 1, "x": "अनुज"})
    assert a == b
    assert store.get(a) == {"x": "अनुज", "n": 1}
    assert store.is_intact(a)


def test_manifest_root_is_order_independent(tmp_path: Path):
    r1 = Run("upsc-cse-2025", [ArtifactRef("serp", "k1", "aa"), ArtifactRef("page", "k2", "bb")])
    r2 = Run("upsc-cse-2025", [ArtifactRef("page", "k2", "bb"), ArtifactRef("serp", "k1", "aa")])
    assert r1.manifest_root() == r2.manifest_root()


def test_save_load_and_tamper_detection(tmp_path: Path):
    store = EvidenceStore(tmp_path / "ev")
    sha = store.put({"a": 1})
    run = Run("upsc-cse-2025")
    run.add(ArtifactRef("serp", "google_en:1", sha, {"rank": 1}))
    run.save(tmp_path / "run.json")
    loaded = Run.load(tmp_path / "run.json")
    assert loaded.manifest_root() == run.manifest_root()
    assert loaded.artifacts[0].meta == {"rank": 1}
    assert damaged(loaded, store) == []
    path = tmp_path / "ev" / sha[:2] / f"{sha}.json"
    path.write_text('{"a":2}', encoding="utf-8")
    assert damaged(loaded, store) == [sha]
