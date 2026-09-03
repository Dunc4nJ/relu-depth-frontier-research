#!/usr/bin/env python3
"""Build the finite n=9-certificate -> n=10 degree-five lift control.

For every one of the 337 frozen MAX9 degree-four certificate terms, append
one of every ordered pair of distinct nonloop edges on ten labels, one edge to
each branch.  Common occurrences are cancelled and the results are quotiented
by S_10 relabeling and global branch/sign reversal.  The emitted universe is
only this source-derived family, not the complete n=10 degree-five universe.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import time
from typing import Any

import build_order as common


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / "subjects/max-relu-known/certificates/certificate_9_4.json"
DEFAULT_UNIVERSE = HERE / "n9-lift-n10-family-universe.json.gz"
DEFAULT_ORDER = HERE / "n9-lift-n10-order.json"
DEFAULT_REPORT = HERE / "n9-lift-n10-map-report.json"
SOURCE_SHA = "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88"
SOURCE_TERMS = 337
N = 10
EDGES = tuple(combinations(range(1, N + 1), 2))
EDGE_PAIRS = tuple((left, right) for left in EDGES for right in EDGES if left != right)
DISJOINT_PER_SOURCE = 45 * 28
SHARED_PER_SOURCE = 45 * 16
RAW_PER_SOURCE = 45 * 44
RAW_TOTAL = SOURCE_TERMS * RAW_PER_SOURCE

Pair = common.Pair
Edge = common.Edge


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_terms() -> tuple[list[Pair], list[Fraction]]:
    require(sha256_path(SOURCE) == SOURCE_SHA, "MAX9 certificate SHA drift")
    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    require(document.get("n") == 9, "MAX9 certificate arity drift")
    raw_terms = document.get("terms")
    require(isinstance(raw_terms, list) and len(raw_terms) == SOURCE_TERMS,
            "MAX9 source term denominator drift")
    pairs: list[Pair] = []
    coefficients: list[Fraction] = []
    for index, term in enumerate(raw_terms):
        raw_pair = term.get("pair")
        require(isinstance(raw_pair, list) and len(raw_pair) == 2,
                f"malformed source pair {index}")
        pair = common.canonical_side(raw_pair[0]), common.canonical_side(raw_pair[1])
        require(len(pair[0]) == len(pair[1]) == 4, f"source degree drift {index}")
        require(all(1 <= u < v <= 9 for side in pair for u, v in side),
                f"loop or label drift {index}")
        pairs.append(pair)
        coefficients.append(Fraction(term["coefficient"]))
    return pairs, coefficients


def extension_pair(source: Pair, left: Edge, right: Edge) -> Pair:
    return (
        tuple(sorted(source[0] + (left,))),
        tuple(sorted(source[1] + (right,))),
    )


def census_term(item: tuple[int, Pair]) -> tuple[int, dict[bytes, Pair], int, int]:
    index, source = item
    classes: dict[bytes, Pair] = {}
    disjoint = 0
    shared = 0
    for left, right in EDGE_PAIRS:
        pair = extension_pair(source, left, right)
        certificate = common.signed_certificate(pair, n=N)
        classes.setdefault(certificate, pair)
        overlap = len(set(left) & set(right))
        if overlap == 0:
            disjoint += 1
        elif overlap == 1:
            shared += 1
        else:
            raise RuntimeError("distinct nonloop edges have invalid overlap")
    require(disjoint == DISJOINT_PER_SOURCE, f"disjoint raw count at term {index}")
    require(shared == SHARED_PER_SOURCE, f"shared raw count at term {index}")
    return index, classes, disjoint, shared


def record_from_pair(pair: Pair) -> dict[str, Any]:
    negative, positive = common.cancelled_pair(pair)
    support = sorted({vertex for edge in negative + positive for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(support)}
    compact: Pair = (
        tuple((relabel[u] + 1, relabel[v] + 1) for u, v in negative),
        tuple((relabel[u] + 1, relabel[v] + 1) for u, v in positive),
    )
    topo = common.topology(compact)
    record: dict[str, Any] = {
        "active_vertices": topo["active_vertices"],
        "signed_mass": topo["signed_mass"],
        "negative_edges": [[u - 1, v - 1] for u, v in compact[0]],
        "positive_edges": [[u - 1, v - 1] for u, v in compact[1]],
        "abs_components": topo["abs_components"],
        "abs_beta": topo["abs_beta"],
    }
    require(common.signed_certificate(compact, n=N) == common.signed_certificate(pair, n=N),
            "support compaction changed signed orbit")
    return record


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")))
        handle.write("\n")


def write_new_gzip(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    require(not path.exists() and not temporary.exists(), f"refusing to overwrite {path}")
    try:
        with temporary.open("xb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                stream.write(canonical_bytes(value))
            raw.flush()
            os.fsync(raw.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def self_test() -> None:
    source: Pair = (((1, 2), (2, 3), (3, 4), (4, 5)),
                    ((1, 3), (2, 4), (3, 5), (5, 6)))
    witness = extension_pair(source, (1, 10), (6, 10))
    permutation = {label: N + 1 - label for label in range(1, N + 1)}
    relabeled: Pair = tuple(
        common.canonical_side((permutation[u], permutation[v]) for u, v in side)
        for side in witness
    )  # type: ignore[assignment]
    certificate = common.signed_certificate(witness, n=N)
    require(common.signed_certificate(relabeled, n=N) == certificate, "relabel control")
    require(common.signed_certificate((witness[1], witness[0]), n=N) == certificate,
            "branch-swap control")
    mutant = extension_pair(source, (2, 10), (6, 10))
    require(common.signed_certificate(mutant, n=N) != certificate,
            "edge mutant was not distinguished")
    loop_mutant = extension_pair(source, (10, 10), (6, 10))
    require(common.signed_certificate(loop_mutant, n=N) != certificate,
            "loop mutant was not distinguished")
    require(len(EDGE_PAIRS) == RAW_PER_SOURCE, "ordered edge-pair count")
    print("N9_TO_N10_SELF_TEST_PASS")


def build(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    pairs, coefficients = load_terms()
    global_representatives: dict[bytes, Pair] = {}
    per_term: list[dict[str, Any]] = []
    raw_disjoint = 0
    raw_shared = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for expected_index, result in enumerate(
            pool.map(census_term, enumerate(pairs), chunksize=1)
        ):
            index, classes, disjoint, shared = result
            require(index == expected_index, "source result order drift")
            raw_disjoint += disjoint
            raw_shared += shared
            class_hashes = sorted(hashlib.sha256(value).hexdigest() for value in classes)
            per_term.append({
                "source_term": index,
                "raw_extensions": disjoint + shared,
                "distinct_signed_W_orbits": len(classes),
                "signed_class_sha256_list_sha256": hashlib.sha256(
                    canonical_bytes(class_hashes)
                ).hexdigest(),
            })
            for certificate, pair in classes.items():
                global_representatives.setdefault(certificate, pair)
    require(raw_disjoint == SOURCE_TERMS * DISJOINT_PER_SOURCE, "global disjoint count")
    require(raw_shared == SOURCE_TERMS * SHARED_PER_SOURCE, "global shared count")
    require(raw_disjoint + raw_shared == RAW_TOTAL, "global raw denominator")

    ordered = sorted(
        global_representatives,
        key=lambda value: (hashlib.sha256(value).digest(), value),
    )
    zero = [cert for cert in ordered if common.topology(global_representatives[cert])["signed_mass"] == 0]
    require(len(zero) == 1, "zero signed-W orbit denominator")
    ordered = zero + [cert for cert in ordered if cert != zero[0]]
    class_hashes = [hashlib.sha256(cert).hexdigest() for cert in ordered]
    require(len(class_hashes) == len(set(class_hashes)), "certificate SHA collision")
    records = [record_from_pair(global_representatives[cert]) for cert in ordered]
    require(records[0] == {
        "active_vertices": 0,
        "signed_mass": 0,
        "negative_edges": [],
        "positive_edges": [],
        "abs_components": 0,
        "abs_beta": 0,
    }, "record zero drift")
    for record, certificate in zip(records, ordered, strict=True):
        pair: Pair = (
            tuple((u + 1, v + 1) for u, v in record["negative_edges"]),
            tuple((u + 1, v + 1) for u, v in record["positive_edges"]),
        )
        require(common.signed_certificate(pair, n=N) == certificate,
                "record certificate replay")

    records_digest = hashlib.sha256()
    for record in records:
        records_digest.update(canonical_bytes(record))
    universe = {
        "schema": "max9-to-max10-lift-family-universe-v1",
        "result": "PASS",
        "n": N,
        "branch_edge_occurrences": 5,
        "loopless": True,
        "quotient": "coordinate relabeling and global branch/sign reversal",
        "function_collapse": "common edge occurrences cancel from W=B-A",
        "records_included": True,
        "records_sha256": records_digest.hexdigest(),
        "records": records,
        "claim_boundary": (
            "Finite source-derived control family only; not the complete n=10 degree-five "
            "universe and not a claim about unrestricted networks."
        ),
    }
    write_new_gzip(args.output_universe, universe)
    order = list(range(len(records)))
    write_new_json(args.output_order, order)

    per_term_digest = hashlib.sha256()
    for item in per_term:
        per_term_digest.update(canonical_bytes(item))
    report = {
        "schema": "max9-to-max10-lift-family-map-v1",
        "result": "PASS",
        "definition": {
            "source": "all 337 terms of the pinned degree-four MAX9 certificate",
            "embedding": "labels 1..9 embedded in [10]; quotient by S_10 covers every injection",
            "extension": "append ordered distinct nonloop edges e_L and e_R, one per branch",
            "raw_strata": {
                "DISJOINT_per_source": DISJOINT_PER_SOURCE,
                "SHARED_DISTINCT_per_source": SHARED_PER_SOURCE,
                "union_per_source": RAW_PER_SOURCE,
            },
            "quotient": "cancel common occurrences, then quotient signed W by S_10 and global sign",
        },
        "bindings": {
            "source_certificate": str(SOURCE.relative_to(ROOT)),
            "source_certificate_sha256": SOURCE_SHA,
            "family_universe": str(args.output_universe.relative_to(ROOT)),
            "family_universe_sha256": sha256_path(args.output_universe),
            "order_file": str(args.output_order.relative_to(ROOT)),
            "order_file_sha256": sha256_path(args.output_order),
        },
        "counts": {
            "source_terms_denominator": SOURCE_TERMS,
            "raw_extensions_denominator": RAW_TOTAL,
            "raw_disjoint_numerator": raw_disjoint,
            "raw_shared_distinct_numerator": raw_shared,
            "signed_W_orbits_denominator": len(records),
            "mapped_signed_W_orbits_numerator": len(records),
            "raw_extensions_outside_loopless_family_numerator": 0,
            "signed_W_orbits_outside_loopless_family_numerator": 0,
            "zero_orbits": 1,
            "record_zero_first": True,
        },
        "source_term_mapping": {
            "terms_with_at_least_one_orbit_numerator": len(per_term),
            "terms_denominator": SOURCE_TERMS,
            "term_orbit_incidence_numerator": sum(
                item["distinct_signed_W_orbits"] for item in per_term
            ),
            "mapping_stream_sha256": per_term_digest.hexdigest(),
            "per_source_term": per_term,
        },
        "controls": {
            "source_coefficients_parsed_as_exact_rationals": len(coefficients),
            "every_source_raw_multiplicity_sum": RAW_PER_SOURCE,
            "all_record_certificates_replayed": len(records),
            "certificate_hashes_unique": len(records),
            "positive_relabel_and_branch_swap_invariance": True,
            "negative_edge_and_loop_mutants_distinguished": True,
        },
        "workers": args.workers,
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "This maps one finite source-derived family. A later modular control does not "
            "establish an exact rational identity or any unrestricted depth result."
        ),
    }
    write_new_json(args.output_report, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output-universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--output-order", type=Path, default=DEFAULT_ORDER)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require(1 <= args.workers <= 8, "workers must be in [1,8]")
    for name in ("output_universe", "output_order", "output_report"):
        setattr(args, name, getattr(args, name).resolve())
    self_test()
    if args.self_test:
        return
    report = build(args)
    print(json.dumps({"result": report["result"], "counts": report["counts"],
                      "bindings": report["bindings"]}, sort_keys=True))


if __name__ == "__main__":
    main()
