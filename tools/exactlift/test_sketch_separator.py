import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exactlift
import sketch_separator


class SketchSeparatorTests(unittest.TestCase):
    def test_tiny_nonmember_separator_and_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            system = root / "tiny.jsonl.gz"
            with gzip.open(system, "wt", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {"A": [], "B": [], "lin": [1, 0], "h": {}}
                    )
                    + "\n"
                )
            buckets = 6
            seed = next(
                candidate
                for candidate in range(1, 100)
                if sketch_separator.linear_bucket(candidate, buckets, 2, 0)[0]
                != sketch_separator.linear_bucket(candidate, buckets, 2, 1)[0]
            )
            pivots = root / "pivots.json"
            pivots.write_text(
                json.dumps(
                    {
                        "schema": "max11-streamrank-pivots-v1",
                        "input_sha256": exactlift.sha256_file(system),
                        "subject": "saved-system:all",
                        "n": 2,
                        "modulus": 1_000_003,
                        "source_columns_denominator": 1,
                        "sketches": [
                            {
                                "rank_a": 1,
                                "rank_augmented": 2,
                                "verdict": "NON_MEMBER",
                                "pivot_columns": [0],
                                "sketch": {
                                    "algorithm": sketch_separator.ALGORITHM,
                                    "seed": seed,
                                    "buckets": buckets,
                                },
                            }
                        ],
                    }
                )
            )
            separator = root / "separator.json"
            report = root / "report.json"
            result = sketch_separator.lift_separator(pivots, 0, system, separator, report)
            self.assertEqual(result["verdict"], "PASS")
            self.assertEqual(result["exact_verification"]["target_pairing"], "1")
            mutant = root / "mutant.json"
            sketch_separator.mutate_separator(separator, mutant, exactlift.Fraction(1))
            mutant_report = sketch_separator.verify_file(system, mutant, root / "mutant-report.json")
            self.assertEqual(mutant_report["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
