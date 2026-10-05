import io
import sys

from typer.testing import CliRunner

from toppertrail.cli import _utf8_stdio, app


def test_version():
    r = CliRunner().invoke(app, ["version"])
    assert r.exit_code == 0
    assert "toppertrail 0.1.0" in r.output


def test_utf8_stdio_survives_cp1252_console(monkeypatch):
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stream)
    _utf8_stdio()
    print("अनुज अग्निहोत्री")
    stream.flush()
    assert "अनुज".encode() in raw.getvalue()
