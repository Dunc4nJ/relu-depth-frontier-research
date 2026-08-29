#!/usr/bin/env python3
"""Audit the frozen certificate input contract without checking its identities."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_ROOT = ROOT / "subjects/max-relu-known"
CERTIFICATES = SUBJECT_ROOT / "certificates"
SUBJECT_MANIFEST_SHA256 = "70851ae4fdd20ddc53a87b7817effd8efb983d721e518bcf6ef8c5a9edf848f2"
EXPECTED = {
    5: (2, 3, "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694"),
    6: (2, 4, "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83"),
    7: (3, 57, "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be"),
    8: (3, 69, "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3"),
    9: (4, 337, "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88"),
    10: (4, 402, "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"),
}
EXPECTED_WIDTHS = {
    5: (20, 360, 1_080),
    6: (27, 2_880, 8_640),
    7: (35, 287_280, 861_840),
    8: (44, 2_782_080, 8_346_240),
    9: (54, 122_290_560, 366_871_680),
    10: (65, 1_458_777_600, 4_376_332_800),
}


def fail(message: str) -> None:
    print(f"certificate-corpus-audit: FAIL — {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def genuine_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


total_terms = 0
total_contributions = 0
seen_files: set[Path] = set()

manifest = SUBJECT_ROOT / "SUBJECT_MANIFEST.sha256"
if not manifest.is_file() or sha256(manifest.read_bytes()) != SUBJECT_MANIFEST_SHA256:
    fail("subject-manifest hash mismatch")

for n, (k, term_count, expected_hash) in EXPECTED.items():
    path = CERTIFICATES / f"certificate_{n}_{k}.json"
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    seen_files.add(path.resolve())
    raw = path.read_bytes()
    if sha256(raw) != expected_hash:
        fail(f"byte hash mismatch for n={n}")
    document = json.loads(raw)
    if set(document) != {"n", "terms"}:
        fail(f"unexpected top-level keys for n={n}")
    if not genuine_int(document["n"]) or document["n"] != n:
        fail(f"invalid registered n in n={n} file")
    terms = document["terms"]
    if not isinstance(terms, list) or len(terms) != term_count:
        fail(f"term census mismatch for n={n}")

    for term_index, term in enumerate(terms):
        if not isinstance(term, dict) or set(term) != {"coefficient", "pair"}:
            fail(f"malformed term {term_index} for n={n}")
        coefficient = term["coefficient"]
        if isinstance(coefficient, bool) or isinstance(coefficient, float):
            fail(f"inexact coefficient type in term {term_index} for n={n}")
        try:
            rational = Fraction(coefficient)
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            fail(f"invalid rational in term {term_index} for n={n}: {exc}")
        if rational == 0:
            fail(f"zero coefficient in term {term_index} for n={n}")
        pair = term["pair"]
        if not isinstance(pair, list) or len(pair) != 2:
            fail(f"term {term_index} for n={n} does not contain exactly two sides")
        for side_index, side in enumerate(pair):
            if not isinstance(side, list) or len(side) != k:
                fail(f"wrong side multiplicity in term {term_index}, side {side_index}, n={n}")
            for edge_index, edge in enumerate(side):
                if not isinstance(edge, list) or len(edge) != 2:
                    fail(f"malformed edge {edge_index} in term {term_index}, n={n}")
                a, b = edge
                if not genuine_int(a) or not genuine_int(b) or not (1 <= a <= b <= n):
                    fail(f"invalid endpoint pair {edge!r} in term {term_index}, n={n}")

    canonical = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    contributions = term_count * math.factorial(n)
    first_width = math.comb(n, 2) + 2 * n
    second_width = 3 * contributions
    if (first_width, contributions, second_width) != EXPECTED_WIDTHS[n]:
        fail(f"symbolic width census mismatch for n={n}")
    total_terms += term_count
    total_contributions += contributions
    print(
        f"n={n} k={k} terms={term_count} contributions={contributions} "
        f"first_width<={first_width} second_width<={second_width} "
        f"bytes_sha256={expected_hash} normalized_sha256={sha256(canonical)}"
    )

extra_files = {
    path.resolve() for path in CERTIFICATES.glob("*.json") if path.is_file()
} - seen_files
if extra_files:
    fail("unregistered certificate files: " + ", ".join(sorted(path.name for path in extra_files)))
if total_terms != 872:
    fail(f"aggregate term census is {total_terms}, expected 872")
if total_contributions != 1_584_140_760:
    fail(
        f"aggregate term-permutation census is {total_contributions}, "
        "expected 1584140760"
    )

print(
    "certificate-corpus-audit: PASS "
    f"(files=6 terms={total_terms} term_permutations={total_contributions})"
)
print("epistemic-boundary: input contract only; no certificate identity was checked")
