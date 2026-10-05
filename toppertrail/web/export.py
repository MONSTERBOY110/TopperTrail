from __future__ import annotations

import shutil
from importlib.resources import files
from pathlib import Path

from toppertrail.data import load_registry, read_data
from toppertrail.web.app import (
    exam_context,
    index_context,
    institute_context,
    tabs,
    topper_context,
)
from toppertrail.web.render import Renderer, load_ledgers


def _write(path: Path, html: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8", newline="\n")
    return path


def export_site(home: Path, out: Path, base: str = "/") -> list[Path]:
    renderer = Renderer(base, static=True)
    registry = load_registry()
    ledgers = load_ledgers(home)

    class _Pages:
        @staticmethod
        def page(name: str, **ctx) -> str:
            ctx.setdefault("tabs", tabs(ledgers))
            return renderer.page(name, **ctx)

    r = _Pages()
    out = Path(out)
    written = [_write(out / "index.html", r.page("index.html", **index_context(ledgers)))]
    guidelines = read_data("ccpa/guidelines-2024.md")
    written.append(_write(out / "methodology" / "index.html",
                          r.page("methodology.html", guidelines=guidelines,
                                 page_id="methodology")))
    for exam_id, led in ledgers.items():
        root = out / "exam" / exam_id
        written.append(_write(root / "index.html",
                              r.page("exam.html", **exam_context(led, registry))))
        for t in led["toppers"]:
            ctx = topper_context(led, t["rank"], registry)
            written.append(_write(root / "topper" / str(t["rank"]) / "index.html",
                                  r.page("topper.html", **ctx)))
        for iid in sorted({c["institute_id"] for c in led["claims"]}):
            ctx = institute_context(led, iid, registry)
            written.append(_write(root / "institute" / iid / "index.html",
                                  r.page("institute.html", **ctx)))
    static = Path(str(files("toppertrail").joinpath("web/static")))
    shutil.copytree(static, out / "static", dirs_exist_ok=True)
    return written
