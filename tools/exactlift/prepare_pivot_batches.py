#!/usr/bin/env python3
"""Split a stream-rank pivot report into bounded colgen order files.

The synthetic 5L carrier is represented by the single source index immediately
after the real universe.  It is removed from order files and requested through
``max11-colgen emit-universe --include-five-l true`` on its containing batch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pivot-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--sketch-index", type=int, default=0)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")

    report = json.loads(args.pivot_report.read_text())
    if report.get("schema") != "max11-streamrank-pivots-v1":
        raise SystemExit("unexpected pivot-report schema")
    sketch = report["sketches"][args.sketch_index]
    pivots = [int(value) for value in sketch["pivot_columns"]]
    if len(pivots) != int(sketch["rank_a"]):
        raise SystemExit("pivot count does not equal rank_a")
    if int(sketch["rank_augmented"]) != int(sketch["rank_a"]):
        raise SystemExit("augmented rank differs: not a MEMBER pivot report")
    if sketch["verdict"] != "MEMBER":
        raise SystemExit("pivot report verdict is not MEMBER")
    if len(set(pivots)) != len(pivots):
        raise SystemExit("pivot source indices are not unique")
    packed = b"".join(struct.pack("<Q", value) for value in pivots)
    packed_sha = hashlib.sha256(packed).hexdigest()
    if packed_sha != sketch["pivot_columns_u64_le_sha256"]:
        raise SystemExit("pivot source-index SHA-256 mismatch")

    universe_count = 754_017
    synthetic_index = universe_count
    unexpected = [value for value in pivots if not 0 <= value <= synthetic_index]
    if unexpected:
        raise SystemExit(f"pivot source index outside universe: {unexpected[0]}")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    order_dir = args.output_dir / "orders"
    order_dir.mkdir()
    batches = []
    for start in range(0, len(pivots), args.batch_size):
        chunk = pivots[start : start + args.batch_size]
        include_five_l = synthetic_index in chunk
        real_indices = [value for value in chunk if value != synthetic_index]
        order_path = order_dir / f"order-{len(batches):03d}.json"
        order_path.write_text(json.dumps(real_indices, separators=(",", ":")) + "\n")
        batches.append(
            {
                "batch": len(batches),
                "pivot_offset": start,
                "pivot_count": len(chunk),
                "real_count": len(real_indices),
                "include_five_l": include_five_l,
                "order_file": str(order_path),
                "order_file_sha256": sha256(order_path),
            }
        )

    plan = {
        "schema": "max11-exact-pivot-gather-plan-v1",
        "pivot_report": str(args.pivot_report),
        "pivot_report_sha256": sha256(args.pivot_report),
        "pivot_columns_u64_le_sha256": packed_sha,
        "rank_a": int(sketch["rank_a"]),
        "rank_augmented": int(sketch["rank_augmented"]),
        "verdict": sketch["verdict"],
        "universe_count": universe_count,
        "synthetic_five_l_index": synthetic_index,
        "synthetic_five_l_pivot_count": pivots.count(synthetic_index),
        "batch_size": args.batch_size,
        "batch_count": len(batches),
        "batches": batches,
    }
    plan_path = args.output_dir / "gather_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"plan": str(plan_path), **{k: plan[k] for k in (
        "rank_a", "rank_augmented", "batch_count", "synthetic_five_l_pivot_count"
    )}}, sort_keys=True))


if __name__ == "__main__":
    main()
