#!/usr/bin/env python3
"""Repair serde_json's OsStr byte-object paths after rechecking every raw file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--repair-report", type=Path, required=True)
    args = parser.parse_args()
    report_path = args.matrix_dir / "matrix.json"
    original_bytes = report_path.read_bytes()
    report = json.loads(original_bytes)
    checks = []
    for label, record in sorted(report["files"].items()):
        encoded = record["path"]
        if isinstance(encoded, dict) and list(encoded) == ["Unix"]:
            name = bytes(encoded["Unix"]).decode("utf-8")
        elif isinstance(encoded, str):
            name = encoded
        else:
            raise ValueError(f"unsupported path encoding for {label}: {encoded!r}")
        if Path(name).name != name:
            raise ValueError(f"raw path is not a filename: {name}")
        path = args.matrix_dir / name
        actual_bytes = path.stat().st_size
        actual_sha = sha256(path)
        if actual_bytes != int(record["bytes"]) or actual_sha != record["sha256"]:
            raise ValueError(f"raw file custody mismatch: {path}")
        record["path"] = name
        checks.append({"label": label, "path": name, "bytes": actual_bytes, "sha256": actual_sha})
    repaired_bytes = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    temporary = report_path.with_suffix(".json.repaired.tmp")
    with temporary.open("xb") as stream:
        stream.write(repaired_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, report_path)
    custody = {
        "schema": "max11-sparse-matrix-report-repair-v1",
        "verdict": "PASS",
        "scope": "report-only Unix filename serialization; no matrix bytes changed",
        "original_matrix_report_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "repaired_matrix_report_sha256": hashlib.sha256(repaired_bytes).hexdigest(),
        "raw_files_verified_numerator": len(checks),
        "raw_files_verified_denominator": len(checks),
        "raw_files": checks,
        "no_claim": "Repairing report path strings is not an LP result or an exact identity.",
    }
    args.repair_report.write_text(json.dumps(custody, indent=2, sort_keys=True) + "\n")
    print(json.dumps(custody, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
