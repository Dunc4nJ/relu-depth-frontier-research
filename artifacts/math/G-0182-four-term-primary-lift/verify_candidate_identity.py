#!/usr/bin/env python3
"""Independently replay the frozen G-0182 identity with two exact evaluators."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


EXPECTED = {
    "candidate": "b345639a47faf6b18d728648f891b913a55a7217a741b9537187da2dd3751d47",
    "primary_records": "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    "star_records": "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    "g0109_source": "dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126",
    "g0109_binary": "e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426",
    "g0179_lib_source": "8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73",
    "g0179_main_source": "128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2",
    "g0179_binary": "ba629a044408e170235523a6f578c55d3201d7be37bb07acf86e27d409a00824",
}
STAR_SEQUENCES = (821, 1_630, 2_986, 3_944)
PRIMARY_SEQUENCES = (11_134, 12_930, 16_701, 22_121, 24_222, 36_968, 122_205)


class VerificationError(RuntimeError):
    """A frozen binding or exact semantic gate failed."""


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
        path.unlink(missing_ok=True)
        raise


def primary_probe_record(record: dict[str, Any]) -> dict[str, Any]:
    if not (record["in_disjoint"] or record["in_shared_distinct"]):
        raise VerificationError("selected primary record lacks primary membership")
    edges = record["negative_edges"] + record["positive_edges"]
    if any(edge[0] == edge[1] for edge in edges):
        raise VerificationError("loop entered a selected old-primary record")
    return {
        "sequence": int(record["sequence"]),
        "signed_mass": int(record["signed_mass"]),
        "active_vertices": int(record["active_vertices"]),
        "negative_loop_count": 0,
        "positive_loop_count": 0,
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
    }


def star_probe_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": int(record["sequence"]),
        "signed_mass": int(record["signed_mass"]),
        "active_vertices": int(record["active_vertices"]),
        "negative_loop_count": int(record["negative_loop_count"]),
        "positive_loop_count": int(record["positive_loop_count"]),
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
    }


def run_probe(binary: Path, probe_input: Path, output: Path, *, subcommand: bool) -> dict[str, Any]:
    command = [str(binary)]
    if subcommand:
        command.append("probe")
    command.extend([str(probe_input), str(output)])
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise VerificationError(
            f"probe failed: {command!r}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if completed.stdout or completed.stderr:
        raise VerificationError(f"probe emitted unexpected output: {command!r}")
    return json.loads(output.read_bytes())


def semantic(form: dict[str, Any]) -> tuple[tuple[int, ...], dict[tuple[int, ...], int]]:
    linear = tuple(map(int, form["linear"]))
    hinges = {
        tuple(map(int, term["direction"])): int(term["coefficient"])
        for term in form["hinges"]
    }
    if len(linear) != 11 or len(hinges) != len(form["hinges"]):
        raise VerificationError("normal-form semantic census drift")
    return linear, hinges


def combine(
    forms: dict[tuple[str, int], tuple[tuple[int, ...], dict[tuple[int, ...], int]]],
    terms: dict[tuple[str, int], int],
) -> tuple[tuple[int, ...], dict[tuple[int, ...], int], int]:
    linear = [0] * 11
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    union: set[tuple[int, ...]] = set()
    for key, coefficient in terms.items():
        source_linear, source_hinges = forms[key]
        for index, value in enumerate(source_linear):
            linear[index] += coefficient * value
        union.update(source_hinges)
        for direction, value in source_hinges.items():
            hinges[direction] += coefficient * value
    return tuple(linear), {direction: value for direction, value in hinges.items() if value}, len(union)


def semantic_digest(linear: tuple[int, ...], hinges: dict[tuple[int, ...], int]) -> str:
    payload = {
        "linear": [str(value) for value in linear],
        "hinges": [
            [list(direction), str(coefficient)]
            for direction, coefficient in sorted(hinges.items())
        ],
    }
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--primary-records", required=True, type=Path)
    parser.add_argument("--star-records", required=True, type=Path)
    parser.add_argument("--g0109-source", required=True, type=Path)
    parser.add_argument("--g0109-binary", required=True, type=Path)
    parser.add_argument("--g0179-lib-source", required=True, type=Path)
    parser.add_argument("--g0179-main-source", required=True, type=Path)
    parser.add_argument("--g0179-binary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise VerificationError(f"refusing to overwrite {args.output}")
    paths = {
        "candidate": args.candidate.resolve(strict=True),
        "primary_records": args.primary_records.resolve(strict=True),
        "star_records": args.star_records.resolve(strict=True),
        "g0109_source": args.g0109_source.resolve(strict=True),
        "g0109_binary": args.g0109_binary.resolve(strict=True),
        "g0179_lib_source": args.g0179_lib_source.resolve(strict=True),
        "g0179_main_source": args.g0179_main_source.resolve(strict=True),
        "g0179_binary": args.g0179_binary.resolve(strict=True),
    }
    opening = {name: sha256_file(path) for name, path in paths.items()}
    if opening != EXPECTED:
        raise VerificationError(f"frozen input hash drift: {opening}")
    if not os.access(paths["g0109_binary"], os.X_OK) or not os.access(
        paths["g0179_binary"], os.X_OK
    ):
        raise VerificationError("probe binary is not executable")

    candidate = json.loads(paths["candidate"].read_bytes())
    expected_left = {sequence: coefficient for sequence, coefficient in candidate["left"]["star"]}
    expected_right = {
        sequence: coefficient for sequence, coefficient in candidate["right"]["primary"]
    }
    if tuple(expected_left) != STAR_SEQUENCES or tuple(expected_right) != PRIMARY_SEQUENCES:
        raise VerificationError("candidate sequence order drift")
    if expected_left != {821: 1, 1_630: -1, 2_986: -1, 3_944: 1}:
        raise VerificationError("STAR coefficient drift")
    if expected_right != {
        11_134: -2,
        12_930: -1,
        16_701: 1,
        22_121: 1,
        24_222: 1,
        36_968: 1,
        122_205: -1,
    }:
        raise VerificationError("primary coefficient drift")

    primary_document = json.loads(paths["primary_records"].read_bytes())
    star_document = json.loads(paths["star_records"].read_bytes())
    primary_by_sequence = {
        int(record["sequence"]): record for record in primary_document["records"]
    }
    star_by_sequence = {int(record["sequence"]): record for record in star_document["records"]}
    if len(primary_by_sequence) != 163_740 or len(star_by_sequence) != 5_773:
        raise VerificationError("source census drift")
    controlled = [
        ("star", sequence, star_probe_record(star_by_sequence[sequence]))
        for sequence in STAR_SEQUENCES
    ] + [
        ("primary", sequence, primary_probe_record(primary_by_sequence[sequence]))
        for sequence in PRIMARY_SEQUENCES
    ]
    probe_payload = canonical_json(
        {
            "schema": "max11-g0109-normal-form-input-v1",
            "records": [record for _, _, record in controlled],
        }
    )
    with tempfile.TemporaryDirectory(prefix="g0182-independent-replay-") as raw_temp:
        temporary = Path(raw_temp)
        probe_input = temporary / "input.json"
        probe_input.write_bytes(probe_payload)
        g0109_output = temporary / "g0109.json"
        g0179_output = temporary / "g0179.json"
        result_0109 = run_probe(
            paths["g0109_binary"], probe_input, g0109_output, subcommand=False
        )
        result_0179 = run_probe(
            paths["g0179_binary"], probe_input, g0179_output, subcommand=True
        )
    forms_0109 = result_0109.get("normal_forms")
    forms_0179 = result_0179.get("normal_forms")
    if not isinstance(forms_0109, list) or forms_0109 != forms_0179:
        raise VerificationError("independent complete-normal-form evaluators disagree")
    if len(forms_0109) != len(controlled):
        raise VerificationError("controlled normal-form census drift")
    if [int(form["sequence"]) for form in forms_0109] != [item[1] for item in controlled]:
        raise VerificationError("controlled normal-form order drift")
    forms = {
        (family, sequence): semantic(form)
        for (family, sequence, _), form in zip(controlled, forms_0109, strict=True)
    }

    left_terms = {("star", sequence): coefficient for sequence, coefficient in expected_left.items()}
    right_terms = {
        ("primary", sequence): coefficient for sequence, coefficient in expected_right.items()
    }
    left_linear, left_hinges, left_union = combine(forms, left_terms)
    right_linear, right_hinges, right_union = combine(forms, right_terms)
    residual_terms = dict(left_terms)
    residual_terms.update({key: -coefficient for key, coefficient in right_terms.items()})
    residual_linear, residual_hinges, residual_union = combine(forms, residual_terms)
    if any(residual_linear) or residual_hinges:
        raise VerificationError("frozen candidate identity has a nonzero exact residual")
    if left_linear != right_linear or left_hinges != right_hinges:
        raise VerificationError("left/right semantic maps disagree despite zero residual")
    if len(left_hinges) != 273 or any(direction[0] != 0 for direction in left_hinges):
        raise VerificationError("four-term loopless residual shape drift")

    mutant_right = dict(right_terms)
    mutant_right[("primary", 11_134)] += 1
    mutant_terms = dict(left_terms)
    mutant_terms.update({key: -coefficient for key, coefficient in mutant_right.items()})
    mutant_linear, mutant_hinges, mutant_union = combine(forms, mutant_terms)
    if not any(mutant_linear) and not mutant_hinges:
        raise VerificationError("p11134 coefficient +1 mutant escaped exact replay")

    closing = {name: sha256_file(path) for name, path in paths.items()}
    if closing != opening:
        raise VerificationError("input changed during exact replay")
    source = Path(__file__).resolve()
    receipt = {
        "schema": "g0182.independent-four-term-primary-lift.v1",
        "result": "FOUR_TERM_STAR_KERNEL_RELATION_CERTIFIED_IN_OLD_PRIMARY_SPAN_O",
        "claim_boundary": (
            "Exact complete ordered-chamber normal-form identity for four frozen STAR records "
            "and seven frozen old-primary records. This proves one G-0181 kernel vector lies "
            "in O; it does not classify the other 477 vectors or settle MAX11 membership."
        ),
        "identity": {
            "left_star": {str(key): value for key, value in expected_left.items()},
            "right_primary": {str(key): value for key, value in expected_right.items()},
        },
        "bindings": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": opening[name]}
            for name, path in paths.items()
        },
        "verifier": {
            "path": str(source),
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
            "python": sys.version,
        },
        "probe_input": {
            "canonical_json_sha256": hashlib.sha256(probe_payload).hexdigest(),
            "controlled_records": [
                {"family": family, "sequence": sequence} for family, sequence, _ in controlled
            ],
        },
        "independent_evaluators_exactly_agree": True,
        "normal_forms_canonical_json_sha256": hashlib.sha256(
            canonical_json(forms_0109)
        ).hexdigest(),
        "exact_semantics": {
            "raw_left_union_hinge_directions": left_union,
            "raw_right_union_hinge_directions": right_union,
            "raw_all_term_union_hinge_directions": residual_union,
            "common_linear": [str(value) for value in left_linear],
            "common_nonzero_hinges": len(left_hinges),
            "all_common_hinges_have_d0_eq_0": True,
            "common_semantic_sha256": semantic_digest(left_linear, left_hinges),
            "residual_linear": [str(value) for value in residual_linear],
            "residual_nonzero_hinges": len(residual_hinges),
        },
        "hostile_control": {
            "mutation": "right-side coefficient of p11134 changed from -2 to -1",
            "mutant_union_hinge_directions": mutant_union,
            "mutant_nonzero_linear_coordinates": sum(value != 0 for value in mutant_linear),
            "mutant_nonzero_hinges": len(mutant_hinges),
            "mutant_semantic_sha256": semantic_digest(mutant_linear, mutant_hinges),
            "rejected": True,
        },
        "all_inputs_rehashed_unchanged_at_end": True,
    }
    write_new(args.output, canonical_json(receipt))
    print(
        json.dumps(
            {
                "result": receipt["result"],
                "output": str(args.output.resolve()),
                "output_sha256": sha256_file(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verify_candidate_identity: {error}", file=sys.stderr)
        raise SystemExit(1)
