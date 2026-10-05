import traceback

import pytest
import requests
import serpapi

from toppertrail.serp.budget import Budget, BudgetExceeded, spend_count
from toppertrail.serp.live import LiveSerpClient, account_searches_left

KEY = "SECRET123"


def http_error(status, url, body=b'{"error": "boom"}', retry_after=None):
    r = requests.Response()
    r.status_code = status
    r._content = body
    r.url = url
    if retry_after:
        r.headers["Retry-After"] = retry_after
    exc = requests.exceptions.HTTPError(f"{status} Client Error for url: {url}", response=r)
    return serpapi.HTTPError(exc)


class FakeSdk:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def search(self, params):
        self.calls.append(dict(params))
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return o

    def account(self):
        return {"total_searches_left": 212, "plan_searches_left": 212}


OK = {
    "search_metadata": {"id": "s1", "json_endpoint": "https://serpapi.com/searches/h/s1.json"},
    "organic_results": [{"title": "t", "link": "l", "extra": 1}],
}


def test_success_charges_scrubs_trims_and_logs(tmp_path):
    budget = Budget(5)
    client = LiveSerpClient(KEY, budget, tmp_path / "spend.jsonl", sdk=FakeSdk([OK]))
    r = client.search("google", {"q": "x", "gl": "in"})
    assert r.search_id == "s1"
    assert "json_endpoint" not in r.data["search_metadata"]
    assert r.data["organic_results"] == [{"title": "t", "link": "l"}]
    assert budget.spent == 1
    assert spend_count(tmp_path / "spend.jsonl") == 1


def test_no_results_json_error_is_free():
    budget = Budget(5)
    sdk = FakeSdk(
        [{"search_metadata": {"id": "s2"},
          "error": "Google hasn't returned any results for this query."}]
    )
    r = LiveSerpClient(KEY, budget, sdk=sdk).search("google", {"q": "zzz"})
    assert r.data["error"].startswith("Google hasn't")
    assert budget.spent == 0


def test_429_retries_with_retry_after_then_succeeds():
    slept = []
    sdk = FakeSdk(
        [http_error(429, f"https://serpapi.com/search?api_key={KEY}", retry_after="2"), OK]
    )
    client = LiveSerpClient(KEY, Budget(5), sdk=sdk, sleep=slept.append)
    r = client.search("google", {"q": "x"})
    assert r.search_id == "s1"
    assert slept == [2.0]
    assert len(sdk.calls) == 2


def test_error_text_and_traceback_never_contain_key():
    sdk = FakeSdk(
        [http_error(401, f"https://serpapi.com/search?engine=google&api_key={KEY}",
                    body=b"not json")]
    )
    client = LiveSerpClient(KEY, Budget(5), sdk=sdk)
    with pytest.raises(Exception) as info:
        client.search("google", {"q": "x"})
    text = "".join(traceback.format_exception(info.value))
    assert KEY not in text
    assert "HTTP 401" in str(info.value)


def test_budget_exceeded_before_any_call():
    sdk = FakeSdk([OK])
    with pytest.raises(BudgetExceeded):
        LiveSerpClient(KEY, Budget(0), sdk=sdk).search("google", {"q": "x"})
    assert sdk.calls == []


def test_account_searches_left():
    assert account_searches_left(KEY, sdk=FakeSdk([])) == 212
