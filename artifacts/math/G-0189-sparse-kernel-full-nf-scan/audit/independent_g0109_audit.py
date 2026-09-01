#!/usr/bin/env python3
"""Independent G-0109 replay of the G-0189 mass-four sparse relations.

This deliberately does not import or execute the G-0179 normal-form library or
the G-0189 scanner.  It reconstructs the frozen 92-record input, asks the older
G-0109 executable for complete normal forms, and aggregates the 17 relations
again in Python exact integers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path("/data/projects/relu-depth-frontier-research")
CANDIDATE = ROOT / "artifacts/math/G-0187-exact-sparse-kernel-basis/candidate/exact_sparse_left_kernel_basis_v1.jsonl"
STAR = ROOT / "artifacts/math/G-0179-star-loop-quarantine/star_outside_primary_records.json"
G0179_HINGE_RECEIPT = ROOT / "artifacts/math/G-0179-star-loop-quarantine/results/hinge5771_producer_receipt.json"
G0189_RESULT = ROOT / "artifacts/math/G-0189-sparse-kernel-full-nf-scan/results/registered_scan_v1.json"
G0109_SOURCE = ROOT / "artifacts/math/G-0109/src/main.rs"
G0109_BINARY = ROOT / "artifacts/math/G-0109/target/release/g0109-normal-form-probe"
G0113_SOURCE = ROOT / "artifacts/math/G-0113/degree5_quotient_census.py"

INPUT = Path("/tmp/g0193_g0109_92_input.json")
OUTPUT = Path("/tmp/g0193_g0109_92_output.json")
RECEIPT = Path("/tmp/g0193_g0189_independent_audit_receipt.json")

EXPECTED = {
    CANDIDATE: "24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe",
    STAR: "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    G0179_HINGE_RECEIPT: "cf6ba0b568c67d0a18d273695b8f09515bab7089510b9de0ed9afd6bb6fc6e23",
    G0189_RESULT: "e90a79984c0dd7c582ca9dbbcb7f73b08c0c1505d0597bfcd98d44361ded8005",
    G0109_SOURCE: "dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126",
    G0109_BINARY: "e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426",
    G0113_SOURCE: "e0cb483d383021cba14730a4cac5b3f4c401106291b37f318233158ce3178edd",
}
EXCLUDED = {1548, 3140, 4259, 5656}
EXPECTED_COLUMNS = [12, 15, 17, 21, 24, 28, 68, 72, 75, 82, 87, 90, 91, 108, 117, 121, 122]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object, *, newline: bool = False, sort_keys: bool = True) -> bytes:
    suffix = "\n" if newline else ""
    return (json.dumps(value, sort_keys=sort_keys, separators=(",", ":"), ensure_ascii=True) + suffix).encode("ascii")


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(canonical_bytes(value, newline=True))
        handle.flush()
        os.fsync(handle.fileno())


def load_g0113():
    spec = importlib.util.spec_from_file_location("g0193_frozen_g0113", G0113_SOURCE)
    require(spec is not None and spec.loader is not None, "cannot import G-0113 producer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compact_from_pair(module, pair):
    negative, positive = module.cancelled_pair(pair)
    support = sorted({vertex for side in (negative, positive) for edge in side for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(support)}
    compact = lambda side: [[relabel[u], relabel[v]] for u, v in side]
    return {
        "signed_mass": len(negative),
        "active_vertices": len(support),
        "negative_loop_count": sum(u == v for u, v in negative),
        "positive_loop_count": sum(u == v for u, v in positive),
        "negative_edges": compact(negative),
        "positive_edges": compact(positive),
        "original_active_labels": support,
        "cancelled_signed_pair": module.serialize_pair((negative, positive)),
    }


def parse_relations():
    with CANDIDATE.open(encoding="ascii") as handle:
        header = json.loads(next(handle))
        relations = [json.loads(line) for line in handle]
    require(header["basis_shape"] == [5769, 478], "candidate basis shape drift")
    require(header["matrix_shape"] == [5769, 6795], "candidate matrix shape drift")
    require(len(relations) == 478, "candidate relation count drift")
    for index, relation in enumerate(relations):
        require(relation["basis_column"] == index, f"basis order drift at {index}")
        require(relation["support"] == len(relation["terms"]), f"support drift at {index}")
    return relations


def aggregate(relation, forms_by_sequence):
    linear = [0] * 11
    hinges = defaultdict(int)
    for _row, sequence, coefficient_text in relation["terms"]:
        coefficient = int(coefficient_text)
        form = forms_by_sequence[sequence]
        for rank, value in enumerate(form["linear"]):
            linear[rank] += coefficient * int(value)
        for hinge in form["hinges"]:
            hinges[tuple(hinge["direction"])] += coefficient * int(hinge["coefficient"])
    return linear, dict(sorted((direction, value) for direction, value in hinges.items() if value))


def residual_binding(linear, hinges):
    return {
        "linear": [str(value) for value in linear],
        "hinges": [
            {"direction": list(direction), "coefficient": str(coefficient)}
            for direction, coefficient in hinges.items()
        ],
    }


def main() -> int:
    require(sys.flags.optimize == 0, "optimized Python prohibited")
    for path, expected in EXPECTED.items():
        require(sha256_path(path) == expected, f"input hash drift: {path}")
    require(not INPUT.exists() and not OUTPUT.exists() and not RECEIPT.exists(), "refusing to overwrite audit artifacts")

    star_document = json.loads(STAR.read_text(encoding="ascii"))
    hinge_receipt = json.loads(G0179_HINGE_RECEIPT.read_text(encoding="ascii"))
    g0189 = json.loads(G0189_RESULT.read_text(encoding="ascii"))
    require(star_document["schema"] == "g0179.star-outside-primary-loop-records.v1", "STAR schema drift")
    records = star_document["records"]
    require(len(records) == 5773, "STAR record count drift")
    require(all(record["sequence"] == index for index, record in enumerate(records)), "STAR sequence order drift")
    require(hinge_receipt["bindings"]["records_sha256"] == EXPECTED[STAR], "G-0179 receipt/file binding drift")
    manifest = hashlib.sha256()
    for record in records:
        manifest.update(canonical_bytes(record, newline=True))
    require(manifest.hexdigest() == star_document["canonical_record_manifest_sha256"], "full G-0179 record manifest drift")

    retained = [record for record in records if record["sequence"] not in EXCLUDED]
    require(len(retained) == 5769, "retained record count drift")
    relations = parse_relations()
    for relation in relations:
        for row, sequence, _coefficient in relation["terms"]:
            require(retained[row]["sequence"] == sequence, f"row/sequence mismatch at column {relation['basis_column']}")
    selected = [
        relation
        for relation in relations
        if relation["support"] <= 6 and all(retained[row]["signed_mass"] == 4 for row, _sequence, _coefficient in relation["terms"])
    ]
    require([relation["basis_column"] for relation in selected] == EXPECTED_COLUMNS, "selected columns drift")
    require(sum(len(relation["terms"]) for relation in selected) == 102, "incidence count drift")
    unique_sequences = sorted({sequence for relation in selected for _row, sequence, _coefficient in relation["terms"]})
    require(len(unique_sequences) == 92, "unique sequence count drift")

    # Rebuild every selected record's semantics from the frozen G-0113 source term
    # and STAR descriptor.  This is stronger than trusting the compact edge fields.
    module = load_g0113()
    terms = module.load_terms()
    record_audit = []
    for sequence in unique_sequences:
        record = records[sequence]
        descriptor_json = record["star_representative"]
        descriptor = (
            int(descriptor_json["source_term"]),
            tuple(map(int, descriptor_json["left_added_edge"])),
            tuple(map(int, descriptor_json["right_added_edge"])),
        )
        pair = module.pair_from_descriptor(terms, descriptor)
        require(module.serialize_pair(pair) == record["representative_pair"], f"representative-pair mismatch q{sequence}")
        compact = compact_from_pair(module, pair)
        for field, value in compact.items():
            require(record[field] == value, f"compact semantic mismatch q{sequence} field {field}")
        certificate_hash = hashlib.sha256(module.signed_certificate(pair)).hexdigest()
        require(certificate_hash == record["signed_class_sha256"], f"certificate hash mismatch q{sequence}")
        loop_flags = [edge[0] == edge[1] for edge in descriptor[1:]]
        require(loop_flags.count(True) == 1 and descriptor[1] != descriptor[2], f"STAR addition semantic drift q{sequence}")
        required_projection = {
            "sequence": record["sequence"],
            "signed_mass": record["signed_mass"],
            "active_vertices": record["active_vertices"],
            "negative_edges": record["negative_edges"],
            "positive_edges": record["positive_edges"],
            "negative_loop_count": record["negative_loop_count"],
            "positive_loop_count": record["positive_loop_count"],
        }
        record_audit.append({
            "sequence": sequence,
            "signed_class_sha256": certificate_hash,
            "full_record_canonical_sha256": hashlib.sha256(canonical_bytes(record, newline=True)).hexdigest(),
            "g0109_projection_sha256": hashlib.sha256(canonical_bytes(required_projection, newline=True)).hexdigest(),
        })

    helper_input = {
        "schema": "max11-g0109-normal-form-input-v1",
        "records": [records[sequence] for sequence in unique_sequences],
    }
    write_exclusive(INPUT, helper_input)
    started = time.perf_counter()
    completed = subprocess.run([str(G0109_BINARY), str(INPUT), str(OUTPUT)], cwd=ROOT, check=False, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    require(completed.returncode == 0, f"G-0109 failed: {completed.stderr[-4000:]}")

    helper = json.loads(OUTPUT.read_text(encoding="ascii"))
    require(helper["schema"] == "max11-g0109-normal-form-probe-v1", "G-0109 output schema drift")
    forms = helper["normal_forms"]
    require([form["sequence"] for form in forms] == unique_sequences, "G-0109 form order drift")
    require(len(forms) == 92, "G-0109 form count drift")
    forms_by_sequence = {form["sequence"]: form for form in forms}

    expected_bindings = {item["sequence"]: item for item in g0189["normal_forms"]["bindings"]}
    normal_form_checks = []
    for form in forms:
        sequence = form["sequence"]
        require(form["hinge_direction_count"] == len(form["hinges"]), f"hinge count drift q{sequence}")
        require(len({tuple(item["direction"]) for item in form["hinges"]}) == len(form["hinges"]), f"duplicate direction q{sequence}")
        # Preserve the Rust struct's JSON field order, matching serde_json::to_vec.
        observed_hash = hashlib.sha256(canonical_bytes(form, sort_keys=False)).hexdigest()
        expected_binding = expected_bindings[sequence]
        require(observed_hash == expected_binding["normal_form_sha256"], f"G-0109/G-0179 normal-form hash mismatch q{sequence}")
        require(form["active_vertices"] == expected_binding["active_vertices"], f"active count mismatch q{sequence}")
        require(form["hinge_direction_count"] == expected_binding["hinge_direction_count"], f"hinge census mismatch q{sequence}")
        normal_form_checks.append({
            "sequence": sequence,
            "canonical_json_sha256": observed_hash,
            "hinge_direction_count": form["hinge_direction_count"],
        })

    expected_relations = {item["basis_column"]: item for item in g0189["relations"]}
    relation_checks = []
    for relation in selected:
        column = relation["basis_column"]
        require(relation["support"] == 6, f"support drift column {column}")
        require(all(int(term[2]) in (-1, 1) for term in relation["terms"]), f"coefficient drift column {column}")
        linear, hinges = aggregate(relation, forms_by_sequence)
        binding = residual_binding(linear, hinges)
        binding_hash = hashlib.sha256(canonical_bytes(binding, sort_keys=False)).hexdigest()
        expected_result = expected_relations[column]
        require(binding_hash == expected_result["complete_residual_sha256"], f"residual hash mismatch column {column}")
        require(linear == [0] * 11, f"nonzero linear residual column {column}")
        require(not hinges, f"nonzero hinge residual column {column}")
        relation_checks.append({
            "basis_column": column,
            "terms": [[sequence, int(coefficient)] for _row, sequence, coefficient in relation["terms"]],
            "complete_residual_sha256": binding_hash,
            "linear_zero": True,
            "hinges_zero": True,
        })

    # Hostile control: add one extra copy of the first atom q235 to column 12.
    first = selected[0]
    require(first["basis_column"] == 12 and first["terms"][0][1] == 235, "hostile target drift")
    mutant = json.loads(json.dumps(first))
    mutant["terms"][0][2] = str(int(mutant["terms"][0][2]) + 1)
    mutant_linear, mutant_hinges = aggregate(mutant, forms_by_sequence)
    atom = forms_by_sequence[235]
    atom_hinges = {tuple(item["direction"]): int(item["coefficient"]) for item in atom["hinges"]}
    require(mutant_linear == [int(value) for value in atom["linear"]], "hostile mutant linear delta mismatch")
    require(mutant_hinges == atom_hinges, "hostile mutant hinge delta mismatch")
    require(len(mutant_hinges) > 0 and any(mutant_linear), "hostile mutant not detected")
    d0_nonzero = sum(direction[0] != 0 for direction in mutant_hinges)
    require(d0_nonzero == g0189["hostile_plus_one_control"]["mutant_d0_not_zero_hinges"], "hostile d0 census mismatch")

    receipt = {
        "schema": "g0193.g0189-independent-g0109-full-normal-form-audit.v1",
        "result": "GO_INDEPENDENT_EXACT_REPLAY_CONFIRMS_ALL_17_GLOBAL_IDENTITIES",
        "claim_boundary": "Exact finite replay of 17 frozen six-term relations using the historical G-0109 evaluator. This certifies these 17 linear combinations vanish as complete symmetrized piecewise-linear functions; it does not generalize the pattern, prove novelty, or settle MAX11.",
        "bindings": {
            "inputs_opening_sha256": {str(path): expected for path, expected in EXPECTED.items()},
            "g0179_canonical_record_manifest_sha256": star_document["canonical_record_manifest_sha256"],
            "g0179_ordered_exact_certificate_bytes_sha256": star_document["ordered_exact_certificate_bytes_sha256"],
            "g0109_input": {"path": str(INPUT), "bytes": INPUT.stat().st_size, "sha256": sha256_path(INPUT)},
            "g0109_output": {"path": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "sha256": sha256_path(OUTPUT)},
            "all_inputs_rehashed_unchanged_at_end": all(sha256_path(path) == expected for path, expected in EXPECTED.items()),
        },
        "selection": {
            "basis_columns": EXPECTED_COLUMNS,
            "relation_count": len(selected),
            "term_incidences": sum(len(relation["terms"]) for relation in selected),
            "unique_record_count": len(unique_sequences),
            "unique_sequences": unique_sequences,
        },
        "record_custody": {
            "literal_row_to_sequence_matches": 102,
            "full_G0179_manifest_recomputed": True,
            "selected_G0113_representative_pairs_recomputed": len(record_audit),
            "selected_compact_semantics_recomputed": len(record_audit),
            "selected_signed_certificate_hashes_recomputed": len(record_audit),
            "records": record_audit,
        },
        "normal_form_cross_evaluator": {
            "historical_g0109_form_count": len(forms),
            "all_92_canonical_forms_match_G0179_hashes": True,
            "records": normal_form_checks,
        },
        "relations": {
            "all_17_exact_linear_residuals_zero": True,
            "all_17_exact_full_hinge_residuals_zero": True,
            "independent_relation_count": 17,
            "checks": relation_checks,
        },
        "hostile_plus_one_control": {
            "mutation": "add one copy of q235 to basis column 12",
            "mutant_full_residual_equals_q235_normal_form": True,
            "mutant_nonzero_hinges": len(mutant_hinges),
            "mutant_d0_not_zero_hinges": d0_nonzero,
            "mutant_linear": mutant_linear,
            "rejected": True,
        },
        "environment": {
            "wall_seconds_g0109": elapsed,
            "python": sys.version,
            "g0109_stdout": completed.stdout,
            "g0109_stderr": completed.stderr,
        },
    }
    write_exclusive(RECEIPT, receipt)
    require(all(sha256_path(path) == expected for path, expected in EXPECTED.items()), "input changed during audit")
    print(json.dumps({
        "result": receipt["result"],
        "input_sha256": sha256_path(INPUT),
        "output_sha256": sha256_path(OUTPUT),
        "receipt_sha256": sha256_path(RECEIPT),
        "receipt_bytes": RECEIPT.stat().st_size,
        "source_sha256": sha256_path(Path(__file__)),
        "g0109_wall_seconds": elapsed,
        "mutant_nonzero_hinges": len(mutant_hinges),
        "mutant_d0_not_zero_hinges": d0_nonzero,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
