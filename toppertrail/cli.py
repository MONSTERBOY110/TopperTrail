from __future__ import annotations

import sys

import typer

from toppertrail import __version__

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="TopperTrail: one rank, many claims. Follow the trail.",
)


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


@app.callback()
def _main() -> None:
    _utf8_stdio()


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(f"toppertrail {__version__}")


@app.command()
def validate() -> None:
    """Score the rules against the frozen CCPA order suite and print a Markdown table."""
    from toppertrail.extract.courses import Lexicon
    from toppertrail.rules import load_orders, score_orders

    scores = score_orders(load_orders(), Lexicon.load())
    typer.echo("| Rule | TP | FP | FN | Precision | Recall |")
    typer.echo("|---|---|---|---|---|---|")
    for rule in ("TT-09", "TT-10", "TT-11"):
        s = scores[rule]
        typer.echo(
            f"| {rule} | {s['tp']} | {s['fp']} | {s['fn']} | {s['precision']} | {s['recall']} |"
        )
    cl = scores["course_labels"]
    typer.echo(f"\nCourse labels classified exactly: {cl['exact']} of {cl['n']} labels (share).")


def _context(exam_id: str, top: int | None):
    from toppertrail.data import load_exam, load_registry, load_roster

    exam = load_exam(exam_id)
    return exam, load_roster(exam, top or exam.default_top), load_registry()


@app.command()
def estimate(exam_id: str, top: int | None = typer.Option(None, help="Top N ranks")) -> None:
    """Show the SerpApi credits a collection run would spend, per engine."""
    from toppertrail.collect import estimate as plan

    exam, toppers, registry = _context(exam_id, top)
    counts = plan(exam, toppers, registry)
    typer.echo(f"{exam.label}, top {len(toppers)}")
    for engine, n in counts.items():
        typer.echo(f"  {engine:<34}{n:>5}")
    typer.echo(f"  {'total credits':<34}{sum(counts.values()):>5}")


@app.command()
def collect(exam_id: str, top: int | None = typer.Option(None), record: bool = False,
            ocr: bool = True) -> None:
    """Collect evidence (live, or replay when TOPPERTRAIL_REPLAY=1)."""
    from toppertrail.collect import Collector, export_fixtures
    from toppertrail.collect import estimate as plan
    from toppertrail.config import load_settings
    from toppertrail.data import load_independent
    from toppertrail.evidence import EvidenceStore
    from toppertrail.extract.courses import Lexicon
    from toppertrail.fetch.images import LiveImageReader, ReplayImageReader, load_rapidocr
    from toppertrail.fetch.pages import LivePageFetcher, ReplayPageFetcher
    from toppertrail.serp.budget import Budget, BudgetExceeded
    from toppertrail.serp.live import LiveSerpClient, account_searches_left
    from toppertrail.serp.replay import ReplaySerpClient

    s = load_settings()
    exam, toppers, registry = _context(exam_id, top)
    budget = None
    if s.replay:
        serp = ReplaySerpClient(s.fixtures)
        pages = ReplayPageFetcher(s.fixtures)
        images = ReplayImageReader(s.fixtures)
        typer.echo("Replay mode: no network calls, no credits.")
    else:
        if not s.api_key:
            typer.echo("SERPAPI_API_KEY is not set (or use TOPPERTRAIL_REPLAY=1).", err=True)
            raise typer.Exit(1)
        need = sum(plan(exam, toppers, registry).values())
        left = account_searches_left(s.api_key)
        cap = min(s.budget_cap, left)
        if need > cap:
            typer.echo(f"Estimated {need} credits exceed the available {cap}. Lower --top.",
                       err=True)
            raise typer.Exit(1)
        budget = Budget(cap)
        serp = LiveSerpClient(s.api_key, budget, s.home / "spend.jsonl")
        pages = LivePageFetcher()
        reader = load_rapidocr() if ocr else None
        images = LiveImageReader(reader) if reader else None
        typer.echo(f"Live mode: estimate {need} credits, cap {cap}, "
                   f"OCR {'on' if images else 'off'}.")
    store = EvidenceStore(s.home / "evidence")
    col = Collector(exam, toppers, registry, load_independent(), Lexicon.load(), serp, pages,
                    images, store, log=typer.echo)
    try:
        run = col.run()
    except BudgetExceeded as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(1) from None
    run.save(s.home / "runs" / f"{exam.id}.json")
    spent = budget.spent if budget else 0
    typer.echo(f"Artifacts: {len(run.artifacts)}, missing: {col.missing}, credits spent: {spent}")
    typer.echo(f"Manifest root: {run.manifest_root()}")
    if record:
        n = export_fixtures(run, store, s.fixtures, top=len(toppers))
        typer.echo(f"Exported {n} fixtures to {s.fixtures}")


@app.command()
def budget() -> None:
    """Show remaining SerpApi searches and this machine's spend log."""
    from toppertrail.config import load_settings
    from toppertrail.serp.budget import spend_count
    from toppertrail.serp.live import account_searches_left

    s = load_settings()
    typer.echo(f"Spend log: {spend_count(s.home / 'spend.jsonl')} paid searches")
    if s.api_key and not s.replay:
        typer.echo(f"Account searches left: {account_searches_left(s.api_key)}")


@app.command()
def analyze(exam_id: str, top: int | None = typer.Option(None)) -> None:
    """Build the ledger from collected evidence and print the headline numbers."""
    import json

    from toppertrail.analyze import analyze as build
    from toppertrail.analyze import ledger_hash
    from toppertrail.config import load_settings
    from toppertrail.evidence import EvidenceStore, Run
    from toppertrail.extract.courses import Lexicon
    from toppertrail.report import ai_findings, headline

    s = load_settings()
    exam, toppers, registry = _context(exam_id, top)
    run_path = s.home / "runs" / f"{exam.id}.json"
    if not run_path.exists():
        typer.echo(f"No collected run for {exam.id}. Run `toppertrail collect {exam.id}` first.",
                   err=True)
        raise typer.Exit(1)
    run = Run.load(run_path)
    ledger = build(exam, toppers, registry, Lexicon.load(), run, EvidenceStore(s.home / "evidence"))
    out = s.home / "ledgers" / f"{exam.id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8",
                   newline="\n")
    numbers = {**headline(ledger), **{"ai_" + k: v for k, v in ai_findings(ledger).items()}}
    for k, v in numbers.items():
        typer.echo(f"  {k:<30}{v}")
    typer.echo(f"Ledger hash: {ledger_hash(ledger)}")


@app.command()
def verify(exam_id: str) -> None:
    """Check evidence integrity and compare the run with the recorded fixture manifest."""
    import json

    from toppertrail.collect import manifest_path
    from toppertrail.config import load_settings
    from toppertrail.evidence import EvidenceStore, Run, damaged

    s = load_settings()
    run = Run.load(s.home / "runs" / f"{exam_id}.json")
    bad = damaged(run, EvidenceStore(s.home / "evidence"))
    typer.echo(f"Evidence files checked: {len(run.artifacts)}, damaged: {len(bad)}")
    path = manifest_path(s.fixtures, exam_id)
    same = True
    if path.exists():
        recorded = json.loads(path.read_text(encoding="utf-8"))["manifest_root"]
        same = recorded == run.manifest_root()
        typer.echo("Manifest root matches the recorded run." if same else
                   f"Manifest root differs: recorded {recorded}, this run {run.manifest_root()}")
    if bad or not same:
        raise typer.Exit(1)


@app.command()
def serve(port: int = 8765, host: str = "127.0.0.1") -> None:
    """Open the local dashboard."""
    import uvicorn

    from toppertrail.config import load_settings
    from toppertrail.web.app import create_app

    typer.echo(f"Dashboard: http://{host}:{port}/")
    uvicorn.run(create_app(load_settings().home), host=host, port=port, log_level="warning")


@app.command()
def export(out: str = "site", base: str = "/") -> None:
    """Write the static findings site."""
    from pathlib import Path

    from toppertrail.config import load_settings
    from toppertrail.web.export import export_site

    written = export_site(load_settings().home, Path(out), base)
    typer.echo(f"Wrote {len(written)} pages to {out}")
