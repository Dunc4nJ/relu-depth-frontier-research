#!/usr/bin/env python3
"""Fail-closed cross-binder for the bounded MAX11 family theorem.

This verifier does not redo either expensive proof obligation.  G-0012 owns
the exact left-dual arithmetic and G-0014 owns the independent semantic
regeneration of the frozen matrix columns.  This file proves that those two
reports, the matrix metadata, the final theorem, and its referee report all
refer to the same bytes, dimensions, row convention, and target scaling.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import platform
import re
import sys
from pathlib import Path

import numpy as np


SCHEMA = "max11-bounded-family-theorem-bundle-verification-v1"
SPEC_SCHEMA = "max11-bounded-family-theorem-bundle-spec-v1"
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE / "bundle_spec_v1.json"
DEFAULT_REPORT = HERE / "bundle_verification_v1.json"

SOURCE_PATH = "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
G18_SOURCE_PATH = "subjects/max-relu-known/certificates/certificate_10_4.json"
EXACT_LIFT_SEARCH_PATH = "artifacts/math/G-0006/exact_lift_search.py"
EVALUATE_MINIMAL_LIFTS_PATH = "artifacts/math/G-0006/evaluate_minimal_lifts.py"
CLASSES_PATH = "artifacts/math/G-0006/isomorphism_classes_v2.json"
BUILD_CUT_MATRIX_PATH = "artifacts/math/G-0008/build_cut_matrix.py"
MODULAR_CEGIS_PATH = "artifacts/math/G-0008/modular_cegis.py"
SELECTION_PATH = "artifacts/math/G-0008/cut_selection_01_02_03_04.json"
MATRIX_PATH = "artifacts/math/G-0008/cut_matrix_01_02_03_04.npz"
MODULAR_SOLUTION_PATH = "artifacts/math/G-0008/mod_solution_01_02_03_04_p1000003_v3.json"
OBSTRUCTION_EXTRACTOR_V1_PATH = "artifacts/math/G-0008/extract_modular_obstruction_v1.py"
OBSTRUCTION_PATH = "artifacts/math/G-0008/mod_obstruction_01_02_03_04_p1000003_v1.json"
BETA2_CLASSES_PATH = "artifacts/math/G-0009/beta2_common_classes.json"
CROSS_CLASSES_PATH = "artifacts/math/G-0009/cross_component_classes.json"
COMPACT_DUAL_SCRIPT_PATH = "artifacts/math/G-0010/compact_dual_search.py"
CUT_ONLY_DUAL_SCRIPT_PATH = "artifacts/math/G-0010/cut_only_dual.py"
COMPACT_DUAL_PATH = "artifacts/math/G-0010/g0005_anchored_dual_p1000003_v1.json"
PROBE_04_PATH = "artifacts/math/G-0010/cut_only_dual_probes_04_v1.json"
PROBE_06_PATH = "artifacts/math/G-0010/cut_only_dual_probes_06_more_v1.json"
PROBE_HOLDOUT_PATH = "artifacts/math/G-0010/cut_only_dual_probe_holdout_1000081_v1.json"
DUAL_GENERATOR_PATH = "artifacts/math/G-0011/cut_only_exact_dual.py"
DUAL_PATH = "artifacts/math/G-0011/cut_only_exact_left_dual_v1.json.gz"
G12_SCRIPT_PATH = "artifacts/math/G-0012/audit_exact_cut_only_witness.py"
G12_REPORT_PATH = "artifacts/math/G-0012/exact_cut_only_audit_v1.json"
G14_SCRIPT_PATH = "artifacts/math/G-0014/semantic_matrix_audit.py"
G14_REPORT_PATH = "artifacts/math/G-0014/semantic_matrix_audit_v1.json"
THEOREM_PATH = "artifacts/math/G-0015/THEOREM_DRAFT.md"
REFEREE_PATH = "artifacts/math/G-0016/REFEREE_REPORT.md"
G18_SCRIPT_PATH = "artifacts/math/G-0018/audit_beta2_union_mapping.py"
G18_REPORT_PATH = "artifacts/math/G-0018/beta2_union_mapping_audit_v1.json"
CROSS_PROBE_SCRIPT_PATH = "artifacts/math/G-0018/probe_cross_class0_omega.py"
CROSS_PROBE_REPORT_PATH = "artifacts/math/G-0018/cross_class0_omega_probe_v1.json"

N = 11
RAW_COUNT = 16_000
CLASS_COUNT = 9_804
HINGE_COUNT = 7_135
ROW_COUNT = 7_146
RANK = 5_269
TARGET = math.factorial(N)
NORMALIZED_TARGET = TARGET // 4
MATRIX_ENTRIES = ROW_COUNT * CLASS_COUNT
RELATION_ENTRIES = (RANK + 1) * CLASS_COUNT

# These are the frozen mathematical, semantic, theorem, and review inputs.
# The final three hard pins prevent a rewritten spec from silently accepting
# altered prose or a substituted semantic/referee result.
PINNED_HASHES = {
    SOURCE_PATH: "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    G18_SOURCE_PATH: "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    EXACT_LIFT_SEARCH_PATH: "8defb04ef8192b62c1386f2685d8cbe98095ab5683cc25d5cb8858edcd936970",
    EVALUATE_MINIMAL_LIFTS_PATH: "a2ed2e6d8749770fb5a0732ab65f84b592d0562c68947f5ae35676237e1f2862",
    CLASSES_PATH: "3f24edd0b8928256e90fe41fbafd846b693efd37285065da907a1ffdf9561f48",
    BUILD_CUT_MATRIX_PATH: "cfb74ea98ab5cb5f283de277c24539264b465553251587bec68c4ff775a48c30",
    MODULAR_CEGIS_PATH: "1acfbdc35eb2d24016de449a5958d743a1ffc07818a8a78809e39fffd2c7b26a",
    SELECTION_PATH: "e37b7637a9edf541ac5e1caf6bebd98f8d04b928ee1525bfaaa194474d5ef235",
    MATRIX_PATH: "acfbb2b0f89e5cca6c72b396ec1c86e0558e3a5e759e5c7f2d29f5ba03f5e758",
    MODULAR_SOLUTION_PATH: "15e7686781db3154c83a83bc00dabd265ed511cbdcc11db37621f83e10445f53",
    OBSTRUCTION_EXTRACTOR_V1_PATH: "ccb12f782ed85ac615f60e67a414f27ed82ca4b321afdc93c72cebe2d9887adb",
    OBSTRUCTION_PATH: "90c2dbdae008894f2bcdfcd840246c3832abfaeb7d705d1deb10d20e0eadc992",
    BETA2_CLASSES_PATH: "11ab55ccb121fc1051331edcbfa9f796c020448266c07fb550976c4656976ce0",
    CROSS_CLASSES_PATH: "c1a6c84ec189690ec640733283da3e566dcc9ef3c312dafbf243f4727eb88878",
    COMPACT_DUAL_SCRIPT_PATH: "d8be30c7d016e4f7d7d4afb517bc8bd012f462770ce6c3a5e17ea45723125762",
    CUT_ONLY_DUAL_SCRIPT_PATH: "8233adee64895a4604e15b2255e2425d47023129d602615a468363ad7e713773",
    COMPACT_DUAL_PATH: "cd4cd839eead97c6678db850d83058a8adf65215d7d48d5894a625dbb31d69d2",
    PROBE_04_PATH: "84ada6d857ad66cb427223b29318703628d0612a12fbaef12cf4e418123b94c1",
    PROBE_06_PATH: "8255000cd832e3913f9ac4c76f206e39eea42d51743ff7000eeab8e86eada2c6",
    PROBE_HOLDOUT_PATH: "23c8b6bd9562507659f33796339a2acfc1596c90c2aa454ff888df4659ac32d5",
    DUAL_GENERATOR_PATH: "e41d34289c6102fef5b5e1943777f597ed9a970e75e7cabcc536da88399e5abc",
    DUAL_PATH: "fe6768c8377aa1cc813dbd00805c807d4dd23f05ba246700503aa8598a951758",
    G12_SCRIPT_PATH: "b3a324c3a3dae2899c0695a8c14e50f370135050556aa796669cb4de3af1b31a",
    G12_REPORT_PATH: "9c26c0e6329804ee2a87ec9ef6b86cd935c91551ca503a97409368f41ac3676a",
    G14_SCRIPT_PATH: "e2042e7508606d2da926f345cdf9d42a3c114ea83aee5ae23f84705e02c4775c",
    G14_REPORT_PATH: "581a8d9b5a1cd28f1ee2896e119a262977084369d32550ca8523fd205596ec71",
    THEOREM_PATH: "852fa1b15ee06c7f04628bded536cd7e29d0533d5740eb96c11fbf4408dc4d9a",
    REFEREE_PATH: "d2a35817866b4ba30a4c89fe39f460e3368a6a23d3bdc78e9033e748e1fce855",
    G18_SCRIPT_PATH: "85b556eeb53584d8541dccd3bc689e4d3347e6153f255427d609e6cabb0dafc1",
    G18_REPORT_PATH: "88ba04742803439713e3a9fd7c01171c3f6fe3a6edc64b8d99b19c546d4c009d",
    CROSS_PROBE_SCRIPT_PATH: "7cde60263a7065229781c1c73c273869b5a05f3906a1d40adf76a3e7d60b5c65",
    CROSS_PROBE_REPORT_PATH: "bb5ae0197453a56a1440b9867ec095037938208c9819243133aaaa435144a722",
}
MATRIX_ARRAY_SHA256 = "aaa4f481f6e29f05ac226f2de44e3829563190fd6daddd8a66130e9257493b0c"
RAW_PAIR_LIST_SHA256 = "d1c6755e5585c5c4f3160589bcb21ca1a989161fb289946b9bbb935a0d6cd569"
SEMANTIC_RAW_PAIR_LIST_SHA256 = "1a86cb9355660032bea2184804fcf0183598879e5ce8c1ec8d1e420e168f2800"
ACCEPTED_SOURCE_INDICES_SHA256 = "72cc9e154af4b234b44b1a60a5d239273cceec44508e0e933dca31a047dfddc9"
DIRECTION_LIST_SHA256 = "5424579b72c8cac5ea282b9f697ee4c7dac4dd2c463effb8998fce47f539516a"
SUPPORT_ROWS_SHA256 = "e2cced10f78f73d0925044684497687f34bc4839327f6ba2513cd86c5b8738f2"
TARGET_ARRAY_SHA256 = "dad1b99177a00fd71ed93c226e5343fd491cfb713b684993b096e6a473da3f45"

CLAIM_BOUNDARY = (
    "exact nonmembership for the registered 16000-raw/9804-class "
    "same-component family union the 6740 named beta2-common edge-multiset lifts"
)
BOUNDED_STATEMENT = (
    "MAX11 is not in the real span of the registered 16000-raw/9804-class "
    "same-component family union the 6740 named beta2-common edge-multiset lifts."
)
BOUNDED_NO_CLAIM = (
    "Does not settle unrestricted MAX11 or exclude cross-component, multi-edge, "
    "other pair-atom, asymmetric, or arbitrary finite two-hidden-layer real-weight "
    "ReLU-network representations."
)
THEOREM_SCOPE_MARKER = "G0015_MACHINE_SCOPE_V1"
REVIEW_RECORD_MARKER = "G0016_MACHINE_REVIEW_V1"
THEOREM_VISIBLE_BEGIN = "<!-- G0015_VISIBLE_SCOPE_V1_BEGIN -->"
THEOREM_VISIBLE_END = "<!-- G0015_VISIBLE_SCOPE_V1_END -->"
REVIEW_VISIBLE_BEGIN = "<!-- G0016_VISIBLE_REVIEW_V1_BEGIN -->"
REVIEW_VISIBLE_END = "<!-- G0016_VISIBLE_REVIEW_V1_END -->"
THEOREM_VISIBLE_SCOPE = (
    f"> **Claim (normative):** {BOUNDED_STATEMENT}\n>\n"
    f"> **No-claim (normative):** {BOUNDED_NO_CLAIM}"
)
REVIEW_VISIBLE_RECORD = (
    "> **Verdict (normative):** PASS_BOUNDED_PROOF_LOGIC\n>\n"
    "> **Tier (normative):** same-family T1\n>\n"
    f"> **Scope (normative):** {CLAIM_BOUNDARY}"
)
THEOREM_STATEMENT_SECTION = (
    "## Statement\n\n"
    "The delimited claim/no-claim pair below is the only normative theorem "
    "statement in this file.\n\n"
    f"{THEOREM_VISIBLE_BEGIN}\n{THEOREM_VISIBLE_SCOPE}\n{THEOREM_VISIBLE_END}"
)
THEOREM_LEVEL2_HEADINGS = [
    "Registered family",
    "Statement",
    "Ordered-cone normal form",
    "Exact separating certificate",
    "Quotient transport",
    "Common-edge multiset lemma",
    "Evidence gates",
    "Explicit non-claims",
]
REFEREE_LEVEL2_HEADINGS = ["Lemma-by-lemma verdicts", "Required disposition"]


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def unique_json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_loads(raw: str, label: str) -> object:
    try:
        return json.loads(raw, object_pairs_hook=unique_json_object)
    except (json.JSONDecodeError, ValueError) as error:
        raise AssertionError(f"{label} is not strict JSON: {error}") from error


def extract_comment_json(text: str, marker: str) -> dict[str, object]:
    prefix = f"<!-- {marker} "
    require(text.count(prefix) == 1, f"{marker} record missing or duplicated")
    start = text.index(prefix) + len(prefix)
    stop = text.find(" -->", start)
    require(stop >= 0, f"{marker} record is unterminated")
    raw = text[start:stop]
    value = strict_json_loads(raw, f"{marker} record")
    require(isinstance(value, dict), f"{marker} record is not an object")
    require(
        raw.encode("ascii") == canonical_json_bytes(value),
        f"{marker} record is not canonical JSON",
    )
    return value


def extract_visible_block(text: str, begin: str, end: str, label: str) -> str:
    require(text.count(begin) == 1 and text.count(end) == 1, f"{label} markers missing or duplicated")
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    require(stop > start, f"{label} block is empty or reversed")
    return text[start:stop].strip("\n")


def remove_comment_record(text: str, marker: str) -> str:
    prefix = f"<!-- {marker} "
    require(text.count(prefix) == 1, f"{marker} record missing or duplicated")
    start = text.index(prefix)
    stop = text.find(" -->", start)
    require(stop >= 0, f"{marker} record is unterminated")
    return text[:start] + text[stop + 4 :]


def level2_headings(text: str) -> list[str]:
    return re.findall(r"(?m)^## (?!#)(.+)$", text)


def level2_section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    require(text.count(marker) == 1, f"level-2 section {heading!r} missing or duplicated")
    start = text.index(marker)
    following = re.search(r"(?m)^## (?!#)", text[start + len(marker) :])
    stop = len(text) if following is None else start + len(marker) + following.start()
    return text[start:stop].rstrip("\n")


def require_outside_fence(text: str, token: str, label: str) -> None:
    position = text.index(token)
    prefix = text[:position]
    backtick_fences = len(re.findall(r"(?m)^\s*```", prefix))
    tilde_fences = len(re.findall(r"(?m)^\s*~~~", prefix))
    require(backtick_fences % 2 == 0 and tilde_fences % 2 == 0, f"{label} lies inside a code fence")


def expected_theorem_scope(observed: dict[str, str]) -> dict[str, object]:
    return {
        "schema": "max11-bounded-theorem-scope-v1",
        "claim_boundary": CLAIM_BOUNDARY,
        "statement": BOUNDED_STATEMENT,
        "field": "R",
        "family_F_raw_occurrences": 16_000,
        "family_F_quotient_classes": 9_804,
        "family_B_raw_occurrences": 6_740,
        "family_B_quotient_classes": 4_916,
        "family_B_adds_new_symmetrised_functions": False,
        "no_claim": BOUNDED_NO_CLAIM,
        "premise_sha256": {
            "source_certificate": observed[SOURCE_PATH],
            "exact_dual": observed[DUAL_PATH],
            "exact_audit": observed[G12_REPORT_PATH],
            "semantic_audit": observed[G14_REPORT_PATH],
            "beta2_mapping_audit": observed[G18_REPORT_PATH],
        },
    }


def validate_theorem_scope(record: dict[str, object], observed: dict[str, str]) -> None:
    require(
        canonical_json_bytes(record) == canonical_json_bytes(expected_theorem_scope(observed)),
        "normative theorem scope record mismatch",
    )


def expected_review_record(observed: dict[str, str]) -> dict[str, object]:
    return {
        "schema": "max11-bounded-theorem-review-v1",
        "subject_sha256": observed[THEOREM_PATH],
        "verdict": "PASS_BOUNDED_PROOF_LOGIC",
        "tier": "same-family T1",
        "claim_boundary": CLAIM_BOUNDARY,
        "semantic_report_sha256": observed[G14_REPORT_PATH],
        "t2_or_human_review_obtained": False,
    }


def validate_review_record(record: dict[str, object], observed: dict[str, str]) -> None:
    require(
        canonical_json_bytes(record) == canonical_json_bytes(expected_review_record(observed)),
        "normative referee record mismatch",
    )


def validate_visible_theorem(text: str) -> None:
    require(level2_headings(text) == THEOREM_LEVEL2_HEADINGS, "theorem section structure changed")
    require(
        level2_section(text, "Statement") == THEOREM_STATEMENT_SECTION,
        "formal theorem Statement section is not the exact bounded template",
    )
    require_outside_fence(text, THEOREM_VISIBLE_BEGIN, "visible theorem scope")
    require(
        extract_visible_block(
            text, THEOREM_VISIBLE_BEGIN, THEOREM_VISIBLE_END, "visible theorem scope"
        )
        == THEOREM_VISIBLE_SCOPE,
        "human-visible theorem scope disagrees with the normative record",
    )
    outside_statement = text.replace(THEOREM_STATEMENT_SECTION, "", 1)
    outside_statement = remove_comment_record(outside_statement, THEOREM_SCOPE_MARKER)
    competing_claim = re.search(
        r"(?i)\bMAX11\s+(?:is\s+not|cannot|is\s+outside|has\s+no|is\s+unrepresentable)",
        outside_statement,
    )
    require(competing_claim is None, "competing MAX11 nonmembership claim outside Statement section")


def validate_visible_review(text: str) -> None:
    require(level2_headings(text) == REFEREE_LEVEL2_HEADINGS, "referee section structure changed")
    require_outside_fence(text, REVIEW_VISIBLE_BEGIN, "visible referee verdict")
    first_section = text.find("\n## ")
    require(first_section > text.index(REVIEW_VISIBLE_END), "visible referee verdict is not in the preamble")
    require(
        extract_visible_block(
            text, REVIEW_VISIBLE_BEGIN, REVIEW_VISIBLE_END, "visible referee verdict"
        )
        == REVIEW_VISIBLE_RECORD,
        "human-visible referee verdict disagrees with the normative record",
    )
    outside_record = text.replace(
        f"{REVIEW_VISIBLE_BEGIN}\n{REVIEW_VISIBLE_RECORD}\n{REVIEW_VISIBLE_END}", "", 1
    )
    outside_record = remove_comment_record(outside_record, REVIEW_RECORD_MARKER)
    normalized = re.sub(r"[*_`]", "", outside_record)
    require(
        re.search(
            r"(?im)^\s*>?\s*verdict(?:\s*\([^\n)]*\))?\s*(?::|=|—|-|\bis\b)",
            normalized,
        )
        is None,
        "referee contains a second formal verdict declaration",
    )


def must_reject(label: str, action) -> dict[str, object]:
    try:
        action()
    except (AssertionError, KeyError, TypeError, ValueError) as error:
        return {"mutation": label, "result": "REJECTED", "reason": str(error)}
    raise AssertionError(f"scope hostile mutation was accepted: {label}")


def load_regular(relative: str) -> Path:
    relative_path = Path(relative)
    require(not relative_path.is_absolute(), f"absolute path forbidden in bundle: {relative}")
    path = ROOT / relative_path
    resolved = path.resolve()
    require(resolved.is_relative_to(ROOT.resolve()), f"path escapes bundle root: {relative}")
    require(path.is_file() and not path.is_symlink(), f"not a contained regular file: {relative}")
    return path


def load_json(relative: str) -> dict[str, object]:
    value = strict_json_loads(load_regular(relative).read_text(encoding="utf-8"), relative)
    require(isinstance(value, dict), f"JSON root is not an object: {relative}")
    return value


def load_gzip_json(relative: str) -> dict[str, object]:
    with gzip.open(load_regular(relative), "rt", encoding="utf-8") as source:
        value = strict_json_loads(source.read(), relative)
    require(isinstance(value, dict), f"gzip JSON root is not an object: {relative}")
    return value


def verify_file_identities(spec: dict[str, object]) -> dict[str, str]:
    require(spec.get("schema") == SPEC_SCHEMA, "bundle spec schema mismatch")
    require(
        spec.get("claim_boundary") == CLAIM_BOUNDARY,
        "bundle spec claim boundary was weakened or broadened",
    )
    files = spec.get("files_sha256")
    require(isinstance(files, dict), "bundle spec files_sha256 is not an object")
    required = set(PINNED_HASHES) | {
        G14_REPORT_PATH,
        THEOREM_PATH,
        REFEREE_PATH,
        str(Path(__file__).resolve().relative_to(ROOT)),
    }
    require(required <= set(files), f"bundle spec is missing required files: {sorted(required-set(files))}")
    observed: dict[str, str] = {}
    for relative, expected in sorted(files.items()):
        require(isinstance(relative, str) and isinstance(expected, str), "invalid file hash entry")
        require(len(expected) == 64, f"invalid SHA-256 text for {relative}")
        path = load_regular(relative)
        actual = sha256_path(path)
        require(actual == expected, f"file hash mismatch for {relative}: {actual} != {expected}")
        observed[relative] = actual
    for relative, expected in PINNED_HASHES.items():
        require(observed.get(relative) == expected, f"pinned hash mismatch for {relative}")
    return observed


def verify_selection_and_classes(observed: dict[str, str]) -> tuple[dict[str, object], dict[str, object]]:
    classes = load_json(CLASSES_PATH)
    require(classes.get("schema") == "max11-minimal-lifts-isomorphism-v2", "class schema mismatch")
    require(classes.get("n") == N, "class n mismatch")
    require(classes.get("raw_candidate_count") == RAW_COUNT, "raw class census mismatch")
    require(classes.get("class_count") == CLASS_COUNT, "quotient class census mismatch")
    require(classes.get("source_certificate_sha256") == observed[SOURCE_PATH], "class/source hash mismatch")
    require(classes.get("raw_pair_list_sha256") == RAW_PAIR_LIST_SHA256, "frozen raw-pair hash mismatch")
    require(len(classes.get("raw_to_class", [])) == RAW_COUNT, "raw_to_class length mismatch")
    require(len(classes.get("representative_raw_indices", [])) == CLASS_COUNT, "representative length mismatch")
    class_sizes = classes.get("class_sizes", [])
    require(len(class_sizes) == CLASS_COUNT and sum(map(int, class_sizes)) == RAW_COUNT, "class sizes mismatch")

    selection = load_json(SELECTION_PATH)
    require(selection.get("schema") == "max11-exact-hinge-cut-selection-v1", "selection schema mismatch")
    require(selection.get("n") == N, "selection n mismatch")
    require(selection.get("selected_count") == HINGE_COUNT, "selection count mismatch")
    directions = selection.get("directions")
    require(isinstance(directions, list) and len(directions) == HINGE_COUNT, "direction list length mismatch")
    require(
        hashlib.sha256(canonical_json_bytes(directions)).hexdigest() == DIRECTION_LIST_SHA256,
        "canonical direction-list hash mismatch",
    )
    return classes, selection


def verify_matrix(observed: dict[str, str], selection: dict[str, object]) -> dict[str, object]:
    with np.load(load_regular(MATRIX_PATH), allow_pickle=False) as archive:
        require(
            sorted(archive.files)
            == ["class_indices", "classes_sha256", "matrix", "schema", "selection_sha256", "source_manifest_json"],
            "matrix archive keys mismatch",
        )
        require(str(archive["schema"][0]) == "max11-exact-hinge-cut-matrix-v1", "matrix schema mismatch")
        require(str(archive["selection_sha256"][0]) == observed[SELECTION_PATH], "matrix/selection hash mismatch")
        require(str(archive["classes_sha256"][0]) == observed[CLASSES_PATH], "matrix/classes hash mismatch")
        require(
            np.array_equal(archive["class_indices"], np.arange(CLASS_COUNT, dtype=np.int64)),
            "matrix class indices are not identity order",
        )
        matrix = archive["matrix"]
        require(matrix.shape == (ROW_COUNT, CLASS_COUNT) and matrix.dtype == np.int64, "matrix shape/dtype mismatch")
        matrix_array_hash = hashlib.sha256(matrix.tobytes(order="C")).hexdigest()
        require(matrix_array_hash == MATRIX_ARRAY_SHA256, "matrix int64 C-byte hash mismatch")
        source_manifest = strict_json_loads(
            str(archive["source_manifest_json"][0]), "matrix source_manifest_json"
        )
    require(source_manifest == selection.get("source_selections"), "matrix source manifest mismatch")
    return {
        "archive_sha256": observed[MATRIX_PATH],
        "int64_c_sha256": matrix_array_hash,
        "rows": ROW_COUNT,
        "columns": CLASS_COUNT,
        "entries": MATRIX_ENTRIES,
    }


def verify_exact_dual(observed: dict[str, str]) -> tuple[dict[str, object], dict[str, object]]:
    solution = load_json(MODULAR_SOLUTION_PATH)
    require(
        solution.get("schema") == "max11-modular-cegis-solution-v3",
        "modular solution schema mismatch",
    )
    require(solution.get("target_member_mod_prime") is False, "modular solution is not a failed solve")
    require(solution.get("selection_sha256") == observed[SELECTION_PATH], "solution/selection hash mismatch")
    require(solution.get("classes_sha256") == observed[CLASSES_PATH], "solution/classes hash mismatch")
    require(solution.get("cut_matrix_sha256") == observed[MATRIX_PATH], "solution/matrix hash mismatch")
    require(solution.get("cut_matrix_int64_c_sha256") == MATRIX_ARRAY_SHA256, "solution matrix-array hash mismatch")
    source_links = {
        "exact_lift_search_sha256": EXACT_LIFT_SEARCH_PATH,
        "evaluate_minimal_lifts_sha256": EVALUATE_MINIMAL_LIFTS_PATH,
        "build_cut_matrix_sha256": BUILD_CUT_MATRIX_PATH,
        "modular_cegis_sha256": MODULAR_CEGIS_PATH,
    }
    for field, relative in source_links.items():
        require(solution.get(field) == observed[relative], f"solution source hash mismatch: {field}")

    obstruction = load_json(OBSTRUCTION_PATH)
    require(obstruction.get("schema") == "max11-modular-left-dual-v1", "obstruction schema mismatch")
    require(obstruction.get("solution_sha256") == observed[MODULAR_SOLUTION_PATH], "obstruction/solution hash mismatch")
    require(
        obstruction.get("extractor_sha256") == observed[OBSTRUCTION_EXTRACTOR_V1_PATH],
        "obstruction/extractor hash mismatch",
    )
    require(obstruction.get("selection_sha256") == observed[SELECTION_PATH], "obstruction/selection hash mismatch")
    require(obstruction.get("classes_sha256") == observed[CLASSES_PATH], "obstruction/classes hash mismatch")
    require(obstruction.get("cut_matrix_sha256") == observed[MATRIX_PATH], "obstruction/matrix hash mismatch")
    require(
        obstruction.get("all_candidate_columns_annihilated_mod_prime") is True,
        "modular obstruction annihilation flag false",
    )
    require(int(obstruction.get("target_pairing_mod_prime", 0)) != 0, "modular obstruction target pairing is zero")
    for field, relative in source_links.items():
        require(obstruction.get(field) == observed[relative], f"obstruction source hash mismatch: {field}")

    compact = load_json(COMPACT_DUAL_PATH)
    require(compact.get("script_sha256") == observed[COMPACT_DUAL_SCRIPT_PATH], "compact dual/script mismatch")
    for relative in (PROBE_04_PATH, PROBE_06_PATH, PROBE_HOLDOUT_PATH):
        probe = load_json(relative)
        require(probe.get("script_sha256") == observed[CUT_ONLY_DUAL_SCRIPT_PATH], f"probe/script mismatch: {relative}")

    dual = load_gzip_json(DUAL_PATH)
    require(dual.get("schema") == "max11-cut-only-exact-left-dual-v1", "dual schema mismatch")
    require(dual.get("result") == "exact-left-dual", "dual result mismatch")
    require(dual.get("cut_matrix_sha256") == observed[MATRIX_PATH], "dual/matrix hash mismatch")
    require(dual.get("selection_sha256") == observed[SELECTION_PATH], "dual/selection hash mismatch")
    require(dual.get("classes_sha256") == observed[CLASSES_PATH], "dual/classes hash mismatch")
    require(dual.get("obstruction_sha256") == observed[OBSTRUCTION_PATH], "dual/obstruction hash mismatch")
    require(dual.get("compact_witness_sha256") == observed[COMPACT_DUAL_PATH], "dual/compact-witness hash mismatch")
    require(dual.get("script_sha256") == observed[DUAL_GENERATOR_PATH], "dual/generator hash mismatch")
    require(dual.get("candidate_columns") == CLASS_COUNT, "dual candidate count mismatch")
    require(dual.get("verified_candidate_columns") == CLASS_COUNT, "dual verified count mismatch")
    require(dual.get("rank") == RANK, "dual rank mismatch")
    require(dual.get("all_candidate_columns_annihilated_exactly") is True, "dual annihilation flag false")
    require(dual.get("failing_cut_row") == ROW_COUNT - 1, "dual failing row mismatch")
    require(dual.get("primitive_failing_row_divisor") == 4, "dual failing row divisor mismatch")
    require(dual.get("raw_target_pairing_with_failing_coefficient_one") == TARGET, "dual raw target mismatch")
    require(dual.get("normalized_target_pairing_integer") == NORMALIZED_TARGET, "dual normalized target mismatch")
    pivot_rows = [int(value) for value in dual.get("pivot_cut_rows", [])]
    divisors = [int(value) for value in dual.get("primitive_pivot_row_divisors", [])]
    numerators = dual.get("primitive_solution_numerators", [])
    require(len(pivot_rows) == len(divisors) == len(numerators) == RANK, "dual support-array lengths mismatch")
    require(len(set(pivot_rows + [ROW_COUNT - 1])) == RANK + 1, "dual support is not unique")
    require(all(0 <= row < ROW_COUNT for row in pivot_rows), "dual support row out of range")
    support_hash = hashlib.sha256(
        np.asarray(pivot_rows + [ROW_COUNT - 1], dtype=np.int64).tobytes(order="C")
    ).hexdigest()
    require(support_hash == SUPPORT_ROWS_SHA256, "dual support-row hash mismatch")

    audit = load_json(G12_REPORT_PATH)
    require(audit.get("schema") == "max11-cut-only-exact-independent-audit-v1", "G-0012 schema mismatch")
    require(audit.get("verdict") == "PASS_BOUNDED_EXACT_IDENTITY", "G-0012 verdict mismatch")
    require(audit.get("certificate_sha256") == observed[DUAL_PATH], "G-0012/dual hash mismatch")
    require(
        audit.get("certificate_generator_sha256") == observed[DUAL_GENERATOR_PATH],
        "G-0012/generator hash mismatch",
    )
    require(audit.get("script_sha256") == observed[G12_SCRIPT_PATH], "G-0012 script hash mismatch")
    require(audit.get("input_sha256_start_and_end_identical") is True, "G-0012 inputs changed during run")
    audit_inputs = audit.get("input_sha256", {})
    for relative in (
        CLASSES_PATH,
        SELECTION_PATH,
        MATRIX_PATH,
        OBSTRUCTION_PATH,
        COMPACT_DUAL_PATH,
        PROBE_04_PATH,
        PROBE_06_PATH,
        PROBE_HOLDOUT_PATH,
        DUAL_GENERATOR_PATH,
        DUAL_PATH,
    ):
        require(audit_inputs.get(relative) == observed[relative], f"G-0012 input link mismatch: {relative}")
    require(audit.get("matrix_int64_c_sha256") == MATRIX_ARRAY_SHA256, "G-0012 matrix-array hash mismatch")
    require(audit.get("exact_columns_replayed") == CLASS_COUNT, "G-0012 column count mismatch")
    require(audit.get("exact_relation_entries_replayed") == RELATION_ENTRIES, "G-0012 relation-entry count mismatch")
    require(audit.get("frozen_matrix_entries_bound_by_content_hash") == MATRIX_ENTRIES, "G-0012 matrix-entry count mismatch")
    require(audit.get("raw_target_pairing_with_failing_coefficient_one") == TARGET, "G-0012 raw target mismatch")
    require(audit.get("normalized_primitive_target_pairing") == NORMALIZED_TARGET, "G-0012 normalized target mismatch")
    require(audit.get("smallest_discrepancy") is None, "G-0012 recorded a discrepancy")
    require(audit.get("all_eleven_delivered_modular_vectors_match_exact_reduction") is True, "11-prime reduction failed")
    require(len(audit.get("eleven_prime_reductions", [])) == 11, "G-0012 prime census mismatch")
    require(audit.get("all_hostile_tampers_rejected") is True, "hostile certificate test failed")
    require(len(audit.get("hostile_tests", [])) == 6, "hostile-test census mismatch")
    support = audit.get("support", {})
    require(
        support.get("pivot_rows") == RANK
        and support.get("failing_row") == ROW_COUNT - 1
        and support.get("primitive_failing_row_gcd") == 4
        and support.get("all_pivot_row_gcds_recomputed") is True,
        "G-0012 support metadata mismatch",
    )
    return dual, audit


def verify_semantic_report(observed: dict[str, str], audit: dict[str, object]) -> dict[str, object]:
    report = load_json(G14_REPORT_PATH)
    require(report.get("schema") == "max11-semantic-matrix-cleanroom-audit-v1", "G-0014 schema mismatch")
    require(report.get("result") == "PASS", "G-0014 result mismatch")
    before = report.get("inputs_sha256_before", {})
    after = report.get("inputs_sha256_after", {})
    require(report.get("inputs_stable_during_run") is True and before == after, "G-0014 inputs changed")
    expected_links = {
        "producer_script": G14_SCRIPT_PATH,
        "source_certificate": SOURCE_PATH,
        "classes": CLASSES_PATH,
        "selection": SELECTION_PATH,
        "cut_matrix": MATRIX_PATH,
        "exact_dual": DUAL_PATH,
    }
    for label, relative in expected_links.items():
        require(before.get(label) == observed[relative], f"G-0014 input link mismatch: {label}")

    raw = report.get("raw_family", {})
    require(raw.get("accepted_source_term_count") == 252, "G-0014 accepted-source census mismatch")
    require(raw.get("raw_candidate_count") == RAW_COUNT, "G-0014 raw-family census mismatch")
    require(
        raw.get("component_size_pair_counts") == {"2+8": 168, "3+7": 39, "4+6": 32, "5+5": 13},
        "G-0014 component census mismatch",
    )
    require(raw.get("accepted_source_indices_sha256") == ACCEPTED_SOURCE_INDICES_SHA256, "accepted-index hash mismatch")
    require(
        raw.get("semantic_raw_pair_list_sha256_without_newline") == SEMANTIC_RAW_PAIR_LIST_SHA256,
        "semantic raw-list hash mismatch",
    )
    require(
        raw.get("frozen_serialization_raw_pair_list_sha256_with_newline") == RAW_PAIR_LIST_SHA256,
        "frozen-serialization raw-list hash mismatch",
    )

    quotient = report.get("quotient", {})
    require(quotient.get("class_count") == CLASS_COUNT, "G-0014 quotient class count mismatch")
    for key in (
        "raw_pair_list_recorded_sha256_exact_match",
        "partition_exact_match_up_to_class_label_bijection",
        "mapped_class_sizes_exact_match",
        "every_frozen_representative_bound_to_claimed_block",
    ):
        require(quotient.get(key) is True, f"G-0014 quotient gate failed: {key}")

    selection = report.get("selection", {})
    require(selection.get("direction_count") == HINGE_COUNT, "G-0014 direction count mismatch")
    for key in (
        "all_integer_nonzero_zero_sum_primitive_first_nonzero_positive",
        "all_ordered_cone_active_via_negative_proper_prefix",
        "unique_lexicographically_sorted",
    ):
        require(selection.get(key) is True, f"G-0014 selection validation failed: {key}")
    require(selection.get("directions_canonical_json_sha256") == DIRECTION_LIST_SHA256, "G-0014 direction hash mismatch")

    replay = report.get("matrix_semantic_replay", {})
    require(replay.get("rows_compared") == ROW_COUNT, "G-0014 row count mismatch")
    require(replay.get("columns_compared") == CLASS_COUNT, "G-0014 column count mismatch")
    require(replay.get("entries_compared") == MATRIX_ENTRIES, "G-0014 entry count mismatch")
    require(replay.get("mismatched_columns") == 0, "G-0014 mismatched columns")
    require(replay.get("mismatched_entries") == 0, "G-0014 mismatched entries")
    require(replay.get("dual_support_mismatched_entries") == 0, "G-0014 dual-support mismatch")
    require(replay.get("regenerated_matrix_int64_c_sha256") == MATRIX_ARRAY_SHA256, "G-0014 regenerated hash mismatch")
    require(report.get("frozen_matrix_int64_c_sha256") == MATRIX_ARRAY_SHA256, "G-0014 frozen hash mismatch")
    require(audit.get("matrix_int64_c_sha256") == replay.get("regenerated_matrix_int64_c_sha256"), "G12/G14 matrix mismatch")
    require(replay.get("workers") == 6, "G-0014 worker count differs from the audited launch")
    require(replay.get("max_tasks_per_child") == 25, "G-0014 worker-recycling setting mismatch")

    dual_support = report.get("exact_dual_support_binding", {})
    require(
        dual_support.get("pivot_row_count") == RANK
        and dual_support.get("support_row_count") == RANK + 1
        and dual_support.get("failing_row") == ROW_COUNT - 1
        and dual_support.get("support_rows_sha256") == SUPPORT_ROWS_SHA256,
        "G-0014 support binding mismatch",
    )
    target = report.get("target_semantics", {})
    require(target.get("hinge_target_nonzero_count") == 0, "G-0014 hinge target is nonzero")
    require(target.get("nonzero_rows") == [ROW_COUNT - 1], "G-0014 target support mismatch")
    require(target.get("final_linear_row") == ROW_COUNT - 1, "G-0014 target row mismatch")
    require(target.get("final_linear_value") == TARGET, "G-0014 target value mismatch")
    require(target.get("target_int64_c_sha256") == TARGET_ARRAY_SHA256, "G-0014 target hash mismatch")
    return report


def verify_beta2_corollary(observed: dict[str, str]) -> dict[str, object]:
    report = load_json(G18_REPORT_PATH)
    require(report.get("schema") == "max11-beta2-to-g8-exact-function-mapping-audit-v1", "G-0018 schema mismatch")
    require(report.get("result") == "PASS", "G-0018 result mismatch")
    require(report.get("script_sha256") == observed[G18_SCRIPT_PATH], "G-0018 script hash mismatch")
    inputs = {
        entry.get("path"): entry.get("sha256")
        for entry in report.get("inputs", [])
        if isinstance(entry, dict)
    }
    for relative in (G18_SOURCE_PATH, CLASSES_PATH, BETA2_CLASSES_PATH):
        require(inputs.get(relative) == observed[relative], f"G-0018 input link mismatch: {relative}")
    bases = report.get("source_bases", {})
    require(bases.get("certificate_term_count") == 402, "G-0018 source-term census mismatch")
    require(bases.get("filtered_base_count") == 252, "G-0018 base census mismatch")
    require(bases.get("branch_edge_counts") == [4, 4], "G-0018 source branch-size mismatch")
    require(bases.get("distinct_loopless_union_edges_per_base") == 8, "G-0018 source edge census mismatch")
    require(bases.get("active_vertices") == list(range(1, 11)), "G-0018 active vertices mismatch")
    require(bases.get("component_count") == 2 and bases.get("forest_cycle_rank") == 0, "G-0018 source topology mismatch")
    g8 = report.get("g8_reconstruction", {})
    require(g8.get("raw_candidate_count") == RAW_COUNT, "G-0018 G8 raw census mismatch")
    require(g8.get("frozen_class_count") == CLASS_COUNT, "G-0018 G8 class census mismatch")
    require(g8.get("raw_pair_list_sha256") == RAW_PAIR_LIST_SHA256, "G-0018 G8 raw hash mismatch")
    require(g8.get("coincident_endpoint_raw_count") == 2_520, "G-0018 coincident-lift census mismatch")
    beta2 = report.get("beta2_reconstruction", {})
    require(beta2.get("raw_candidate_count") == 6_740, "G-0018 beta2 raw census mismatch")
    require(beta2.get("frozen_class_count") == 4_916, "G-0018 beta2 class census mismatch")
    require(
        beta2.get("raw_pair_list_sha256") == "38974c9e13135073dfc3c7c5cbe6e8c18bddeeb1462d8a9f4c732cc03c75c61f",
        "G-0018 beta2 raw hash mismatch",
    )
    require(beta2.get("every_added_edge_loopless_internal_and_common") is True, "G-0018 beta2 edge condition failed")
    mapping = report.get("mapping", {})
    require(mapping.get("record_count") == 6_740, "G-0018 mapping census mismatch")
    require(mapping.get("source_base_count") == 252, "G-0018 mapping base coverage mismatch")
    require(mapping.get("target_g8_raw_count") == 252, "G-0018 witness raw census mismatch")
    require(mapping.get("beta2_representative_count") == 4_916, "G-0018 representative mapping mismatch")
    require(mapping.get("mapped_source_base_and_signed_adjacency_equal_for_every_record") is True, "G-0018 mapping equality failed")
    require(
        mapping.get("records_canonical_sha256")
        == "891c48572318a6396786023349fa4358dfc6beeef515137836bd1d465afb100e",
        "G-0018 mapping payload hash mismatch",
    )
    records = mapping.get("records")
    require(isinstance(records, list) and len(records) == 6_740, "G-0018 mapping records malformed")
    source = load_json(G18_SOURCE_PATH)
    source_terms = source.get("terms")
    require(isinstance(source_terms, list), "G-0018 source terms malformed")
    duplicate_in_one_source_branch = 0
    absent_from_both_source_branches = 0
    for record in records:
        require(isinstance(record, dict), "G-0018 mapping record is not an object")
        term_index = record.get("source_term_index")
        edge = record.get("beta_common_edge")
        require(type(term_index) is int and 0 <= term_index < len(source_terms), "G-0018 source term index invalid")
        require(
            isinstance(edge, list)
            and len(edge) == 2
            and all(type(endpoint) is int for endpoint in edge),
            "G-0018 beta edge malformed",
        )
        source_pair = source_terms[term_index].get("pair")
        require(isinstance(source_pair, list) and len(source_pair) == 2, "G-0018 source pair malformed")
        normalized_edge = tuple(sorted(map(int, edge)))
        memberships = []
        for branch in source_pair:
            require(isinstance(branch, list), "G-0018 source branch malformed")
            normalized_branch = {
                tuple(sorted((int(source_edge[0]), int(source_edge[1]))))
                for source_edge in branch
            }
            memberships.append(normalized_edge in normalized_branch)
        require(not all(memberships), "G-0018 source branches unexpectedly share the beta edge")
        if any(memberships):
            duplicate_in_one_source_branch += 1
        else:
            absent_from_both_source_branches += 1
    require(duplicate_in_one_source_branch == 2_016, "G-0018 duplicate-occurrence census mismatch")
    require(absent_from_both_source_branches == 4_724, "G-0018 new-edge census mismatch")
    controls = report.get("common_edge_lemma", {}).get("small_n_direct_permutation_controls", [])
    require(len(controls) == 4 and [case.get("n") for case in controls] == [4, 5, 6, 7], "G-0018 direct-control census mismatch")
    require(all(case.get("identity_holds_exactly") is True for case in controls), "G-0018 direct identity control failed")
    mutants = report.get("hostile_controls", [])
    require(len(mutants) == 3 and all(case.get("rejected") is True for case in mutants), "G-0018 hostile control failed")
    corollary = report.get("certified_corollary", {})
    for key in (
        "every_beta2_raw_function_pointwise_equals_its_mapped_g8_witness",
        "every_beta2_quotient_function_is_in_the_g8_function_set",
        "span_Q_G8_union_beta2_equals_span_Q_G8",
        "span_R_G8_union_beta2_equals_span_R_G8",
        "g0011_dual_annihilates_G8_union_beta2",
        "g0011_target_pairing_unchanged_and_nonzero",
        "union_no_go_certified",
    ):
        require(corollary.get(key) is True, f"G-0018 corollary gate failed: {key}")
    report["bundle_verified_occurrence_census"] = {
        "duplicate_in_exactly_one_source_branch": duplicate_in_one_source_branch,
        "absent_from_both_source_branches": absent_from_both_source_branches,
    }
    return report


def verify_cross_diagnostic(observed: dict[str, str]) -> dict[str, object]:
    report = load_json(CROSS_PROBE_REPORT_PATH)
    require(report.get("schema") == "g0011-omega-single-cross-class-probe-v1", "cross-probe schema mismatch")
    require(report.get("result") == "NONZERO", "cross-probe result mismatch")
    require(report.get("script_sha256") == observed[CROSS_PROBE_SCRIPT_PATH], "cross-probe script mismatch")
    inputs = {
        entry.get("path"): entry.get("sha256")
        for entry in report.get("inputs", [])
        if isinstance(entry, dict)
    }
    for relative in (
        G18_SOURCE_PATH,
        CROSS_CLASSES_PATH,
        SELECTION_PATH,
        DUAL_PATH,
        G14_SCRIPT_PATH,
        G18_SCRIPT_PATH,
    ):
        require(inputs.get(relative) == observed[relative], f"cross-probe input mismatch: {relative}")
    representative = report.get("cross_representative", {})
    require(representative.get("class_index") == 0, "cross-probe class index mismatch")
    require(
        representative.get("reconstructed_raw_family_count_for_binding_only") == 9_200,
        "cross-probe raw-family census mismatch",
    )
    scope = report.get("scope", {})
    require(scope.get("evaluated_cross_class_indices") == [0], "cross-probe evaluated scope mismatch")
    require(scope.get("evaluated_cross_representative_count") == 1, "cross-probe count mismatch")
    require(scope.get("family_scan_performed") is False, "cross-probe overstates a family scan")
    omega = report.get("omega", {})
    require(omega.get("nonzero") is True and omega.get("sign") == -1, "cross-probe exact omega mismatch")
    require(omega.get("absolute_bit_length") == 12_580, "cross-probe omega bit length mismatch")
    require(omega.get("exact_modular_agreement") is True, "cross-probe modular control failed")
    require(omega.get("modulus") == 2**61 - 1, "cross-probe modulus mismatch")
    require(omega.get("residue") == 1_755_775_690_469_619_915, "cross-probe residue mismatch")
    return report


def verify_theorem_and_review(observed: dict[str, str]) -> dict[str, object]:
    theorem = load_regular(THEOREM_PATH).read_text(encoding="utf-8")
    referee = load_regular(REFEREE_PATH).read_text(encoding="utf-8")
    scope_record = extract_comment_json(theorem, THEOREM_SCOPE_MARKER)
    review_record = extract_comment_json(referee, REVIEW_RECORD_MARKER)
    validate_theorem_scope(scope_record, observed)
    validate_review_record(review_record, observed)
    validate_visible_theorem(theorem)
    validate_visible_review(referee)
    require(observed[THEOREM_PATH] in referee, "visible referee subject hash missing")
    require("It therefore does not settle unrestricted MAX11" in theorem, "unrestricted nonclaim missing")
    require("7,135 rows are not asserted to contain every active direction" in theorem, "selection nonclaim missing")
    require("validated frozen direction list" in theorem, "selection-provenance scope correction missing")
    require("theorem/convention check" in theorem, "target-audit scope correction missing")
    require("6,740" in theorem and "beta2" in theorem, "beta2-union corollary missing")
    require("edge multiset" in theorem and "2,016" in theorem, "beta2 multiset scope correction missing")
    require("9,200" in theorem and "cross-component" in theorem, "cross-family nonclaim missing")
    hostile_scope = dict(scope_record)
    hostile_scope["statement"] = (
        "MAX11 is not representable by any arbitrary finite two-hidden-layer real-weight ReLU network."
    )
    hostile_review = dict(review_record)
    hostile_review["verdict"] = "FAIL"
    hostile_boundary = dict(scope_record)
    hostile_boundary["claim_boundary"] = "unrestricted MAX11 lower bound"
    hostile_visible_theorem = theorem.replace(
        THEOREM_VISIBLE_SCOPE,
        "> **Claim (normative):** MAX11 is not representable by any arbitrary finite "
        "two-hidden-layer real-weight ReLU network.\n>\n"
        f"> **No-claim (normative):** {BOUNDED_NO_CLAIM}",
        1,
    )
    hostile_visible_review = referee.replace(
        REVIEW_VISIBLE_RECORD,
        "> **Verdict (normative):** FAIL\n>\n"
        "> **Tier (normative):** same-family T1\n>\n"
        f"> **Scope (normative):** {CLAIM_BOUNDARY}",
        1,
    )
    appended_broad_theorem = theorem + (
        "\n\nMAX11 is not in the real span of arbitrary finite two-hidden-layer "
        "real-weight ReLU networks.\n"
    )
    appended_bold_fail = referee + "\n\n**Verdict:** **FAIL**\n"
    appended_parenthetical_fail = referee + "\n\nVerdict (final): FAIL\n"
    appended_equals_fail = referee + "\n\nVerdict = FAIL\n"
    fenced_visible_theorem = theorem.replace(
        f"{THEOREM_VISIBLE_BEGIN}\n{THEOREM_VISIBLE_SCOPE}\n{THEOREM_VISIBLE_END}",
        "```text\n"
        f"{THEOREM_VISIBLE_BEGIN}\n{THEOREM_VISIBLE_SCOPE}\n{THEOREM_VISIBLE_END}\n"
        "```",
        1,
    )
    duplicate_scope_json = (
        f"<!-- {THEOREM_SCOPE_MARKER} "
        '{"statement":"unrestricted MAX11 lower bound",'
        + canonical_json_bytes(scope_record).decode("ascii")[1:]
        + " -->"
    )
    duplicate_review_json = (
        f"<!-- {REVIEW_RECORD_MARKER} "
        '{"verdict":"FAIL",'
        + canonical_json_bytes(review_record).decode("ascii")[1:]
        + " -->"
    )
    hostile_controls = [
        must_reject(
            "broadened_normative_theorem_statement",
            lambda: validate_theorem_scope(hostile_scope, observed),
        ),
        must_reject(
            "broadened_normative_claim_boundary",
            lambda: validate_theorem_scope(hostile_boundary, observed),
        ),
        must_reject(
            "explicitly_failing_referee_verdict",
            lambda: validate_review_record(hostile_review, observed),
        ),
        must_reject(
            "broadened_human_visible_theorem",
            lambda: validate_visible_theorem(hostile_visible_theorem),
        ),
        must_reject(
            "failing_human_visible_referee",
            lambda: validate_visible_review(hostile_visible_review),
        ),
        must_reject(
            "duplicate_theorem_json_key",
            lambda: extract_comment_json(duplicate_scope_json, THEOREM_SCOPE_MARKER),
        ),
        must_reject(
            "duplicate_referee_json_key",
            lambda: extract_comment_json(duplicate_review_json, REVIEW_RECORD_MARKER),
        ),
        must_reject(
            "appended_competing_broad_theorem",
            lambda: validate_visible_theorem(appended_broad_theorem),
        ),
        must_reject(
            "appended_markdown_bold_fail_verdict",
            lambda: validate_visible_review(appended_bold_fail),
        ),
        must_reject(
            "appended_parenthetical_fail_verdict",
            lambda: validate_visible_review(appended_parenthetical_fail),
        ),
        must_reject(
            "appended_equals_fail_verdict",
            lambda: validate_visible_review(appended_equals_fail),
        ),
        must_reject(
            "visible_theorem_scope_inside_code_fence",
            lambda: validate_visible_theorem(fenced_visible_theorem),
        ),
    ]
    return {
        "theorem_sha256": observed[THEOREM_PATH],
        "referee_sha256": observed[REFEREE_PATH],
        "review_tier": "same-family T1; no T2/human promotion",
        "normative_scope": scope_record,
        "normative_review": review_record,
        "hostile_scope_mutations": hostile_controls,
    }


def git_blob_status(relative_paths: list[str]) -> dict[str, object]:
    """Report custody without making it a mathematical pass condition.

    The final release commit is made after this generated report, so a clean
    working tree cannot be required inside the report without a hash cycle.
    """

    import subprocess

    status: dict[str, object] = {}
    for relative in relative_paths:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
        porcelain = subprocess.run(
            ["git", "status", "--short", "--", relative],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout.strip()
        status[relative] = {"tracked": tracked, "porcelain": porcelain or "clean"}
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    started = __import__("time").perf_counter()
    spec_raw = args.spec.read_text(encoding="utf-8")
    spec = strict_json_loads(spec_raw, str(args.spec))
    require(isinstance(spec, dict), "bundle spec JSON root is not an object")
    require(
        spec_raw.encode("ascii") == canonical_json_bytes(spec) + b"\n",
        "bundle spec is not canonical JSON plus one newline",
    )
    observed = verify_file_identities(spec)
    _classes, selection = verify_selection_and_classes(observed)
    matrix = verify_matrix(observed, selection)
    _dual, audit = verify_exact_dual(observed)
    semantic = verify_semantic_report(observed, audit)
    beta2 = verify_beta2_corollary(observed)
    cross = verify_cross_diagnostic(observed)
    theorem = verify_theorem_and_review(observed)
    report = {
        "schema": SCHEMA,
        "verdict": "PASS_BOUNDED_THEOREM_BUNDLE",
        "claim": BOUNDED_STATEMENT,
        "no_claim": BOUNDED_NO_CLAIM,
        "composition": {
            "semantic_replay": "G-0014 independently reconstructs the raw family, quotient, and every coefficient for the frozen validated direction list.",
            "exact_arithmetic": "G-0012 exactly replays the G-0011 rational left dual on every frozen matrix column.",
            "target": "G-0015 proves the 11!*MAX11 ordered-chamber coordinate convention; G-0014 only checks its serialization.",
            "selection": "The 7135 directions are a frozen validated projection; their adaptive discovery provenance is not independently regenerated and is not needed for the obstruction.",
            "beta2": "G-0018 maps every named beta2-common atom pointwise to a coincident-endpoint atom already in the G8 function set.",
        },
        "files_sha256": observed,
        "matrix": matrix,
        "semantic_report": {
            "sha256": observed[G14_REPORT_PATH],
            "rows": semantic["matrix_semantic_replay"]["rows_compared"],
            "columns": semantic["matrix_semantic_replay"]["columns_compared"],
            "entries": semantic["matrix_semantic_replay"]["entries_compared"],
            "mismatches": semantic["matrix_semantic_replay"]["mismatched_entries"],
        },
        "exact_audit": {
            "sha256": observed[G12_REPORT_PATH],
            "columns": audit["exact_columns_replayed"],
            "relation_entries": audit["exact_relation_entries_replayed"],
            "raw_target_pairing": audit["raw_target_pairing_with_failing_coefficient_one"],
            "eleven_prime_reductions": audit["all_eleven_delivered_modular_vectors_match_exact_reduction"],
            "hostile_mutations_rejected": audit["all_hostile_tampers_rejected"],
        },
        "beta2_mapping_audit": {
            "sha256": observed[G18_REPORT_PATH],
            "raw_mappings": beta2["mapping"]["record_count"],
            "beta2_classes": beta2["mapping"]["beta2_representative_count"],
            "duplicate_in_exactly_one_source_branch": beta2["bundle_verified_occurrence_census"]["duplicate_in_exactly_one_source_branch"],
            "absent_from_both_source_branches": beta2["bundle_verified_occurrence_census"]["absent_from_both_source_branches"],
            "span_union_equals_g8": beta2["certified_corollary"]["span_R_G8_union_beta2_equals_span_R_G8"],
        },
        "cross_family_diagnostic": {
            "sha256": observed[CROSS_PROBE_REPORT_PATH],
            "evaluated_classes": cross["scope"]["evaluated_cross_class_indices"],
            "family_scan_performed": cross["scope"]["family_scan_performed"],
            "current_dual_value_nonzero": cross["omega"]["nonzero"],
            "meaning": (
                "The present dual does not extend unchanged to the union containing this one "
                "cross-component class; target membership in that union remains undecided."
            ),
        },
        "theorem_and_review": theorem,
        "review_boundary": "Internal fresh-context/same-model-family T1 only; no independent-family or human T2 review.",
        "residual_risks": [
            "The exact dual audit and semantic replay share a host and mathematical specification.",
            "No completeness theorem connects this registered family to all two-hidden-layer ReLU networks.",
            "Content hashes and Git custody are integrity receipts, not external signatures.",
        ],
        "custody_at_verification_time": git_blob_status(sorted(observed)),
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "pid": os.getpid(),
        },
        "seconds": round(__import__("time").perf_counter() - started, 6),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(canonical_json_bytes(report) + b"\n")
    print(f"G0017_RESULT PASS report={args.report} sha256={sha256_path(args.report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
