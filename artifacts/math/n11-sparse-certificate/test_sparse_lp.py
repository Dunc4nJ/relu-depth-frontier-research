#!/usr/bin/env python3

import gzip
import json
import tempfile
import unittest
from pathlib import Path

import build_saved_csc
import select_exact_support
import solve_l1
import solve_l1_cuopt_dual


class SparseLpTests(unittest.TestCase):
    def test_dual_candidate_requires_multiplier_and_active_bound(self):
        coefficients = solve_l1_cuopt_dual.np.array([0.5, 0.25, 1e-14, 0.75])
        activity = solve_l1_cuopt_dual.np.array([1.0, 0.8, -1.0, -1.0])
        scaled_bounds = solve_l1_cuopt_dual.np.ones(4)
        positions, slack = solve_l1_cuopt_dual.candidate_positions(
            coefficients, activity, scaled_bounds, 1e-12, 1e-9, 0.0
        )
        self.assertEqual(positions.tolist(), [0, 3])
        self.assertEqual(slack.tolist(), [0.0, 0.19999999999999996, 0.0, 0.0])

    def test_tiny_member_and_negative_target_control(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            system = root / "tiny.jsonl.gz"
            rows = [
                {"A": [], "B": [], "lin": [0, 1], "h": {"1,-1": 1}},
                {"A": [], "B": [], "lin": [0, 1], "h": {"1,-1": -1}},
                {"A": [], "B": [], "lin": [1, 0], "h": {}},
            ]
            with gzip.open(system, "wt") as stream:
                for row in rows:
                    stream.write(json.dumps(row) + "\n")
            matrix = root / "matrix"
            built = build_saved_csc.build(system, matrix)
            self.assertEqual((built["rows_denominator"], built["columns_denominator"], built["nonzeros_denominator"]), (3, 3, 5))
            initial = root / "initial.json"
            initial.write_text(json.dumps({"coefficients": [
                {"column": 0, "coefficient": "1/2"},
                {"column": 1, "coefficient": "1/2"},
            ]}))
            report = solve_l1.solve(matrix, root / "l1.json", root / "highs.log", 1, 1, 1e-9, 1e-10, 1e-8, 1e6, initial, "epigraph")
            self.assertEqual(report["rounds"][0]["support_numerator"], 2)
            self.assertEqual(report["initial_feasible_witness"]["support_numerator"], 2)
            self.assertEqual(report["lp_formulation"], "epigraph")
            selected = select_exact_support.select(
                matrix,
                root / "l1.json",
                root / "pivots.json",
                root / "selection.json",
                1_000_003,
                None,
            )
            self.assertEqual(selected["chosen_independent_support_numerator"], 2)
            target = matrix / "target.i64le"
            data = bytearray(target.read_bytes())
            data[-8:] = (2).to_bytes(8, "little", signed=True)
            target.write_bytes(data)
            with self.assertRaises(ValueError):
                solve_l1.solve(matrix, root / "bad.json", root / "bad.log", 1, 0, 1e-9, 1e-10, 1e-8, 1e6)


if __name__ == "__main__":
    unittest.main()
