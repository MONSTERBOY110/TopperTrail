from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from toppertrail.hashing import canonical_json, short_hash

DROP_PARAMS = {"api_key", "no_cache", "async", "output", "zero_trace"}
SCRUB_META = ("json_endpoint", "raw_html_file", "prettify_html_file")
_KEY_IN_URL = re.compile(r"(api_key=)[^&\s\"']+")

# Fields kept per engine. Everything else is dropped before evidence is stored, which keeps
# fixtures small and avoids redistributing third-party content we never use.
_KEEP_TOP = ("search_metadata", "search_parameters", "error")
_KEEP: dict[str, dict[str, Any]] = {
    "google": {
        "organic_results": (
            "position", "title", "link", "displayed_link", "snippet", "date", "source",
        )
    },
    "google_images": {"images_results": ("position", "title", "link", "source", "original")},
    "youtube": {
        "video_results": (
            "position_on_page", "title", "link", "channel", "published_date", "length",
            "description", "views",
        )
    },
    "youtube_video": {"title": None, "description": None, "channel": None, "published_date": None},
    "youtube_video_transcript": {"transcript": None, "available_transcripts": None},
    "google_ads_transparency_center": {
        "advertiser": None,
        "search_information": None,
        "ad_creatives": (
            "advertiser_id", "advertiser", "ad_creative_id", "format", "image", "width",
            "height", "first_shown", "last_shown", "details_link",
        ),
    },
    "google_ai_mode": {"text_blocks": None, "references": None, "reconstructed_markdown": None},
}
_META_KEEP = ("id", "status", "created_at", "processed_at")


class SerpError(RuntimeError):
    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class MissingFixture(SerpError):
    pass


@dataclass(frozen=True)
class SerpResult:
    engine: str
    params: dict
    data: dict
    source: str  # "live" or "replay"

    @property
    def search_id(self) -> str | None:
        return (self.data.get("search_metadata") or {}).get("id")


class SerpClient(Protocol):
    def search(self, engine: str, params: dict) -> SerpResult: ...


def canonical_params(engine: str, params: dict) -> dict:
    clean = {k: str(v) for k, v in params.items() if k not in DROP_PARAMS and v is not None}
    clean["engine"] = engine
    return dict(sorted(clean.items()))


def params_hash(engine: str, params: dict) -> str:
    return short_hash(canonical_json(canonical_params(engine, params)))


def redact(text: str, api_key: str | None) -> str:
    out = _KEY_IN_URL.sub(r"\1REDACTED", text)
    if api_key:
        out = out.replace(api_key, "REDACTED")
    return out


def _walk(obj: Any, api_key: str | None) -> Any:
    if isinstance(obj, str):
        return redact(obj, api_key)
    if isinstance(obj, list):
        return [_walk(x, api_key) for x in obj]
    if isinstance(obj, dict):
        return {k: _walk(v, api_key) for k, v in obj.items()}
    return obj


def scrub(data: dict, api_key: str | None) -> dict:
    copy = json.loads(json.dumps(data))
    meta = copy.get("search_metadata")
    if isinstance(meta, dict):
        for k in SCRUB_META:
            meta.pop(k, None)
    return _walk(copy, api_key)


def trim(engine: str, data: dict) -> dict:
    spec = _KEEP.get(engine, {})
    out: dict[str, Any] = {}
    for key in _KEEP_TOP:
        if key in data:
            out[key] = data[key]
    if isinstance(out.get("search_metadata"), dict):
        out["search_metadata"] = {
            k: v for k, v in out["search_metadata"].items() if k in _META_KEEP
        }
    for key, fields in spec.items():
        if key not in data:
            continue
        value = data[key]
        if fields is None:
            out[key] = value
        elif isinstance(value, list):
            out[key] = [
                {f: item[f] for f in fields if f in item}
                for item in value
                if isinstance(item, dict)
            ]
    return out
