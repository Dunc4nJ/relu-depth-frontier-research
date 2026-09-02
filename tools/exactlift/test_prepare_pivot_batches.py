from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("prepare_pivot_batches.py")


def pivot_report(pivots: list[int]) -> dict[str, object]:
    packed = b"".join(struct.pack("<Q", value) for value in pivots)
    return {
        "schema": "max11-streamrank-pivots-v1",
        "sketches": [
            {
                "rank_a": len(pivots),
                "rank_augmented": len(pivots),
                "verdict": "MEMBER",
                "pivot_columns": pivots,
                "pivot_columns_u64_le_sha256": hashlib.sha256(packed).hexdigest(),
            }
        ],
    }


class PreparePivotBatchesTests(unittest.TestCase):
    def run_prepare(self, pivots: list[int], batch_size: int) -> tuple[subprocess.CompletedProcess[str], Path, tempfile.TemporaryDirectory[str]]:
        temporary = tempfile.TemporaryDirectory()
        directory = Path(temporary.name)
        report = directory / "pivot.json"
        report.write_text(json.dumps(pivot_report(pivots)), encoding="utf-8")
        output = directory / "plan"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--pivot-report",
                str(report),
                "--output-dir",
                str(output),
                "--batch-size",
                str(batch_size),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        return result, output, temporary

    def test_five_l_last_preserves_pivot_order(self) -> None:
        result, output, temporary = self.run_prepare([4, 9, 754_017], 3)
        self.addCleanup(temporary.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads((output / "gather_plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["synthetic_five_l_pivot_count"], 1)
        self.assertTrue(plan["batches"][0]["include_five_l"])
        order = json.loads((output / "orders/order-000.json").read_text(encoding="utf-8"))
        self.assertEqual(order, [4, 9])

    def test_five_l_in_batch_middle_fails_closed(self) -> None:
        result, _output, temporary = self.run_prepare([4, 754_017, 9], 3)
        self.addCleanup(temporary.cleanup)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not last in its batch", result.stderr)


if __name__ == "__main__":
    unittest.main()
