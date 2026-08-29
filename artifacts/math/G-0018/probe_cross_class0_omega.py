#!/usr/bin/env python3
"""Evaluate G-0011 Omega on exactly one G-0009 cross representative.

The only evaluated candidate is frozen cross quotient class 0.  The selected
hinge/linear column is reconstructed with the independently reviewed G-0014
semantic functions in one sequential process.  The script refuses to start
unless MemAvailable is at least 10 GiB and RLIMIT_AS is finite and at most
4 GiB.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
from math import lcm
from pathlib import Path
import resource
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
CROSS_CLASSES = ROOT / "artifacts/math/G-0009/cross_component_classes.json"
SELECTION = ROOT / "artifacts/math/G-0008/cut_selection_01_02_03_04.json"
DUAL = ROOT / "artifacts/math/G-0011/cut_only_exact_left_dual_v1.json.gz"
G14_SCRIPT = ROOT / "artifacts/math/G-0014/semantic_matrix_audit.py"
RECONSTRUCTION_HELPER = HERE / "audit_beta2_union_mapping.py"
DEFAULT_OUTPUT = HERE / "cross_class0_omega_probe_v1.json"

N = 11
MIN_AVAILABLE_BYTES = 10 * (1 << 30)
MAX_ADDRESS_SPACE_BYTES = 4 * (1 << 30)
MODULUS = 2_305_843_009_213_693_951  # 2^61 - 1, prime.


class ProbeError(AssertionError):
    pass


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if line.startswith("MemAvailable:"):
            fields = line.split()
            if len(fields) != 3 or fields[2] != "kB":
                raise ProbeError("unexpected MemAvailable encoding")
            return int(fields[1]) * 1024
    raise ProbeError("/proc/meminfo has no MemAvailable line")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def pair_list_sha256(helper, pairs) -> str:
    return sha256_bytes(helper.canonical_bytes(helper.pair_payload(pairs)))


def reconstruct_cross_family(helper, bases):
    pairs = []
    metadata = []
    for base in bases:
        base_index = int(base["base_index"])
        term_index = int(base["term_index"])
        left = tuple(base["left"])
        right = tuple(base["right"])
        parts = tuple(base["components"])
        if len(parts) != 2:
            raise ProbeError("source base does not have two components")
        for left_component, right_component in ((0, 1), (1, 0)):
            for left_endpoint in parts[left_component]:
                for right_endpoint in parts[right_component]:
                    pairs.append(
                        (
                            left + ((left_endpoint, N),),
                            right + ((right_endpoint, N),),
                        )
                    )
                    metadata.append(
                        (
                            base_index,
                            term_index,
                            left_component,
                            right_component,
                            left_endpoint,
                            right_endpoint,
                        )
                    )
    if len(pairs) != 9_200 or len(metadata) != 9_200:
        raise ProbeError(f"cross reconstruction census changed: {len(pairs)}")
    return pairs, metadata


def validate_tree(pair) -> dict[str, object]:
    edges = tuple(pair[0]) + tuple(pair[1])
    if len(edges) != 10 or len(set(edges)) != 10 or any(a == b for a, b in edges):
        raise ProbeError("cross class-0 representative is not a simple ten-edge union")
    vertices = {vertex for edge in edges for vertex in edge}
    if vertices != set(range(1, 12)):
        raise ProbeError("cross class-0 representative is not full-support")
    adjacency = {vertex: set() for vertex in vertices}
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    seen = set()
    stack = [1]
    while stack:
        vertex = stack.pop()
        if vertex in seen:
            continue
        seen.add(vertex)
        stack.extend(adjacency[vertex] - seen)
    if seen != vertices or len(edges) != len(vertices) - 1:
        raise ProbeError("cross class-0 representative is not a tree")
    return {
        "loopless": True,
        "simple_union": True,
        "active_vertices": len(vertices),
        "union_edges": len(edges),
        "connected": True,
        "tree": True,
    }


def zero_based_pair(pair):
    return tuple(
        tuple((a - 1, b - 1) for a, b in side)
        for side in pair
    )


def load_dual() -> dict[str, object]:
    with gzip.open(DUAL, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if value.get("rank") != 5269 or value.get("candidate_columns") != 9804:
        raise ProbeError("G-0011 certificate census changed")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    started = time.perf_counter()
    available_at_start = mem_available_bytes()
    if available_at_start < MIN_AVAILABLE_BYTES:
        raise SystemExit(
            f"ABORT: MemAvailable={available_at_start} below {MIN_AVAILABLE_BYTES}"
        )
    address_soft, address_hard = resource.getrlimit(resource.RLIMIT_AS)
    if address_soft == resource.RLIM_INFINITY or address_soft > MAX_ADDRESS_SPACE_BYTES:
        raise SystemExit(
            f"ABORT: RLIMIT_AS soft={address_soft}; launch under <=4GiB external cap"
        )

    helper = load_module("g0018_mapping_helper", RECONSTRUCTION_HELPER)
    g14 = load_module("g0014_reviewed_semantics", G14_SCRIPT)

    certificate_sha = sha256_path(CERTIFICATE)
    certificate = helper.load_json(CERTIFICATE)
    bases, _rejected, _term_count = helper.reconstruct_bases(certificate)
    cross_pairs, cross_metadata = reconstruct_cross_family(helper, bases)
    cross_metadata_sha = sha256_bytes(helper.canonical_bytes(cross_metadata))
    cross_pair_sha = pair_list_sha256(helper, cross_pairs)

    classes = helper.load_json(CROSS_CLASSES)
    expected_class_bindings = {
        "schema": "max11-cross-component-lifts-isomorphism-v1",
        "n": N,
        "raw_candidate_count": 9_200,
        "class_count": 3_615,
        "source_certificate_sha256": certificate_sha,
        "candidate_metadata_sha256": cross_metadata_sha,
        "raw_pair_list_sha256": cross_pair_sha,
    }
    for key, expected in expected_class_bindings.items():
        if classes.get(key) != expected:
            raise ProbeError(f"cross quotient binding mismatch: {key}")
    representatives = classes.get("representative_raw_indices")
    raw_to_class = classes.get("raw_to_class")
    if not isinstance(representatives, list) or len(representatives) != 3_615:
        raise ProbeError("cross representative list malformed")
    if not isinstance(raw_to_class, list) or len(raw_to_class) != 9_200:
        raise ProbeError("cross raw-to-class map malformed")
    raw_index = int(representatives[0])
    if not 0 <= raw_index < len(cross_pairs) or raw_to_class[raw_index] != 0:
        raise ProbeError("cross class 0 representative is malformed")
    pair_one_based = cross_pairs[raw_index]
    pair_metadata = cross_metadata[raw_index]
    topology = validate_tree(pair_one_based)
    pair = zero_based_pair(pair_one_based)

    selection = helper.load_json(SELECTION)
    directions = g14.validate_selection(selection)
    if len(directions) != 7_135:
        raise ProbeError("selected direction census changed")
    direction_to_row = {
        tuple(map(int, direction)): row for row, direction in enumerate(directions)
    }

    column_started = time.perf_counter()
    words = g14.dp_direction_words(pair, N)
    distinct_words = len(words)
    permutation_multiplicity = sum(words.values())
    if permutation_multiplicity != 39_916_800:
        raise ProbeError("direction-word multiplicities do not sum to 11!")
    hinges = g14.hinge_histogram(words)
    del words
    all_hinges = len(hinges)
    linear = g14.linear_coefficients(pair, N, hinges)
    if len(linear) != N:
        raise ProbeError("linear coordinate census changed")
    column = np.zeros(len(directions) + N, dtype=np.int64)
    for direction, coefficient in hinges.items():
        if type(coefficient) is not int or coefficient <= 0:
            raise ProbeError("hinge histogram contains a nonpositive/noninteger coefficient")
        row = direction_to_row.get(direction)
        if row is not None:
            column[row] = coefficient
    column[-N:] = np.asarray(linear, dtype=np.int64)
    column_seconds = time.perf_counter() - column_started
    if column.shape != (7_146,) or column.dtype != np.int64:
        raise ProbeError(f"wrong generated column: {column.shape} {column.dtype}")

    dual = load_dual()
    if dual.get("selection_sha256") != sha256_path(SELECTION):
        raise ProbeError("dual/selection binding mismatch")
    pivot_rows = [int(value) for value in dual["pivot_cut_rows"]]
    divisors = [int(value) for value in dual["primitive_pivot_row_divisors"]]
    numerators = [int(value) for value in dual["primitive_solution_numerators"]]
    denominator = int(dual["primitive_solution_common_denominator"])
    failing_row = int(dual["failing_cut_row"])
    failing_divisor = int(dual["primitive_failing_row_divisor"])
    if not (
        len(pivot_rows) == len(divisors) == len(numerators) == 5_269
        and failing_row == 7_145
        and failing_divisor == 4
        and all(divisor > 0 for divisor in divisors)
    ):
        raise ProbeError("dual support/normalisation malformed")
    scale = lcm(*divisors, failing_divisor)
    if scale != 3_628_800:
        raise ProbeError(f"unexpected integer scale: {scale}")

    omega = sum(
        numerator * (scale // divisor) * int(column[row])
        for row, divisor, numerator in zip(pivot_rows, divisors, numerators)
    )
    omega += denominator * (scale // failing_divisor) * int(column[failing_row])
    omega_mod_direct = sum(
        (numerator % MODULUS)
        * ((scale // divisor) % MODULUS)
        * (int(column[row]) % MODULUS)
        for row, divisor, numerator in zip(pivot_rows, divisors, numerators)
    ) % MODULUS
    omega_mod_direct = (
        omega_mod_direct
        + (denominator % MODULUS)
        * ((scale // failing_divisor) % MODULUS)
        * (int(column[failing_row]) % MODULUS)
    ) % MODULUS
    if omega_mod_direct != omega % MODULUS:
        raise ProbeError("exact and modular Omega evaluations disagree")

    nonzero = omega != 0
    conclusion = (
        "This one exact nonzero cross column proves only that the current G-0011 "
        "functional does not annihilate the G8-union-cross candidate family. It "
        "does not decide target membership in that union or any broader family."
        if nonzero
        else
        "The current G-0011 functional vanishes on this one deterministic cross "
        "sample. This is not evidence of exhaustive cross-family annihilation."
    )

    elapsed = time.perf_counter() - started
    maximum_rss_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    result = {
        "schema": "g0011-omega-single-cross-class-probe-v1",
        "result": "NONZERO" if nonzero else "ZERO_ON_ONE_SAMPLE",
        "script": relative(Path(__file__)),
        "script_sha256": sha256_path(Path(__file__)),
        "inputs": [
            {"path": relative(CERTIFICATE), "sha256": certificate_sha},
            {"path": relative(CROSS_CLASSES), "sha256": sha256_path(CROSS_CLASSES)},
            {"path": relative(SELECTION), "sha256": sha256_path(SELECTION)},
            {"path": relative(DUAL), "sha256": sha256_path(DUAL)},
            {"path": relative(G14_SCRIPT), "sha256": sha256_path(G14_SCRIPT)},
            {
                "path": relative(RECONSTRUCTION_HELPER),
                "sha256": sha256_path(RECONSTRUCTION_HELPER),
            },
        ],
        "resource_gate": {
            "minimum_mem_available_bytes": MIN_AVAILABLE_BYTES,
            "mem_available_at_start_bytes": available_at_start,
            "rlimit_as_soft_bytes": address_soft,
            "rlimit_as_hard_bytes": address_hard,
            "external_cap_at_most_4gib": address_soft <= MAX_ADDRESS_SPACE_BYTES,
            "single_process": True,
            "sequential": True,
            "maximum_rss_kib": maximum_rss_kib,
            "column_seconds": round(column_seconds, 6),
            "total_seconds": round(elapsed, 6),
        },
        "scope": {
            "evaluated_cross_representative_count": 1,
            "evaluated_cross_class_indices": [0],
            "family_scan_performed": False,
            "g0014_modified": False,
        },
        "cross_representative": {
            "class_index": 0,
            "raw_index": raw_index,
            "metadata": list(pair_metadata),
            "pair_one_based": helper.pair_payload([pair_one_based])[0],
            "topology": topology,
            "reconstructed_raw_family_count_for_binding_only": len(cross_pairs),
            "reconstructed_metadata_sha256": cross_metadata_sha,
            "reconstructed_pair_list_sha256": cross_pair_sha,
        },
        "column": {
            "semantics": (
                "rows 0..7134 are the frozen selected primitive active hinge "
                "coefficients; rows 7135..7145 are ordered-cone linear ranks 0..10"
            ),
            "shape": list(column.shape),
            "dtype": str(column.dtype),
            "int64_c_sha256": sha256_bytes(column.tobytes(order="C")),
            "selected_direction_count": len(directions),
            "linear_coordinate_count": N,
            "selected_hinge_nonzero_count": int(np.count_nonzero(column[:-N])),
            "column_nonzero_count": int(np.count_nonzero(column)),
            "distinct_direction_word_count": distinct_words,
            "direction_word_permutation_multiplicity": permutation_multiplicity,
            "complete_primitive_hinge_count": all_hinges,
            "linear_coordinates": list(map(int, linear)),
            "minimum_entry": int(column.min()),
            "maximum_entry": int(column.max()),
        },
        "omega": {
            "integer_scaling_lcm": scale,
            "exact_integer_decimal": str(omega),
            "sign": 1 if omega > 0 else (-1 if omega < 0 else 0),
            "absolute_bit_length": abs(omega).bit_length(),
            "nonzero": nonzero,
            "modulus": MODULUS,
            "residue": omega_mod_direct,
            "residue_nonzero": omega_mod_direct != 0,
            "exact_modular_agreement": True,
        },
        "conclusion": conclusion,
        "claim_boundary": (
            "Exactly one deterministic cross quotient representative was evaluated. "
            "A nonzero result falsifies annihilation of the G8-union-cross family by "
            "this particular dual only; a zero result would concern one sample only."
        ),
    }

    raw = canonical_bytes(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as destination:
        destination.write(raw)
    print(
        f"{result['result']} output={args.output} bytes={len(raw)} "
        f"sha256={sha256_bytes(raw)} omega_bits={abs(omega).bit_length()} "
        f"residue={omega_mod_direct} max_rss_kib={maximum_rss_kib} "
        f"seconds={elapsed:.3f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
