#!/usr/bin/env python3
"""Audit the pair-support 3-cover property of the upstream MAX certificates.

Each certificate is a rational linear combination of fully symmetrized pair
atoms.  A non-loop inner max(x_a, x_b) has a first-layer ReLU realization with
support {a,b}; its full coordinate orbit contains every two-element support.
This script checks that exact orbit consequence, not minimal network width.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import itertools
import json
from math import comb, factorial
from pathlib import Path
import sys
import time
from typing import Iterable


SCHEMA = "max11-gmp6-certificate-3cover-audit-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def all_triples(n: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(itertools.combinations(range(1, n + 1), 3))


def missed_triples(
    n: int, supports: Iterable[frozenset[int]]
) -> tuple[tuple[int, int, int], ...]:
    allowed = {
        support
        for support in supports
        if len(support) in (2, 3) and all(1 <= vertex <= n for vertex in support)
    }
    return tuple(
        triple
        for triple in all_triples(n)
        if not any(support <= frozenset(triple) for support in allowed)
    )


def minimum_pair_cover(n: int) -> set[frozenset[int]]:
    """Complement of the balanced complete bipartite Mantel graph."""

    split = n // 2
    left = range(1, split + 1)
    right = range(split + 1, n + 1)
    return {
        frozenset(pair)
        for block in (left, right)
        for pair in itertools.combinations(block, 2)
    }


def read_certificate(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text())
    n = int(value["n"])
    terms = value["terms"]
    if n < 3 or not isinstance(terms, list) or not terms:
        raise ValueError(f"invalid certificate header in {path}")

    nonzero_terms = 0
    nonloop_occurrences = 0
    loop_occurrences = 0
    seed_supports: set[frozenset[int]] = set()
    for term_index, term in enumerate(terms):
        coefficient = Fraction(term["coefficient"])
        pair = term["pair"]
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"term {term_index}: pair must have two sides")
        if len(pair[0]) != len(pair[1]):
            raise ValueError(f"term {term_index}: side sizes differ")
        if coefficient == 0:
            continue
        nonzero_terms += 1
        for side in pair:
            for raw_edge in side:
                if not isinstance(raw_edge, list) or len(raw_edge) != 2:
                    raise ValueError(f"term {term_index}: malformed edge")
                a, b = map(int, raw_edge)
                if not 1 <= a <= b <= n:
                    raise ValueError(f"term {term_index}: invalid edge {(a, b)}")
                if a == b:
                    loop_occurrences += 1
                else:
                    nonloop_occurrences += 1
                    seed_supports.add(frozenset((a, b)))
    if nonzero_terms == 0 or nonloop_occurrences == 0:
        raise AssertionError(f"{path}: no nonzero term supplies a pair support")

    # One non-loop pair under the full S_n coordinate action has precisely all
    # C(n,2) pair supports.  Construct that orbit explicitly as a control-sized
    # set rather than expanding n! certificate copies.
    orbit_supports = {
        frozenset(pair) for pair in itertools.combinations(range(1, n + 1), 2)
    }
    missing = missed_triples(n, orbit_supports)
    if missing:
        raise AssertionError(f"{path}: full pair orbit misses triples {missing[:3]}")

    target_triple = (1, 2, 3)
    target_set = frozenset(target_triple)
    mutated_supports = {
        support for support in orbit_supports if not support <= target_set
    }
    mutant_missing = missed_triples(n, mutated_supports)
    if mutant_missing != (target_triple,):
        raise AssertionError(
            f"{path}: destructive cover mutation did not isolate {target_triple}: {mutant_missing}"
        )

    minimum = minimum_pair_cover(n)
    minimum_expected = comb(n, 2) - (n * n // 4)
    if len(minimum) != minimum_expected or missed_triples(n, minimum):
        raise AssertionError(f"n={n}: Mantel-complement minimum-cover control failed")
    if len(missed_triples(n, set())) != comb(n, 3):
        raise AssertionError(f"n={n}: empty-support null failed")

    return {
        "n": n,
        "path": str(path),
        "sha256": sha256_path(path),
        "terms": len(terms),
        "nonzero_terms": nonzero_terms,
        "seed_distinct_nonloop_pair_supports": len(seed_supports),
        "nonloop_pair_occurrences_per_unsymmetrized_terms": nonloop_occurrences,
        "loop_occurrences_per_unsymmetrized_terms": loop_occurrences,
        "literal_symmetrized_nonloop_neuron_occurrences": factorial(n)
        * nonloop_occurrences,
        "distinct_pair_supports_after_symmetrization": len(orbit_supports),
        "triple_denominator": comb(n, 3),
        "triples_covered": comb(n, 3),
        "minimum_pair_3cover_size": minimum_expected,
        "support_sizes_after_symmetrization": [2],
        "controls": {
            "balanced_partition_cover_pass": True,
            "balanced_partition_cover_size": len(minimum),
            "empty_supports_missed_triples": comb(n, 3),
            "removed_target_triple_pairs": 3,
            "destructive_mutation_missing_triples": [list(triple) for triple in mutant_missing],
        },
    }


def run(certificates: Path) -> dict[str, object]:
    started = time.monotonic()
    paths = sorted(certificates.glob("certificate_*_*.json"))
    records = [read_certificate(path) for path in paths]
    records.sort(key=lambda record: int(record["n"]))
    if [record["n"] for record in records] != [5, 6, 7, 8, 9, 10]:
        raise AssertionError("expected exactly one upstream certificate for each n=5..10")
    n11_cover = minimum_pair_cover(11)
    if len(n11_cover) != 25 or missed_triples(11, n11_cover):
        raise AssertionError("n=11 numerical 25-cover known answer failed")
    return {
        "schema": SCHEMA,
        "result": "PASS",
        "certificate_directory": str(certificates),
        "certificate_denominator": len(records),
        "records": records,
        "n11_pair_3cover": {
            "triple_denominator": comb(11, 3),
            "minimum_pair_3cover_size": len(n11_cover),
            "mantel_formula": "C(11,2)-floor(11^2/4)=55-30=25",
        },
        "controls": {
            "certificate_positive_controls_passed": len(records),
            "certificate_positive_control_denominator": len(records),
            "destructive_cover_mutations_rejected": len(records),
            "destructive_cover_mutation_denominator": len(records),
            "empty_cover_nulls_rejected": len(records),
            "empty_cover_null_denominator": len(records),
            "n11_balanced_partition_known_answer": True,
        },
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "This checks a support property of six explicit fully symmetrized "
            "certificate constructions. It does not prove the certificates' functional "
            "identities, a necessary condition for arbitrary networks, or a depth lower bound."
        ),
    }


def self_test() -> None:
    supports = minimum_pair_cover(7)
    assert len(supports) == 9
    assert not missed_triples(7, supports)
    mutant = set(supports)
    victim = next(iter(supports))
    mutant.remove(victim)
    assert missed_triples(7, mutant)
    assert len(missed_triples(7, set())) == 35
    print("GMP6_SELF_TEST_PASS positive=1 destructive=1 empty_null=1")


def atomic_write(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--certificates", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.certificates is None or args.output is None:
        raise SystemExit("--certificates and --output are required unless --self-test is used")
    report = run(args.certificates)
    atomic_write(args.output, report)
    print(
        f"GMP6_CERTIFICATE_COVER_PASS certificates={report['certificate_denominator']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
