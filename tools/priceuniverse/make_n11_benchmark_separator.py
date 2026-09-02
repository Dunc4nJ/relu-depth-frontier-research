#!/usr/bin/env python3
"""Make a deterministic large-integer n=11 separator-shaped benchmark input."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    # Padding on the right preserves zero sum and canonical first-nonzero sign.
    hinges = {f"{key},0,0": value for key, value in source["hinge_weights"].items()}
    payload = {
        "schema": "max11-exact-sketch-separator-v1",
        "method": "deterministic n=9 separator padding for n=11 throughput control",
        "n": 11,
        "subject": "G-0027 throughput control only",
        "linear_weights": [*source["linear_weights"], "0", "1/304819200"],
        "hinge_weights": hinges,
        "no_claim": "This separator-shaped input is a throughput control and has no MAX11 mathematical standing.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
