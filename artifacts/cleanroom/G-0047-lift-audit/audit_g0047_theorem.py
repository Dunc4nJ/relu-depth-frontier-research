#!/usr/bin/env python3
"""Adversarial clean-room audit of G-0047 and its proper-core extension.

The producer is read-only.  This audit independently checks:

* the alternating-binomial annihilator and its exact normalization;
* common-loop/common-nonloop padding constants;
* MAX5/MAX6/MAX10 by a signed-direction subset DP whose linear part is
  reconstructed from direct binary evaluations (a different state space from
  G-0047's paired-branch-word DP); and
* the stronger U-statistic theorem for arbitrary proper-support kernels and
  for degree-five pair atoms whose *signed core* has proper support.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import functools
import gzip
import hashlib
import itertools
import json
import math
import os
import platform
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Callable, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / "artifacts/math/G-0047/induction_span_obstruction.py"
PRODUCER_REPORT = ROOT / "artifacts/math/G-0047/induction_span_obstruction_v1.json.gz"
TREE_UNIVERSE = ROOT / "artifacts/math/G-0023/all_tree_universe_v1.json"
SIGNED_STREAM = ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
CERTIFICATES = {
    5: ROOT / "subjects/max-relu-known/certificates/certificate_5_2.json",
    6: ROOT / "subjects/max-relu-known/certificates/certificate_6_2.json",
    10: ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json",
}
PINS = {
    "producer": "0906a834e4f4ee7635a25b8a5c4ab17bfd1ca34d65004e17a64d4eaccdd1ad2d",
    "producer_report": "47f02e125c4010e50d943c31ef4278f9d8679b0e54d26d86ea5414ac12ebf83a",
    "tree_universe": "7dc597d7cefd514ca3d0b49887846cc7bb53a3fc12096217f70887ad12c4dfa3",
    "signed_stream": "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd",
    "certificate_5": "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    "certificate_6": "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    "certificate_10": "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
}

Edge = tuple[int, int]
Branch = tuple[Edge, ...]
Pair = tuple[Branch, Branch]
Vector = tuple[int, ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_pins() -> dict[str, str]:
    paths = {
        "producer": PRODUCER,
        "producer_report": PRODUCER_REPORT,
        "tree_universe": TREE_UNIVERSE,
        "signed_stream": SIGNED_STREAM,
        **{f"certificate_{n}": path for n, path in CERTIFICATES.items()},
    }
    observed = {name: sha256(path) for name, path in paths.items()}
    if observed != PINS:
        raise RuntimeError(json.dumps({"expected": PINS, "observed": observed}, sort_keys=True))
    return observed


def alternating_vector(n: int) -> Vector:
    return tuple((-1) ** (n - rank) * math.comb(n - 1, rank - 1) for rank in range(1, n + 1))


def subset_max_vector(n: int, m: int) -> Vector:
    return tuple(math.comb(rank - 1, m - 1) if rank >= m else 0 for rank in range(1, n + 1))


def dot(first: Iterable[int], second: Iterable[int]) -> int:
    return sum(a * b for a, b in zip(first, second, strict=True))


def nth_difference(profile: Sequence[int]) -> int:
    n = len(profile) - 1
    return sum((-1) ** (n - t) * math.comb(n, t) * profile[t] for t in range(n + 1))


def chamber_vector_to_binary_profile(vector: Sequence[int]) -> list[int]:
    n = len(vector)
    return [sum(vector[n - t :]) for t in range(n + 1)]


def falling(total: int, chosen: int) -> int:
    if chosen < 0 or chosen > total:
        return 0
    return math.factorial(total) // math.factorial(total - chosen)


def u_statistic_binary_profile(n: int, arity: int, kernel: Callable[[int], int]) -> list[int]:
    """Full unnormalised S_n symmetrisation of a labelled arity-r kernel."""
    if not (0 <= arity <= n):
        raise ValueError("bad U-statistic arity")
    profile = []
    inactive_factor = math.factorial(n - arity)
    kernel_by_weight: dict[int, int] = Counter()
    for mask in range(1 << arity):
        kernel_by_weight[mask.bit_count()] += kernel(mask)
    for top_count in range(n + 1):
        value = 0
        for weight, kernel_sum in kernel_by_weight.items():
            value += (
                falling(top_count, weight)
                * falling(n - top_count, arity - weight)
                * kernel_sum
            )
        profile.append(inactive_factor * value)
    return profile


def relabel_active(pair: Pair) -> tuple[Pair, int]:
    active = sorted({vertex for side in pair for edge in side for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(active)}
    reduced = tuple(
        tuple((relabel[a], relabel[b]) for a, b in side) for side in pair
    )
    return reduced, len(active)  # type: ignore[return-value]


def pair_kernel(pair: Pair, mask: int) -> int:
    branch_values = [
        sum(int(((mask >> a) & 1) or ((mask >> b) & 1)) for a, b in side)
        for side in pair
    ]
    return max(branch_values)


def pair_u_profile(pair: Pair, n: int) -> list[int]:
    reduced, arity = relabel_active(pair)
    return u_statistic_binary_profile(n, arity, lambda mask: pair_kernel(reduced, mask))


def remove_common_edges(pair: Pair) -> tuple[Pair, Branch]:
    left, right = map(Counter, pair)
    common = left & right
    left.subtract(common)
    right.subtract(common)
    if any(value < 0 for value in left.values()) or any(value < 0 for value in right.values()):
        raise AssertionError("multiset subtraction underflow")
    reduced: Pair = (
        tuple(sorted(edge for edge, count in left.items() for _ in range(count))),
        tuple(sorted(edge for edge, count in right.items() for _ in range(count))),
    )
    common_branch = tuple(sorted(edge for edge, count in common.items() for _ in range(count)))
    if len(reduced[0]) != len(reduced[1]):
        raise AssertionError("signed core is unbalanced")
    return reduced, common_branch


def common_edge_profile(edge: Edge, n: int) -> list[int]:
    if edge[0] == edge[1]:
        # (N-1)! F_1; at a binary point F_1=t.
        return [math.factorial(n - 1) * t for t in range(n + 1)]
    # 2(N-2)! F_2; F_2 counts pairs meeting the t-element one-set.
    return [
        2
        * math.factorial(n - 2)
        * (math.comb(n, 2) - math.comb(n - t, 2))
        for t in range(n + 1)
    ]


def pair_profile_via_signed_core(pair: Pair, n: int) -> tuple[list[int], int, int]:
    core, common = remove_common_edges(pair)
    core_profile = pair_u_profile(core, n) if core[0] else [0] * (n + 1)
    profile = list(core_profile)
    for edge in common:
        contribution = common_edge_profile(edge, n)
        profile = [a + b for a, b in zip(profile, contribution, strict=True)]
    core_active = len({vertex for side in core for edge in side for vertex in edge})
    pair_active = len({vertex for side in pair for edge in side for vertex in edge})
    return profile, core_active, pair_active


def parse_certificate(n: int) -> list[tuple[Pair, Fraction]]:
    document = json.loads(CERTIFICATES[n].read_text(encoding="utf-8"))
    result = []
    for term in document["terms"]:
        pair = tuple(
            tuple((int(edge[0]) - 1, int(edge[1]) - 1) for edge in side)
            for side in term["pair"]
        )
        result.append((pair, Fraction(term["coefficient"])))
    return result  # type: ignore[return-value]


def signed_direction_words(pair: Pair, n: int) -> Counter[Vector]:
    loops = [0] * n
    adjacency = [[0] * n for _ in range(n)]
    for sign, side in ((1, pair[0]), (-1, pair[1])):
        for a, b in side:
            if a == b:
                loops[a] += sign
            else:
                adjacency[a][b] += sign
                adjacency[b][a] += sign
    full = (1 << n) - 1

    @functools.lru_cache(maxsize=None)
    def suffixes(mask: int) -> tuple[tuple[Vector, int], ...]:
        if mask == full:
            return (((), 1),)
        result: Counter[Vector] = Counter()
        for vertex in range(n):
            if (mask >> vertex) & 1:
                continue
            increment = loops[vertex] + sum(
                adjacency[vertex][other] for other in range(n) if (mask >> other) & 1
            )
            for suffix, count in suffixes(mask | (1 << vertex)):
                result[(increment,) + suffix] += count
        return tuple(result.items())

    return Counter(dict(suffixes(0)))


def active_hinges(words: Counter[Vector]) -> Counter[Vector]:
    result: Counter[Vector] = Counter()
    for word, multiplicity in words.items():
        first = next((value for value in word if value), 0)
        if not first:
            continue
        oriented = word if first > 0 else tuple(-value for value in word)
        running = 0
        prefixes = []
        for value in oriented[:-1]:
            running += value
            prefixes.append(running)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = math.gcd(*(abs(value) for value in oriented))
        primitive = tuple(value // divisor for value in oriented)
        result[primitive] += divisor * multiplicity
    return result


def direct_binary_atom_values(pair: Pair, n: int) -> list[int]:
    degree = len(pair[0])
    values = []
    for zero_count in range(n + 1):
        subset_sum = 0
        for zero_vertices in itertools.combinations(range(n), zero_count):
            zeros = set(zero_vertices)
            internal = [sum(a in zeros and b in zeros for a, b in side) for side in pair]
            subset_sum += degree - min(internal)
        values.append(math.factorial(zero_count) * math.factorial(n - zero_count) * subset_sum)
    return values


def independent_atom_normal_form(pair: Pair, n: int) -> tuple[Vector, Counter[Vector]]:
    hinges = active_hinges(signed_direction_words(pair, n))
    values = direct_binary_atom_values(pair, n)
    tails = []
    for zero_count, value in enumerate(values):
        hinge_value = sum(
            coefficient * max(0, sum(direction[zero_count:]))
            for direction, coefficient in hinges.items()
        )
        tails.append(value - hinge_value)
    if tails[-1] != 0:
        raise AssertionError("zero-input normalization failed")
    linear = tuple(tails[index] - tails[index + 1] for index in range(n))
    return linear, hinges


def independent_atom_worker(payload: tuple[int, Pair, int]) -> tuple[int, Vector, dict[Vector, int]]:
    index, pair, n = payload
    linear, hinges = independent_atom_normal_form(pair, n)
    return index, linear, dict(hinges)


def independent_certificate_replay(n: int, workers: int) -> dict:
    terms = parse_certificate(n)
    total_linear = [Fraction() for _ in range(n)]
    total_hinges: dict[Vector, Fraction] = {}
    union: set[Vector] = set()
    forms: list[tuple[Vector, Counter[Vector]] | None] = [None] * len(terms)
    payloads = [(index, pair, n) for index, (pair, _) in enumerate(terms)]
    if n == 10 and workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(independent_atom_worker, payload) for payload in payloads]
            completed = 0
            for future in as_completed(futures):
                index, linear, raw_hinges = future.result()
                forms[index] = (linear, Counter(raw_hinges))
                completed += 1
                if completed % 50 == 0 or completed == len(terms):
                    print(f"G0047_AUDIT MAX10 terms={completed}/{len(terms)}", flush=True)
    else:
        for payload in payloads:
            index, linear, raw_hinges = independent_atom_worker(payload)
            forms[index] = (linear, Counter(raw_hinges))

    for (_, coefficient), form in zip(terms, forms, strict=True):
        if form is None:
            raise AssertionError("missing independent atom form")
        linear, hinges = form
        union.update(hinges)
        for index, value in enumerate(linear):
            total_linear[index] += coefficient * value
        for direction, value in hinges.items():
            updated = total_hinges.get(direction, Fraction()) + coefficient * value
            if updated:
                total_hinges[direction] = updated
            else:
                total_hinges.pop(direction, None)
    target = [Fraction()] * (n - 1) + [Fraction(1)]
    if total_linear != target or total_hinges:
        raise AssertionError(f"independent MAX{n} replay failed")

    mutation_index = 1
    mutation = Fraction(1, 2 * terms[mutation_index][1].denominator)
    mutation_form = forms[mutation_index]
    if mutation_form is None:
        raise AssertionError("missing mutation atom form")
    mutant_linear = [mutation * value for value in mutation_form[0]]
    mutant_hinges = {direction: mutation * value for direction, value in mutation_form[1].items()}
    if not any(mutant_linear) and not mutant_hinges:
        raise AssertionError("nonlinear coefficient mutant escaped")
    return {
        "n": n,
        "terms": len(terms),
        "result": "EXACT_IDENTITY",
        "combined_linear_vector": [str(value) for value in total_linear],
        "combined_nonzero_active_hinges": len(total_hinges),
        "union_active_hinge_directions": len(union),
        "nonlinear_mutation_term_index": mutation_index,
        "mutant_nonzero_linear_coordinates": sum(value != 0 for value in mutant_linear),
        "mutant_nonzero_active_hinges": len(mutant_hinges),
    }


def brute_profile(pair: Pair, n: int) -> list[int]:
    result = []
    for top_count in range(n + 1):
        point = (0,) * (n - top_count) + (1,) * top_count
        total = 0
        for rank_of_label in itertools.permutations(range(n)):
            branches = [
                sum(point[max(rank_of_label[a], rank_of_label[b])] for a, b in side)
                for side in pair
            ]
            total += max(branches)
        result.append(total)
    return result


def theorem_and_counterexample_search() -> dict:
    n = 11
    witness = alternating_vector(n)
    subset_pairings = [dot(witness, subset_max_vector(n, m)) for m in range(1, n)]
    if any(subset_pairings):
        raise AssertionError("alternating vector did not annihilate lower subset maxima")
    max_vector = (0,) * (n - 1) + (1,)
    max_profile = chamber_vector_to_binary_profile(max_vector)
    if dot(witness, max_vector) != 1 or nth_difference(max_profile) != 1:
        raise AssertionError("MAX11 potency control failed")

    # Exact relation Lambda(c)=Delta^N g(0) for arbitrary chamber-linear c.
    relation_controls = []
    for index in range(n):
        vector = tuple(int(j == index) for j in range(n))
        lhs = dot(witness, vector)
        rhs = nth_difference(chamber_vector_to_binary_profile(vector))
        if lhs != rhs:
            raise AssertionError("Lambda/finite-difference relation failed")
        relation_controls.append(lhs)

    proper_no_common: Pair = (
        ((0, 1), (2, 3), (4, 5), (6, 7), (8, 9)),
        ((0, 2), (1, 3), (4, 6), (5, 8), (7, 9)),
    )
    full_pair_proper_core: Pair = (
        ((0, 1), (2, 3), (4, 5), (6, 7), (10, 10)),
        ((0, 8), (1, 9), (2, 4), (3, 5), (10, 10)),
    )
    universe = json.loads(TREE_UNIVERSE.read_text(encoding="utf-8"))
    first_tree_raw = universe["n11_subject"]["representatives"][0]
    full_core_control: Pair = tuple(
        tuple((int(a), int(b)) for a, b in side) for side in first_tree_raw
    )  # type: ignore[assignment]

    explicit = []
    for label, pair, expected_zero in (
        ("proper_core_active10_no_common", proper_no_common, True),
        ("pair_active11_but_signed_core_active10", full_pair_proper_core, True),
        ("full_signed_core_tree_potency_control", full_core_control, False),
    ):
        profile, core_active, pair_active = pair_profile_via_signed_core(pair, n)
        difference = nth_difference(profile)
        if (difference == 0) != expected_zero:
            raise AssertionError(f"explicit proper/full-core control failed: {label}")
        explicit.append(
            {
                "label": label,
                "pair": pair,
                "signed_core_active_vertices": core_active,
                "full_pair_active_vertices": pair_active,
                "binary_profile": profile,
                "eleventh_finite_difference": difference,
                "expected_zero": expected_zero,
            }
        )

    # Exhaust every proper-support signed core in the mass<=3 prefix.  Pad to
    # degree five with one repeated common nonloop; the exact decomposition is
    # used, so this includes pair atoms rather than only abstract core records.
    checked = 0
    counts: Counter[int] = Counter()
    with gzip.open(SIGNED_STREAM, "rt", encoding="utf-8") as stream:
        header = json.loads(next(stream))
        if int(header["expected_record_count"]) != 7_015_841:
            raise ValueError("signed stream header drift")
        for line in stream:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass > 3:
                break
            if not signed_mass or int(record["active_vertices"]) >= n:
                continue
            left = tuple(tuple(map(int, edge)) for edge in record["negative_edges"])
            right = tuple(tuple(map(int, edge)) for edge in record["positive_edges"])
            common = ((0, 1),) * (5 - signed_mass)
            pair: Pair = (left + common, right + common)
            profile, core_active, _ = pair_profile_via_signed_core(pair, n)
            if core_active >= n or nth_difference(profile) != 0:
                raise AssertionError(f"proper-core counterexample at sequence {record['sequence']}")
            checked += 1
            counts[signed_mass] += 1
    if counts != Counter({1: 5, 2: 107, 3: 3195}):
        raise AssertionError(f"proper-core prefix census mismatch: {counts}")

    # Brute full-permutation control at small N validates the U-statistic
    # multiplicities independently of the polynomial proof.
    small_pair: Pair = (((0, 1), (1, 2)), ((0, 2), (3, 3)))
    if pair_u_profile(small_pair, 6) != brute_profile(small_pair, 6):
        raise AssertionError("U-statistic profile disagrees with direct S_6 symmetrisation")

    return {
        "N": n,
        "alternating_vector": witness,
        "lower_subset_max_pairings": subset_pairings,
        "MAX11_pairing": dot(witness, max_vector),
        "MAX11_eleventh_binary_finite_difference": nth_difference(max_profile),
        "Lambda_equals_eleventh_difference_basis_checks": relation_controls,
        "proper_kernel_theorem": (
            "For every h:R^r->R with r<N, the binary profile of its unnormalised full S_N "
            "permutation symmetrisation is (N-r)! sum_{U subset [r]} "
            "(t)_{|U|}(N-t)_{r-|U|} h(1_U), a polynomial of degree at most r; "
            "therefore its Nth finite difference and Lambda pairing vanish."
        ),
        "signed_core_corollary": (
            "After cancelling common branch edges, every degree-five pair orbit with signed-core "
            "support <N is a proper-kernel U-statistic plus common F1/F2 terms. Any signed linear "
            "combination of such orbits has zero Nth binary finite difference and cannot equal MAX_N."
        ),
        "explicit_degree_five_controls": explicit,
        "proper_core_mass_1_through_3_atoms_checked": checked,
        "proper_core_counts_by_mass": {str(key): value for key, value in sorted(counts.items())},
        "ustatistic_multiplicity_vs_direct_S6": "PASS",
        "counterexample_found": False,
    }


def normalization_audit() -> dict:
    n, m = 11, 5
    # One lifted certificate orbit retains the original certificate
    # coefficients.  Each m-subset receives (N-m)! copies of its complete S_m
    # orbit sum.  Full-symmetrising the already-symmetric function MAX_m has an
    # extra m! factor.  The span obstruction is invariant to either scalar.
    template_lift_factor = math.factorial(n - m)
    symmetric_function_factor = math.factorial(m) * math.factorial(n - m)
    loop_factor = math.factorial(n - 1)
    nonloop_factor = 2 * math.factorial(n - 2)

    # Direct small-N counts make both conventions observable.
    small_n, small_m = 5, 3
    subset = (0, 1, 2)
    fixed_binary = (0, 0, 1, 1, 1)
    direct_symmetric_function = 0
    for permutation in itertools.permutations(range(small_n)):
        direct_symmetric_function += max(fixed_binary[permutation[i]] for i in subset)
    f_m_value = sum(
        max(fixed_binary[i] for i in choice)
        for choice in itertools.combinations(range(small_n), small_m)
    )
    if direct_symmetric_function != math.factorial(small_m) * math.factorial(
        small_n - small_m
    ) * f_m_value:
        raise AssertionError("direct symmetric-function normalization failed")

    loop_profile = common_edge_profile((0, 0), n)
    nonloop_profile = common_edge_profile((0, 1), n)
    if nth_difference(loop_profile) or nth_difference(nonloop_profile):
        raise AssertionError("common padding escaped finite-difference annihilator")
    return {
        "certificate_template_lift_factor_for_m5_to_N11": template_lift_factor,
        "formula_certificate_template_lift": "(N-m)! F_m^(N)",
        "already_symmetric_function_full_sym_factor_for_m5_to_N11": symmetric_function_factor,
        "formula_already_symmetric_function": "m!(N-m)! F_m^(N)",
        "wording_caveat": (
            "G-0047's (N-m)! formula is correct for lifting every unsymmetrised certificate "
            "template and retaining its coefficient. Calling this Ind(MAX_m) without defining "
            "the orbit-basis convention is ambiguous; directly full-symmetrising the already "
            "symmetric MAX_m function has an additional m! factor. The obstruction is unchanged."
        ),
        "common_loop_per_occurrence_factor": loop_factor,
        "common_nonloop_per_occurrence_factor": nonloop_factor,
        "G0047_five_loop_factor": 5 * loop_factor,
        "G0047_five_nonloop_factor": 5 * nonloop_factor,
        "small_N_direct_normalization_control": "PASS",
    }


def run(workers: int) -> dict:
    before = verify_pins()
    theorem = theorem_and_counterexample_search()
    normalization = normalization_audit()
    replays = [independent_certificate_replay(n, workers) for n in (5, 6, 10)]
    after = verify_pins()
    if before != after:
        raise RuntimeError("inputs changed during audit")
    report = {
        "schema": "max11-g0047-independent-theorem-audit-v1",
        "result": "CONSISTENT_WITH_WORDING_CAVEAT_AND_STRONGER_PROPER_CORE_THEOREM",
        "audit_script_sha256": sha256(Path(__file__)),
        "inputs_sha256_before_and_after": before,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "workers": workers,
        },
        "alternating_and_proper_core_theorem": theorem,
        "normalization_audit": normalization,
        "independent_certificate_replays": replays,
        "adversarial_verdict": (
            "No counterexample was found. The lower-MAX/common-padding obstruction is exact. "
            "More strongly, the Nth binary finite difference annihilates arbitrary proper-support "
            "local kernels, so any degree-five pair-orbit MAX11 certificate must contain at least "
            "one atom whose signed core (after common-edge cancellation) uses all 11 coordinates."
        ),
        "remaining_boundary": (
            "The theorem is only a necessary full-signed-core-support condition. Full-core atoms "
            "can have nonzero finite difference but also non-braid hinges; it neither constructs "
            "the required hinge-cancelling signed circuit nor excludes one, and it does not cover "
            "unrestricted arbitrary-real first-layer weights."
        ),
        "no_claim": (
            "A proper-core null is not an unrestricted MAX11 lower bound. The finite mass<=3 scan "
            "is a potency/control sample; the universal proper-kernel conclusion comes from the "
            "exact U-statistic polynomial proof, not from that scan. Re-running G-0047 is not "
            "independent proof; this audit instead uses a different signed-word DP and binary reconstruction."
        ),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=HERE / "g0047_theorem_audit_v1.json")
    args = parser.parse_args()
    if args.self_test:
        # Small tests do not read the 7-million-record stream beyond pins.
        verify_pins()
        small_pair: Pair = (((0, 1), (1, 2)), ((0, 2), (3, 3)))
        if pair_u_profile(small_pair, 6) != brute_profile(small_pair, 6):
            raise AssertionError("U-statistic multiplicity self-test failed")
        for arity in range(0, 6):
            profile = u_statistic_binary_profile(6, arity, lambda mask: mask * mask + 3)
            if nth_difference(profile):
                raise AssertionError("proper-kernel finite-difference self-test failed")
        print(json.dumps({"result": "PASS"}, sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit("output must remain inside the project") from exc
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    report = run(args.workers)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
