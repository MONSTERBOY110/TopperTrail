"""Convert the research case file into toppertrail/data/ccpa/orders.yaml (claims without labels).

Usage: python scripts/build_orders.py <path to ccpa_coaching_cases.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

src = Path(sys.argv[1])
cases = json.loads(src.read_text(encoding="utf-8"))
out = []
for c in cases:
    out.append({
        "id": c["id"],
        "institute": c["institute"],
        "domain": c.get("domain"),
        "exam": c["exam"],
        "exam_year": c.get("exam_year"),
        "order_date": c["order_date"],
        "penalty_inr": c.get("penalty_inr"),
        "order_pdf": c.get("order_pdf"),
        "pib": c.get("pib"),
        "claims": [{"text": t, "expected": []} for t in c.get("claims", [])],
    })
dest = Path("toppertrail/data/ccpa/orders.yaml")
dest.parent.mkdir(parents=True, exist_ok=True)
doc = {"orders": out, "course_labels": []}
dest.write_text(
    yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=120),
    encoding="utf-8",
    newline="\n",
)
print(f"wrote {len(out)} orders, {sum(len(o['claims']) for o in out)} claim texts")
