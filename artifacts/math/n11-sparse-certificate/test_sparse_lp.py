#!/usr/bin/env python3

import gzip
import json
import tempfile
import unittest
from pathlib import Path

import build_saved_csc
import solve_l1


class SparseLpTests(unittest.TestCase):
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
            report = solve_l1.solve(matrix, root / "l1.json", root / "highs.log", 1, 1, 1e-9, 1e-10, 1e-8, 1e6)
            self.assertEqual(report["rounds"][0]["support_numerator"], 2)
            target = matrix / "target.i64le"
            data = bytearray(target.read_bytes())
            data[-8:] = (2).to_bytes(8, "little", signed=True)
            target.write_bytes(data)
            with self.assertRaises(ValueError):
                solve_l1.solve(matrix, root / "bad.json", root / "bad.log", 1, 0, 1e-9, 1e-10, 1e-8, 1e6)


if __name__ == "__main__":
    unittest.main()
