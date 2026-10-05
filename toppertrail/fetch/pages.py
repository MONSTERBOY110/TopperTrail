from __future__ import annotations

import json
import re
import time
import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from selectolax.lexbor import LexborNode as Node

from toppertrail.hashing import sha256_bytes, short_hash

USER_AGENT = "TopperTrail/0.1 (research on public coaching claims)"
_REMOVE = (
    "script", "style", "noscript", "template", "svg", "iframe", "form", "nav", "aside",
    "body > header", "body > footer", "footer", "header nav", "[role=navigation]",
    "[role=banner]", "[role=contentinfo]", "[aria-hidden=true]", "[class*=menu]", "[id*=menu]",
    "[class*=navbar]", "[class*=footer]", "[id*=footer]", "[class*=breadcrumb]",
    "[class*=sidebar]", "[class*=cookie]",
)
_BLOCKS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "figcaption", "blockquote",
    "dt", "dd", "caption", "div", "section", "article",
}


@dataclass(frozen=True)
class PageSnapshot:
    url: str
    status: int
    fetched_at: str
    html_sha256: str | None
    blocks: tuple[tuple[int, str], ...]
    error: str | None


def snapshot_from_dict(d: dict) -> PageSnapshot:
    return PageSnapshot(
        d["url"],
        int(d["status"]),
        d["fetched_at"],
        d.get("html_sha256"),
        tuple((int(i), t) for i, t in d.get("blocks") or ()),
        d.get("error"),
    )


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _walk(node: Node, out: list[str]) -> bool:
    """Append leaf block texts in document order; return True if the subtree holds a block."""
    contains = False
    child = node.child
    while child is not None:
        if child.tag not in ("-text", "-comment", "_comment") and _walk(child, out):
            contains = True
        child = child.next
    if node.tag == "img":
        alt = _clean(node.attributes.get("alt") or "")
        if alt:
            out.append(f"image: {alt}")
        return False
    if node.tag in _BLOCKS:
        if not contains:
            text = _clean(node.text(deep=True, separator=" "))
            if len(text) > 1:
                out.append(text)
        return True
    return contains


def html_to_blocks(html: str) -> list[tuple[int, str]]:
    tree = HTMLParser(html)
    for selector in _REMOVE:
        for node in tree.css(selector):
            node.decompose()
    root = tree.body or tree.root
    texts: list[str] = []
    if root is not None:
        _walk(root, texts)
    deduped = [t for i, t in enumerate(texts) if i == 0 or t != texts[i - 1]]
    return list(enumerate(deduped))


def filter_blocks(
    blocks: list[tuple[int, str]], relevant: Callable[[str], bool]
) -> list[tuple[int, str]]:
    keep: set[int] = set()
    index = {i for i, _ in blocks}
    for i, text in blocks:
        if relevant(text):
            keep.update(j for j in (i - 1, i, i + 1) if j in index)
    return [(i, t) for i, t in blocks if i in keep]


def page_fixture_path(root: Path, url: str) -> Path:
    return Path(root) / "pages" / f"{short_hash(url)}.json"


class LivePageFetcher:
    def __init__(self, client: httpx.Client | None = None, min_interval: float = 1.0,
                 max_bytes: int = 2_000_000, timeout: float = 10.0,
                 sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, today: str | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
        self.min_interval = min_interval
        self.max_bytes = max_bytes
        self._sleep, self._clock = sleep, clock
        self._today = today
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._last: dict[str, float] = {}

    def _date(self) -> str:
        return self._today or datetime.now(UTC).date().isoformat()

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self._client.get(base + "/robots.txt")
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except httpx.HTTPError:
                rp.parse([])
            self._robots[base] = rp
        return rp.can_fetch(USER_AGENT, url)

    def _throttle(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            wait = self.min_interval - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        self._last[host] = self._clock()

    def fetch(self, url: str) -> PageSnapshot:
        day = self._date()
        if not self._allowed(url):
            return PageSnapshot(url, 0, day, None, (), "robots_disallowed")
        self._throttle(urlsplit(url).netloc)
        try:
            with self._client.stream("GET", url) as r:
                if "html" not in r.headers.get("content-type", ""):
                    return PageSnapshot(url, r.status_code, day, None, (), "not_html")
                if r.status_code >= 400:
                    return PageSnapshot(url, r.status_code, day, None, (), f"http_{r.status_code}")
                body = b""
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > self.max_bytes:
                        return PageSnapshot(url, r.status_code, day, None, (), "too_large")
                encoding = r.encoding or "utf-8"
                status = r.status_code
        except httpx.HTTPError as err:
            return PageSnapshot(url, 0, day, None, (), f"fetch_error:{type(err).__name__}")
        html = body.decode(encoding, errors="replace")
        return PageSnapshot(url, status, day, sha256_bytes(body), tuple(html_to_blocks(html)), None)


class ReplayPageFetcher:
    def __init__(self, fixtures: Path) -> None:
        self.fixtures = Path(fixtures)

    def fetch(self, url: str) -> PageSnapshot:
        path = page_fixture_path(self.fixtures, url)
        if not path.exists():
            return PageSnapshot(url, 0, "", None, (), "missing_fixture")
        return snapshot_from_dict(json.loads(path.read_text(encoding="utf-8")))
