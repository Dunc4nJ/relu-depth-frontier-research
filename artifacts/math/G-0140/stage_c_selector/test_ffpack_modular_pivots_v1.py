#!/usr/bin/env python3
"""Asymmetric oracle and hostile-I/O tests for the frozen FFPACK proposer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
SELECTOR_PATH = HERE / "complete_matrix_rank_selector_v1.py"
DEFAULT_BINARY = HERE / "ffpack_modular_pivots_v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_selector() -> Any:
    specification = importlib.util.spec_from_file_location(
        "g0140_stage_c_native_test_selector", SELECTOR_PATH
    )
    require(
        specification is not None and specification.loader is not None,
        "cannot import selector",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def rejected(process: subprocess.CompletedProcess[str], fragment: str) -> None:
    require(
        process.returncode == 2
        and process.stdout == ""
        and fragment in process.stderr,
        f"native hostile case escaped or failed closed incorrectly: {fragment}",
    )


def run(binary: Path) -> None:
    selector = load_selector()
    prime = 101
    threads = 1

    # Each row below is one original M column, i.e. one row of the row-major
    # transpose consumed by FFPACK.  Duplicate zeros plus the asymmetric late
    # pivot make transpose/permutation decoding mistakes observable.
    transpose_rows = [
        [1, 2, 0, 0],
        [0, 0, 0, 0],
        [0, 3, 4, 0],
        [0, 0, 0, 0],
        [5, 1, 7, 0],
        [0, 0, 0, 9],
    ]
    expected = [0, 2, 4, 5]
    oracle = selector.modular_column_proposal(
        column_loader=transpose_rows.__getitem__,
        row_count=4,
        record_count=6,
        prime=prime,
    )
    require(
        oracle["selected_sequences"] == expected,
        "pure-Python modular oracle fixture drift",
    )

    encoded = b"".join(
        struct.pack("<4i", *(value % prime for value in row))
        for row in transpose_rows
    )
    with tempfile.TemporaryDirectory(prefix="g0140-ffpack-self-test-") as raw:
        directory = Path(raw)
        input_path = directory / "fixture.i32le"
        input_path.write_bytes(encoded)
        proposal, execution = selector.invoke_native_proposer(
            binary_path=binary,
            transpose={
                "path": input_path,
                "prime": prime,
                "bytes": len(encoded),
                "i32le_sha256": hashlib.sha256(encoded).hexdigest(),
            },
            row_count=4,
            record_count=6,
            threads=threads,
        )
        require(
            proposal["selected_sequences"] == expected
            and proposal == oracle
            and execution["rank"] == len(expected)
            and execution["role"] == selector.MODULAR_ROLE,
            "FFPACK pivots differ from the independent modular oracle",
        )

        # The successful output already exists, so a second invocation must not
        # reuse or overwrite it.
        collision = subprocess.run(
            [
                str(binary),
                str(input_path),
                str(input_path.with_suffix(".pivots.u32le")),
                "6",
                "4",
                str(prime),
                str(threads),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        rejected(collision, "refusing to overwrite output")

        truncated_path = directory / "truncated.i32le"
        truncated_path.write_bytes(encoded[:-1])
        truncated = subprocess.run(
            [
                str(binary),
                str(truncated_path),
                str(directory / "truncated.u32le"),
                "6",
                "4",
                str(prime),
                str(threads),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        rejected(truncated, "input size/regular-file contract failed")

        noncanonical_path = directory / "noncanonical.i32le"
        noncanonical_path.write_bytes(struct.pack("<i", -1) + encoded[4:])
        noncanonical = subprocess.run(
            [
                str(binary),
                str(noncanonical_path),
                str(directory / "noncanonical.u32le"),
                "6",
                "4",
                str(prime),
                str(threads),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        rejected(noncanonical, "input contains a noncanonical residue")

    print(
        "g0140-ffpack-modular-pivots-self-test: PASS "
        "(asymmetric oracle plus overwrite/truncation/residue controls)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", type=Path, default=DEFAULT_BINARY)
    args = parser.parse_args(argv)
    binary = args.binary.resolve()
    require(binary.is_file() and not binary.is_symlink(), "binary missing or symlinked")
    run(binary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
