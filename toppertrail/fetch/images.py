from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from toppertrail.fetch.pages import USER_AGENT
from toppertrail.hashing import sha256_bytes, short_hash


@dataclass(frozen=True)
class ImageText:
    url: str
    image_sha256: str | None
    text: str
    error: str | None


def image_fixture_path(root: Path, url: str) -> Path:
    return Path(root) / "images" / f"{short_hash(url)}.json"


class LiveImageReader:
    def __init__(self, ocr: Callable[[bytes], str], client: httpx.Client | None = None,
                 max_bytes: int = 5_000_000) -> None:
        self._ocr = ocr
        self._client = client or httpx.Client(
            timeout=15.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
        self.max_bytes = max_bytes

    def read(self, url: str) -> ImageText:
        try:
            r = self._client.get(url)
        except httpx.HTTPError as err:
            return ImageText(url, None, "", f"fetch_error:{type(err).__name__}")
        if r.status_code >= 400:
            return ImageText(url, None, "", f"http_{r.status_code}")
        if not r.headers.get("content-type", "").startswith("image/"):
            return ImageText(url, None, "", "not_image")
        if len(r.content) > self.max_bytes:
            return ImageText(url, None, "", "too_large")
        try:
            text = self._ocr(r.content)
        except Exception as err:  # OCR engines raise many types on odd images
            return ImageText(url, sha256_bytes(r.content), "", f"ocr_error:{type(err).__name__}")
        return ImageText(url, sha256_bytes(r.content), text, None)


class ReplayImageReader:
    def __init__(self, fixtures: Path) -> None:
        self.fixtures = Path(fixtures)

    def read(self, url: str) -> ImageText:
        path = image_fixture_path(self.fixtures, url)
        if not path.exists():
            return ImageText(url, None, "", "missing_fixture")
        d = json.loads(path.read_text(encoding="utf-8"))
        return ImageText(d["url"], d.get("image_sha256"), d.get("text", ""), d.get("error"))


def load_rapidocr() -> Callable[[bytes], str] | None:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    engine = RapidOCR()

    def run(data: bytes) -> str:
        result, _ = engine(data)
        if not result:
            return ""
        rows = sorted(result, key=lambda r: (round(r[0][0][1] / 12), r[0][0][0]))
        return "\n".join(r[1] for r in rows)

    return run
