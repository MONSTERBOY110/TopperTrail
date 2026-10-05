from __future__ import annotations

import json
import re
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from toppertrail.extract.text import name_regex, snap_span
from toppertrail.rules import RULES

NOTICE = (
    "TopperTrail records what institutes publicly claim and what they disclose next to the "
    "claim. Only the CCPA decides whether an advertisement is misleading."
)
SOURCE_LABELS = {
    "web_page": "Web page",
    "snippet_only": "Search snippet only",
    "poster": "Poster",
    "ad_creative": "Google ad (India)",
    "youtube_hosted": "YouTube video",
    "youtube_description": "YouTube description",
}
# Gaps that apply to most claims render as a compact tag row; the rest keep a detail line.
GAP_RULES = ("TT-01", "TT-03", "TT-04", "TT-05", "TT-13", "TT-14")
OWN_WORDS = {
    "mentioned": "Topper mentions this institute",
    "denied": "Words to check",
    "not_mentioned": "Not mentioned by the topper",
    "no_interview": "No independent interview",
}


def highlight(text: str, terms) -> Markup:
    """Escape text, then wrap the matched course terms in <mark>. Never trusts the input."""
    terms = [t for t in (terms or []) if t]
    if not terms:
        return escape(text)
    pattern = re.compile("|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)),
                         re.IGNORECASE)
    out, last = [], 0
    for m in pattern.finditer(text):
        out.append(escape(text[last:m.start()]))
        out.append(Markup("<mark>") + escape(m.group()) + Markup("</mark>"))
        last = m.end()
    out.append(escape(text[last:]))
    return Markup("").join(out)


_GENERIC_ALT = {"banner", "logo", "icon", "image", "img", "photo", "picture", "thumbnail"}


def _display_lines(window: str) -> str:
    lines = []
    for line in window.splitlines():
        if line.startswith("image: "):
            alt = line[len("image: "):].strip()
            if len(alt.split()) < 2 or alt.lower() in _GENERIC_ALT:
                continue  # a one-word alt such as "banner" says nothing
            lines.append("Image text: " + alt)
        else:
            lines.append(line)
    return "\n".join(lines)


def excerpt(window: str, name: str, terms, width: int = 360) -> Markup:
    """The claim window centred on the topper it is filed under, name and course words marked."""
    text = _display_lines(window)
    pattern = name_regex(name)
    m = pattern.search(text) if pattern else None
    start = 0
    if m and len(text) > width:
        start = max(0, m.start() - width // 3)
    end = min(len(text), start + width)
    start, end = snap_span(text, start, end)
    piece = text[start:end]
    out = _mark(piece, pattern, terms)
    if start > 0 and not piece.startswith("..."):
        out = Markup("...") + out
    if end < len(text) and not piece.endswith("..."):
        out = out + Markup("...")
    return out


def full_text(window: str, name: str, terms) -> Markup:
    return _mark(_display_lines(window), name_regex(name), terms)


def _mark(text: str, name_pattern, terms) -> Markup:
    spans = []
    if name_pattern:
        spans += [(m.start(), m.end(), "who") for m in name_pattern.finditer(text)]
    terms = [t for t in (terms or []) if t]
    if terms:
        tp = re.compile("|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)),
                        re.IGNORECASE)
        spans += [(m.start(), m.end(), "mark") for m in tp.finditer(text)]
    spans.sort()
    out, last = [], 0
    for s, e, kind in spans:
        if s < last:
            continue
        out.append(escape(text[last:s]))
        piece = escape(text[s:e])
        if kind == "who":
            out.append(Markup('<strong class="who">') + piece + Markup("</strong>"))
        else:
            out.append(Markup("<mark>") + piece + Markup("</mark>"))
        last = e
    out.append(escape(text[last:]))
    return Markup("").join(out)


def clock(ms: int) -> str:
    s = int(ms) // 1000
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def inr(amount) -> str:
    """Indian digit grouping: 1100000 becomes ₹11,00,000."""
    digits = str(int(amount or 0))
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return "₹" + ",".join(groups + [tail]) if groups else "₹" + tail


def mdlite(text: str) -> Markup:
    """The small Markdown subset used in shipped data files: headings, lists, paragraphs."""
    out: list[Markup] = []
    items: list[Markup] = []
    para: list[str] = []

    def flush() -> None:
        if items:
            out.append(Markup("<ul>") + Markup("").join(items) + Markup("</ul>"))
            items.clear()
        if para:
            out.append(Markup("<p>") + escape(" ".join(para)) + Markup("</p>"))
            para.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
        elif stripped.startswith("## "):
            flush()
            out.append(Markup("<h3>") + escape(stripped[3:]) + Markup("</h3>"))
        elif stripped.startswith("# "):
            flush()
            out.append(Markup("<h2>") + escape(stripped[2:]) + Markup("</h2>"))
        elif stripped.startswith("- "):
            if para:
                flush()
            items.append(Markup("<li>") + escape(stripped[2:]) + Markup("</li>"))
        else:
            if items:
                flush()
            para.append(stripped)
    flush()
    return Markup("").join(out)


def load_ledgers(home: Path) -> dict[str, dict]:
    folder = Path(home) / "ledgers"
    if not folder.exists():
        return {}
    paths = sorted(folder.glob("*.json"))
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in paths}


class Renderer:
    def __init__(self, base: str = "/", static: bool = False) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.static = static
        folder = str(files("toppertrail").joinpath("web/templates"))
        self.env = Environment(loader=FileSystemLoader(folder),
                               autoescape=select_autoescape(["html"]))
        self.env.globals.update(link=self.link, NOTICE=NOTICE, RULES=RULES,
                                SOURCE_LABELS=SOURCE_LABELS, OWN_WORDS=OWN_WORDS,
                                GAP_RULES=GAP_RULES,
                                static_mode=static)
        self.env.filters.update(highlight=highlight, clock=clock, inr=inr, mdlite=mdlite)
        self.env.globals.update(excerpt=excerpt, full_text=full_text)

    def link(self, path: str) -> str:
        path = path.lstrip("/")
        if self.static and path and not path.endswith((".css", ".html", ".svg")):
            path = path.rstrip("/") + "/"
        return self.base + path

    def page(self, name: str, **ctx) -> str:
        return self.env.get_template(name).render(**ctx)
