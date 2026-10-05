from toppertrail.hashing import canonical_json, sha256_text, short_hash


def test_canonical_json_is_order_independent_and_keeps_unicode():
    a = canonical_json({"b": 1, "a": "अनुज"})
    b = canonical_json({"a": "अनुज", "b": 1})
    assert a == b == '{"a":"अनुज","b":1}'


def test_hashes_are_stable():
    assert sha256_text("x") == "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"
    assert short_hash("x") == "2d711642b726b044"
