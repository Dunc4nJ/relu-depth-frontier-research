"""Independently hand-derived synthetic MAX2 certificate.

Let M=max(x1,x2).  The first block has the common pair (1,2):

  max(x1 + M, x2 + M) = 2M.

The second block repeats its loop on each side:

  max(2x1, 2x2) = 2M.

Each block is unchanged by the two S2 label permutations, so its unnormalized
symmetrization is 4M.  Giving each block coefficient 1/8 contributes M/2;
together the two independently described blocks give exactly M.  This fixture
was authored for Stage A and does not copy a registered MAX5--MAX10 term.
"""

from __future__ import annotations

from copy import deepcopy
import json

from cleanroom.maxrelu import SubjectSpec, parse_certificate_bytes


_FIXTURE = {
    "n": 2,
    "terms": [
        {
            "coefficient": "1/8",
            "pair": [
                [[1, 1], [1, 2]],
                [[2, 2], [1, 2]],
            ],
        },
        {
            "coefficient": "1/8",
            "pair": [
                [[1, 1], [1, 1]],
                [[2, 2], [2, 2]],
            ],
        },
    ],
}


def fixture_object() -> dict[str, object]:
    return deepcopy(_FIXTURE)


def fixture_bytes(value: dict[str, object] | None = None) -> bytes:
    return json.dumps(
        _FIXTURE if value is None else value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def fixture_spec(
    *, n: int = 2, k: int = 2, term_count: int = 2
) -> SubjectSpec:
    return SubjectSpec(
        subject_id="synthetic-MAX2-stage-a",
        filename="synthetic_max2.json",
        n=n,
        k=k,
        term_count=term_count,
    )


def fixture_certificate(value: dict[str, object] | None = None):
    return parse_certificate_bytes(fixture_bytes(value), fixture_spec())
