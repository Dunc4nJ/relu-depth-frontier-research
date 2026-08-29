from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import unittest

from cleanroom.maxrelu import (
    Certificate,
    Term,
    VerificationInputError,
    canonicalize_hinge,
    ordered_cone_sign,
    parse_certificate_bytes,
    side_linear_form,
    SubjectSpec,
    verify_certificate,
)

from _fixture import fixture_certificate, fixture_object


def _fraction_string(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _scale_coefficients(value: dict[str, object], scale: Fraction) -> None:
    for term in value["terms"]:
        coefficient = Fraction(term["coefficient"])
        term["coefficient"] = _fraction_string(coefficient * scale)


def _relabel(value: dict[str, object], labels: dict[int, int]) -> None:
    for term in value["terms"]:
        for side in term["pair"]:
            for endpoint in side:
                a, b = labels[endpoint[0]], labels[endpoint[1]]
                endpoint[:] = sorted((a, b))


class ExactAccumulatorTests(unittest.TestCase):
    def test_hand_derived_max2_has_exact_zero_residual(self) -> None:
        result = verify_certificate(fixture_certificate())
        self.assertTrue(result.accepted)
        self.assertEqual(result.verdict, "ACCEPT")
        self.assertEqual(result.integer_scale, 8)
        self.assertEqual(result.residual.linear, (0, 8))
        self.assertEqual(result.residual.target, (0, 8))
        self.assertEqual(result.residual.linear_minus_target, (0, 0))
        self.assertEqual(result.residual.hinges, ())
        self.assertTrue(result.census.complete)
        self.assertEqual(result.census.expected_contributions, 4)
        self.assertEqual(result.census.observed_contributions, 4)
        self.assertTrue(result.symmetrization_transport_checked)

        serialized = result.canonical_bytes()
        self.assertEqual(serialized, result.canonical_bytes())
        self.assertEqual(result.sha256(), hashlib.sha256(serialized).hexdigest())

    def test_coefficient_scaling_by_two_with_fixed_target_is_rejected(self) -> None:
        value = fixture_object()
        _scale_coefficients(value, Fraction(2, 1))
        result = verify_certificate(fixture_certificate(value))
        self.assertFalse(result.accepted)
        self.assertTrue(result.residual.hinge_zero)
        self.assertFalse(result.residual.target_matched)
        self.assertIn("linear-target-mismatch", result.failure_reasons)
        self.assertTrue(result.census.complete)

    def test_omission_plus_duplication_fails_census_even_when_residual_matches(self) -> None:
        # Both S2 contributions of term 0 equal 2*MAX2.  Replacing rank 0 by a
        # second rank 1 leaves the algebraic sum unchanged, isolating the census.
        result = verify_certificate(
            fixture_certificate(), rank_plans={0: (1, 1), 1: (0, 1)}
        )
        self.assertFalse(result.accepted)
        self.assertEqual(result.outcome, "INCOMPLETE")
        self.assertTrue(result.cannot_verify)
        self.assertTrue(result.residual.hinge_zero)
        self.assertTrue(result.residual.target_matched)
        self.assertEqual(result.census.observed_contributions, 4)
        self.assertEqual(result.census.unique_contributions, 3)
        self.assertEqual(result.census.missing_contributions, 1)
        self.assertEqual(result.census.duplicate_contributions, 1)
        self.assertFalse(result.census.complete)
        self.assertFalse(result.symmetrization_transport_checked)
        self.assertIn("census-incomplete", result.failure_reasons)

    def test_missing_explicit_term_schedule_is_typed_incomplete(self) -> None:
        result = verify_certificate(
            fixture_certificate(), rank_plans={0: (0, 1)}
        )
        self.assertEqual(result.outcome, "INCOMPLETE")
        self.assertTrue(result.cannot_verify)
        self.assertFalse(result.accepted)
        self.assertEqual(
            result.census.terms[1].schedule_kind, "missing-explicit-plan"
        )
        self.assertEqual(result.census.terms[1].observed, 0)
        self.assertEqual(result.payload()["outcome"], "INCOMPLETE")

    def test_complete_explicit_schedule_remains_decidable(self) -> None:
        result = verify_certificate(
            fixture_certificate(), rank_plans={0: (1, 0), 1: (0, 1)}
        )
        self.assertEqual(result.outcome, "ACCEPT")
        self.assertTrue(result.census.complete)
        self.assertTrue(
            all(
                term.schedule_kind == "explicit-ranks"
                for term in result.census.terms
            )
        )

    def test_schedule_identity_binds_which_rank_was_missing_and_duplicated(self) -> None:
        missing_zero = verify_certificate(
            fixture_certificate(), rank_plans={0: (1, 1), 1: (0, 1)}
        )
        missing_one = verify_certificate(
            fixture_certificate(), rank_plans={0: (0, 0), 1: (0, 1)}
        )
        self.assertEqual(missing_zero.outcome, "INCOMPLETE")
        self.assertEqual(missing_one.outcome, "INCOMPLETE")
        self.assertEqual(missing_zero.residual.payload(), missing_one.residual.payload())
        self.assertEqual(
            missing_zero.census.missing_contributions,
            missing_one.census.missing_contributions,
        )
        self.assertEqual(
            missing_zero.census.duplicate_contributions,
            missing_one.census.duplicate_contributions,
        )
        self.assertNotEqual(
            missing_zero.census.terms[0].coverage_sha256,
            missing_one.census.terms[0].coverage_sha256,
        )
        self.assertNotEqual(
            missing_zero.census.terms[0].duplicate_multiset_sha256,
            missing_one.census.terms[0].duplicate_multiset_sha256,
        )
        self.assertNotEqual(missing_zero.sha256(), missing_one.sha256())

    def test_ordered_cone_and_primitive_orientation_are_exact(self) -> None:
        self.assertEqual(ordered_cone_sign((0, 0)), "zero")
        self.assertEqual(ordered_cone_sign((-1, 1)), "nonnegative")
        self.assertEqual(ordered_cone_sign((1, -1)), "nonpositive")
        self.assertEqual(ordered_cone_sign((1, -2, 1)), "mixed")

        forward = canonicalize_hinge((2, -4, 2))
        reverse = canonicalize_hinge((-2, 4, -2))
        self.assertEqual(forward.direction, (1, -2, 1))
        self.assertEqual(reverse.direction, (1, -2, 1))
        self.assertEqual(forward.magnitude, 2)
        self.assertEqual(reverse.magnitude, 2)
        self.assertFalse(forward.flipped)
        self.assertTrue(reverse.flipped)

    def test_sparse_mixed_hinges_accumulate_and_cancel_exactly(self) -> None:
        # On the identity labelling, right-left is (1,-2,1), which has both
        # gap signs on x1<=x2<=x3.  It therefore exercises the genuine sparse
        # hinge path rather than either fixed-sign cone simplification.
        block = {
            "coefficient": "1",
            "pair": [
                [[2, 2], [2, 2]],
                [[1, 1], [3, 3]],
            ],
        }

        def parse_terms(terms):
            raw = json.dumps(
                {"n": 3, "terms": terms},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
            return parse_certificate_bytes(
                raw,
                SubjectSpec(
                    "synthetic-MAX3-mixed-hinge",
                    "synthetic_max3.json",
                    3,
                    2,
                    len(terms),
                ),
            )

        one_term = verify_certificate(parse_terms([block]))
        self.assertGreater(len(one_term.residual.hinges), 0)
        for direction, coefficient in one_term.residual.hinges:
            self.assertGreater(coefficient, 0)
            self.assertGreater(next(value for value in direction if value), 0)

        negative_block = {
            "coefficient": "-1",
            "pair": [
                [[2, 2], [2, 2]],
                [[1, 1], [3, 3]],
            ],
        }
        two_terms = verify_certificate(parse_terms([block, negative_block]))
        self.assertTrue(two_terms.residual.hinge_zero)
        self.assertEqual(two_terms.residual.linear, (0, 0, 0))
        self.assertFalse(two_terms.residual.target_matched)

    def test_labelled_side_conversion_on_ordered_cone(self) -> None:
        side = ((1, 1), (1, 2))
        self.assertEqual(side_linear_form(side, (0, 1), 2), (1, 1))
        self.assertEqual(side_linear_form(side, (1, 0), 2), (0, 2))

    def test_public_direct_object_boundary_is_fully_revalidated(self) -> None:
        base = fixture_certificate()
        direct = Certificate(
            subject_id=base.subject_id,
            n=base.n,
            k=base.k,
            term_count=base.term_count,
            terms=base.terms,
            raw_sha256=base.raw_sha256,
            normalized_sha256=base.normalized_sha256,
        )
        self.assertTrue(verify_certificate(direct).accepted)

        first = base.terms[0]

        def with_first(term):
            return replace(base, terms=(term,) + base.terms[1:])

        hostile_objects = {
            "boolean-n": replace(base, n=True),
            "zero-n": replace(base, n=0),
            "boolean-k": replace(base, k=True),
            "wrong-k": replace(base, k=3),
            "boolean-term-count": replace(base, term_count=True),
            "wrong-term-count": replace(base, term_count=1),
            "empty-terms": replace(base, term_count=0, terms=()),
            "list-terms": replace(base, terms=list(base.terms)),
            "integer-coefficient": with_first(
                Term(1, first.left, first.right)
            ),
            "zero-coefficient": with_first(
                Term(Fraction(0), first.left, first.right)
            ),
            "short-side": with_first(
                Term(first.coefficient, ((1, 1),), first.right)
            ),
            "list-side": with_first(
                Term(first.coefficient, list(first.left), first.right)
            ),
            "zero-label": with_first(
                Term(first.coefficient, ((0, 1), (1, 2)), first.right)
            ),
            "boolean-label": with_first(
                Term(first.coefficient, ((True, 1), (1, 2)), first.right)
            ),
            "descending-endpoint": with_first(
                Term(first.coefficient, ((2, 1), (1, 2)), first.right)
            ),
            "out-of-range-label": with_first(
                Term(first.coefficient, ((1, 3), (1, 2)), first.right)
            ),
            "short-endpoint": with_first(
                Term(first.coefficient, ((1,), (1, 2)), first.right)
            ),
            "list-endpoint": with_first(
                Term(first.coefficient, ([1, 1], (1, 2)), first.right)
            ),
            "bad-subject-id": replace(base, subject_id="bad id"),
            "bad-raw-hash": replace(base, raw_sha256="not-a-hash"),
            "bad-normalized-hash": replace(
                base, normalized_sha256="A" * 64
            ),
        }
        for label, candidate in hostile_objects.items():
            with self.subTest(label=label):
                with self.assertRaises(VerificationInputError):
                    verify_certificate(candidate)

    def test_public_side_helper_refuses_negative_indexing_shapes(self) -> None:
        for side in (
            ((0, 1),),
            ((True, 1),),
            ((2, 1),),
            ([1, 1],),
        ):
            with self.subTest(side=side):
                with self.assertRaises(VerificationInputError):
                    side_linear_form(side, (0, 1), 2)

    def test_preregistered_metamorphisms_preserve_synthetic_acceptance(self) -> None:
        base = verify_certificate(fixture_certificate())
        transformed_results = []

        relabelled = fixture_object()
        _relabel(relabelled, {1: 2, 2: 1})
        transformed_results.append(verify_certificate(fixture_certificate(relabelled)))

        side_swapped = fixture_object()
        for term in side_swapped["terms"]:
            term["pair"].reverse()
        transformed_results.append(verify_certificate(fixture_certificate(side_swapped)))

        pair_reordered = fixture_object()
        for term in pair_reordered["terms"]:
            for side in term["pair"]:
                side.reverse()
        transformed_results.append(verify_certificate(fixture_certificate(pair_reordered)))

        term_reordered = fixture_object()
        term_reordered["terms"].reverse()
        transformed_results.append(verify_certificate(fixture_certificate(term_reordered)))

        for result in transformed_results:
            self.assertTrue(result.accepted)
            self.assertEqual(result.residual.payload(), base.residual.payload())
            self.assertEqual(result.census.payload(), base.census.payload())
            # The complete digest remains input-bound, so metamorphic subjects
            # cannot collide in a future cache despite sharing a zero residual.
            self.assertNotEqual(
                result.input_normalized_sha256, base.input_normalized_sha256
            )

    def test_positive_target_and_coefficient_scaling_preserves_acceptance(self) -> None:
        value = fixture_object()
        scale = Fraction(3, 2)
        _scale_coefficients(value, scale)
        result = verify_certificate(
            fixture_certificate(value), target_scale=scale
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.target_scale, scale)
        self.assertEqual(result.residual.linear_minus_target, (0, 0))
        self.assertEqual(result.residual.hinges, ())

    def test_exact_two_to_minus_128_perturbation_with_fixed_target_flips(self) -> None:
        value = fixture_object()
        perturbation = Fraction(1, 1) + Fraction(1, 2**128)
        _scale_coefficients(value, perturbation)
        result = verify_certificate(fixture_certificate(value))
        self.assertFalse(result.accepted)
        self.assertTrue(result.census.complete)
        self.assertFalse(result.residual.target_matched)


if __name__ == "__main__":
    unittest.main()
