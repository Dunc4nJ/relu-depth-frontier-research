"""Tests for the independent lattice-point falsifier.

Run with::

    PYTHONPATH=.venv/lib/python3.13/site-packages python3 -m pytest \
        tools/t2-referee/test_lattice_check.py -q
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_check as lc  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
UPSTREAM = REPO / "literature/repos/max-relu-certificates/certificates"
WITNESS = REPO / "artifacts/math/exact-witness-n9-n10"
CONTROLS = REPO / "artifacts/math/t2-referee/controls-v1"


# --------------------------------------------------------------------------
# the counting shortcut against literal permutation enumeration
# --------------------------------------------------------------------------


def literal_symmetrization(left, right, n, point):
    """Definitional sum over all n! permutations, used as ground truth."""
    total = 0
    for sigma in itertools.permutations(range(n)):
        values = [point[sigma[j]] for j in range(n)]
        lhs = sum(max(values[a], values[b]) for a, b in left)
        rhs = sum(max(values[a], values[b]) for a, b in right)
        total += max(lhs, rhs)
    return total


@pytest.mark.parametrize("n,base", [(4, 2), (4, 3), (5, 2), (5, 3), (6, 3)])
def test_counting_matches_literal_enumeration(n, base):
    """Injective-placement counting must reproduce the S_n sum exactly."""
    cases = [
        (((0, 1), (0, 2)), ((1, 2), (0, 3))),  # simple, loopless
        (((0, 0), (1, 1)), ((0, 1), (2, 3))),  # loops on both branches
        (((0, 1), (0, 1)), ((0, 1), (0, 1))),  # repeated and identical branches
        (((0, 1),), ((2, 3),)),  # single edge per branch
        (((0, 1), (2, 3), (0, 3)), ((0, 2), (1, 3), (1, 2))),  # three edges
    ]
    for left, right in cases:
        if max(v for e in left + right for v in e) >= n:
            continue
        weights, scale = lc.structure_weights(n, left, right, base, {})
        for index, profile in enumerate(lc.profiles_for(n, base)):
            point = []
            for value, multiplicity in enumerate(profile):
                point.extend([value] * multiplicity)
            assert int(weights[index]) * scale == literal_symmetrization(
                left, right, n, point
            ), (left, right, profile)


def test_end_to_end_against_literal_certificate_evaluation(tmp_path):
    """Whole pipeline vs a definitional evaluation of a random certificate.

    Builds random (invalid) certificates, evaluates the left-hand side of the
    identity by literal enumeration over S_n at one concrete lattice point, and
    checks the tool reproduces that value in its failure record.
    """
    rng = random.Random(20260903)
    n = 5
    for _ in range(4):
        terms = []
        for _ in range(3):
            k = rng.randint(1, 3)
            left = [sorted(rng.sample(range(1, n + 1), 2)) for _ in range(k)]
            right = [sorted(rng.sample(range(1, n + 1), 2)) for _ in range(k)]
            terms.append(
                {
                    "coefficient": f"{rng.randint(-50, 50)}/{rng.randint(1, 97)}",
                    "pair": [left, right],
                }
            )
        path = tmp_path / "random.json"
        path.write_text(json.dumps({"n": n, "terms": terms}))
        report = lc.check_certificate(path, bases=(3,), processes=1)
        failure = report["per_base"]["{0..2}^n"]["first_failure"]
        if failure is None:
            continue
        point = []
        for value, multiplicity in enumerate(failure["profile_multiplicities"]):
            point.extend([value] * multiplicity)
        expected = sum(
            Fraction(t["coefficient"])
            * literal_symmetrization(
                [(a - 1, b - 1) for a, b in t["pair"][0]],
                [(a - 1, b - 1) for a, b in t["pair"][1]],
                n,
                point,
            )
            for t in terms
        )
        assert Fraction(failure["certificate_value"]) == expected
        path.unlink()


def test_target_value_is_max():
    assert lc.target_value((5, 0, 0)) == 0
    assert lc.target_value((3, 2, 0)) == 1
    assert lc.target_value((0, 0, 5)) == 2


def test_profile_counts():
    assert len(lc.profiles_for(11, 2)) == 12
    assert len(lc.profiles_for(11, 3)) == 78
    assert all(sum(p) == 11 for p in lc.profiles_for(11, 3))


def test_merge_denominator_groups_is_exact():
    groups = [(3, [1, 2]), (7, [5, -5]), (11, [0, 4])]
    den, nums = lc.merge_denominator_groups(sorted(groups))
    for i in range(2):
        expected = sum(Fraction(g[1][i], g[0]) for g in groups)
        assert Fraction(nums[i], den) == expected


# --------------------------------------------------------------------------
# positive controls
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["certificate_5_2", "certificate_6_2", "certificate_7_3"])
def test_upstream_certificates_pass(name):
    report = lc.check_certificate(UPSTREAM / f"{name}.json", bases=(2, 3), processes=1)
    assert report["verdict"] == "PASS", report["per_base"]


def test_recovered_n9_passes():
    path = WITNESS / "recovered_n9_upstream.json"
    if not path.exists():  # pragma: no cover - campaign artifact may be absent
        pytest.skip(f"{path} not present")
    report = lc.check_certificate(path, bases=(2,), processes=1)
    assert report["verdict"] == "PASS"


# --------------------------------------------------------------------------
# negative controls
# --------------------------------------------------------------------------


def test_plus_one_mutant_fails():
    path = WITNESS / "certificate_5_2_mutated_plus1.json"
    if not path.exists():  # pragma: no cover - campaign artifact may be absent
        pytest.skip(f"{path} not present")
    report = lc.check_certificate(path, bases=(2, 3), processes=1)
    assert report["verdict"] == "FAIL"
    failure = report["per_base"]["{0..1}^n"]["first_failure"]
    assert failure["profile_multiplicities"] == [4, 1]
    assert failure["certificate_value"] == "145"
    assert failure["target_value"] == "1"


def test_edge_swap_mutant_fails():
    path = CONTROLS / "certificate_9_4_mutated_edge_swap.json"
    if not path.exists():  # pragma: no cover - control artifact may be absent
        pytest.skip(f"{path} not present")
    report = lc.check_certificate(path, bases=(2, 3), processes=1)
    assert report["verdict"] == "FAIL"
    assert report["per_base"]["{0..2}^n"]["failing_profiles"] > 0


def test_zero_one_blind_mutant_needs_the_three_valued_lattice():
    """A structure swap the 0/1 cube cannot see must still be caught."""
    path = CONTROLS / "certificate_6_2_mutated_zero_one_blind.json"
    if not path.exists():  # pragma: no cover - control artifact may be absent
        pytest.skip(f"{path} not present")
    report = lc.check_certificate(path, bases=(2, 3), processes=1)
    assert report["per_base"]["{0..1}^n"]["verdict"] == "PASS"
    assert report["per_base"]["{0..2}^n"]["verdict"] == "FAIL"
    assert report["verdict"] == "FAIL"


def test_coefficient_perturbation_is_caught(tmp_path):
    """Perturbing any single nonzero coefficient must break lattice agreement."""
    source = json.loads((UPSTREAM / "certificate_6_2.json").read_text())
    for index in range(len(source["terms"])):
        mutated = json.loads((UPSTREAM / "certificate_6_2.json").read_text())
        coefficient = Fraction(mutated["terms"][index]["coefficient"])
        mutated["terms"][index]["coefficient"] = str(coefficient + Fraction(1, 7))
        path = tmp_path / f"mutant_{index}.json"
        path.write_text(json.dumps(mutated))
        report = lc.check_certificate(path, bases=(2, 3), processes=1)
        assert report["verdict"] == "FAIL", index


# --------------------------------------------------------------------------
# schema handling
# --------------------------------------------------------------------------


def test_zero_coefficient_terms_are_skipped(tmp_path):
    source = json.loads((UPSTREAM / "certificate_5_2.json").read_text())
    source["terms"].append({"coefficient": "0", "pair": [[[1, 1]], [[2, 2]]]})
    path = tmp_path / "with_zero_term.json"
    path.write_text(json.dumps(source))
    report = lc.check_certificate(path, bases=(2, 3), processes=1)
    assert report["verdict"] == "PASS"
    assert report["terms"] == 4
    assert report["nonzero_terms"] == 3


def test_mismatched_branch_sizes_are_rejected(tmp_path):
    source = json.loads((UPSTREAM / "certificate_5_2.json").read_text())
    source["terms"][0]["pair"] = [[[1, 2]], [[1, 2], [3, 4]]]
    path = tmp_path / "bad_sides.json"
    path.write_text(json.dumps(source))
    with pytest.raises(lc.CertificateError):
        lc.check_certificate(path, bases=(2,), processes=1)


def test_out_of_range_endpoint_is_rejected(tmp_path):
    source = json.loads((UPSTREAM / "certificate_5_2.json").read_text())
    source["terms"][0]["pair"][0][0] = [1, 99]
    path = tmp_path / "bad_endpoint.json"
    path.write_text(json.dumps(source))
    with pytest.raises(lc.CertificateError):
        lc.check_certificate(path, bases=(2,), processes=1)


def test_output_is_create_new(tmp_path):
    out = tmp_path / "report.json"
    out.write_text("{}")
    code = lc.main(
        [str(UPSTREAM / "certificate_5_2.json"), "--processes", "1", "--output", str(out)]
    )
    assert code == 2
    assert out.read_text() == "{}"


def test_cli_exit_codes(tmp_path):
    good = lc.main([str(UPSTREAM / "certificate_5_2.json"), "--processes", "1"])
    assert good == 0
    bad = WITNESS / "certificate_5_2_mutated_plus1.json"
    if bad.exists():
        assert lc.main([str(bad), "--processes", "1"]) == 1
