#!/usr/bin/env python3
"""Exact symbolic decision of the last G-0035 three-wall J_2 arrangement.

For each of the eight maximal cells, this program computes the complete
nonnegative edge-scaling cone.  Every cone is two-dimensional and has two
exact extreme rays.  It then decides the necessary two-center reflection
cover condition on both endpoint rays and, in one exact QF_LIRA query, on
the entire positive projective interval between them.

The logical direction used is deliberately only

    primitive P^2 block  ==>  feasible two-center reflection cover.

Thus an UNSAT cover query is a complete obstruction, while SAT alone would
not certify a primitive block.  The two genuine endpoint blocks found here
are instead certified constructively by exact zonotope vertex partitions.

The G-0035 machinery is imported only after its source bytes match the
frozen hashes below.  The hashes are checked again after the computation so
that a concurrent source change invalidates the run rather than silently
changing its meaning.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from fractions import Fraction as Q
from pathlib import Path
from typing import Any, Sequence
from zipfile import BadZipFile, ZipFile


Vector = tuple[Q, ...]

HARD_WALLS = (
    (-1, -1, 1, -1, 1, 1, 3),
    (-1, -1, 1, 3, 1, 1, -1),
    (-1, 1, -1, 1, -1, 3, 1),
)

EXPECTED_DEPENDENCY_HASHES = {
    "analyze_survivor_type_cones.py": "7233d201bf85fb2c8b11d6d08bee263bb2efd1848a72a93ca64a3d088e215142",
    "audit_four_wall_survivor.py": "c20261fa7ea6fc9c0fc699f12c8ab70daff6724db99e58e56bbe0ddb2f37318a",
    "audit_one_wall_obstructions.py": "9969e3d4d0b6798c53dfd9029581104747a38fd160fd982a6d2f1b002e0e1687",
    "audit_unresolved_triple_type_cones.py": "51848649633a8695e3e71b418c709209f8b55e9e424b3e97df725f1be2918631",
    "cone_join_obstruction.py": "f4907e8d48dd0653f0b2b433a4f49844d19bb4b10a260d964885d97ac1757c97",
    "exact_zonotope.py": "c82791acad73858078bc542aebf17d7bf1cee222f0657697138a4e200359df3c",
    "prove_separating_wall_caps.py": "54f020b8030ceedaa5389431e38d1780f173b297df315649c232ec92ac0d2ecd",
    "search_one_wall_refinements.py": "3f5f2a435aa6079aa6a7772f29cb3066490eb5eb58301532df3737345c8373ee",
    "search_seeded_multiwall_arrangements.py": "793db2b6f5e6cd0ab31ac59e9c3b7291a05c6372f9db336941ccd362efe92529",
}
DEPENDENCY_ARCHIVE_NAME = "g0035_exact_dependencies_v1.zip"
EXPECTED_DEPENDENCY_ARCHIVE_SHA256 = "ad3a4359553c7ed11a23aea2384f39fe3c9cf65f7e6ca2587046cc1f6992cb56"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def dependency_archive() -> Path:
    return Path(__file__).resolve().with_name(DEPENDENCY_ARCHIVE_NAME)


def dependency_hashes() -> dict[str, str]:
    archive_path = dependency_archive()
    if sha256_file(archive_path) != EXPECTED_DEPENDENCY_ARCHIVE_SHA256:
        raise SystemExit("G-0035 dependency archive hash mismatch")
    try:
        with ZipFile(archive_path) as archive:
            if set(archive.namelist()) != set(EXPECTED_DEPENDENCY_HASHES):
                raise SystemExit("G-0035 dependency archive member-set mismatch")
            return {
                name: sha256_bytes(archive.read(name))
                for name in EXPECTED_DEPENDENCY_HASHES
            }
    except BadZipFile as error:
        raise SystemExit(f"invalid G-0035 dependency archive: {error}") from error


def require_frozen_dependencies() -> dict[str, str]:
    actual = dependency_hashes()
    if actual != EXPECTED_DEPENDENCY_HASHES:
        differences = {
            name: {
                "expected": EXPECTED_DEPENDENCY_HASHES.get(name),
                "actual": actual.get(name),
            }
            for name in sorted(set(actual) | set(EXPECTED_DEPENDENCY_HASHES))
            if actual.get(name) != EXPECTED_DEPENDENCY_HASHES.get(name)
        }
        raise SystemExit(f"G-0035 dependency custody failure: {differences}")
    return actual


START_DEPENDENCY_HASHES = require_frozen_dependencies()
START_DEPENDENCY_ARCHIVE_SHA256 = sha256_file(dependency_archive())
sys.path.insert(0, str(dependency_archive()))

import z3  # noqa: E402
from analyze_survivor_type_cones import (  # noqa: E402
    nullspace_basis,
    scaling_cone_rays,
    scaling_system,
    summand_vertex_map,
)
from audit_four_wall_survivor import fixed_central_cover_query  # noqa: E402
from cone_join_obstruction import affine_rank, matrix_rank  # noqa: E402
from exact_zonotope import affine_coordinates, self_test as zonotope_self_test  # noqa: E402
from prove_separating_wall_caps import (  # noqa: E402
    active_normal_ranks,
    facet_halfspaces,
    parametric_cover_query,
    verify_support_face_hrep,
)
from search_one_wall_refinements import primitive_p2_partition  # noqa: E402
from search_seeded_multiwall_arrangements import (  # noqa: E402
    J2_VERTEX_ORDER,
    affine_coefficients,
    all_one_ray_coefficients,
    arrangement_cells,
    cell_digest,
    convex_hull_vertices,
    dot,
    encode_q,
)


def encode_vertex(vertex: Sequence[Q]) -> list[list[int]]:
    return [encode_q(value) for value in vertex]


def encode_points(points: Sequence[Vector]) -> list[list[list[int]]]:
    return [encode_vertex(point) for point in points]


def translate_to_origin(points: Sequence[Vector]) -> tuple[Vector, ...]:
    origin = points[0]
    return tuple(
        tuple(value - base for value, base in zip(point, origin))
        for point in points
    )


def chamber_signs(cell: Sequence[Vector]) -> list[int]:
    barycenter = tuple(
        sum((point[coordinate] for point in cell), Q(0)) / len(cell)
        for coordinate in range(len(cell[0]))
    )
    coefficients = tuple(
        affine_coefficients(J2_VERTEX_ORDER, wall)
        for wall in HARD_WALLS
    )
    values = tuple(dot(row, (Q(1), *barycenter)) for row in coefficients)
    if any(value == 0 for value in values):
        raise AssertionError("cell barycenter lies on an arrangement wall")
    return [1 if value > 0 else -1 for value in values]


def proof_record(
    *,
    cell_index: int,
    query: str,
    result: z3.CheckSatResult,
    proof: str | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    record: dict[str, Any] = {
        "cell_index": cell_index,
        "query": query,
        "result": str(result),
    }
    bundle_record = None
    if result == z3.unsat:
        if proof is None:
            raise AssertionError("UNSAT query has no exact Z3 proof")
        digest = sha256_bytes(proof.encode())
        record.update({
            "proof_character_count": len(proof),
            "proof_sha256": digest,
        })
        bundle_record = {**record, "proof": proof}
    return record, bundle_record


def fixed_endpoint_query(
    points: Sequence[Vector],
    *,
    cell_index: int,
    ray_index: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    halfspaces = facet_halfspaces(points)
    ranks = active_normal_ranks(points, halfspaces)
    dimension = len(points[0])
    if not ranks or min(ranks) != dimension:
        raise AssertionError("endpoint hull contains an unproved nonvertex")
    barycenter = tuple(
        sum((point[coordinate] for point in points), Q(0)) / len(points)
        for coordinate in range(dimension)
    )
    mutant_rank = active_normal_ranks((barycenter,), halfspaces)[0]
    if mutant_rank >= dimension:
        raise AssertionError("interior barycenter was not rejected as a vertex")
    result, proof, model = fixed_central_cover_query(points, 2, want_proof=True)
    query, bundle = proof_record(
        cell_index=cell_index,
        query=f"endpoint-ray-{ray_index}",
        result=result,
        proof=proof,
    )
    query.update({
        "facet_count": len(halfspaces),
        "minimum_extreme_vertex_active_normal_rank": min(ranks),
        "ambient_dimension": dimension,
        "planted_barycenter_active_normal_rank": mutant_rank,
        "sat_model": model,
    })
    return query, bundle


def endpoint_record(
    polytope: tuple[Vector, ...],
    *,
    cell_index: int,
    ray_index: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    dimension = affine_rank(polytope)
    certificate = primitive_p2_partition(polytope)
    base: dict[str, Any] = {
        "ray_index": ray_index,
        "vertex_count": len(polytope),
        "affine_dimension": dimension,
        "vertices": encode_points(polytope),
        "constructive_primitive_p2_partition": certificate,
    }
    if certificate is not None:
        # Run the necessary relaxation intrinsically as a planted SAT control.
        intrinsic = affine_coordinates(polytope)
        result, _proof, model = fixed_central_cover_query(intrinsic, 2)
        if result != z3.sat:
            raise AssertionError("constructive primitive endpoint failed its cover control")
        base.update({
            "classification": "genuine_primitive_P2_ray",
            "two_center_cover": "sat",
            "two_center_cover_role": "potency control; the zonotope partition is the certificate",
            "two_center_sat_model": model,
        })
        return base, None
    if dimension != len(polytope[0]):
        raise AssertionError("uncertified lower-dimensional endpoint requires a separate audit")
    query, bundle = fixed_endpoint_query(
        polytope,
        cell_index=cell_index,
        ray_index=ray_index,
    )
    if query["result"] != "unsat":
        raise AssertionError("an uncertified endpoint survived the necessary cover query")
    base.update({
        "classification": "no_primitive_P2_block_on_this_ray",
        "two_center_cover": query,
    })
    return base, bundle


def analyze_cell(cell: tuple[Vector, ...], cell_index: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    translated = translate_to_origin(cell)
    edges, rows = scaling_system(translated)
    basis = nullspace_basis(rows, len(edges))
    rays = scaling_cone_rays(basis)
    if len(basis) != 2 or len(rays) != 2 or matrix_rank(rays) != 2:
        raise AssertionError("survivor cell does not have the frozen complete two-ray cone")
    target_coefficients = all_one_ray_coefficients(rays, 2)
    if any(coefficient <= 0 for coefficient in target_coefficients):
        raise AssertionError("parent is not in the relative interior of its type cone")
    maps = tuple(
        summand_vertex_map(translated, edges, ray)
        for ray in rays
    )
    ray_polytopes = tuple(
        convex_hull_vertices(vertex_map)
        for vertex_map in maps
    )

    # Exact vertexwise reconstruction of the target cell from the ray maps.
    reconstructed = tuple(
        tuple(
            sum(
                (
                    coefficient * vertex_map[vertex_index][coordinate]
                    for coefficient, vertex_map in zip(target_coefficients, maps)
                ),
                Q(0),
            )
            for coordinate in range(len(translated[0]))
        )
        for vertex_index in range(len(translated))
    )
    if reconstructed != translated:
        raise AssertionError("type-cone rays do not reconstruct the target cell")

    proofs: list[dict[str, Any]] = []
    endpoint_records = []
    for ray_index, polytope in enumerate(ray_polytopes):
        record, proof = endpoint_record(
            polytope,
            cell_index=cell_index,
            ray_index=ray_index,
        )
        endpoint_records.append(record)
        if proof is not None:
            proofs.append(proof)

    genuine_indices = [
        record["ray_index"]
        for record in endpoint_records
        if record["classification"] == "genuine_primitive_P2_ray"
    ]
    obstructed_indices = [
        record["ray_index"]
        for record in endpoint_records
        if record["classification"] == "no_primitive_P2_block_on_this_ray"
    ]
    if not obstructed_indices:
        raise AssertionError("no obstructed target coordinate was found")
    required_bad_index = obstructed_indices[0]
    other_index = 1 - required_bad_index

    halfspaces = facet_halfspaces(translated)
    full_support_hrep = verify_support_face_hrep(
        maps,
        ray_polytopes,
        halfspaces,
        (0, 1),
    )
    result, proof, metadata = parametric_cover_query(
        maps,
        ray_polytopes,
        halfspaces,
        required_bad_index,
        (other_index,),
        want_proof=True,
    )
    if metadata is None:
        raise AssertionError("parametric query omitted metadata")
    interior_query, bundle = proof_record(
        cell_index=cell_index,
        query=f"positive-interior-normalize-ray-{required_bad_index}",
        result=result,
        proof=proof,
    )
    if bundle is not None:
        proofs.append(bundle)
    interior_query.update({
        "normalization": f"coefficient[{required_bad_index}]=1",
        "strict_parameter": f"coefficient[{other_index}]>0",
        "representative_extreme_vertex_count": metadata["vertex_count"],
        "full_support_hrep_check": full_support_hrep,
    })
    if result != z3.unsat:
        raise AssertionError("positive projective type-cone interval was not excluded")

    # Potency: the same parametric inequalities are satisfiable when each
    # extreme vertex may have its own point-center.
    potency, _potency_proof, potency_metadata = parametric_cover_query(
        maps,
        ray_polytopes,
        halfspaces,
        required_bad_index,
        (other_index,),
        center_count=len(cell),
    )
    if potency != z3.sat or potency_metadata is None or potency_metadata["model"] is None:
        raise AssertionError("one-center-per-vertex potency mutation did not become SAT")

    if genuine_indices not in ([], [0]):
        raise AssertionError("unexpected genuine endpoint classification")
    return {
        "cell_index": cell_index,
        "cell_sha256": cell_digest(cell),
        "chamber_signs": chamber_signs(cell),
        "vertex_count": len(cell),
        "affine_dimension": affine_rank(cell),
        "vertices": encode_points(cell),
        "edge_count": len(edges),
        "edge_scaling_rank": matrix_rank(rows),
        "edge_scaling_nullity": len(basis),
        "complete_nonnegative_type_cone": {
            "extreme_ray_count": len(rays),
            "extreme_ray_edge_scalings": [
                [encode_q(value) for value in ray]
                for ray in rays
            ],
            "target_all_one_coefficients": [
                encode_q(value) for value in target_coefficients
            ],
            "target_coefficients_strictly_positive": True,
            "target_vertexwise_reconstruction": True,
        },
        "endpoint_block_classification": endpoint_records,
        "genuine_nonzero_primitive_endpoint_ray_indices": genuine_indices,
        "obstructed_endpoint_ray_indices": obstructed_indices,
        "positive_projective_interior_two_center_query": interior_query,
        "potency_one_point_center_per_extreme_vertex": {
            "result": str(potency),
            "center_count": len(cell),
            "model": potency_metadata["model"],
        },
        "required_obstructed_coordinate": required_bad_index,
        "additivity_conclusion": (
            "The target has positive coefficient on the required obstructed ray. "
            "Nonnegative type-cone coordinates are additive, so a P2 decomposition "
            "would contain a primitive block with positive coefficient there. Such a "
            "block lies either on the obstructed endpoint or in the positive interior; "
            "both exact two-center necessary queries are UNSAT."
        ),
        "p2_membership": "outside_P2",
    }, proofs


def run_self_test() -> dict[str, Any]:
    exact_zonotope = zonotope_self_test()
    square = tuple((Q(x), Q(y)) for x, y in ((0, 0), (1, 0), (0, 1), (1, 1)))
    triangle = ((Q(0), Q(0)), (Q(1), Q(0)), (Q(0), Q(1)))
    square_one, _proof, _model = fixed_central_cover_query(square, 1)
    triangle_one, triangle_proof, _model = fixed_central_cover_query(
        triangle,
        1,
        want_proof=True,
    )
    triangle_two, _proof, triangle_model = fixed_central_cover_query(triangle, 2)
    triangle_partition = primitive_p2_partition(triangle)
    if square_one != z3.sat:
        raise AssertionError("square positive control was not one-center SAT")
    if triangle_one != z3.unsat or triangle_proof is None:
        raise AssertionError("triangle one-center negative control was not UNSAT")
    if triangle_two != z3.sat or triangle_model is None or triangle_partition is None:
        raise AssertionError("triangle two-center constructive control was not SAT")
    return {
        "exact_zonotope_controls": exact_zonotope,
        "square_one_center_positive_control": str(square_one),
        "triangle_one_center_must_fail_control": str(triangle_one),
        "triangle_one_center_proof_sha256": sha256_bytes(triangle_proof.encode()),
        "triangle_two_center_positive_control": str(triangle_two),
        "triangle_constructive_point_segment_partition": triangle_partition,
        "result": "PASS",
    }


def deterministic_gzip(payload: bytes) -> bytes:
    return gzip.compress(payload, compresslevel=9, mtime=0)


def write_outputs(
    report: dict[str, Any],
    proof_bundle: dict[str, Any],
    output: Path | None,
    proof_output: Path | None,
) -> None:
    if (output is None) != (proof_output is None):
        raise SystemExit("--output and --proof-output must be supplied together")
    proof_json = (json.dumps(proof_bundle, sort_keys=True, separators=(",", ":")) + "\n").encode()
    compressed = deterministic_gzip(proof_json)
    report["proof_bundle"] = {
        "path": str(proof_output) if proof_output is not None else None,
        "gzip_sha256": sha256_bytes(compressed),
        "uncompressed_json_sha256": sha256_bytes(proof_json),
        "query_proof_count": len(proof_bundle["queries"]),
    }
    report_json = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    if output is not None and proof_output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        proof_output.parent.mkdir(parents=True, exist_ok=True)
        proof_output.write_bytes(compressed)
        output.write_bytes(report_json)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--proof-output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    z3.set_param(proof=True)
    self_test = run_self_test()
    if args.self_test:
        print(json.dumps(self_test, sort_keys=True))
        return

    cells = arrangement_cells(HARD_WALLS)
    if len(cells) != 8:
        raise AssertionError("frozen wall arrangement does not have eight maximal cells")
    records = []
    proofs = []
    for cell_index, cell in enumerate(cells):
        record, cell_proofs = analyze_cell(cell, cell_index)
        records.append(record)
        proofs.extend(cell_proofs)

    if any(record["p2_membership"] != "outside_P2" for record in records):
        raise AssertionError("not every maximal cell was decided outside P2")
    chamber_set = {tuple(record["chamber_signs"]) for record in records}
    if len(chamber_set) != 8:
        raise AssertionError("maximal cells do not realize the eight sign chambers exactly")

    end_hashes = dependency_hashes()
    if end_hashes != START_DEPENDENCY_HASHES:
        raise SystemExit("G-0035 dependency changed during execution; outputs refused")
    end_archive_hash = sha256_file(dependency_archive())
    if end_archive_hash != START_DEPENDENCY_ARCHIVE_SHA256:
        raise SystemExit("G-0035 dependency archive changed during execution; outputs refused")
    source_hash = sha256_file(Path(__file__))
    proof_bundle = {
        "schema": "g0080-three-wall-j2-z3-proofs-v1",
        "arithmetic": "Z3 exact QF_LIRA proof objects over rational coefficients",
        "source_sha256": source_hash,
        "z3_version": z3.get_version_string(),
        "queries": proofs,
    }
    report = {
        "schema": "g0080-three-wall-j2-symbolic-decision-v1",
        "arithmetic": "fractions.Fraction exact polyhedral arithmetic plus Z3 exact QF_LIRA",
        "source_sha256": source_hash,
        "dependency_hashes_start": START_DEPENDENCY_HASHES,
        "dependency_hashes_end": end_hashes,
        "dependency_archive": {
            "path": DEPENDENCY_ARCHIVE_NAME,
            "sha256_start": START_DEPENDENCY_ARCHIVE_SHA256,
            "sha256_end": end_archive_hash,
            "member_count": len(START_DEPENDENCY_HASHES),
        },
        "dependency_custody_unchanged": True,
        "z3_version": z3.get_version_string(),
        "wall_vertex_order": ["T0", "T1", "T2", "S00", "S10", "S01", "S11"],
        "wall_values": [list(wall) for wall in HARD_WALLS],
        "maximal_cell_count": len(cells),
        "all_eight_sign_chambers_present": True,
        "cells": records,
        "self_test": self_test,
        "theorem": (
            "Every one of the eight maximal cells of the displayed three-wall "
            "arrangement is outside P2. Hence this exact arrangement is not a P2 "
            "subdivision of J2."
        ),
        "logical_bridge": {
            "primitive_implies_cover": (
                "If Q=conv(Z0 union Z1), every extreme vertex of Q belongs to Z0 or Z1. "
                "A zonotope Zi is centrally symmetric about ci and contained in Q, so an "
                "assigned vertex v has reflection 2ci-v in Q. Therefore every genuine "
                "primitive block satisfies the two-center LRA. The converse is not claimed."
            ),
            "type_cone_exhaustion": (
                "Every Minkowski summand gives a nonnegative edge scaling satisfying all "
                "polygonal two-face closure equations. The exact nullspace has dimension two; "
                "intersecting it with the nonnegative orthant yields exactly the two listed "
                "extreme rays. A nonzero summand is therefore on an endpoint or in the positive "
                "projective interior."
            ),
            "additivity": (
                "Type-cone coordinates add under Minkowski sum. Each target cell has positive "
                "coordinates on both rays, so for either required coordinate some primitive "
                "block in any P2 expression must carry it positively. The endpoint and entire "
                "interior carrying that coordinate are both cover-UNSAT."
            ),
        },
        "no_claim": (
            "This decides only the displayed three-wall arrangement. It is not a no-go theorem "
            "for other subdivisions of J2, for arbitrary three-wall arrangements, for W2 or "
            "virtual S2 identities, or for unrestricted MAX11. A two-center SAT result would "
            "not by itself certify a primitive P2 block."
        ),
        "result": "PASS",
    }
    write_outputs(report, proof_bundle, args.output, args.proof_output)
    print(json.dumps({
        "schema": report["schema"],
        "cells": len(records),
        "outside_P2": sum(record["p2_membership"] == "outside_P2" for record in records),
        "genuine_endpoint_rays": sum(
            len(record["genuine_nonzero_primitive_endpoint_ray_indices"])
            for record in records
        ),
        "proofs": len(proofs),
        "proof_bundle_sha256": report["proof_bundle"]["gzip_sha256"],
        "result": report["result"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
