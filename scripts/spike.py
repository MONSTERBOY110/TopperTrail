"""Run the AIR 1 (UPSC CSE 2025) queries once and save trimmed, scrubbed responses.

Costs about 8 credits. Output: .toppertrail/spike/NN-<engine>.json
"""

from __future__ import annotations

import json
import sys

from toppertrail.config import load_settings
from toppertrail.serp.budget import Budget
from toppertrail.serp.live import LiveSerpClient, account_searches_left

QUERIES = [
    ("google", {"q": '"Anuj Agnihotri" UPSC CSE 2025 AIR 1', "gl": "in", "hl": "en"}),
    ("google_images", {"q": "Anuj Agnihotri AIR 1 UPSC 2025", "gl": "in", "hl": "en"}),
    (
        "youtube",
        {"search_query": "Anuj Agnihotri UPSC 2025 topper interview", "gl": "in", "hl": "en"},
    ),
    ("youtube_video", {"v": "8X-e5cJ_L3M", "gl": "in", "hl": "en"}),
    ("youtube_video_transcript", {"v": "KIr6dWSqspI", "language_code": "hi"}),
    ("youtube_video_transcript", {"v": "KIr6dWSqspI", "language_code": "hi", "type": "asr"}),
    (
        "google_ads_transparency_center",
        {
            "text": "visionias.in",
            "region": "2356",
            "start_date": "20260306",
            "end_date": "20261005",
            "num": "100",
        },
    ),
    (
        "google_ai_mode",
        {
            "q": "Which coaching institute did Anuj Agnihotri, UPSC CSE 2025 AIR 1, study at?",
            "gl": "in",
            "hl": "en",
        },
    ),
]


def main() -> None:
    s = load_settings()
    if not s.api_key:
        sys.exit("SERPAPI_API_KEY is not set in .env")
    left = account_searches_left(s.api_key)
    print("searches left before spike:", left)
    if left < len(QUERIES) + 5:
        sys.exit("not enough credits for the spike")
    client = LiveSerpClient(s.api_key, Budget(len(QUERIES)), s.home / "spend.jsonl")
    out = s.home / "spike"
    out.mkdir(parents=True, exist_ok=True)
    for i, (engine, params) in enumerate(QUERIES):
        r = client.search(engine, params)
        path = out / f"{i:02d}-{engine}.json"
        path.write_text(
            json.dumps(r.data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
        )
        print(f"{engine}: keys={sorted(r.data)} search_id={r.search_id}")
    print("searches left after spike:", account_searches_left(s.api_key))


if __name__ == "__main__":
    main()
