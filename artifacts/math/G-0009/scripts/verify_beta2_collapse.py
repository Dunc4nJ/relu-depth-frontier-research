#!/usr/bin/env python3
"""Certify the common-edge beta2 family's 4,916-to-252 collapse.

The symbolic common-edge identity makes the fully symmetrized function
independent of the added edge's location for a fixed source atom.  This replay
also checks that the stored orbit and held-out columns agree exactly within
each of the 252 source-base groups and that their joint representatives are
pairwise distinct on the stored 886-row system.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import beta2_evaluate as beta2_eval  # noqa: E402
import cross_component_search as cross  # noqa: E402
import enumerate_beta2_common as beta2  # noqa: E402


SCHEMA = "max11-g0009-beta2-functional-collapse-v1"


def build(args: argparse.Namespace) -> dict[str, object]:
    pairs, metadata, metadata_sha, _sizes = beta2.build_family()
    del pairs
    classes = beta2.load_classes(args.classes)
    representatives = list(map(int, classes["representative_raw_indices"]))
    class_to_source_base = [int(metadata[index][0]) for index in representatives]
    groups: dict[int, list[int]] = defaultdict(list)
    for class_index, base_index in enumerate(class_to_source_base):
        groups[base_index].append(class_index)
    if sorted(groups) != list(range(252)):
        raise AssertionError("not every source base occurs in the exact quotient")

    orbit, _target, _profiles, orbit_files, _loaded_classes = beta2_eval.reduced_beta2(
        args.classes, args.orbits
    )
    cut = beta2_eval.load_cut_matrix(
        args.cut, args.selection, args.classes, len(representatives)
    )
    joint = np.concatenate((orbit, cut), axis=0)
    if joint.shape != (886, 4_916):
        raise AssertionError(f"unexpected beta2 joint shape {joint.shape}")

    within_base_disagreements = []
    reference_columns = []
    for base_index in range(252):
        indices = groups[base_index]
        reference = joint[:, indices[0]]
        reference_columns.append(reference)
        for class_index in indices[1:]:
            if not np.array_equal(reference, joint[:, class_index]):
                within_base_disagreements.append(
                    {"source_base": base_index, "class_index": class_index}
                )
    if within_base_disagreements:
        raise AssertionError(
            f"{len(within_base_disagreements)} within-base joint-column disagreements"
        )

    # Byte strings are compared by exact equality; no digest collision is used
    # to establish the uniqueness count.
    all_exact_columns = {joint[:, column].tobytes(order="C") for column in range(joint.shape[1])}
    reference_exact_columns = {column.tobytes(order="C") for column in reference_columns}
    if len(all_exact_columns) != 252 or len(reference_exact_columns) != 252:
        raise AssertionError(
            f"unexpected exact joint-column counts {len(all_exact_columns)}, "
            f"{len(reference_exact_columns)}"
        )

    group_histogram = Counter(len(indices) for indices in groups.values())
    class_to_base_array = np.asarray(class_to_source_base, dtype=np.int64)
    identity_path = args.identity
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    if identity.get("schema") != "max-common-edge-lift-identity-attestation-v1":
        raise ValueError("wrong common-edge identity schema")
    return {
        "schema": SCHEMA,
        "n": 11,
        "beta2_classes_path": cross.relative_root(args.classes),
        "beta2_classes_sha256": cross.sha256_path(args.classes),
        "candidate_metadata_sha256": metadata_sha,
        "common_edge_identity_path": cross.relative_root(identity_path),
        "common_edge_identity_sha256": cross.sha256_path(identity_path),
        "symbolic_global_consequence": identity["single_atom_identity"],
        "symbolic_application": (
            "For each fixed one of the 252 source MAX10 atoms, every admitted internal "
            "loopless common edge e produces the same fully symmetrized function "
            "Phi_11(A,B)+2*9!*F_2^(11)."
        ),
        "raw_candidate_count": int(classes["raw_candidate_count"]),
        "exact_graph_class_count": int(classes["class_count"]),
        "source_base_count": len(groups),
        "class_to_source_base_int64_sha256": cross.sha256_bytes(
            class_to_base_array.tobytes(order="C")
        ),
        "classes_per_source_base_histogram": {
            str(size): count for size, count in sorted(group_histogram.items())
        },
        "classes_per_source_base_min": min(map(len, groups.values())),
        "classes_per_source_base_max": max(map(len, groups.values())),
        "finite_joint_replay": {
            "rows": joint.shape[0],
            "columns": joint.shape[1],
            "orbit_rows": orbit.shape[0],
            "heldout_plus_linear_rows": cut.shape[0],
            "joint_matrix_int64_c_sha256": cross.sha256_bytes(joint.tobytes(order="C")),
            "within_source_base_disagreement_count": 0,
            "exact_distinct_column_count": len(all_exact_columns),
            "source_reference_exact_distinct_column_count": len(reference_exact_columns),
            "all_4916_columns_partition_into_252_exact_equal_column_groups": True,
        },
        "inputs": {
            "selection_sha256": cross.sha256_path(args.selection),
            "cut_matrix_sha256": cross.sha256_path(args.cut),
            "orbit_files": orbit_files,
        },
        "claim_boundary": (
            "Edge-placement independence is global for this common-edge construction by the "
            "proved identity.  Pairwise distinctness of the 252 source-base functions is "
            "asserted only on the stored 886-row joint system."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classes", type=Path, required=True)
    parser.add_argument("--orbits", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--cut", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cross.write_json(args.output, build(args))


if __name__ == "__main__":
    main()
