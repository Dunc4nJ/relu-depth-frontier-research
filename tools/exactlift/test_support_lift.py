import gzip
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exactlift
import support_lift


class SupportLiftTests(unittest.TestCase):
    def test_mcolgen_exact_reader_and_modular_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exact = root / "exact.bin"
            with exact.open("wb") as stream:
                stream.write(b"MCOLGEN1")
                stream.write(struct.pack("<HHQQ", 2, 1, 0, 1))
                stream.write(struct.pack("<Q2qQ2hq", 7, 0, 1, 1, 1, -1, 3))
            n, k, count, columns = support_lift.read_mcolgen_batch(exact)
            self.assertEqual((n, k, count), (2, 1, 1))
            self.assertEqual(columns[0].source_index, 7)
            self.assertEqual(columns[0].hinges, {"1,-1": 3})

            modular = root / "modular.bin"
            with modular.open("wb") as stream:
                stream.write(b"MCOLGEN1")
                stream.write(struct.pack("<HHQQ", 2, 1, 1_000_003, 0))
            with self.assertRaisesRegex(ValueError, "requires modulus=0"):
                support_lift.read_mcolgen_batch(modular)

    def test_tiny_pivot_support_lifts_on_real_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            system = root / "tiny.jsonl.gz"
            columns = [
                {"A": [[0, 1]], "B": [[0, 1]], "lin": [0, 1], "h": {"1,-1": 1}},
                {"A": [[0, 1]], "B": [[0, 1]], "lin": [0, 0], "h": {"1,-1": -1}},
            ]
            with gzip.open(system, "wt", encoding="utf-8") as stream:
                for column in columns:
                    stream.write(json.dumps(column) + "\n")
            pivots = root / "pivots.json"
            pivots.write_text(
                json.dumps(
                    {
                        "schema": "max11-streamrank-pivots-v1",
                        "input_sha256": exactlift.sha256_file(system),
                        "subject": "saved-system:all",
                        "n": 2,
                        "modulus": 1_000_003,
                        "source_columns_denominator": 2,
                        "sketches": [
                            {
                                "rank_a": 2,
                                "verdict": "MEMBER",
                                "pivot_columns": [0, 1],
                                "sketch": {"algorithm": "test", "seed": 1, "buckets": 6},
                            }
                        ],
                    }
                )
            )
            witness = root / "witness.json"
            report = root / "report.json"
            result = support_lift.lift(pivots, 0, system, [], witness, report, None)
            self.assertEqual(result["verdict"], "PASS")
            self.assertEqual(result["pivot_columns_numerator"], 2)
            self.assertEqual(result["witness_support_numerator"], 2)
            self.assertEqual(result["complete_exact_verification"]["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
