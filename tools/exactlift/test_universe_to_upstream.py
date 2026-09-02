import gzip
import json
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import universe_to_upstream as translate


class UniverseToUpstreamTests(unittest.TestCase):
    def test_loopless_carrier_known_answer(self) -> None:
        record = {
            "signed_mass": 2,
            "negative_edges": [[0, 2], [1, 3]],
            "positive_edges": [[0, 3], [1, 2]],
        }
        self.assertEqual(
            translate.pair_representative(record, 5),
            [
                [[0, 2], [1, 3], [0, 1], [0, 1], [0, 1]],
                [[0, 3], [1, 2], [0, 1], [0, 1], [0, 1]],
            ],
        )

    def test_synthetic_five_l_known_answer(self) -> None:
        pair = translate.synthetic_five_l_pair(5)
        self.assertEqual(pair, [[[0, 0]] * 5, [[0, 0]] * 5])
        # For n=11, summing five copies of x_{sigma(0)} over all 11!
        # permutations gives 5*10! = 18,144,000 on each coordinate.
        coefficient = 5
        for value in range(1, 11):
            coefficient *= value
        self.assertEqual(coefficient, 18_144_000)

    def test_end_to_end_three_column_known_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            universe_path = root / "universe.json.gz"
            universe = {
                "schema": "max11-g0027-loopless-signed-degree5-universe-v1",
                "n": 11,
                "branch_edge_occurrences": 5,
                "records": [
                    {"signed_mass": 0, "negative_edges": [], "positive_edges": []},
                    {
                        "signed_mass": 1,
                        "negative_edges": [[0, 2]],
                        "positive_edges": [[1, 2]],
                    },
                ],
            }
            with gzip.open(universe_path, "wt", encoding="utf-8") as handle:
                json.dump(universe, handle)
            witness_path = root / "witness.json"
            witness_path.write_text(
                json.dumps(
                    {
                        "n": 11,
                        "system_sha256": translate.sha256(universe_path),
                        "coefficients": [
                            {"column": 0, "coefficient": "2/4"},
                            {"column": 1, "coefficient": "-3/7"},
                            {"column": 2, "coefficient": "5/9"},
                        ],
                    }
                )
            )
            output = root / "certificate.json"
            report = translate.convert(universe_path, witness_path, output)
            certificate = json.loads(output.read_text())
            self.assertEqual(report["support_terms_numerator"], 3)
            self.assertEqual([term["coefficient"] for term in certificate["terms"]], ["1/2", "-3/7", "5/9"])
            self.assertEqual(certificate["terms"][0]["pair"], [[[1, 2]] * 5, [[1, 2]] * 5])
            self.assertEqual(certificate["terms"][1]["pair"][0][0], [1, 3])
            self.assertEqual(certificate["terms"][1]["pair"][1][0], [2, 3])
            self.assertEqual(certificate["terms"][2]["pair"], [[[1, 1]] * 5, [[1, 1]] * 5])
            with self.assertRaises(FileExistsError):
                translate.convert(universe_path, witness_path, output)


if __name__ == "__main__":
    unittest.main()
