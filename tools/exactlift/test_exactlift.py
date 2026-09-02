import gzip
import json
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exactlift


class ExactLiftTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.system = self.root / "tiny.jsonl.gz"
        columns = [
            {"A": [[0, 1]], "B": [[0, 1]], "lin": [0, 1], "h": {"1,-1": 1}},
            {"A": [[0, 1]], "B": [[0, 2]], "lin": [0, 0], "h": {"1,-1": -1}},
        ]
        with gzip.open(self.system, "wt", encoding="utf-8") as stream:
            for column in columns:
                stream.write(json.dumps(column) + "\n")

    def tearDown(self):
        self.temporary.cleanup()

    def write_witness(self, second=Fraction(1)):
        witness = self.root / "witness.json"
        witness.write_text(
            json.dumps(
                {
                    "schema": exactlift.SCHEMA,
                    "n": 2,
                    "coefficients": [
                        {"column": 0, "coefficient": "1"},
                        {"column": 1, "coefficient": exactlift.fraction_text(second)},
                    ],
                }
            )
        )
        return witness

    def test_exact_positive_and_negative(self):
        positive = exactlift.verify_witness(self.system, self.write_witness())
        self.assertEqual(positive["verdict"], "PASS")
        self.assertEqual(positive["rows_checked"], 3)
        negative = exactlift.verify_witness(self.system, self.write_witness(Fraction(2)))
        self.assertEqual(negative["verdict"], "FAIL")
        self.assertEqual(negative["nonzero_hinge_residual_count"], 1)

    def test_mutation_is_exact(self):
        certificate = self.root / "certificate.json"
        certificate.write_text(
            json.dumps(
                {
                    "n": 2,
                    "terms": [
                        {"coefficient": "1/3", "pair": [[[1, 2]], [[1, 2]]]}
                    ],
                }
            )
        )
        mutated = self.root / "mutated.json"
        exactlift.mutate_upstream(certificate, mutated, Fraction(1, 6))
        value = json.loads(mutated.read_text())["terms"][0]["coefficient"]
        self.assertEqual(value, "1/2")

    def test_modular_basis_to_exact_solution(self):
        witness = self.root / "recovered.json"
        report = self.root / "recovery-report.json"
        result = exactlift.recover_exact(
            self.system,
            n=2,
            prime=1_000_003,
            output=witness,
            report_path=report,
        )
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["rank"], 2)
        self.assertEqual(result["support_size"], 2)


if __name__ == "__main__":
    unittest.main()
