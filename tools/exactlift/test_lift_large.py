import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lift_large
import support_lift


class LiftLargeRowSelectionTests(unittest.TestCase):
    def test_candidate_retry_finds_exact_independent_real_rows(self) -> None:
        columns = [
            support_lift.ExactColumn(0, [0, 0], {"1,-1": 1}, None, None),
            support_lift.ExactColumn(1, [0, 0], {"1,0,-1": 1}, None, None),
            support_lift.ExactColumn(2, [0, 1], {}, None, None),
        ]
        row_index = support_lift.build_row_index(columns)
        selected, _seconds, attempts = lift_large.select_real_rows(
            columns, row_index, 1_000_003, candidate_count=3, candidate_seed=7
        )
        self.assertEqual(len(selected), 3)
        self.assertEqual(len(set(selected)), 3)
        self.assertEqual(attempts[-1]["rank_numerator"], 3)
        self.assertEqual(attempts[-1]["required_rank_denominator"], 3)

    def test_candidate_count_below_rank_is_rejected(self) -> None:
        columns = [
            support_lift.ExactColumn(0, [1, 0], {}, None, None),
            support_lift.ExactColumn(1, [0, 1], {}, None, None),
        ]
        with self.assertRaisesRegex(ValueError, "at least the pivot rank"):
            lift_large.select_real_rows(columns, {}, 1_000_003, 1, 9)


if __name__ == "__main__":
    unittest.main()
