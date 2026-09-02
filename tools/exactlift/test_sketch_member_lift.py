from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sketch_member_lift


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SketchMemberLiftTests(unittest.TestCase):
    def test_finalize_checks_custody_counts_and_normalizes_coefficients(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            universe = directory / "universe.json.gz"
            universe.write_bytes(b"frozen tiny universe")
            problem = directory / "problem.eliftq02"
            problem.write_bytes(b"exact problem")
            pivot_path = directory / "pivots.json"
            pivot = {
                "n": 2,
                "sketches": [
                    {
                        "verdict": "MEMBER",
                        "rank_a": 2,
                        "rank_augmented": 2,
                        "pivot_columns": [9, 4],
                    }
                ],
            }
            pivot_path.write_text(json.dumps(pivot), encoding="utf-8")
            build_path = directory / "build.json"
            build = {
                "schema": "max11-sketch-member-problem-v1",
                "verdict": "PASS",
                "pivot_report_sha256": digest(pivot_path),
                "problem": str(problem),
                "problem_schema": "ELIFTQ02",
                "problem_bytes": problem.stat().st_size,
                "problem_sha256": digest(problem),
                "source_universe": str(universe),
                "source_universe_sha256": digest(universe),
                "pivot_columns_numerator": 2,
                "pivot_columns_denominator": 2,
                "sketch_rows_denominator": 2,
                "linear_rows_denominator": 2,
                "union_hinge_rows_denominator": 3,
                "real_rows_denominator": 5,
                "combined_rows_denominator": 7,
                "exact_batch_records_numerator": 2,
                "exact_batch_records_denominator": 2,
            }
            build_path.write_text(json.dumps(build), encoding="utf-8")
            solver_path = directory / "solver.json"
            solver = {
                "schema": "max11-lift-large-result-v1",
                "verdict": "PASS",
                "input": str(problem),
                "input_sha256": digest(problem),
                "columns_denominator": 2,
                "selected_minor_rows_numerator": 2,
                "selected_minor_rows_denominator": 2,
                "rows_checked_denominator": 7,
                "exact_rows_verified_numerator": 7,
                "exact_rows_verified_denominator": 7,
                "mutation_nonzero_rows_numerator": 4,
                "mutation_rows_checked_denominator": 7,
                "recovered_support_numerator": 2,
                "recovered_support_denominator": 2,
                "recovered_denominator_lcm": "6",
                "prime": 65521,
                "recovery_method": "control",
                "coefficients": [
                    {"source_index": 9, "numerator": "1", "denominator": "2"},
                    {"source_index": 4, "numerator": "-1", "denominator": "3"},
                ],
            }
            solver_path.write_text(json.dumps(solver), encoding="utf-8")
            witness_path = directory / "witness.json"
            report_path = directory / "report.json"
            report = sketch_member_lift.finalize(
                build_path,
                solver_path,
                pivot_path,
                witness_path,
                report_path,
            )
            self.assertEqual(report["verdict"], "PASS")
            self.assertEqual(report["real_rows_verified_numerator"], 5)
            self.assertEqual(report["real_rows_verified_denominator"], 5)
            self.assertEqual(report["coefficient_denominator_factorization"], {"2": 1, "3": 1})
            witness = json.loads(witness_path.read_text(encoding="utf-8"))
            self.assertEqual([entry["column"] for entry in witness["coefficients"]], [4, 9])

    def test_factorization_known_answers(self) -> None:
        self.assertEqual(sketch_member_lift.factorization(1), {})
        self.assertEqual(sketch_member_lift.factorization(304_819_200), {"2": 10, "3": 5, "5": 2, "7": 2})


if __name__ == "__main__":
    unittest.main()
