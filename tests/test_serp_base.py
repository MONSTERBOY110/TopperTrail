from toppertrail.serp.base import canonical_params, params_hash, redact, scrub, trim


def test_canonical_params_drop_transport_keys_and_stringify():
    p = canonical_params(
        "google", {"q": "x", "num": 10, "api_key": "K", "no_cache": True, "hl": None}
    )
    assert p == {"engine": "google", "num": "10", "q": "x"}
    assert params_hash("google", {"q": "x", "num": 10}) == params_hash(
        "google", {"num": "10", "q": "x"}
    )


def test_redact_removes_key_from_urls_and_plain_text():
    msg = "401 for url: https://serpapi.com/search?engine=google&api_key=SECRET123&q=a SECRET123"
    out = redact(msg, "SECRET123")
    assert "SECRET123" not in out
    assert "api_key=REDACTED" in out


def test_scrub_drops_account_urls_and_nested_key():
    data = {
        "search_metadata": {
            "id": "abc",
            "json_endpoint": "https://serpapi.com/searches/4f73/abc.json",
            "raw_html_file": "https://serpapi.com/searches/4f73/abc.html",
            "prettify_html_file": "https://serpapi.com/searches/4f73/abc.prettify",
        },
        "organic_results": [{"link": "https://x.test/?api_key=SECRET123"}],
    }
    out = scrub(data, "SECRET123")
    assert out["search_metadata"] == {"id": "abc"}
    assert "SECRET123" not in str(out)
    assert data["search_metadata"]["json_endpoint"]  # input not mutated


def test_trim_keeps_only_used_fields():
    data = {
        "search_metadata": {
            "id": "abc",
            "status": "Success",
            "created_at": "2026-10-06 10:00:00 UTC",
        },
        "search_parameters": {"engine": "google", "q": "x"},
        "organic_results": [
            {"title": "t", "link": "l", "snippet": "s", "rich_snippet": {"big": 1}}
        ],
        "related_searches": [{"query": "y"}],
    }
    out = trim("google", data)
    assert set(out) == {"search_metadata", "search_parameters", "organic_results"}
    assert out["organic_results"] == [{"title": "t", "link": "l", "snippet": "s"}]
