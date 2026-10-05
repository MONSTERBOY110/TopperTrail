import json

import httpx

from toppertrail.fetch.pages import (
    LivePageFetcher,
    ReplayPageFetcher,
    filter_blocks,
    html_to_blocks,
    page_fixture_path,
)

PAGE = """<html><body>
<header><nav><ul><li>GS Foundation Course</li><li>Test Series</li><li>IGP</li></ul></nav></header>
<div class="mega-menu"><a>Mains Test Series</a></div>
<main><h1>Anuj Agnihotri UPSC AIR 1 2025</h1>
<p>Congratulations Anuj Agnihotri, AIR 1 in UPSC CSE 2025.</p>
<img alt="Anuj Agnihotri poster" src="x.jpg">
<ul><li>Rajeshwari Suve M AIR 2 (IGP)</li></ul></main>
<footer><p>Best IAS coaching in Delhi</p></footer>
<script>var courses = "Test Series";</script></body></html>"""


def test_blocks_drop_menus_footer_and_scripts():
    texts = [t for _, t in html_to_blocks(PAGE)]
    assert "Congratulations Anuj Agnihotri, AIR 1 in UPSC CSE 2025." in texts
    assert "image: Anuj Agnihotri poster" in texts
    joined = " ".join(texts)
    assert "GS Foundation Course" not in joined
    assert "Mains Test Series" not in joined
    assert "Best IAS coaching" not in joined
    assert "var courses" not in joined


def test_filter_keeps_relevant_blocks_and_neighbours():
    blocks = [(0, "a"), (1, "b"), (2, "Anuj"), (3, "c"), (4, "d")]
    assert filter_blocks(blocks, lambda t: t == "Anuj") == [(1, "b"), (2, "Anuj"), (3, "c")]


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
    if request.url.path == "/report.pdf":
        return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
    return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=PAGE)


def fetcher():
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LivePageFetcher(client=client, min_interval=0, today="2026-10-06")


def test_live_fetch_ok_robots_and_non_html():
    f = fetcher()
    ok = f.fetch("https://inst.test/anuj")
    assert ok.error is None and ok.fetched_at == "2026-10-06" and ok.html_sha256
    assert f.fetch("https://inst.test/private/x").error == "robots_disallowed"
    assert f.fetch("https://inst.test/report.pdf").error == "not_html"


def test_replay_page(tmp_path):
    path = page_fixture_path(tmp_path, "https://inst.test/anuj")
    path.parent.mkdir(parents=True)
    doc = {
        "url": "https://inst.test/anuj",
        "status": 200,
        "fetched_at": "2026-10-06",
        "html_sha256": "ab",
        "blocks": [[2, "Anuj"]],
        "error": None,
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    snap = ReplayPageFetcher(tmp_path).fetch("https://inst.test/anuj")
    assert snap.blocks == ((2, "Anuj"),)
    assert ReplayPageFetcher(tmp_path).fetch("https://inst.test/other").error == "missing_fixture"
