from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from cleanroom.maxrelu import (
    CertificateFormatError,
    SubjectSpec,
    load_corpus,
    parse_certificate_bytes,
    parse_registered_certificate_bytes,
)

from _fixture import fixture_bytes, fixture_object, fixture_spec


class StrictParserTests(unittest.TestCase):
    def parse(self, value: dict[str, object]):
        return parse_certificate_bytes(fixture_bytes(value), fixture_spec())

    def test_exact_fraction_coefficients(self) -> None:
        certificate = self.parse(fixture_object())
        self.assertEqual(certificate.n, 2)
        self.assertEqual(certificate.k, 2)
        self.assertEqual(certificate.term_count, 2)
        self.assertEqual(len(certificate.terms), 2)
        self.assertIs(type(certificate.terms[0].coefficient), Fraction)
        self.assertEqual(certificate.terms[0].coefficient, Fraction(1, 8))
        self.assertRegex(certificate.raw_sha256, r"^[0-9a-f]{64}$")
        self.assertRegex(certificate.normalized_sha256, r"^[0-9a-f]{64}$")

    def test_floating_json_number_is_rejected_before_coercion(self) -> None:
        value = fixture_object()
        value["n"] = 2.0
        with self.assertRaisesRegex(CertificateFormatError, "floating JSON number"):
            self.parse(value)

        value = fixture_object()
        value["terms"][0]["coefficient"] = 0.125
        with self.assertRaisesRegex(CertificateFormatError, "floating JSON number"):
            self.parse(value)

    def test_booleans_are_not_integers(self) -> None:
        value = fixture_object()
        value["n"] = True
        with self.assertRaisesRegex(CertificateFormatError, "genuine JSON integer"):
            self.parse(value)

        value = fixture_object()
        value["terms"][0]["pair"][0][0][0] = True
        with self.assertRaisesRegex(CertificateFormatError, "genuine JSON integer"):
            self.parse(value)

    def test_unknown_and_duplicate_keys_are_rejected(self) -> None:
        for location in ("root", "term"):
            with self.subTest(location=location):
                value = fixture_object()
                if location == "root":
                    value["extra"] = 1
                else:
                    value["terms"][0]["extra"] = 1
                with self.assertRaisesRegex(CertificateFormatError, "keys mismatch"):
                    self.parse(value)

        duplicate_key_json = b'{"n":2,"n":2,"terms":[]}'
        with self.assertRaisesRegex(CertificateFormatError, "duplicate JSON key"):
            parse_certificate_bytes(duplicate_key_json, fixture_spec())

    def test_malformed_endpoints_are_rejected(self) -> None:
        hostile_endpoints = (
            [1],
            [2, 1],
            [0, 1],
            [1, 3],
            ["1", 1],
            [True, 1],
        )
        for endpoint in hostile_endpoints:
            with self.subTest(endpoint=endpoint):
                value = fixture_object()
                value["terms"][0]["pair"][0][0] = endpoint
                with self.assertRaises(CertificateFormatError):
                    self.parse(value)

    def test_mismatched_side_lengths_are_rejected(self) -> None:
        value = fixture_object()
        value["terms"][0]["pair"][1].pop()
        with self.assertRaisesRegex(CertificateFormatError, "requires k=2"):
            self.parse(value)

    def test_zero_and_noncanonical_coefficients_are_rejected(self) -> None:
        for coefficient in ("0", "0/7", "01/8", "1/08", " 1/8", 1, True):
            with self.subTest(coefficient=coefficient):
                value = fixture_object()
                value["terms"][0]["coefficient"] = coefficient
                with self.assertRaises(CertificateFormatError):
                    self.parse(value)

    def test_shape_must_match_explicit_contract(self) -> None:
        hostile_specs = (
            fixture_spec(n=3),
            fixture_spec(k=1),
            fixture_spec(term_count=1),
        )
        for spec in hostile_specs:
            with self.subTest(spec=spec):
                with self.assertRaises(CertificateFormatError):
                    parse_certificate_bytes(fixture_bytes(), spec)

        with self.assertRaisesRegex(CertificateFormatError, "unregistered"):
            parse_registered_certificate_bytes(fixture_bytes(), "synthetic_max2.json")

    def test_corpus_refuses_extra_file_without_parsing_around_it(self) -> None:
        spec = fixture_spec()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / spec.filename).write_bytes(fixture_bytes())
            (root / "unregistered.json").write_bytes(b"{}")
            with self.assertRaisesRegex(CertificateFormatError, "extra"):
                load_corpus(root, (spec,))

    def test_hash_contract_fails_closed(self) -> None:
        bad_hash_spec = SubjectSpec(
            subject_id="synthetic-MAX2-stage-a",
            filename="synthetic_max2.json",
            n=2,
            k=2,
            term_count=2,
            byte_sha256="0" * 64,
        )
        with self.assertRaisesRegex(CertificateFormatError, "SHA-256 mismatch"):
            parse_certificate_bytes(fixture_bytes(), bad_hash_spec)


if __name__ == "__main__":
    unittest.main()
