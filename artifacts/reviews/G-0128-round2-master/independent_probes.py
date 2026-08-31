#!/usr/bin/env python3
"""Independent synthetic probes for the frozen G-0128 master source.

This never builds a scientific manifest and never invokes the scientific master.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import tempfile


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "artifacts/math/G-0128/full_family_master_v2.py"
EXPECTED_SOURCE_SHA256 = "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_subject():
    assert sha256_path(SOURCE) == EXPECTED_SOURCE_SHA256
    specification = importlib.util.spec_from_file_location("g0128_round2_review_subject", SOURCE)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def fraction_rank(rows: list[list[int]]) -> int:
    if not rows:
        return 0
    matrix = [[Fraction(value) for value in row] for row in rows]
    height = len(matrix)
    width = len(matrix[0])
    assert all(len(row) == width for row in matrix)
    pivot_row = 0
    for column in range(width):
        pivot = next((row for row in range(pivot_row, height) if matrix[row][column]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        scale = matrix[pivot_row][column]
        matrix[pivot_row] = [value / scale for value in matrix[pivot_row]]
        for row in range(height):
            if row == pivot_row or not matrix[row][column]:
                continue
            scale = matrix[row][column]
            matrix[row] = [
                value - scale * pivot_value
                for value, pivot_value in zip(matrix[row], matrix[pivot_row], strict=True)
            ]
        pivot_row += 1
        if pivot_row == height:
            break
    return pivot_row


def exact_algebra_probes(subject) -> dict[str, int]:
    helper = subject.AUDITED.load_module(subject.AUDITED.HELPER_PATH, "g0128_round2_probe_helper")
    generator = random.Random(0x60128)
    rank_cases = 0
    separator_cases = 0
    rank_growth_cases = 0
    for _ in range(400):
        height = generator.randint(2, 7)
        width = generator.randint(1, 6)
        rows = [
            [generator.randint(-4, 4) for _ in range(width)]
            for _ in range(height)
        ]
        expected_rank = fraction_rank(rows)
        matrix = helper.qmatrix(rows)
        assert int(matrix.rank()) == expected_rank
        target = [generator.randint(-5, 5) for _ in range(height)]
        augmented_rows = [row + [target[index]] for index, row in enumerate(rows)]
        augmented_rank = fraction_rank(augmented_rows)
        assert int(helper.qmatrix(augmented_rows).rank()) == augmented_rank
        rank_cases += 1
        if augmented_rank != expected_rank:
            separator, pairing, _ = helper.first_target_separator(matrix, rows, target)
            assert len(separator) == height
            assert math.gcd(*[abs(value) for value in separator]) == 1
            assert next(value for value in separator if value) > 0
            assert pairing == sum(a * b for a, b in zip(separator, target, strict=True)) != 0
            assert all(
                sum(separator[row] * rows[row][column] for row in range(height)) == 0
                for column in range(width)
            )
            separator_cases += 1

            violating = [generator.randint(-4, 4) for _ in range(height)]
            while sum(a * b for a, b in zip(separator, violating, strict=True)) == 0:
                violating = [generator.randint(-4, 4) for _ in range(height)]
            grown = [row + [violating[index]] for index, row in enumerate(rows)]
            assert fraction_rank(grown) == expected_rank + 1
            rank_growth_cases += 1

    member_cases = 0
    coefficient_permutation_cases = 0
    while member_cases < 250:
        size = generator.randint(1, 5)
        rows = [
            [generator.randint(-5, 5) for _ in range(size)]
            for _ in range(size)
        ]
        if fraction_rank(rows) != size:
            continue
        target = [generator.randint(-6, 6) for _ in range(size)]
        if not any(target):
            continue
        matrix = helper.qmatrix(rows)
        rational = matrix.solve(helper.qmatrix([[value] for value in target]))
        fractions = [Fraction(str(rational[index, 0])) for index in range(size)]
        integers, scale = subject.normalize_member(fractions)
        assert scale > 0
        common = scale
        for value in integers:
            common = math.gcd(common, abs(value))
        assert common == 1
        assert all(
            sum(rows[row][column] * integers[column] for column in range(size))
            == scale * target[row]
            for row in range(size)
        )
        first = next(index for index, value in enumerate(integers) if value)
        mutant = integers[:]
        mutant[first] += 1
        assert any(
            sum(rows[row][column] * mutant[column] for column in range(size))
            != scale * target[row]
            for row in range(size)
        )
        unequal = next(
            (
                (first_index, second_index)
                for first_index in range(size)
                for second_index in range(first_index + 1, size)
                if integers[first_index] != integers[second_index]
            ),
            None,
        )
        if unequal is not None:
            permuted = integers[:]
            first_index, second_index = unequal
            permuted[first_index], permuted[second_index] = (
                permuted[second_index],
                permuted[first_index],
            )
            assert any(
                sum(rows[row][column] * permuted[column] for column in range(size))
                != scale * target[row]
                for row in range(size)
            )
            coefficient_permutation_cases += 1
        member_cases += 1

    previous_rank = fraction_rank([[1], [0], [0]])
    non_unit_growth_rank = fraction_rank([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    assert previous_rank == 1 and non_unit_growth_rank == 3
    try:
        subject.require(
            non_unit_growth_rank == previous_rank + 1,
            "appended column failed unit exact rank increase",
        )
    except subject.MasterError:
        non_unit_rank_mutants = 1
    else:
        raise AssertionError("non-unit rank-growth mutant was accepted")

    return {
        "rank_cases": rank_cases,
        "separator_cases": separator_cases,
        "rank_growth_cases": rank_growth_cases,
        "member_cases": member_cases,
        "coefficient_permutation_cases": coefficient_permutation_cases,
        "non_unit_rank_mutants": non_unit_rank_mutants,
    }


def scan_probes(subject) -> dict[str, int]:
    visited: list[int] = []
    columns = [[1, 0], [2, 0], [-1, 0], [7, 0], [0, 1]]

    def load_final(index: int) -> list[int]:
        visited.append(index)
        return columns[index]

    assert subject.scan_first_violation_records([0, 1], len(columns), load_final) == (4, 1, 5)
    assert visited == list(range(5))

    visited.clear()
    null_columns = [[1, 1], [2, 2], [-3, -3], [5, 5], [0, 0]]

    def load_null(index: int) -> list[int]:
        visited.append(index)
        return null_columns[index]

    assert subject.scan_first_violation_records([1, -1], len(null_columns), load_null) is None
    assert visited == list(range(5))

    visited.clear()

    def load_failure(index: int) -> list[int]:
        visited.append(index)
        if index == 3:
            raise RuntimeError("planted loader failure")
        return [1, 1]

    try:
        subject.scan_first_violation_records([1, -1], 5, load_failure)
    except RuntimeError as error:
        assert str(error) == "planted loader failure"
    else:
        raise AssertionError("loader exception was swallowed into a null scan")
    assert visited == [0, 1, 2, 3]
    return {"final_column_visits": 5, "null_scan_visits": 5, "failure_index": 3}


def target_and_row_order_probes(subject) -> dict[str, str | int]:
    target = subject.build_target()
    panel = subject.load_json(subject.AUDITED.PANEL_INPUT_PATH)["target"]
    assert len(target) == subject.ROWS == 380
    assert target[: subject.PANEL_ROWS] == [int(value) for value in panel]
    assert target[subject.PANEL_ROWS : subject.PANEL_ROWS + subject.N - 1] == [0] * 10
    assert target[subject.PANEL_ROWS + subject.N - 1] == math.factorial(subject.N)
    assert target[subject.PANEL_ROWS + subject.N :] == [0] * 68

    accumulated = [[index] for index in range(subject.ACCUMULATED_ROWS)]
    old_rows = [
        [subject.ACCUMULATED_ROWS + index] for index in range(subject.OLD_BATCH_ROWS)
    ]
    new_rows = [
        [subject.ACCUMULATED_ROWS + subject.OLD_BATCH_ROWS + index]
        for index in range(subject.NEW_BATCH_ROWS)
    ]
    old_block = {
        "role": "old_batch32",
        "selection_receipt": subject.relative(subject.AUDITED.REPLAY_PATH),
        "price_receipt": subject.relative(subject.AUDITED.PRICE_PATH),
        "rows": old_rows,
    }
    new_block = {
        "role": "new_batch32",
        "selection_receipt": subject.relative(subject.G0126_RECEIPT_PATH),
        "price_receipt": subject.relative(subject.G0127_PRICE_PATH),
        "rows": new_rows,
    }
    assembled = subject.ordered_hinge_rows(accumulated, old_block, new_block)
    assert [row[0] for row in assembled] == list(range(68))
    try:
        subject.ordered_hinge_rows(accumulated, new_block, old_block)
    except subject.MasterError:
        pass
    else:
        raise AssertionError("old/new block swap was accepted")

    target_digest = hashlib.sha256(
        ("\n".join(str(value) for value in target) + "\n").encode("ascii")
    ).hexdigest()
    return {"target_entries": len(target), "target_decimal_lf_sha256": target_digest, "hinge_rows": 68}


def atomic_write_probes(subject) -> dict[str, int]:
    failures = 0
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as raw:
        directory = Path(raw)

        existing = directory / "existing.json"
        subject.write_exclusive(existing, {"first": True})
        original = existing.read_bytes()
        try:
            subject.write_exclusive(existing, {"second": True})
        except FileExistsError:
            failures += 1
        else:
            raise AssertionError("exclusive publication overwrote an existing artifact")
        assert existing.read_bytes() == original

        serialization = directory / "serialization.json"
        try:
            subject.write_exclusive(serialization, {"bad": {1}})
        except TypeError:
            failures += 1
        else:
            raise AssertionError("non-serializable payload was accepted")
        assert not serialization.exists()

        link_failure = directory / "link-failure.json"
        real_link = subject.os.link

        def fail_link(_source, _target):
            raise OSError("planted link failure")

        subject.os.link = fail_link
        try:
            try:
                subject.write_exclusive(link_failure, {"ok": True})
            except OSError as error:
                assert str(error) == "planted link failure"
                failures += 1
            else:
                raise AssertionError("link failure was swallowed")
        finally:
            subject.os.link = real_link
        assert not link_failure.exists()

        write_failure = directory / "write-failure.json"
        real_fdopen = subject.os.fdopen

        class FailingDestination:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, exception_type, exception, traceback):
                self.stream.close()
                return False

            def fileno(self):
                return self.stream.fileno()

            def write(self, payload: bytes):
                self.stream.write(payload[: max(1, len(payload) // 2)])
                raise OSError("planted temporary write failure")

        def failing_fdopen(descriptor: int, mode: str):
            return FailingDestination(real_fdopen(descriptor, mode))

        subject.os.fdopen = failing_fdopen
        try:
            try:
                subject.write_exclusive(write_failure, {"ok": True})
            except OSError as error:
                assert str(error) == "planted temporary write failure"
                failures += 1
            else:
                raise AssertionError("temporary write failure was swallowed")
        finally:
            subject.os.fdopen = real_fdopen
        assert not write_failure.exists()

        directory_fsync_failure = directory / "directory-fsync-failure.json"
        real_fsync = subject.os.fsync
        calls = 0

        def fail_second_fsync(descriptor: int):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("planted directory fsync failure")
            return real_fsync(descriptor)

        subject.os.fsync = fail_second_fsync
        try:
            try:
                subject.write_exclusive(directory_fsync_failure, {"ok": True})
            except OSError as error:
                assert str(error) == "planted directory fsync failure"
                failures += 1
            else:
                raise AssertionError("directory fsync failure was swallowed")
        finally:
            subject.os.fsync = real_fsync
        assert calls == 2 and not directory_fsync_failure.exists()

        leftovers = [path for path in directory.iterdir() if path.name.startswith(".")]
        assert not leftovers

    return {"failure_paths_rejected": failures}


def path_and_seed_probes(subject) -> dict[str, int]:
    rejected = 0

    def expect_master_error(action) -> None:
        nonlocal rejected
        try:
            action()
        except subject.MasterError:
            rejected += 1
        else:
            raise AssertionError("planted custody/seed mutation was accepted")

    components = subject.load_validated_components()
    prior = components["prior_result"]

    duplicate = json.loads(json.dumps(prior))
    duplicate_value = duplicate["selected_sequences"][0]
    duplicate["selected_sequences"][1] = duplicate_value
    duplicate["support_sequences"][1] = duplicate_value
    expect_master_error(
        lambda: subject.validate_prior_documents(
            components["prior_manifest"],
            duplicate,
            components["old_replay"],
            components["old_price"],
        )
    )

    out_of_range = json.loads(json.dumps(prior))
    out_of_range["selected_sequences"][-1] = subject.RECORDS
    out_of_range["support_sequences"][-1] = subject.RECORDS
    expect_master_error(
        lambda: subject.validate_prior_documents(
            components["prior_manifest"],
            out_of_range,
            components["old_replay"],
            components["old_price"],
        )
    )

    review_directory = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(dir=review_directory) as raw, tempfile.TemporaryDirectory() as outside_raw:
        directory = Path(raw)
        original = directory / "original.bin"
        original.write_bytes(b"same inode target")
        alias = directory / "alias.bin"
        alias.symlink_to(original)
        digest = sha256_path(original)
        original_expected = subject.AUDITED.EXPECTED_INPUTS
        static_expected = subject.STATIC_EXPECTED_INPUTS
        subject.AUDITED.EXPECTED_INPUTS = {
            subject.relative(original): digest,
            alias.relative_to(subject.ROOT).as_posix(): digest,
        }
        subject.STATIC_EXPECTED_INPUTS = {}
        try:
            expect_master_error(lambda: subject.validate_expected_inputs(include_future=False))
        finally:
            subject.AUDITED.EXPECTED_INPUTS = original_expected
            subject.STATIC_EXPECTED_INPUTS = static_expected

        escape = directory / "escape"
        escape.symlink_to(Path(outside_raw), target_is_directory=True)
        expect_master_error(lambda: subject.contained(escape / "artifact.bin"))

    return {"production_mutations_rejected": rejected, "components_loaded": 1}


def main() -> int:
    subject = load_subject()
    assert not subject.MANIFEST_PATH.exists()
    assert not subject.RESULT_PATH.exists()
    receipt = {
        "schema": "g0128-round2-independent-probes-v1",
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "exact_algebra": exact_algebra_probes(subject),
        "scan": scan_probes(subject),
        "target_and_row_order": target_and_row_order_probes(subject),
        "atomic_write": atomic_write_probes(subject),
        "path_and_seed": path_and_seed_probes(subject),
        "scientific_manifest_observed": False,
        "scientific_result_observed": False,
        "result": "PASS",
    }
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
