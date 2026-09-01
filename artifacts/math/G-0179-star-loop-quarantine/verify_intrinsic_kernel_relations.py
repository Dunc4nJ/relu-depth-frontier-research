#!/usr/bin/env python3
"""Certify the two intrinsic G-0179 row relations by two exact evaluators."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from typing import Any


EXPECTED = {
    "primary_records": "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    "star_records": "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    "g0109_source": "dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126",
    "g0109_binary": "e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426",
    "g0179_lib_source": "8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73",
    "g0179_main_source": "128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2",
    "g0179_binary": "ba629a044408e170235523a6f578c55d3201d7be37bb07acf86e27d409a00824",
}
PRIMARY_SEQUENCES = (15_947, 22_121, 36_968)
STAR_SEQUENCES = (22, 2_986, 3_140, 5_656)


class RelationError(RuntimeError):
    """An exact relation or custody invariant failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def selected_record(record: dict[str, Any], loopless: bool) -> dict[str, Any]:
    return {
        "sequence": int(record["sequence"]),
        "signed_mass": int(record["signed_mass"]),
        "active_vertices": int(record["active_vertices"]),
        "negative_loop_count": 0 if loopless else int(record["negative_loop_count"]),
        "positive_loop_count": 0 if loopless else int(record["positive_loop_count"]),
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
    }


def run_probe(
    binary: Path, probe_input: Path, output: Path, *, needs_probe_subcommand: bool
) -> dict[str, Any]:
    command = [str(binary)]
    if needs_probe_subcommand:
        command.append("probe")
    command.extend([str(probe_input), str(output)])
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RelationError(
            f"probe {binary.name} failed ({completed.returncode})\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if completed.stdout or completed.stderr:
        raise RelationError(f"probe {binary.name} emitted unexpected output")
    return json.loads(output.read_bytes())


def semantic(form: dict[str, Any]) -> tuple[tuple[int, ...], dict[tuple[int, ...], int]]:
    linear = tuple(map(int, form["linear"]))
    hinges = {
        tuple(map(int, item["direction"])): int(item["coefficient"])
        for item in form["hinges"]
    }
    if len(linear) != 11 or len(hinges) != len(form["hinges"]):
        raise RelationError("normal-form semantic census drift")
    return linear, hinges


def semantic_digest(
    linear: tuple[int, ...], hinges: dict[tuple[int, ...], int]
) -> str:
    digest = hashlib.sha256()
    for value in linear:
        digest.update(struct.pack("<q", value))
    for direction, coefficient in sorted(hinges.items()):
        digest.update(bytes(value & 0xFF for value in direction))
        digest.update(struct.pack("<q", coefficient))
    return digest.hexdigest()


def combine(
    forms: dict[int, tuple[tuple[int, ...], dict[tuple[int, ...], int]]],
    terms: dict[int, int],
) -> tuple[tuple[int, ...], dict[tuple[int, ...], int], int]:
    linear = [0] * 11
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    union: set[tuple[int, ...]] = set()
    for sequence, coefficient in terms.items():
        source_linear, source_hinges = forms[sequence]
        for index, value in enumerate(source_linear):
            linear[index] += coefficient * value
        union.update(source_hinges)
        for direction, value in source_hinges.items():
            hinges[direction] += coefficient * value
    return tuple(linear), {key: value for key, value in hinges.items() if value}, len(union)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-records", required=True, type=Path)
    parser.add_argument("--star-records", required=True, type=Path)
    parser.add_argument("--g0109-source", required=True, type=Path)
    parser.add_argument("--g0109-binary", required=True, type=Path)
    parser.add_argument("--g0179-lib-source", required=True, type=Path)
    parser.add_argument("--g0179-main-source", required=True, type=Path)
    parser.add_argument("--g0179-binary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise RelationError(f"refusing to overwrite {arguments.output}")
    paths = {
        "primary_records": arguments.primary_records.resolve(strict=True),
        "star_records": arguments.star_records.resolve(strict=True),
        "g0109_source": arguments.g0109_source.resolve(strict=True),
        "g0109_binary": arguments.g0109_binary.resolve(strict=True),
        "g0179_lib_source": arguments.g0179_lib_source.resolve(strict=True),
        "g0179_main_source": arguments.g0179_main_source.resolve(strict=True),
        "g0179_binary": arguments.g0179_binary.resolve(strict=True),
    }
    opening = {name: sha256_file(path) for name, path in paths.items()}
    if opening != EXPECTED:
        raise RelationError(f"frozen input hash drift: {opening}")
    if not os.access(paths["g0109_binary"], os.X_OK) or not os.access(
        paths["g0179_binary"], os.X_OK
    ):
        raise RelationError("probe binary is not executable")

    primary_document = json.loads(paths["primary_records"].read_bytes())
    primary_by_sequence = {
        int(record["sequence"]): record for record in primary_document["records"]
    }
    star_document = json.loads(paths["star_records"].read_bytes())
    star_by_sequence = {
        int(record["sequence"]): record for record in star_document["records"]
    }
    records = [
        selected_record(primary_by_sequence[sequence], loopless=True)
        for sequence in PRIMARY_SEQUENCES
    ] + [
        selected_record(star_by_sequence[sequence], loopless=False)
        for sequence in STAR_SEQUENCES
    ]
    if [record["sequence"] for record in records] != list(PRIMARY_SEQUENCES + STAR_SEQUENCES):
        raise RelationError("controlled-record order drift")
    for record in records[: len(PRIMARY_SEQUENCES)]:
        if any(edge[0] == edge[1] for edge in record["negative_edges"] + record["positive_edges"]):
            raise RelationError("loop entered controlled primary record")

    probe_payload = canonical_json(
        {"schema": "max11-g0109-normal-form-input-v1", "records": records}
    )
    with tempfile.TemporaryDirectory(prefix="g0179-intrinsic-relations-") as raw_temp:
        temp = Path(raw_temp)
        probe_input = temp / "input.json"
        probe_input.write_bytes(probe_payload)
        output_0109 = temp / "g0109.json"
        output_0179 = temp / "g0179.json"
        result_0109 = run_probe(
            paths["g0109_binary"],
            probe_input,
            output_0109,
            needs_probe_subcommand=False,
        )
        result_0179 = run_probe(
            paths["g0179_binary"],
            probe_input,
            output_0179,
            needs_probe_subcommand=True,
        )

    forms_0109 = result_0109.get("normal_forms")
    forms_0179 = result_0179.get("normal_forms")
    if forms_0109 != forms_0179 or not isinstance(forms_0109, list):
        raise RelationError("independent normal-form evaluators disagree")
    if [int(form["sequence"]) for form in forms_0109] != [
        record["sequence"] for record in records
    ]:
        raise RelationError("normal-form result order drift")
    semantics = {int(form["sequence"]): semantic(form) for form in forms_0109}

    duplicate_terms = {22: 1, 3_140: -1}
    duplicate_linear, duplicate_hinges, duplicate_union = combine(
        semantics, duplicate_terms
    )
    if any(duplicate_linear) or duplicate_hinges:
        raise RelationError("q22=q3140 identity failed")

    quotient_terms = {2_986: 1, 5_656: -1, 15_947: -2, 22_121: 1, 36_968: 1}
    quotient_linear, quotient_hinges, quotient_union = combine(semantics, quotient_terms)
    if any(quotient_linear) or quotient_hinges:
        raise RelationError("q2986-q5656 primary-span identity failed")

    delta_linear, delta_hinges, delta_union = combine(
        semantics, {2_986: 1, 5_656: -1}
    )
    if len(delta_hinges) != 210 or any(direction[0] != 0 for direction in delta_hinges):
        raise RelationError("delta d0=0 hinge support drift")
    delta_sha256 = semantic_digest(delta_linear, delta_hinges)
    if delta_sha256 != "cfea6be422ca4f0b55d35a674ed129b55c68b0485eab3bf1ada2b3001acd5847":
        raise RelationError("delta semantic digest drift")

    closing = {name: sha256_file(path) for name, path in paths.items()}
    if closing != opening:
        raise RelationError("input changed during relation replay")
    result = {
        "schema": "g0179.intrinsic-kernel-relations.v1",
        "result": "TWO_INTRINSIC_D0_EQ_1_RELATIONS_CERTIFIED_AND_QUOTIENTABLE_MOD_O",
        "claim_boundary": (
            "Exact complete ordered-chamber normal-form identities for seven frozen records. "
            "This proves that q3140 duplicates q22 and that q2986-q5656 lies in the old "
            "primary span O. It does not certify independence of the remaining STAR quotient, "
            "MAX11 membership, ansatz completeness, or a neural-network lower bound."
        ),
        "bindings": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": opening[name]}
            for name, path in paths.items()
        },
        "verifier": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "probe_input": {
            "canonical_json_sha256": hashlib.sha256(probe_payload).hexdigest(),
            "primary_sequences": list(PRIMARY_SEQUENCES),
            "star_sequences": list(STAR_SEQUENCES),
        },
        "independent_evaluators_exactly_agree": True,
        "normal_forms_canonical_json_sha256": hashlib.sha256(
            canonical_json(forms_0109)
        ).hexdigest(),
        "relations": [
            {
                "identity": "q_22 - q_3140 = 0",
                "terms": {"22": 1, "3140": -1},
                "union_hinge_directions": duplicate_union,
                "linear_residual": list(duplicate_linear),
                "nonzero_hinge_residuals": len(duplicate_hinges),
                "interpretation": "exact duplicate function; remove q_3140",
            },
            {
                "identity": "q_2986 - q_5656 = 2*p_15947 - p_22121 - p_36968",
                "terms_moved_to_left": {str(key): value for key, value in quotient_terms.items()},
                "union_hinge_directions": quotient_union,
                "semantic_coordinates": 11 + quotient_union,
                "linear_residual": list(quotient_linear),
                "nonzero_hinge_residuals": len(quotient_hinges),
                "interpretation": "same coset modulo O; remove q_5656",
            },
        ],
        "delta_q2986_minus_q5656": {
            "linear": list(delta_linear),
            "nonzero_hinges": len(delta_hinges),
            "all_nonzero_hinges_have_d0_eq_0": True,
            "union_hinge_directions_before_cancellation": delta_union,
            "semantic_i64_direction_coefficient_sha256": delta_sha256,
        },
        "all_inputs_rehashed_unchanged_at_end": True,
    }
    write_new(arguments.output, canonical_json(result))
    print(
        json.dumps(
            {
                "output": str(arguments.output.resolve()),
                "output_sha256": sha256_file(arguments.output),
                "result": result["result"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verify_intrinsic_kernel_relations: {error}", file=sys.stderr)
        raise SystemExit(1)
