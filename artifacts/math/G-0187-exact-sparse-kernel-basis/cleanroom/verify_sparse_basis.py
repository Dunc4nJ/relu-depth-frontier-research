#!/usr/bin/env python3
"""Clean replay of the frozen G-0187 sparse left-kernel basis."""

from __future__ import annotations

from array import array
import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import statistics
import subprocess
import sys
import tempfile
from typing import Any


ROWS = 5_769
MATRIX_COLUMNS = 6_795
BASIS_DIMENSION = 478
EXCLUDED = {1_548, 3_140, 4_259, 5_656}
PRIMES = (1_000_003, 1_000_033, 1_000_099, 1_000_037)
EXPECTED = {
    "candidate": "24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe",
    "matrix": "d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd",
    "star_records": "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    "old_basis": "56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232",
    "matrix_rank": "61925993c97c40fac1ced04f374ffa05144026f2c2c8d3a579fa483d2219178a",
}


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_atomic(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


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


def run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, text=True, capture_output=True, env=env, check=False)
    require(
        completed.returncode == 0,
        f"command failed ({completed.returncode}): {command!r}\n{completed.stdout}\n{completed.stderr}",
    )
    return completed


def zero_sha256(byte_count: int) -> str:
    digest = hashlib.sha256()
    block = bytes(8 << 20)
    while byte_count:
        take = min(byte_count, len(block))
        digest.update(block[:take])
        byte_count -= take
    return digest.hexdigest()


def parse_basis(path: Path, retained_sequences: list[int], build_dense: bool):
    with path.open() as stream:
        header = json.loads(next(stream))
        records = [json.loads(line) for line in stream]
    require(len(records) == BASIS_DIMENSION, f"basis record count drift in {path}")
    dense = array("q", [0]) * (ROWS * BASIS_DIMENSION) if build_dense else None
    union: set[int] = set()
    supports: list[int] = []
    sum_abs_values: list[int] = []
    max_abs_values: list[int] = []
    provenance: collections.Counter[str] = collections.Counter()
    greedy_pivots: list[int] = []
    for expected_column, record in enumerate(records):
        require(record.get("basis_column") == expected_column,
                f"basis column order drift at {expected_column} in {path}")
        terms = record.get("terms")
        require(isinstance(terms, list) and terms, f"empty terms at {expected_column}")
        previous_row = -1
        coefficients = []
        for term in terms:
            require(isinstance(term, list) and len(term) == 3, "malformed term")
            output_row, sequence, coefficient_text = term
            require(type(output_row) is int and previous_row < output_row < ROWS,
                    f"row order/range drift at basis column {expected_column}")
            require(type(sequence) is int and retained_sequences[output_row] == sequence,
                    f"row/sequence drift at basis column {expected_column}")
            require(isinstance(coefficient_text, str), "coefficient encoding is not text")
            coefficient = int(coefficient_text)
            require(str(coefficient) == coefficient_text and coefficient != 0,
                    f"noncanonical/zero coefficient at basis column {expected_column}")
            require(-(1 << 63) < coefficient < (1 << 63), "coefficient exceeds signed i64")
            coefficients.append(coefficient)
            union.add(output_row)
            if dense is not None:
                dense[output_row * BASIS_DIMENSION + expected_column] = coefficient
            previous_row = output_row
        support = len(terms)
        sum_abs = sum(map(abs, coefficients))
        max_abs = max(map(abs, coefficients))
        require(record.get("support") == support, "support statistic drift")
        require(record.get("sum_abs_coefficients") == str(sum_abs), "sum-abs statistic drift")
        require(record.get("max_abs_coefficient") == str(max_abs), "max-abs statistic drift")
        require(math.gcd(*map(abs, coefficients)) == 1, "nonprimitive basis vector")
        supports.append(support)
        sum_abs_values.append(sum_abs)
        max_abs_values.append(max_abs)
        source = record.get("provenance", {}).get("source")
        if source is not None:
            require(isinstance(source, str), "invalid provenance source")
            provenance[source] += 1
        if "greedy_pivot" in record:
            require(type(record["greedy_pivot"]) is int, "invalid greedy pivot")
            greedy_pivots.append(record["greedy_pivot"])
    return {
        "header": header,
        "dense": dense,
        "records": records,
        "union": union,
        "supports": supports,
        "sum_abs_values": sum_abs_values,
        "max_abs_values": max_abs_values,
        "provenance": provenance,
        "greedy_pivots": greedy_pivots,
    }


def support_metrics(parsed: dict[str, Any]) -> dict[str, Any]:
    supports = parsed["supports"]
    ordered = sorted(supports)
    thresholds = (6, 10, 16, 20, 50, 100, 250, 500, 1_000, 1_500, 2_000)
    quantiles = {}
    for numerator, label in ((25, "p25"), (50, "p50"), (75, "p75"),
                             (90, "p90"), (95, "p95"), (99, "p99")):
        index = round((numerator / 100) * (len(ordered) - 1))
        quantiles[label] = ordered[index]
    return {
        "minimum": min(supports),
        "maximum": max(supports),
        "total_terms": sum(supports),
        "mean": sum(supports) / len(supports),
        "median": statistics.median(supports),
        "quantiles_nearest": quantiles,
        "at_most": {str(value): sum(item <= value for item in supports) for value in thresholds},
        "above": {str(value): sum(item > value for item in supports) for value in thresholds},
        "histogram": {
            str(value): count for value, count in sorted(collections.Counter(supports).items())
        },
        "maximum_sum_abs_coefficients": str(max(parsed["sum_abs_values"])),
        "maximum_abs_coefficient": str(max(parsed["max_abs_values"])),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--star-records", required=True, type=Path)
    parser.add_argument("--old-basis", required=True, type=Path)
    parser.add_argument("--matrix-rank", required=True, type=Path)
    parser.add_argument("--rank-source", required=True, type=Path)
    parser.add_argument("--exact-source", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(args.threads > 0, "--threads must be positive")
    require(sys.byteorder == "little" and array("q").itemsize == 8,
            "certificate requires a little-endian host with 64-bit signed q arrays")
    require(not args.output.exists(), f"refusing to overwrite {args.output}")
    args.output.parent.resolve(strict=True)

    bound_paths = {
        "candidate": args.candidate.resolve(strict=True),
        "matrix": args.matrix.resolve(strict=True),
        "star_records": args.star_records.resolve(strict=True),
        "old_basis": args.old_basis.resolve(strict=True),
        "matrix_rank": args.matrix_rank.resolve(strict=True),
        "verifier": Path(__file__).resolve(strict=True),
        "rank_source": args.rank_source.resolve(strict=True),
        "exact_source": args.exact_source.resolve(strict=True),
    }
    opening = {name: sha256_file(path) for name, path in bound_paths.items()}
    for name, expected in EXPECTED.items():
        require(opening[name] == expected, f"frozen {name} hash drift")
    require(bound_paths["matrix"].stat().st_size == ROWS * MATRIX_COLUMNS * 8,
            "frozen matrix byte count drift")

    star = json.loads(bound_paths["star_records"].read_bytes())
    records = star.get("records")
    require(isinstance(records, list) and len(records) == 5_773, "STAR census drift")
    require([record.get("sequence") for record in records] == list(range(5_773)),
            "STAR sequence/index drift")
    retained_sequences = [sequence for sequence in range(5_773) if sequence not in EXCLUDED]
    require(len(retained_sequences) == ROWS, "retained sequence count drift")

    candidate = parse_basis(bound_paths["candidate"], retained_sequences, build_dense=True)
    header = candidate["header"]
    require(header.get("schema") == "g0193.greedy-exact-sparse-left-kernel-basis.v1",
            "candidate schema drift")
    require(header.get("basis_shape") == [ROWS, BASIS_DIMENSION], "candidate basis shape drift")
    require(header.get("matrix_shape") == [ROWS, MATRIX_COLUMNS], "candidate matrix shape drift")
    require(header.get("selection_prime") == 1_000_003, "selection prime drift")
    require(set(candidate["provenance"]) <= set(header.get("source_labels", {}).values()),
            "unregistered provenance source")
    require(len(candidate["greedy_pivots"]) == BASIS_DIMENSION
            and set(candidate["greedy_pivots"]) == set(range(BASIS_DIMENSION)),
            "greedy-pivot permutation drift")

    dense = candidate["dense"]
    assert dense is not None
    coefficient_payload = dense.tobytes()
    coefficient_sha256 = hashlib.sha256(coefficient_payload).hexdigest()
    require(coefficient_sha256
            == "01f22fc7c295167b10fe7290bd111935a52dc3805f3661f1e525938b3d6b42c4",
            "derived coefficient matrix digest drift")

    old = parse_basis(bound_paths["old_basis"], retained_sequences, build_dense=False)
    require(old["header"].get("schema") == "g0189.exact-primitive-left-kernel-basis.v1",
            "old basis schema drift")
    require(old["header"].get("basis_shape") == [ROWS, BASIS_DIMENSION],
            "old basis shape drift")

    matrix_rank = json.loads(bound_paths["matrix_rank"].read_bytes())
    require(matrix_rank.get("input_rows") == ROWS and matrix_rank.get("input_columns") == MATRIX_COLUMNS,
            "matrix-rank receipt shape drift")
    require(matrix_rank.get("prime") == 1_000_003 and matrix_rank.get("rank_mod_prime") == 5_291,
            "frozen matrix modular rank drift")
    require(matrix_rank.get("selected_raw_cells_sha256") == opening["matrix"],
            "matrix-rank receipt matrix hash drift")

    with tempfile.TemporaryDirectory(prefix="g0187-clean-replay-") as raw_temporary:
        temporary = Path(raw_temporary)
        coefficients = temporary / "coefficients5769x478.i64le"
        write_atomic(coefficients, coefficient_payload)

        pkg_config = run(["pkg-config", "--cflags", "--libs", "flint", "openssl"])
        rank_binary = temporary / "rank_rectangular_flint"
        rank_compile = [
            "g++", "-std=c++20", "-O3", "-DNDEBUG", "-Wall", "-Wextra",
            "-Wpedantic", str(bound_paths["rank_source"]),
            *shlex.split(pkg_config.stdout), "-o", str(rank_binary),
        ]
        run(rank_compile)
        rank_binary_sha256 = sha256_file(rank_binary)

        coefficient_rank_checks = []
        common_pivots = None
        for prime in PRIMES:
            rank_path = temporary / f"coefficient_rank_mod_{prime}.json"
            run([
                str(rank_binary), str(coefficients), "i64le", str(ROWS),
                str(BASIS_DIMENSION), "0", str(BASIS_DIMENSION), "-",
                str(prime), str(rank_path),
            ])
            rank = json.loads(rank_path.read_bytes())
            require(rank.get("input_rows") == ROWS
                    and rank.get("input_columns") == BASIS_DIMENSION,
                    f"coefficient rank shape drift at {prime}")
            require(rank.get("selected_rows") == ROWS
                    and rank.get("selected_columns") == BASIS_DIMENSION,
                    f"coefficient selected shape drift at {prime}")
            require(rank.get("prime") == prime
                    and rank.get("rank_mod_prime") == BASIS_DIMENSION,
                    f"coefficient rank failed at {prime}")
            require(rank.get("selected_raw_cells_sha256") == coefficient_sha256,
                    f"coefficient matrix hash drift in rank receipt at {prime}")
            pivots = rank.get("pivot_columns")
            require(pivots == list(range(BASIS_DIMENSION)),
                    f"coefficient pivot drift at {prime}")
            if common_pivots is None:
                common_pivots = pivots
            else:
                require(pivots == common_pivots, "coefficient rank pivot mismatch")
            coefficient_rank_checks.append({
                "prime": prime,
                "rank": BASIS_DIMENSION,
                "receipt_sha256": sha256_file(rank_path),
                "rref_modp_u64le_sha256": rank["rref_modp_u64le_sha256"],
            })

        exact_binary = temporary / "exact_sparse_replay"
        exact_compile = [
            "g++", "-O3", "-std=c++20", "-fopenmp", "-Wall", "-Wextra",
            "-Werror", str(bound_paths["exact_source"]), "-o", str(exact_binary),
        ]
        run(exact_compile)
        exact_residual = temporary / "exact_residual478x6795.i128le"
        mutant_residual = temporary / "mutant_residual6795.i128le"
        exact_summary = temporary / "exact_replay_summary.json"
        exact_env = dict(os.environ)
        exact_env["OMP_NUM_THREADS"] = str(args.threads)
        exact_run = run([
            str(exact_binary), str(bound_paths["matrix"]), str(coefficients),
            str(exact_residual), str(mutant_residual), str(exact_summary),
            str(ROWS), str(MATRIX_COLUMNS),
        ], env=exact_env)
        exact = json.loads(exact_summary.read_bytes())
        exact_binary_sha256 = sha256_file(exact_binary)
        exact_residual_bytes = exact_residual.stat().st_size
        mutant_residual_bytes = mutant_residual.stat().st_size
        exact_residual_sha256 = sha256_file(exact_residual)
        mutant_residual_sha256 = sha256_file(mutant_residual)
        exact_stdout = exact_run.stdout.strip()

    require(exact.get("basis_vectors") == BASIS_DIMENSION,
            "exact replay basis count drift")
    require(exact.get("coordinates_per_vector") == MATRIX_COLUMNS,
            "exact replay coordinate count drift")
    require(exact.get("equations_checked") == BASIS_DIMENSION * MATRIX_COLUMNS,
            "exact replay equation count drift")
    require(exact.get("residual_nonzero_coordinates") == 0,
            "candidate has nonzero exact residual")
    require(exact.get("signed_i128_safe") is True,
            "exact replay arithmetic safety failed")
    require(exact.get("mutant_nonzero_coordinates", 0) > 0
            and exact.get("mutant_equals_added_row") is True,
            "hostile mutant escaped")
    require(exact_residual_bytes == BASIS_DIMENSION * MATRIX_COLUMNS * 16,
            "exact residual byte count drift")
    require(mutant_residual_bytes == MATRIX_COLUMNS * 16,
            "mutant residual byte count drift")
    zero_residual_sha256 = zero_sha256(BASIS_DIMENSION * MATRIX_COLUMNS * 16)
    require(exact_residual_sha256 == zero_residual_sha256,
            "exact residual is not canonical all-zero i128")

    candidate_metrics = support_metrics(candidate)
    old_metrics = support_metrics(old)
    require(len(candidate["union"]) == 4_174, "candidate row union drift")
    require(candidate["union"] == old["union"], "candidate/old basis union mismatch")
    require(candidate_metrics["total_terms"] == 115_540, "candidate term total drift")
    require(old_metrics["total_terms"] == 228_692, "old term total drift")

    # The invariant argument is mathematical, not empirical: after exact nullity
    # and independence show that the candidate spans K=ker(A^T), the union of
    # supports of any basis is {r : some v in K has v_r != 0}.  This coordinate
    # support depends only on K, so 4,174 is basis-invariant.
    union_rows = sorted(candidate["union"])
    union_sequences = [retained_sequences[row] for row in union_rows]
    complement_rows = sorted(set(range(ROWS)) - candidate["union"])

    closing = {name: sha256_file(path) for name, path in bound_paths.items()}
    require(closing == opening, "bound input changed during audit")
    receipt = {
        "schema": "g0187.clean-room-exact-sparse-basis-replay.v1",
        "result": "PASS_EXACT_FULL_LEFT_KERNEL_BASIS_WITH_MATERIALLY_SPARSE_SUPPORT",
        "candidate_sha256": opening["candidate"],
        "rank_sandwich": {
            "exact_independent_null_vectors": BASIS_DIMENSION,
            "exact_null_replay_equations": BASIS_DIMENSION * MATRIX_COLUMNS,
            "rank_Q_upper_bound": ROWS - BASIS_DIMENSION,
            "upper_bound_reason": "478 exact independent left-null vectors",
            "rank_mod_1000003": 5_291,
            "rank_Q_lower_bound": 5_291,
            "lower_bound_reason": (
                "a nonzero 5291-minor modulo 1000003 is a nonzero integer minor over Q"
            ),
            "rank_Q": 5_291,
            "left_nullity_Q": BASIS_DIMENSION,
            "candidate_spans_full_left_kernel": True,
        },
        "exact_replay": {
            **exact,
            "residual_i128le_sha256": zero_residual_sha256,
            "mutant_residual_i128le_sha256": mutant_residual_sha256,
            "exact_source_sha256": opening["exact_source"],
            "exact_binary_sha256": exact_binary_sha256,
            "stdout": exact_stdout,
        },
        "independence": {
            "method": "full column rank of the reconstructed 5769x478 integer coefficient matrix modulo four primes",
            "coefficient_matrix_sha256": coefficient_sha256,
            "profiles": coefficient_rank_checks,
            "proof_direction": (
                "rank 478 modulo either prime exhibits a nonzero integer 478-minor, hence the vectors are independent over Q"
            ),
        },
        "support": {
            "candidate": candidate_metrics,
            "old_canonical_basis": old_metrics,
            "total_term_reduction_fraction": (
                1 - candidate_metrics["total_terms"] / old_metrics["total_terms"]
            ),
            "provenance_histogram": dict(sorted(candidate["provenance"].items())),
            "honest_interpretation": (
                "The basis is materially sparser in total and median support, but not uniformly sparse: "
                f"{candidate_metrics['above']['1000']} of 478 vectors still have support above 1000."
            ),
        },
        "basis_invariant_row_union": {
            "union_rows": len(union_rows),
            "complement_rows": len(complement_rows),
            "union_output_rows": union_rows,
            "union_record_sequences": union_sequences,
            "old_basis_union_matches": True,
            "is_basis_invariant": True,
            "proof": (
                "For K=ker(A^T), the union of supports of any basis equals "
                "{r | there exists v in K with v_r != 0}; if every basis vector is zero at r, "
                "every vector in K is zero there, and conversely. Hence the 4174-row union depends "
                "only on K, not on the chosen basis."
            ),
        },
        "hostile_control": {
            "mutation": "add +1 to the coefficient of output row 821 in basis vector 0",
            "nonzero_coordinates": exact["mutant_nonzero_coordinates"],
            "residual_equals_added_frozen_matrix_row": True,
            "rejected": True,
        },
        "claim_boundary": (
            "This certifies an exact, complete, materially sparser basis of the frozen finite "
            "restriction matrix's left kernel. It does not show that any newly exposed basis "
            "vector is a sparse graph circuit, lies in O, or vanishes as a complete function; it "
            "does not prove full STAR quarantine, MAX11 membership, ansatz completeness, or an "
            "unrestricted neural-network lower bound."
        ),
        "bindings": {
            name: {"path": str(path.resolve()), "bytes": path.stat().st_size,
                   "sha256": opening[name]}
            for name, path in bound_paths.items()
        },
        "compiled_helpers": {
            "compiler": run(["g++", "--version"]).stdout.splitlines()[0],
            "rank_binary_sha256": rank_binary_sha256,
            "exact_binary_sha256": exact_binary_sha256,
        },
    }
    write_new(args.output, canonical_json(receipt))
    print(json.dumps({
        "result": receipt["result"],
        "candidate_sha256": opening["candidate"],
        "receipt_sha256": sha256_file(args.output),
        "total_terms": candidate_metrics["total_terms"],
        "median_support": candidate_metrics["median"],
        "row_union": len(union_rows),
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"audit_sparse_basis: {error}", file=sys.stderr)
        raise
