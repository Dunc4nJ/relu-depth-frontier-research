"""Independent exact probes for the frozen G-0135 Stage B/C sources.

The probe never imports either subject producer.  It implements the planted
hinge and rational-linear-algebra fixtures from scratch, while invoking the
frozen Stage-B kernel through a temporary, separately compiled client and the
Stage-C producer only through its public ``--self-test`` command.
"""

from __future__ import annotations

import base64
import hashlib
import importlib
import importlib.metadata
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Sequence
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
N = 11
RECORDS = 163_740
BATCH = 32

SUBJECTS = {
    "stage_b_source": (
        "artifacts/math/G-0135/stage_b_pricer/src/main.rs",
        "c591504757815ff63c46d29cfcc2ac10568bea92212ade32490def93b5d862b2",
        "0291920fde55fd9cf6f2429fe64bb52cc83326b8",
    ),
    "stage_b_cargo_manifest": (
        "artifacts/math/G-0135/stage_b_pricer/Cargo.toml",
        "a4057885f58199feb18e733ca01c7ec2a00dc05d8f2700a6dcb04f56825af11d",
        "73ec8f6d29f7308b18be4d49f990bf3b29a400d0",
    ),
    "stage_b_cargo_lock": (
        "artifacts/math/G-0135/stage_b_pricer/Cargo.lock",
        "72315f7a541bf34fe135a25e651d2d85a885652944bdcac6862fb770d29669d3",
        "73ec8f6d29f7308b18be4d49f990bf3b29a400d0",
    ),
    "stage_b_executable": (
        "artifacts/math/G-0135/stage_b_pricer/target/release/g0135-stage-b-batch32-coordinate-pricer",
        "e2e84801749bc0f2ca7bf18a149895531038ee0eab68f964b01ad25f1a3de7ef",
        "0291920fde55fd9cf6f2429fe64bb52cc83326b8",
    ),
    "stage_c_executable_source": (
        "artifacts/math/G-0135/stage_c_master/full_family_master_v3.py",
        "c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a",
        "ff579acd4dcad838a582cd6c8411fdec5650d94e",
    ),
    "stage_c_executable_wrapper": (
        "artifacts/math/G-0135/stage_c_master/run-full-family-master-v3",
        "b125566098be17edc0a572b776e1887813758afc7412324c29408592275ab508",
        "0291920fde55fd9cf6f2429fe64bb52cc83326b8",
    ),
}

DEPENDENCY_PINS = {
    "requirements_lock": (
        "requirements-solvers.lock",
        "dae95ec0dd59c0b30ea69bfe541248049cee612a92d56c4d18e0c3217c170fb8",
    ),
    "python_wheel_hashes": (
        "environment/python-wheel-hashes.txt",
        "68c90da2eecf3285c99ad135ef142070c830fe4b14a4a35ebec265e6ffb3b311",
    ),
    "toolchain_manifest": (
        "environment/toolchain-manifest.txt",
        "a4e7b09efb4d445b9a34217f0aff478771c36542ca8c4d58e5b15e9d6273b81e",
    ),
    "toolchain_description": (
        "TOOLCHAIN.md",
        "ffc55f711d52c90f4a1710cfd55366b2d1249a736db97f17c3a1c3e52188f150",
    ),
    "stage_b_kernel": (
        "artifacts/math/G-0117/src/lib.rs",
        "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6",
    ),
    "stage_c_exact_helper": (
        "artifacts/math/G-0117/fresh_q_cegis_exact.py",
        "ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281",
    ),
    "stage_c_ancestor": (
        "artifacts/math/G-0128/full_family_master_v2.py",
        "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8",
    ),
    "audit_preregistration": (
        "artifacts/reviews/G-0137-g0135-stages-bc-source/PREREGISTRATION.md",
        "e2bda62986001208e4e611ae147071b6932dc9ed99449aa4f54fcd178771948f",
    ),
}

SCIENTIFIC_PATHS = [
    "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json",
    "artifacts/math/G-0135/batch32_global_replay_v1.json",
    "artifacts/math/G-0135/batch32_coordinate_prices_v1.json",
    "artifacts/math/G-0135/full_family_master_result_v3.json",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(path: str) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", path],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def verify_bindings() -> dict[str, object]:
    observed: dict[str, object] = {}
    for label, (name, expected_sha, expected_commit) in SUBJECTS.items():
        path = ROOT / name
        require(path.is_file(), f"missing subject: {name}")
        actual_sha = sha256_path(path)
        actual_commit = git_commit(name)
        require(actual_sha == expected_sha, f"subject SHA drift: {name}")
        require(actual_commit == expected_commit, f"subject commit drift: {name}")
        committed = subprocess.run(
            ["git", "show", f"{actual_commit}:{name}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        require(
            hashlib.sha256(committed).hexdigest() == actual_sha,
            f"working bytes differ from committed subject: {name}",
        )
        observed[label] = {
            "path": name,
            "sha256": actual_sha,
            "git_commit": actual_commit,
        }
    for label, (name, expected_sha) in DEPENDENCY_PINS.items():
        path = ROOT / name
        require(path.is_file(), f"missing dependency pin: {name}")
        actual_sha = sha256_path(path)
        require(actual_sha == expected_sha, f"dependency pin drift: {name}")
        observed[label] = {"path": name, "sha256": actual_sha}
    return observed


def assert_no_scientific_outputs() -> None:
    present = [name for name in SCIENTIFIC_PATHS if (ROOT / name).exists()]
    require(not present, f"scientific output observed: {present}")


def signed_i8_digest(directions: Iterable[Sequence[int]]) -> str:
    payload = bytearray()
    for direction in directions:
        require(len(direction) == N, "direction width drift")
        for value in direction:
            require(-128 <= value <= 127, "i8 overflow")
            payload.append(value & 0xFF)
    return hashlib.sha256(payload).hexdigest()


def decimal_lf_digest(values: Iterable[int]) -> str:
    rendered = "".join(f"{int(value)}\n" for value in values).encode("ascii")
    return hashlib.sha256(rendered).hexdigest()


def i64le_digest(values: Iterable[int]) -> str:
    payload = bytearray()
    for value in values:
        require(-(1 << 63) <= value < (1 << 63), "i64 overflow")
        payload.extend(int(value).to_bytes(8, "little", signed=True))
    return hashlib.sha256(payload).hexdigest()


def matrix_for_record(record: dict[str, object]) -> list[list[int]]:
    active = int(record["active"])
    matrix = [[0 for _ in range(active)] for _ in range(active)]
    for sign, field in [(-1, "negative"), (1, "positive")]:
        for u, v in record[field]:  # type: ignore[index]
            require(0 <= u < v < active, "invalid planted edge")
            matrix[u][v] += sign
            matrix[v][u] += sign
    return matrix


def active_direction(direction: Sequence[int]) -> bool:
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return True
    return False


def normalize_word(word: Sequence[int]) -> tuple[int, ...] | None:
    first = next((value for value in word if value), None)
    if first is None:
        return None
    divisor = 0
    for value in word:
        divisor = math.gcd(divisor, abs(value))
    sign = 1 if first > 0 else -1
    direction = tuple(sign * value // divisor for value in word)
    return direction if active_direction(direction) else None


def literal_hinge_map(record: dict[str, object]) -> dict[tuple[int, ...], int]:
    """Enumerate injections directly, with inactive-label multiplicity."""

    active = int(record["active"])
    matrix = matrix_for_record(record)
    inactive_factor = math.factorial(N - active)
    output: dict[tuple[int, ...], int] = {}
    for positions in itertools.combinations(range(N), active):
        for order in itertools.permutations(range(active)):
            at_rank = dict(zip(positions, order, strict=True))
            placed: list[int] = []
            word: list[int] = []
            for rank in range(N):
                if rank not in at_rank:
                    word.append(0)
                    continue
                vertex = at_rank[rank]
                word.append(sum(matrix[vertex][other] for other in placed))
                placed.append(vertex)
            direction = normalize_word(word)
            if direction is None:
                continue
            divisor = 0
            for value in word:
                divisor = math.gcd(divisor, abs(value))
            output[direction] = output.get(direction, 0) + divisor * inactive_factor
    return output


def independent_matching_price(
    record: dict[str, object], direction: Sequence[int]
) -> int:
    """Subset-DP price independently transcribed from the mathematical spec."""

    active = int(record["active"])
    matrix = matrix_for_record(record)
    inactive = N - active
    full = (1 << active) - 1

    increment = [[0 for _ in range(1 << active)] for _ in range(active)]
    for vertex in range(active):
        for mask in range(1 << active):
            increment[vertex][mask] = sum(
                matrix[vertex][other] for other in range(active) if mask & (1 << other)
            )

    unlabelled = 0
    for scale in range(-5, 6):
        if not scale:
            continue
        current = {0: 1}
        for rank, coordinate in enumerate(direction):
            expected = scale * coordinate
            nxt: dict[int, int] = {}
            for mask, count in current.items():
                placed = mask.bit_count()
                inactive_used = rank - placed
                if expected == 0 and inactive_used < inactive:
                    nxt[mask] = nxt.get(mask, 0) + count
                for vertex in range(active):
                    bit = 1 << vertex
                    if not mask & bit and increment[vertex][mask] == expected:
                        nxt[mask | bit] = nxt.get(mask | bit, 0) + count
            current = nxt
        unlabelled += abs(scale) * current.get(full, 0)
    return unlabelled * math.factorial(inactive)


def invoke_frozen_kernel(
    records: Sequence[dict[str, object]], directions: Sequence[Sequence[int]]
) -> list[list[int]]:
    direction_source = ",\n".join(
        "[" + ",".join(str(value) for value in direction) + "]"
        for direction in directions
    )

    def record_source(record: dict[str, object]) -> str:
        negative = ",".join(
            f"[{u},{v}]"
            for u, v in record["negative"]  # type: ignore[index]
        )
        positive = ",".join(
            f"[{u},{v}]"
            for u, v in record["positive"]  # type: ignore[index]
        )
        return (
            "Record{sequence:0,signed_mass:"
            f"{len(record['negative'])},active_vertices:{record['active']},"
            f"negative_edges:vec![{negative}],positive_edges:vec![{positive}]}}"
        )

    record_source_text = ",\n".join(record_source(record) for record in records)
    main = f"""
use g0117_global_coordinate_pricer::{{hinge_coefficients, Record}};
fn main() {{
    let directions: [[i8; 11]; {len(directions)}] = [{direction_source}];
    let records = [{record_source_text}];
    for record in records {{
        let prices = hinge_coefficients(&record, &directions).unwrap();
        println!("{{:?}}", prices);
    }}
}}
"""
    with tempfile.TemporaryDirectory(prefix="g0137-kernel-") as directory:
        temporary = Path(directory)
        (temporary / "src").mkdir()
        (temporary / "Cargo.toml").write_text(
            "[package]\nname='g0137-kernel-probe'\nversion='0.0.0'\nedition='2024'\n"
            "[dependencies]\n"
            "g0117-global-coordinate-pricer={path='"
            + (ROOT / "artifacts/math/G-0117").as_posix()
            + "'}\n",
            encoding="utf-8",
        )
        (temporary / "src/main.rs").write_text(main, encoding="utf-8")
        completed = subprocess.run(
            [
                "cargo",
                "run",
                "--offline",
                "--quiet",
                "--release",
                "--manifest-path",
                str(temporary / "Cargo.toml"),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
            env={**os.environ, "CARGO_TERM_COLOR": "never"},
        )
    return [json.loads(line) for line in completed.stdout.splitlines() if line]


def stage_b_probe() -> dict[str, object]:
    records: list[dict[str, object]] = [
        {
            "active": 4,
            "negative": [(0, 1), (1, 2), (2, 3)],
            "positive": [(0, 2), (0, 3), (1, 3)],
        },
        {
            "active": 4,
            "negative": [(0, 1), (1, 2)],
            "positive": [(0, 2), (2, 3)],
        },
    ]
    literal_maps = [literal_hinge_map(record) for record in records]
    directions = sorted(literal_maps[0])[:8]
    require(len(directions) == 8, "planted literal support too small")
    expected = [
        [literal.get(tuple(direction), 0) for direction in directions]
        for literal in literal_maps
    ]
    independent_dp = [
        [independent_matching_price(record, direction) for direction in directions]
        for record in records
    ]
    require(expected == independent_dp, "literal/DP hinge routes disagree")
    frozen = invoke_frozen_kernel(records, directions)
    require(
        frozen == expected, "frozen Stage-B kernel disagrees with independent route"
    )

    direction_major = [
        [frozen[record][direction] for record in range(len(records))]
        for direction in range(len(directions))
    ]
    aggregate_digest = i64le_digest(value for row in direction_major for value in row)
    corrupt = [row[:] for row in direction_major]
    corrupt[0][0] += 1
    require(
        i64le_digest(value for row in corrupt for value in row) != aggregate_digest,
        "coordinate mutation preserved digest",
    )
    require(BATCH * RECORDS == 5_239_680, "production coordinate census drift")
    require(
        sum(len(row) for row in direction_major) == len(directions) * len(records),
        "planted coordinate census drift",
    )
    require(
        sum(len(row) for row in direction_major[:-1]) != len(directions) * len(records),
        "truncated planted census escaped",
    )

    huge = int(
        "363926958096805201036820427711562039306502598983761375638772015048"
        "437029843340726060005211433825934240455425251219346437121889771857"
        "125452344913600504791360"
    )
    coefficients = [huge, -huge + 1]
    exact_dots = [
        sum(coefficient * value for coefficient, value in zip(coefficients, row))
        for row in direction_major
    ]
    coefficient_mutant = [
        dot + row[0] for dot, row in zip(exact_dots, direction_major, strict=True)
    ]
    require(
        exact_dots != coefficient_mutant
        and decimal_lf_digest(exact_dots) != decimal_lf_digest(coefficient_mutant),
        "arbitrary-precision coefficient mutant escaped",
    )

    signed_digest = signed_i8_digest(directions)
    reordered_digest = signed_i8_digest(list(reversed(directions)))
    require(signed_digest != reordered_digest, "direction order mutation escaped")
    residual_digest = decimal_lf_digest(exact_dots)
    residual_plus_one = exact_dots[:]
    residual_plus_one[0] += 1
    require(
        residual_digest != decimal_lf_digest(residual_plus_one),
        "decimal-LF residual mutant escaped",
    )
    return {
        "records": len(records),
        "directions": [list(direction) for direction in directions],
        "literal_support_sizes": [len(value) for value in literal_maps],
        "frozen_kernel_prices": frozen,
        "literal_equals_independent_dp_equals_frozen_kernel": True,
        "signed_i8_direction_sha256": signed_digest,
        "decimal_lf_exact_dot_sha256": residual_digest,
        "direction_major_i64le_sha256": aggregate_digest,
        "production_coordinate_census": BATCH * RECORDS,
        "coordinate_mutant_rejected": True,
        "census_truncation_rejected": True,
        "coefficient_plus_one_mutant_rejected": True,
        "direction_order_mutant_rejected": True,
        "residual_decimal_mutant_rejected": True,
        "arbitrary_precision_dot_exceeds_i128": any(
            abs(value) >= (1 << 127) for value in exact_dots
        ),
    }


def rref(
    rows: Sequence[Sequence[int | Fraction]],
) -> tuple[list[list[Fraction]], list[int]]:
    matrix = [[Fraction(value) for value in row] for row in rows]
    if not matrix:
        return matrix, []
    columns = len(matrix[0])
    require(all(len(row) == columns for row in matrix), "ragged matrix")
    pivots: list[int] = []
    pivot_row = 0
    for column in range(columns):
        candidate = next(
            (row for row in range(pivot_row, len(matrix)) if matrix[row][column]),
            None,
        )
        if candidate is None:
            continue
        matrix[pivot_row], matrix[candidate] = matrix[candidate], matrix[pivot_row]
        scale = matrix[pivot_row][column]
        matrix[pivot_row] = [value / scale for value in matrix[pivot_row]]
        for row in range(len(matrix)):
            if row == pivot_row or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                value - factor * pivot
                for value, pivot in zip(matrix[row], matrix[pivot_row], strict=True)
            ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return matrix, pivots


def rank_columns(
    columns: Sequence[Sequence[int]], target: Sequence[int] | None = None
) -> int:
    width = len(columns) + (1 if target is not None else 0)
    rows = []
    for row in range(len(columns[0])):
        values = [column[row] for column in columns]
        if target is not None:
            values.append(target[row])
        rows.append(values)
    reduced, pivots = rref(rows)
    require(all(len(row) == width for row in reduced), "rank width drift")
    return len(pivots)


def primitive(values: Sequence[int]) -> list[int]:
    divisor = 0
    for value in values:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "zero vector is not primitive")
    result = [value // divisor for value in values]
    first = next(value for value in result if value)
    return [-value for value in result] if first < 0 else result


def stage_c_probe() -> dict[str, object]:
    target = [1, 1, 0]
    columns = [[1, 0, 1], [0, 1, 1], [0, 0, 1]]
    seed = columns[:2]
    require(rank_columns(seed) == 2, "seed rank drift")
    require(rank_columns(seed, target) == 3, "seed augmented rank drift")
    separator = primitive([1, 1, -1])
    require(
        all(
            sum(y * value for y, value in zip(separator, column, strict=True)) == 0
            for column in seed
        ),
        "planted separator misses seed nullspace",
    )
    pairing = sum(y * value for y, value in zip(separator, target, strict=True))
    require(pairing == 2, "planted target pairing drift")
    prices = [
        sum(y * value for y, value in zip(separator, column, strict=True))
        for column in columns
    ]
    require(prices == [0, 0, -1], "canonical first-violation scan drift")
    require(
        rank_columns(columns) == rank_columns(columns, target) == 3, "member rank drift"
    )
    coefficients = [1, 1, -2]
    replay = [
        sum(
            coefficient * column[row]
            for coefficient, column in zip(coefficients, columns, strict=True)
        )
        for row in range(3)
    ]
    require(replay == target, "exact member replay failed")
    coefficient_mutant = coefficients[:]
    coefficient_mutant[0] += 1
    mutant_replay = [
        sum(
            coefficient * column[row]
            for coefficient, column in zip(coefficient_mutant, columns, strict=True)
        )
        for row in range(3)
    ]
    require(mutant_replay != target, "member coefficient mutant escaped")

    nonmember_columns = seed
    require(
        rank_columns(nonmember_columns) == 2
        and rank_columns(nonmember_columns, target) == 3
        and all(
            sum(y * value for y, value in zip(separator, column, strict=True)) == 0
            for column in nonmember_columns
        )
        and pairing != 0,
        "exact nonmember branch failed",
    )
    sign_mutant = [-value for value in separator]
    require(
        next(value for value in separator if value) > 0,
        "canonical separator sign drift",
    )
    require(
        next(value for value in sign_mutant if value) < 0, "sign mutant not exposed"
    )
    coordinate_mutant = separator[:]
    coordinate_mutant[0] += 1
    require(
        any(
            sum(y * value for y, value in zip(coordinate_mutant, column, strict=True))
            for column in nonmember_columns
        ),
        "separator coordinate mutant still annihilates family",
    )
    require(
        sum(y * value for y, value in zip(separator, target, strict=True))
        != pairing + 1,
        "separator pairing mutant escaped",
    )

    expected_target = target
    scale_mutant = [2 * value for value in target]
    require(scale_mutant != expected_target, "target-scale mutant escaped")
    expected_rows = list(zip(*columns, strict=True))
    row_mutant = expected_rows[:]
    row_mutant[0], row_mutant[1] = row_mutant[1], row_mutant[0]
    require(row_mutant != expected_rows, "row-order mutant escaped")
    declared_columns = 3
    scanned_columns = len(nonmember_columns)
    require(scanned_columns != declared_columns, "omitted-column census mutant escaped")

    return {
        "member_fixture": {
            "seed_rank": 2,
            "seed_augmented_rank": 3,
            "first_violating_sequence": 2,
            "final_rank": 3,
            "final_augmented_rank": 3,
            "integer_coefficients": [str(value) for value in coefficients],
            "all_rows_replayed": True,
        },
        "nonmember_fixture": {
            "rank": 2,
            "augmented_rank": 3,
            "primitive_separator": [str(value) for value in separator],
            "target_pairing": str(pairing),
            "all_columns_annihilated": True,
        },
        "member_and_nonmember_branches_exercised": True,
        "coefficient_plus_one_mutant_rejected": True,
        "target_scale_mutant_rejected": True,
        "omitted_column_census_rejected": True,
        "row_order_mutant_rejected": True,
        "separator_sign_mutant_rejected": True,
        "separator_coordinate_mutant_rejected": True,
        "separator_pairing_mutant_rejected": True,
    }


def cli_checks() -> dict[str, object]:
    stage_b = ROOT / SUBJECTS["stage_b_executable"][0]
    stage_c = ROOT / SUBJECTS["stage_c_executable_source"][0]
    stage_c_wrapper = ROOT / SUBJECTS["stage_c_executable_wrapper"][0]
    assert_no_scientific_outputs()
    stage_b_selftest = subprocess.run(
        [str(stage_b), "--self-test"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    stage_b_preflight = subprocess.run(
        [
            str(stage_b),
            "--preflight-static",
            "artifacts/math/G-0113/panel_solver_input_v1.json",
            "artifacts/math/G-0128/full_family_master_result_v2.json",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    stage_c_selftest = subprocess.run(
        [str(stage_c_wrapper), "--self-test"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    system_python = subprocess.run(
        ["/usr/bin/python3", "-B", str(stage_c), "--self-test"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    require(
        system_python.returncode != 0
        and "Stage C must run in the pinned CPython 3.13.7 .venv"
        in system_python.stderr,
        "Stage C accepted the unpinned system Python",
    )
    require(
        Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
        and sys.version_info[:3] == (3, 13, 7),
        "independent probe is not running in the pinned CPython 3.13.7 .venv",
    )
    distribution = importlib.metadata.distribution("python-flint")
    files = list(distribution.files or [])
    record = next(file for file in files if file.name == "RECORD")
    record_path = Path(distribution.locate_file(record))
    require(
        sha256_path(record_path)
        == "4157ce9fde01368d5ad3a215d94073a0706b62253bc53170f33c00633629b088",
        "installed python-flint RECORD drift",
    )
    hashed_files = [file for file in files if file.hash is not None]
    require(
        distribution.version == "0.9.0"
        and len(files) == 139
        and len(hashed_files) == 114,
        "installed python-flint metadata census drift",
    )
    for file in hashed_files:
        installed = Path(distribution.locate_file(file))
        actual = hashlib.sha256(installed.read_bytes()).digest()
        expected = file.hash.value
        require(
            base64.urlsafe_b64encode(actual).decode("ascii").rstrip("=") == expected
            and installed.stat().st_size == file.size,
            f"installed python-flint file drift: {file}",
        )
    require("flint" not in sys.modules, "python-flint imported before byte attestation")
    flint = importlib.import_module("flint")
    require(flint.__version__ == "0.9.0", "imported python-flint version drift")
    assert_no_scientific_outputs()
    return {
        "stage_b_self_test": stage_b_selftest.stdout.strip(),
        "stage_b_static_preflight": stage_b_preflight.stdout.strip(),
        "stage_c_committed_wrapper_self_test": stage_c_selftest.stdout.strip(),
        "stage_c_system_python_exit_code": system_python.returncode,
        "stage_c_system_python_rejected_as_unpinned": True,
        "pinned_python_version": sys.version.split()[0],
        "python_flint_version": distribution.version,
        "python_flint_record_sha256": sha256_path(record_path),
        "python_flint_record_rows": len(files),
        "python_flint_hashed_files_verified": len(hashed_files),
        "python_flint_verified_before_import": True,
        "python_flint_imported_version": flint.__version__,
        "pinned_stage_c_invocation_required": True,
        "scientific_outputs_absent_after": True,
    }


def static_contract_checks() -> dict[str, object]:
    stage_b = (ROOT / SUBJECTS["stage_b_source"][0]).read_text(encoding="utf-8")
    stage_c = (ROOT / SUBJECTS["stage_c_executable_source"][0]).read_text(
        encoding="utf-8"
    )
    required_b = [
        "HINGE_ENTRIES: usize = K * RECORDS",
        "exact_dot(row: &[i64]",
        "record_major.len() == RECORDS",
        "direction_major.len() == K",
        "publish_exclusive",
        "inputs.custody == custody_end",
        "planned_outputs",
        "shared-manifest output contracts drift",
    ]
    required_c = [
        "OLD_ROWS = 380",
        "STAGE_B_ROWS = 32",
        "RECORDS = 163_740",
        "full_target = old_target + [0] * STAGE_B_ROWS",
        "for sequence in range(record_count)",
        "terminal separator scan truncated",
        "appended column failed exact unit rank increase",
        "primitive integer all-row replay failed",
        "write_exclusive(output_path, result)",
        'rehash_snapshot(prepared["snapshot"])',
        "def validate_python_runtime()",
        "Path(sys.prefix).resolve() == expected_prefix",
        "sys.version_info[:3] == (3, 13, 7)",
        'distribution.version == "0.9.0"',
        "PYTHON_FLINT_RECORD_SHA256",
        "hashed == PYTHON_FLINT_HASHED_FILES",
        'flint = importlib.import_module("flint")',
        'require(flint.__version__ == "0.9.0"',
    ]
    require(
        all(fragment in stage_b for fragment in required_b), "Stage-B call-path drift"
    )
    require(
        all(fragment in stage_c for fragment in required_c), "Stage-C call-path drift"
    )
    require(
        stage_c.index("hashed == PYTHON_FLINT_HASHED_FILES")
        < stage_c.index('flint = importlib.import_module("flint")'),
        "Stage-C native import precedes installed-byte attestation",
    )
    return {
        "stage_b_required_call_paths": len(required_b),
        "stage_c_required_call_paths": len(required_c),
        "stage_b_manifest_schema_and_path_checks_reachable": True,
        "stage_c_exact_planned_output_contract_reachable": True,
        "stage_b_shared_manifest_denies_unknown_fields": (
            "#[serde(deny_unknown_fields)]\nstruct SharedManifest" in stage_b
        ),
        "stage_c_shared_manifest_requires_exact_top_level_key_set": (
            "set(manifest)"
            in stage_c[
                stage_c.index("def validate_shared_manifest") : stage_c.index(
                    "G0128_RESULT_KEYS"
                )
            ]
        ),
        "stage_c_runtime_attestation_reachable_from_fixed_input_validation": (
            "validate_python_runtime()"
            in stage_c[
                stage_c.index("def validate_fixed_inputs") : stage_c.index(
                    "def expected_planned_outputs"
                )
            ]
        ),
        "stage_c_runtime_attestation_reachable_from_self_test": (
            "runtime = validate_python_runtime()"
            in stage_c[stage_c.index("def self_test") : stage_c.index("def main")]
        ),
        "stage_c_installed_bytes_attested_before_native_import": True,
    }


def main() -> int:
    require(Path.cwd().resolve() == ROOT, "run from repository root")
    assert_no_scientific_outputs()
    receipt = {
        "schema": "max11-g0137-g0135-stages-bc-independent-probe-v1",
        "status": "PASS",
        "bindings": verify_bindings(),
        "stage_b": stage_b_probe(),
        "stage_c": stage_c_probe(),
        "cli": cli_checks(),
        "static_contract": static_contract_checks(),
        "scientific_manifest_observed": False,
        "scientific_output_observed": False,
    }
    assert_no_scientific_outputs()
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
