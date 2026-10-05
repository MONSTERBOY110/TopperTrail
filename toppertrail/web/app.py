from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from toppertrail.data import exam_ids, load_exam, load_registry, read_data
from toppertrail.evidence import EvidenceStore
from toppertrail.report import (
    ai_findings,
    claimant_chips,
    claimants,
    headline,
    institute_rows,
    institute_slots,
    institute_view,
    tally,
    topper_view,
)
from toppertrail.web.render import Renderer, load_ledgers


def exam_context(led: dict, registry) -> dict:
    chips = {t["rank"]: claimant_chips(led, t["rank"], registry) for t in led["toppers"]}
    return {"led": led, "h": headline(led), "ai": ai_findings(led),
            "rows": institute_rows(led, registry), "claimants": claimants(led),
            "tally": tally(led, registry), "chips": chips, "slots": institute_slots(led),
            "registry_size": len(registry.all()), "rank_label": _rank_label(led),
            "as_of": max((c.get("observed_at") or "" for c in led["claims"]), default="")}


def _rank_label(led: dict) -> str:
    return load_exam(led["exam"]).rank_label if led["exam"] in exam_ids() else "AIR"


def topper_context(led: dict, rank: int, registry) -> dict:
    return {"led": led, "v": topper_view(led, rank), "registry": registry,
            "chips": claimant_chips(led, rank, registry), "slots": institute_slots(led),
            "rank_label": _rank_label(led)}


def institute_context(led: dict, iid: str, registry) -> dict:
    return {"led": led, "v": institute_view(led, iid, registry),
            "slot": institute_slots(led).get(iid), "rank_label": _rank_label(led)}


def index_context(ledgers: dict) -> dict:
    return {"exams": [(k, v, headline(v)) for k, v in ledgers.items()]}


def tabs(ledgers: dict) -> list[tuple[str, str]]:
    return [(k, v["label"]) for k, v in ledgers.items()]


def create_app(home: Path) -> FastAPI:
    app = FastAPI(title="TopperTrail", docs_url=None, redoc_url=None, openapi_url=None)
    static = str(files("toppertrail").joinpath("web/static"))
    app.mount("/static", StaticFiles(directory=static), name="static")
    renderer = Renderer("/")
    registry = load_registry()

    class _Pages:
        @staticmethod
        def page(name: str, **ctx) -> str:
            ctx.setdefault("tabs", tabs(load_ledgers(home)))
            return renderer.page(name, **ctx)

    r = _Pages()
    store = EvidenceStore(Path(home) / "evidence")

    def ledger(exam_id: str) -> dict:
        found = load_ledgers(home).get(exam_id)
        if not found:
            raise HTTPException(404, "No ledger for this exam. Run collect and analyze first.")
        return found

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return r.page("index.html", **index_context(load_ledgers(home)))

    @app.get("/exam/{exam_id}", response_class=HTMLResponse)
    def exam(exam_id: str) -> str:
        return r.page("exam.html", **exam_context(ledger(exam_id), registry))

    @app.get("/exam/{exam_id}/topper/{rank}", response_class=HTMLResponse)
    def topper(exam_id: str, rank: int) -> str:
        led = ledger(exam_id)
        if not any(t["rank"] == rank for t in led["toppers"]):
            raise HTTPException(404, "Rank not in this ledger.")
        return r.page("topper.html", **topper_context(led, rank, registry))

    @app.get("/exam/{exam_id}/institute/{iid}", response_class=HTMLResponse)
    def institute(exam_id: str, iid: str) -> str:
        led = ledger(exam_id)
        try:
            ctx = institute_context(led, iid, registry)
        except KeyError:
            raise HTTPException(404, "Unknown institute.") from None
        return r.page("institute.html", **ctx)

    @app.get("/methodology", response_class=HTMLResponse)
    def methodology() -> str:
        return r.page("methodology.html", guidelines=read_data("ccpa/guidelines-2024.md"),
                      page_id="methodology")

    @app.get("/evidence/{sha}", response_class=HTMLResponse)
    def evidence(sha: str) -> str:
        if len(sha) != 64 or not all(ch in "0123456789abcdef" for ch in sha):
            raise HTTPException(404, "Not an evidence id.")
        try:
            obj = store.get(sha)
        except FileNotFoundError:
            raise HTTPException(404, "Evidence not found on this machine.") from None
        body = json.dumps(obj, ensure_ascii=False, indent=1)
        return r.page("evidence.html", sha=sha, body=body, intact=store.is_intact(sha))

    return app
