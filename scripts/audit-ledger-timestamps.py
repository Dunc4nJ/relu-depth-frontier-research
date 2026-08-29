#!/usr/bin/env python3
"""Fail closed on future or pre-charter canonical ledger timestamps."""

from __future__ import annotations

import datetime as dt
import re
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc


def fail(message: str) -> None:
    print(f"timestamp-audit: FAIL — {message}", file=sys.stderr)
    raise SystemExit(1)


charter = (ROOT / "RESEARCH_CHARTER.md").read_text(encoding="utf-8")
match = re.search(r"\*\*Created:\*\*\s*([0-9T:\-]+Z)", charter)
if match is None:
    fail("RESEARCH_CHARTER.md has no UTC creation timestamp")
charter_created = dt.datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
now = dt.datetime.now(tz=UTC)
tolerance = dt.timedelta(seconds=60)
checked = 0

for ledger_path in sorted((ROOT / "ledger").glob("*.toml")):
    data = tomllib.loads(ledger_path.read_text(encoding="utf-8"))
    for table_name, records in data.items():
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict) or "created" not in record:
                continue
            created = record["created"]
            if not isinstance(created, dt.datetime) or created.tzinfo is None:
                fail(f"{ledger_path.name}:{table_name} has a non-UTC-aware created value")
            created = created.astimezone(UTC)
            identity = record.get("id", f"{table_name}[unknown]")
            if created < charter_created:
                fail(f"{identity} predates the campaign charter")
            if created > now + tolerance:
                fail(f"{identity} is future-dated: {created.isoformat()}")
            checked += 1

if checked == 0:
    fail("no canonical created timestamps were found")

print(
    "timestamp-audit: PASS "
    f"({checked} ledger records; charter={charter_created.isoformat()}; "
    f"checked_at={now.isoformat()})"
)
