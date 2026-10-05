from __future__ import annotations

from typing import Any

from toppertrail.data import Registry
from toppertrail.models import AIAnswer


def flatten_text_blocks(blocks: Any) -> str:
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("snippet"), str):
                parts.append(node["snippet"])
            for key, value in node.items():
                if key != "snippet":
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(blocks)
    return " ".join(p.strip() for p in parts if p.strip())


def ai_answer(response: dict, rank: int, registry: Registry) -> AIAnswer:
    text = flatten_text_blocks(response.get("text_blocks") or [])
    if not text and isinstance(response.get("reconstructed_markdown"), str):
        text = response["reconstructed_markdown"]
    sid = (response.get("search_metadata") or {}).get("id")
    return AIAnswer(rank, "google_ai_mode", sid, tuple(registry.find_aliases(text)), text[:500])
