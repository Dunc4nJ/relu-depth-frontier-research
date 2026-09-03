#!/usr/bin/env python3
"""Render the RESULT.md verdict tables from the JSON outputs (no transcription)."""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAMES = {"T3": "T3 (finest)", "T2": "T2", "T2b": "T2b", "T1": "T1 (base)",
         "T1s": "T1s", "Tv": "Tv", "Tn": "Tn", "T0": "T0 (planted negative)"}


def rows(report, primes):
    out = []
    for r in report["results"]["h1"] + report["results"]["h2"]:
        m = r["modular"]
        cert = r["certificate"]
        kind = cert.get("kind", "-")
        detail = ""
        if kind == "primal":
            detail = f"primal, support {cert['support_size']}"
        elif kind == "dual":
            detail = f"dual on {cert['support_rows']} rows"
        out.append((r["case"], r["classes"], r["rows"],
                    m[str(primes[0])]["rank_S"], m[str(primes[0])]["rank_S_augmented"],
                    m[str(primes[1])]["rank_S"], m[str(primes[1])]["rank_S_augmented"],
                    r["verdict"], detail))
    return out


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "lift_recursion_9to10.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    primes = report["primes"]
    print(f"| hypothesis / taxonomy | unknowns | rows | rank S (p={primes[0]:,}) | rank [S\\|b] | "
          f"rank S (p={primes[1]:,}) | rank [S\\|b] | verdict | certificate |")
    print("|---|---:|---:|---:|---:|---:|---:|---|---|")
    for case, cls, rws, r1, a1, r2, a2, verdict, detail in rows(report, primes):
        print(f"| {case} | {cls:,} | {rws:,} | {r1:,} | {a1:,} | {r2:,} | {a2:,} | "
              f"{verdict} | {detail} |")


if __name__ == "__main__":
    main()
