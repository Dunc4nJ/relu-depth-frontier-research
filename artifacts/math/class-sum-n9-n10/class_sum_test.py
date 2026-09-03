#!/usr/bin/env python3
"""Class-sum span test for MAX_n at n = 9 and n = 10.

Question
--------
Every symmetrized loop-free pairwise-max atom is stored in the saved systems as
one column ``(lin, h)``: an integer linear part indexed by the sorted-cone
coordinates and an integer hinge part indexed by primitive ambiguous
directions.  ``MAX_n`` restricted to the sorted cone is the target vector ``b``
that is ``1`` on the last linear row and ``0`` on every other row (this is the
convention of ``tools/exactlift/exactlift.py``).  The campaign already knows
``b`` lies in the span of the individual columns.

This script asks whether ``b`` stays in the span after the columns are replaced
by *class sums*

    S_c = sum_{W in class c} col_W ,

for a family of coarsenings ``c = phi(W)`` of the signed graph ``W = B - A``.
A MEMBER verdict at a coarse ``phi`` means a certificate exists whose
coefficients depend only on ``phi(W)``, which is what a uniform all-``n``
construction would look like.

Rigour
------
* Ranks are computed modulo two primes with a streaming reduced-row-echelon
  routine (float64 arithmetic kept exact: every accumulated dot product stays
  below ``2**53``).  A modular rank is a lower bound for the rational rank, so
  ranks are reported as modular unless the exact confirmation below succeeds.
* Verdicts are exact.  MEMBER is certified by an exact rational solution
  verified on *every* row of the saved row universe.  NON_MEMBER is certified
  by an exact rational dual vector ``y`` supported on a few rows with
  ``y^T S = 0`` on every class and ``y^T b != 0``.  Integer identities are
  checked modulo enough primes that the product of the primes exceeds twice an
  a-priori bound on the residual, so the conclusion is exact and not
  probabilistic.
* Exact rank confirmation (where it fits in memory): an integer basis of
  ``ker S_R`` for the modular pivot rows ``R`` is verified against *all* rows,
  which upper-bounds the rational rank and pins it to the modular value.

Usage
-----
    python class_sum_test.py --n 9 \
        --system handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz \
        --witness artifacts/math/exact-witness-n9-n10/recovered_n9_witness.json \
        --outdir artifacts/math/class-sum-n9-n10
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterator, Sequence

import numpy as np

SCHEMA = "max11-class-sum-span-v1"
PRIMES = (1000003, 1000033)
REPO_ROOT = Path(__file__).resolve().parents[3]

COARSENINGS = ["C0", "C0w", "C10", "C11", "C9", "C3", "C1", "C2", "C4", "C5", "C8", "C6", "C7"]

DESCRIPTIONS = {
    "C0": "identity on stored records (control; one class per saved column)",
    "C0w": "identity on the S_n-isomorphism type of the signed graph W",
    "C1": "(unordered pair of isomorphism types of the positive and negative graphs, "
          "number of vertices shared by both)",
    "C2": "unordered pair of isomorphism types of the positive and negative graphs",
    "C3": "vertex-type multiset {(d_plus(v), d_minus(v)) : v active}, orientation-canonicalised",
    "C4": "unordered pair of degree sequences (positive graph, negative graph)",
    "C5": "(active vertices, components of the union graph, cycle rank of the union, "
          "unordered pair of cycle ranks of the positive and negative graphs)",
    "C6": "active vertices only",
    "C7": "total collapse to one class (planted negative)",
    "C8": "(active vertices, number of uncancelled edges per side)",
    "C9": "common refinement of C1 and C3 (both isomorphism types, shared vertices, "
          "and the vertex-type multiset)",
    "C10": "C9 together with the isomorphism type of the unsigned union graph "
           "(the finest invariant built from the listed pieces, still below C0w)",
    "C11": "C1 together with the isomorphism type of the unsigned union graph "
           "(C10 with the vertex-type multiset dropped)",
}


# --------------------------------------------------------------------------
# provenance helpers
# --------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def factor_integer(value: int) -> dict[str, int]:
    value = abs(value)
    factors: dict[str, int] = {}
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            key = str(divisor)
            factors[key] = factors.get(key, 0) + 1
            value //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        factors[str(value)] = factors.get(str(value), 0) + 1
    return factors


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    for small in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % small == 0:
            return value == small
    d, s = value - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def primes_below(limit: int, count: int) -> list[int]:
    found: list[int] = []
    candidate = limit - 1 | 1
    while candidate > 3 and len(found) < count:
        if is_prime(candidate):
            found.append(candidate)
        candidate -= 2
    return found


# --------------------------------------------------------------------------
# system loading
# --------------------------------------------------------------------------
def iter_columns(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, mode="rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            column = json.loads(line)
            if not {"A", "B", "lin", "h"}.issubset(column):
                raise ValueError(f"missing column field at {path}:{line_number}")
            yield column


def signed_graph(column: dict[str, Any]) -> tuple[tuple, tuple]:
    """``(positive_edges, negative_edges)`` of ``W = B - A``; common edges cancel."""
    left = Counter(tuple(sorted(int(v) for v in e)) for e in column["A"])
    right = Counter(tuple(sorted(int(v) for v in e)) for e in column["B"])
    return tuple(sorted((right - left).elements())), tuple(sorted((left - right).elements()))


# --------------------------------------------------------------------------
# graph invariants
# --------------------------------------------------------------------------
_ISO_CACHE: dict[tuple, tuple] = {}


def iso_type(edges: tuple) -> tuple:
    """Isomorphism type of a simple graph with isolated vertices discarded.

    The label is ``(vertices, edges, nauty certificate hex)``.  nauty
    certificates are canonical, so equality of labels is graph isomorphism.
    """
    cached = _ISO_CACHE.get(edges)
    if cached is not None:
        return cached
    if not edges:
        result: tuple = (0, 0, "")
    else:
        from pynauty import Graph, certificate

        verts = sorted({v for e in edges for v in e})
        index = {v: i for i, v in enumerate(verts)}
        adjacency = {i: [] for i in range(len(verts))}
        for u, v in edges:
            adjacency[index[u]].append(index[v])
        result = (
            len(verts),
            len(edges),
            certificate(Graph(len(verts), directed=False, adjacency_dict=adjacency)).hex(),
        )
    _ISO_CACHE[edges] = result
    return result


def components_and_cycle_rank(edges: tuple) -> tuple[int, int, int]:
    if not edges:
        return 0, 0, 0
    verts = sorted({v for e in edges for v in e})
    parent = {v: v for v in verts}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[ru] = rv
    components = len({find(v) for v in verts})
    return len(verts), components, len(edges) - len(verts) + components


def invariants(positive: tuple, negative: tuple) -> dict[str, Any]:
    union = tuple(sorted(set(positive) | set(negative)))
    vp = {v for e in positive for v in e}
    vn = {v for e in negative for v in e}
    active = vp | vn
    dp = Counter(v for e in positive for v in e)
    dn = Counter(v for e in negative for v in e)
    _, comp_u, beta_u = components_and_cycle_rank(union)
    _, _, beta_p = components_and_cycle_rank(positive)
    _, _, beta_n = components_and_cycle_rank(negative)
    return {
        "iso_pos": iso_type(positive),
        "iso_neg": iso_type(negative),
        "iso_union": iso_type(union),
        "shared": len(vp & vn),
        "active": len(active),
        "edges": len(positive),
        "vertex_types": tuple(sorted((dp[v], dn[v]) for v in active)),
        "vertex_types_swapped": tuple(sorted((dn[v], dp[v]) for v in active)),
        "deg_pos": tuple(sorted(dp[v] for v in vp)),
        "deg_neg": tuple(sorted(dn[v] for v in vn)),
        "components_union": comp_u,
        "beta_union": beta_u,
        "beta_pos": beta_p,
        "beta_neg": beta_n,
    }


# --------------------------------------------------------------------------
# coarsenings
#
# The saved system stores one record per S_n x side-swap orbit of the unordered
# pair {A, B}, so W = B - A is only defined up to the global sign flip W -> -W
# (which exchanges the positive and negative parts).  Every coarsening below is
# therefore made invariant under that flip by taking the smaller of the two
# orientations.  Without this, a record's class would depend on the arbitrary
# orientation nauty happened to store, and phi would not be a function of the
# atom.
# --------------------------------------------------------------------------
def _unordered(a: Any, b: Any) -> tuple:
    return tuple(sorted([a, b], key=repr))


def coarsening_key(name: str, inv: dict[str, Any]) -> tuple:
    if name == "C1":
        return ("C1", _unordered(inv["iso_pos"], inv["iso_neg"]), inv["shared"])
    if name == "C2":
        return ("C2", _unordered(inv["iso_pos"], inv["iso_neg"]))
    if name == "C3":
        return ("C3", min(inv["vertex_types"], inv["vertex_types_swapped"]))
    if name == "C4":
        return ("C4", _unordered(inv["deg_pos"], inv["deg_neg"]))
    if name == "C5":
        return ("C5", inv["active"], inv["components_union"], inv["beta_union"],
                _unordered(inv["beta_pos"], inv["beta_neg"]))
    if name == "C6":
        return ("C6", inv["active"])
    if name == "C7":
        return ("C7",)
    if name == "C8":
        return ("C8", inv["active"], inv["edges"])
    if name == "C9":
        return ("C9", coarsening_key("C1", inv)[1:], coarsening_key("C3", inv)[1:])
    if name == "C10":
        return ("C10", coarsening_key("C9", inv)[1:], inv["iso_union"])
    if name == "C11":
        return ("C11", coarsening_key("C1", inv)[1:], inv["iso_union"])
    raise KeyError(name)


def canonical_class_label(key: tuple) -> str:
    return json.dumps(key, sort_keys=True, default=str)


# --------------------------------------------------------------------------
# streaming modular reduced row echelon form
# --------------------------------------------------------------------------
def _inv_upper_unit_mod(T: np.ndarray, p: int) -> np.ndarray:
    k = T.shape[0]
    inv = np.eye(k, dtype=np.float64)
    for j in range(k - 1, -1, -1):
        for i in range(j - 1, -1, -1):
            coef = T[i, j] % p
            if coef:
                inv[i] = np.mod(inv[i] - coef * inv[j], p)
                T[i] = np.mod(T[i] - coef * T[j], p)
    return inv


class ModRREF:
    """Reduced row echelon basis of the row space of a streamed matrix mod p."""

    def __init__(self, ncols: int, prime: int) -> None:
        self.n = ncols
        self.p = float(prime)
        self.pi = prime
        self.basis = np.zeros((0, ncols), dtype=np.float64)
        self.pivots: list[int] = []
        self.sources: list[int] = []

    def _check_exact(self, inner: int) -> None:
        if inner * (self.pi - 1) ** 2 > 2**53:
            raise OverflowError("float64 matmul would be inexact at this prime and rank")

    def add_block(self, block: np.ndarray, source_ids: Sequence[int]) -> None:
        p, pi = self.p, self.pi
        X = np.mod(block.astype(np.float64), p)
        if self.pivots:
            self._check_exact(len(self.pivots))
            X = np.mod(X - X[:, self.pivots] @ self.basis, p)
        rows: list[np.ndarray] = []
        cols: list[int] = []
        srcs: list[int] = []
        for i in range(X.shape[0]):
            nz = np.flatnonzero(X[i])
            if nz.size == 0:
                continue
            j = int(nz[0])
            X[i] = np.mod(X[i] * pow(int(X[i, j]), pi - 2, pi), p)
            if i + 1 < X.shape[0]:
                coef = X[i + 1 :, j].copy()
                mask = coef != 0
                if mask.any():
                    X[i + 1 :][mask] = np.mod(X[i + 1 :][mask] - np.outer(coef[mask], X[i]), p)
            rows.append(X[i].copy())
            cols.append(j)
            srcs.append(int(source_ids[i]))
        if not rows:
            return
        Y = np.array(rows, dtype=np.float64)
        self._check_exact(Y.shape[0])
        Y = np.mod(_inv_upper_unit_mod(Y[:, cols], pi) @ Y, p)
        if self.basis.shape[0]:
            self._check_exact(Y.shape[0])
            self.basis = np.mod(self.basis - self.basis[:, cols] @ Y, p)
        self.basis = np.concatenate([self.basis, Y], axis=0)
        self.pivots.extend(cols)
        self.sources.extend(srcs)

    @property
    def rank(self) -> int:
        return len(self.pivots)


def streamed_rank(rows: Iterator[tuple[int, np.ndarray]], ncols: int, prime: int,
                  block: int = 64) -> ModRREF:
    state = ModRREF(ncols, prime)
    buf: list[np.ndarray] = []
    ids: list[int] = []
    for source, vector in rows:
        buf.append(vector)
        ids.append(source)
        if len(buf) == block:
            state.add_block(np.array(buf, dtype=np.float64), ids)
            buf, ids = [], []
    if buf:
        state.add_block(np.array(buf, dtype=np.float64), ids)
    return state


def modular_ranks(matrix: np.ndarray, target: np.ndarray, primes: Sequence[int]) -> tuple[
    dict[str, Any], list[int], list[int]
]:
    """Modular rank of ``S`` and of ``[S | b]``.

    Also returns, at the first prime, the pivot rows of ``S`` and the class
    indices whose columns are independent, so that ``S[rows, classes]`` is a
    nonsingular square minor.
    """
    report: dict[str, Any] = {}
    pivot_rows: list[int] = []
    pivot_classes: list[int] = []
    m = matrix.shape[0]
    for prime in primes:
        state = streamed_rank(((i, matrix[i]) for i in range(m)), matrix.shape[1], prime)
        rank_s = state.rank
        rows = sorted(state.pivots)
        classes = sorted(state.sources)
        state.add_block(target.reshape(1, -1).astype(np.float64), [m])
        report[str(prime)] = {
            "rank_S": rank_s,
            "rank_S_augmented": state.rank,
            "modular_member": state.rank == rank_s,
        }
        if not pivot_rows:
            pivot_rows, pivot_classes = rows, classes
        del state
    return report, pivot_rows, pivot_classes


# --------------------------------------------------------------------------
# exact integer identity checking
# --------------------------------------------------------------------------
def _float_safe_prime_limit(cols: int) -> int:
    """Largest prime bound keeping ``cols`` products of residues exact in float64."""
    return max(3, int(math.isqrt((1 << 53) // max(cols, 1))))


def exact_product_matches(matrix: np.ndarray, vectors: Sequence[Sequence[int]],
                          rhs: Sequence[Sequence[int]], max_primes: int = 600,
                          block: int = 4096) -> tuple[bool, dict[str, Any]]:
    """Decide ``matrix @ v == r`` over Z for every ``(v, r)`` pair, exactly.

    Checked modulo primes whose product exceeds twice a proved bound on every
    residual entry, which turns the modular checks into an exact conclusion.
    """
    rows, cols = matrix.shape
    colmax = [int(x) for x in np.abs(matrix).max(axis=0)] if rows else [0] * cols
    bound = 0
    for v, r in zip(vectors, rhs):
        value = sum(colmax[j] * abs(int(v[j])) for j in range(cols))
        value += max((abs(int(x)) for x in r), default=0)
        bound = max(bound, value)
    pool = primes_below(_float_safe_prime_limit(cols), max_primes)
    modulus = 1
    used: list[int] = []
    for prime in pool:
        if modulus > 2 * bound:
            break
        modulus *= prime
        used.append(prime)
    evidence = {
        "bound_bits": int(bound).bit_length(),
        "check_prime_count": len(used),
        "check_prime_max": max(used) if used else None,
        "check_modulus_bits": modulus.bit_length(),
        "sufficient_modulus": modulus > 2 * bound,
    }
    if modulus <= 2 * bound:
        return False, evidence
    for prime in used:
        vmod = np.array([[int(x) % prime for x in v] for v in vectors],
                        dtype=np.float64).T
        rmod = np.array([[int(x) % prime for x in r] for r in rhs],
                        dtype=np.float64).T
        for start in range(0, rows, block):
            stop = min(start + block, rows)
            piece = np.mod(matrix[start:stop], prime).astype(np.float64)
            residual = np.mod(piece @ vmod - rmod[start:stop], float(prime))
            if residual.any():
                evidence["failing_prime"] = prime
                return False, evidence
    return True, evidence


def first_nonzero_row(matrix: np.ndarray, vector: Sequence[int], rhs: Sequence[int],
                      block: int = 4096) -> int | None:
    """A row index where ``matrix @ vector != rhs``, proved by one prime."""
    rows, cols = matrix.shape
    for prime in primes_below(_float_safe_prime_limit(cols), 8):
        vmod = np.array([int(x) % prime for x in vector], dtype=np.float64)
        rmod = np.array([int(x) % prime for x in rhs], dtype=np.float64)
        for start in range(0, rows, block):
            stop = min(start + block, rows)
            piece = np.mod(matrix[start:stop], prime).astype(np.float64)
            residual = np.mod(piece @ vmod - rmod[start:stop], float(prime))
            nz = np.flatnonzero(residual)
            if nz.size:
                return start + int(nz[0])
    return None


# --------------------------------------------------------------------------
# exact rational linear algebra on small submatrices
# --------------------------------------------------------------------------
def fmpz_matrix(rows: Sequence[Sequence[int]]):
    from flint import fmpz_mat

    return fmpz_mat([[int(x) for x in row] for row in rows])


def _as_fraction(value: Any) -> Fraction:
    try:
        return Fraction(int(value.numer()), int(value.denom()))
    except AttributeError:
        return Fraction(int(value))


def square_solve(square: np.ndarray, rhs: Sequence[int]) -> list[Fraction] | None:
    """Exact rational solution of a nonsingular square integer system."""
    k = square.shape[0]
    matrix = fmpz_matrix(square.tolist())
    vector = fmpz_matrix([[int(x)] for x in rhs])
    try:
        solution = matrix.solve(vector)
    except Exception:
        return None
    table = solution.tolist()
    return [_as_fraction(table[i][0]) for i in range(k)]


def exact_right_kernel(sub: np.ndarray) -> list[list[int]]:
    """Integer basis of ``{v : sub @ v = 0}``."""
    matrix = fmpz_matrix(sub.tolist())
    kernel, nullity = matrix.nullspace()
    table = kernel.tolist()
    return [[int(table[r][c]) for r in range(sub.shape[1])] for c in range(int(nullity))]


def clear_denominators(values: Sequence[Fraction]) -> tuple[int, list[int]]:
    lcm = math.lcm(*(v.denominator for v in values)) if values else 1
    return lcm, [int(v * lcm) for v in values]


# --------------------------------------------------------------------------
# membership decision for one class-sum matrix
# --------------------------------------------------------------------------
def decide_membership(class_matrix: np.ndarray, target: np.ndarray,
                      pivot_rows: Sequence[int], pivot_classes: Sequence[int]) -> dict[str, Any]:
    """Exact MEMBER / NON_MEMBER decision with a certificate.

    ``pivot_rows`` (``R``) and ``pivot_classes`` (``C``) come from the modular
    echelon form and have the same size ``r``; the ``r x r`` integer minor
    ``D = S[R, C]`` is nonsingular modulo the prime, hence over ``Q``.
    Everything below is exact rational or bounded-modulus integer arithmetic.
    """
    m = class_matrix.shape[0]
    transposed = class_matrix.T  # (rows x classes)
    R = sorted(int(x) for x in pivot_rows)
    C = sorted(int(x) for x in pivot_classes)
    if len(R) != len(C):
        return {"verdict": "UNKNOWN", "certificate": {"reason": "pivot sets disagree"}}
    D = class_matrix[np.ix_(C, R)].T  # (r x r): rows indexed by R, columns by C
    solution_C = square_solve(D, [int(target[i]) for i in R])
    if solution_C is None:
        return {"verdict": "UNKNOWN", "certificate": {"reason": "modular pivot minor is singular"}}
    solution = [Fraction(0)] * m
    for position, cls in enumerate(C):
        solution[cls] = solution_C[position]
    lcm, scaled = clear_denominators(solution)
    ok, evidence = exact_product_matches(
        transposed, [scaled], [[int(x) * lcm for x in target]]
    )
    if ok:
        return {
            "verdict": "MEMBER",
            "certificate": {
                "kind": "primal",
                "support_size": sum(1 for c in solution if c != 0),
                "denominator_lcm": str(lcm),
                "denominator_lcm_factorization": factor_integer(lcm),
                "max_numerator_bits": max(
                    (abs(c.numerator).bit_length() for c in solution), default=0
                ),
                "verified_on_all_rows": True,
                "verification": evidence,
            },
            "solution": solution,
        }
    extra = first_nonzero_row(transposed, scaled, [int(x) * lcm for x in target])
    if extra is None:
        return {"verdict": "UNKNOWN",
                "certificate": {"reason": "residual nonzero but no witnessing row"}}
    # Dual certificate on rows R + {extra}: y = (u, -1) with u^T D = S[extra, C].
    u = square_solve(D.T, [int(class_matrix[cls, extra]) for cls in C])
    if u is None:
        return {"verdict": "UNKNOWN", "certificate": {"reason": "transposed minor is singular"}}
    y_rows = R + [int(extra)]
    y_values = list(u) + [Fraction(-1)]
    y_lcm, y_scaled = clear_denominators(y_values)
    sub = class_matrix[:, y_rows]  # (m x (r+1))
    zero_ok, zero_evidence = exact_product_matches(sub, [y_scaled], [[0] * m])
    y_dot_b = sum(
        (y_values[i] * int(target[y_rows[i]]) for i in range(len(y_rows))), Fraction(0)
    )
    if zero_ok and y_dot_b != 0:
        return {
            "verdict": "NON_MEMBER",
            "certificate": {
                "kind": "dual",
                "support_rows": len(y_rows),
                "rows": y_rows if len(y_rows) <= 64 else y_rows[:64] + ["..."],
                "y_denominator_lcm": str(y_lcm),
                "y_max_numerator_bits": max(
                    (abs(v.numerator).bit_length() for v in y_values), default=0
                ),
                "y_dot_b": f"{y_dot_b.numerator}/{y_dot_b.denominator}",
                "y_transpose_S_is_zero_on_all_classes": True,
                "verification": zero_evidence,
                "exact": True,
            },
            "dual": {"rows": y_rows, "y": [f"{v.numerator}/{v.denominator}" for v in y_values]},
        }
    return {
        "verdict": "UNKNOWN",
        "certificate": {
            "reason": "dual vector from the modular pivot set is not exactly annihilating; "
                      "the rational rank exceeds the modular rank",
            "y_transpose_S_is_zero_on_all_classes": bool(zero_ok),
            "y_dot_b_nonzero": bool(y_dot_b != 0),
        },
    }


def exact_rank_confirmation(class_matrix: np.ndarray, pivot_rows: Sequence[int],
                            modular_rank: int, cap: int = 400) -> dict[str, Any]:
    """Pin the rational rank to the modular rank by verifying ``ker S_R == ker S``.

    ``rank_Q(S) >= modular rank`` always holds; verifying that an integer basis
    of ``ker S_R`` annihilates *every* row of ``S`` supplies the matching upper
    bound.  Only attempted when the class count is small enough for an exact
    nullspace.
    """
    m = class_matrix.shape[0]
    if m > cap:
        return {"attempted": False, "reason": f"classes {m} above exact-nullspace cap {cap}",
                "exact_rank_lower_bound": modular_rank}
    sub = class_matrix[:, list(pivot_rows)].T
    exact_sub_rank = int(fmpz_matrix(sub.tolist()).rank())
    kernel = exact_right_kernel(sub)
    if not kernel:
        confirmed = exact_sub_rank == m == modular_rank
        return {"attempted": True, "exact_rank_of_pivot_rows": exact_sub_rank,
                "kernel_dimension": 0, "kernel_verified_on_all_rows": True,
                "exact_rank": m if confirmed else None, "confirmed": bool(confirmed)}
    zeros = [[0] * class_matrix.shape[1] for _ in kernel]
    ok, evidence = exact_product_matches(class_matrix.T, kernel, zeros)
    exact_rank = m - len(kernel) if ok else None
    return {
        "attempted": True,
        "exact_rank_of_pivot_rows": exact_sub_rank,
        "kernel_dimension": len(kernel),
        "kernel_verified_on_all_rows": bool(ok),
        "verification": evidence,
        "exact_rank": exact_rank,
        "confirmed": bool(ok and exact_rank == modular_rank),
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--witness", type=Path, required=True,
                        help="exact rational witness over the same saved system (C0/C0w)")
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--primes", type=int, nargs=2, default=list(PRIMES))
    parser.add_argument("--coarsenings", nargs="*", default=None)
    parser.add_argument("--dedup-w", action="store_true",
                        help="keep one record per W-orbit, so a class sum weights every "
                             "signed graph once instead of once per stored pair")
    parser.add_argument("--refinement-only", action="store_true",
                        help="only compute the refinement poset of the coarsenings")
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    wanted = args.coarsenings or COARSENINGS
    started = time.time()
    system_digest = sha256_file(args.system)

    print(f"[n={args.n}] loading {args.system}", flush=True)
    hinge_rows: set[str] = set()
    records: list[dict[str, Any]] = []
    for index, column in enumerate(iter_columns(args.system)):
        if len(column["lin"]) != args.n:
            raise ValueError(f"record {index} has linear length {len(column['lin'])}")
        hinge_rows.update(column["h"])
        positive, negative = signed_graph(column)
        if len(positive) != len(negative):
            raise ValueError(f"record {index} is unbalanced")
        for u, v in positive + negative:
            if u == v:
                raise ValueError(f"record {index} has a loop")
        records.append({"positive": positive, "negative": negative,
                        "lin": [int(x) for x in column["lin"]],
                        "h": {k: int(v) for k, v in column["h"].items()}})
    order = sorted(hinge_rows)
    row_of_hinge = {direction: args.n + i for i, direction in enumerate(order)}
    nrows = args.n + len(order)
    print(f"[n={args.n}] {len(records)} records, {nrows} rows "
          f"({len(order)} hinge + {args.n} linear)", flush=True)

    target = np.zeros(nrows, dtype=np.int64)
    target[args.n - 1] = 1

    if args.refinement_only:
        names = [c for c in (args.coarsenings or COARSENINGS) if c not in ("C0", "C0w")]
        assignment: dict[str, list[tuple]] = {}
        for name in names:
            keys = []
            for record in records:
                if not record["positive"] and not record["negative"]:
                    keys.append(("CARRIER",))
                else:
                    if "inv" not in record:
                        record["inv"] = invariants(record["positive"], record["negative"])
                    keys.append(coarsening_key(name, record["inv"]))
            assignment[name] = keys
        refines: dict[str, list[str]] = {}
        for a in names:
            refines[a] = []
            for b in names:
                if a == b:
                    continue
                mapping: dict[tuple, tuple] = {}
                ok = True
                for ka, kb in zip(assignment[a], assignment[b]):
                    seen = mapping.setdefault(ka, kb)
                    if seen != kb:
                        ok = False
                        break
                if ok:
                    refines[a].append(b)
        payload = {
            "schema": SCHEMA + "-refinement",
            "n": args.n,
            "classes": {name: len(set(assignment[name])) for name in names},
            "refines": refines,
            "descriptions": {name: DESCRIPTIONS[name] for name in names},
        }
        out = args.outdir / f"refinement_n{args.n}.json"
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(payload["refines"], indent=2, sort_keys=True))
        print(f"[n={args.n}] wrote {out}", flush=True)
        return 0

    columns = np.zeros((len(records), nrows), dtype=np.int64)
    for i, record in enumerate(records):
        columns[i, : args.n] = record["lin"]
        for direction, value in record["h"].items():
            columns[i, row_of_hinge[direction]] = value

    sys.path.insert(0, str(REPO_ROOT / "tools" / "exactlift"))
    from exactlift import canonical_key  # noqa: E402

    by_w: dict[bytes, list[int]] = defaultdict(list)
    for i, record in enumerate(records):
        key = canonical_key([list(e) for e in record["positive"]],
                            [list(e) for e in record["negative"]], args.n)
        by_w[key].append(i)
    same_w_same_column = all(
        np.array_equal(columns[group[0]], columns[j]) for group in by_w.values() for j in group
    )
    original_groups = {i: list(group) for i, (_, group) in enumerate(sorted(
        by_w.items(), key=lambda kv: kv[1][0]))}
    position: dict[int, int] = {}
    if args.dedup_w:
        keep = sorted(group[0] for group in by_w.values())
        position = {old: new for new, old in enumerate(keep)}
        records = [records[i] for i in keep]
        columns = columns[keep]
        by_w = {key: [position[group[0]]] for key, group in by_w.items()}
        print(f"[n={args.n}] dedup-w: {len(records)} representative records", flush=True)

    structure = {
        "dedup_w": bool(args.dedup_w),
        "distinct_W_orbits": len(by_w),
        "identical_W_gives_identical_column": bool(same_w_same_column),
        "distinct_columns": len({columns[i].tobytes() for i in range(len(records))}),
        "carrier_records": sum(
            1 for r in records if not r["positive"] and not r["negative"]
        ),
    }
    print(f"[n={args.n}] structure {structure}", flush=True)

    witness = json.loads(args.witness.read_text(encoding="utf-8"))
    raw_coefficients: dict[int, Fraction] = defaultdict(Fraction)
    for entry in witness["coefficients"]:
        raw_coefficients[int(entry["column"])] += Fraction(entry["coefficient"])
    if args.dedup_w:
        # Columns are constant on a W-orbit, so the witness transports to the
        # representatives by summing the coefficients of each orbit.
        moved: dict[int, Fraction] = defaultdict(Fraction)
        for group in original_groups.values():
            total = sum((raw_coefficients.get(j, Fraction(0)) for j in group), Fraction(0))
            moved[position[group[0]]] += total
        raw_coefficients = moved
    base_coefficients = {k: v for k, v in raw_coefficients.items() if v}

    results: list[dict[str, Any]] = []

    def record_result(entry: dict[str, Any]) -> None:
        results.append(entry)
        rank = entry["modular"][str(args.primes[0])]["rank_S"]
        print(f"    {entry['coarsening']}: classes={entry['classes']} rank={rank} "
              f"-> {entry['verdict']}", flush=True)
        per = args.outdir / f"class_sum_n{args.n}_{entry['coarsening']}.json"
        per.write_text(
            json.dumps({"schema": SCHEMA, "n": args.n,
                        "system": str(args.system),
                        "system_sha256": system_digest,
                        "rank_primes": list(args.primes), **entry},
                       indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    # ---- C0: identity on stored records ---------------------------------
    if "C0" in wanted:
        print(f"[n={args.n}] C0", flush=True)
        modular, _, _ = modular_ranks(columns, target, args.primes)
        lcm = math.lcm(*(c.denominator for c in base_coefficients.values()))
        scaled = [0] * len(records)
        for k, v in base_coefficients.items():
            scaled[k] = int(v * lcm)
        ok, evidence = exact_product_matches(
            columns.T, [scaled], [[int(x) * lcm for x in target]]
        )
        record_result({
            "coarsening": "C0",
            "description": DESCRIPTIONS["C0"],
            "classes": len(records),
            "rows": nrows,
            "modular": modular,
            "verdict": "MEMBER" if ok else "UNKNOWN",
            "certificate": {
                "kind": "primal",
                "source": str(args.witness),
                "source_sha256": sha256_file(args.witness),
                "support_size": len(base_coefficients),
                "denominator_lcm": str(lcm),
                "denominator_lcm_factorization": factor_integer(lcm),
                "verified_on_all_rows": bool(ok),
                "verification": evidence,
            },
            "exact_rank": {"attempted": False,
                           "reason": "identity coarsening is too wide for exact kernel"},
        })

    # ---- C0w: identity on the W isomorphism type -------------------------
    if "C0w" in wanted:
        print(f"[n={args.n}] C0w", flush=True)
        groups = sorted(by_w.items(), key=lambda kv: kv[1][0])
        class_matrix = np.zeros((len(groups), nrows), dtype=np.int64)
        for c, (_, members) in enumerate(groups):
            class_matrix[c] = columns[members].sum(axis=0)
        modular, _, _ = modular_ranks(class_matrix, target, args.primes)
        # S_c = |c| * col_rep because identical W gives an identical column, so
        # the C0 witness transports: y_c = (sum of C0 coefficients in c) / |c|.
        verdict, certificate = "UNKNOWN", {}
        if same_w_same_column:
            coefficients = []
            for _, members in groups:
                total = sum((base_coefficients.get(j, Fraction(0)) for j in members),
                            Fraction(0))
                coefficients.append(total / len(members))
            lcm = math.lcm(*(c.denominator for c in coefficients))
            scaled = [int(c * lcm) for c in coefficients]
            ok, evidence = exact_product_matches(
                class_matrix.T, [scaled], [[int(x) * lcm for x in target]]
            )
            verdict = "MEMBER" if ok else "UNKNOWN"
            certificate = {
                "kind": "primal",
                "derived_from": str(args.witness),
                "support_size": sum(1 for c in coefficients if c != 0),
                "denominator_lcm": str(lcm),
                "denominator_lcm_factorization": factor_integer(lcm),
                "verified_on_all_rows": bool(ok),
                "verification": evidence,
            }
        record_result({
            "coarsening": "C0w",
            "description": DESCRIPTIONS["C0w"],
            "classes": len(groups),
            "rows": nrows,
            "modular": modular,
            "verdict": verdict,
            "certificate": certificate,
            "exact_rank": {"attempted": False,
                           "reason": "W-identity coarsening is too wide for exact kernel"},
        })
        del class_matrix

    # ---- coarse coarsenings ---------------------------------------------
    for name in wanted:
        if name in ("C0", "C0w"):
            continue
        print(f"[n={args.n}] {name}", flush=True)
        buckets: dict[tuple, list[int]] = defaultdict(list)
        for i, record in enumerate(records):
            if not record["positive"] and not record["negative"]:
                buckets[("CARRIER",)].append(i)
            else:
                if "inv" not in record:
                    record["inv"] = invariants(record["positive"], record["negative"])
                buckets[coarsening_key(name, record["inv"])].append(i)
        ordered = sorted(buckets.items(), key=lambda kv: canonical_class_label(kv[0]))
        class_matrix = np.zeros((len(ordered), nrows), dtype=np.int64)
        labels, sizes = [], []
        for c, (key, members) in enumerate(ordered):
            class_matrix[c] = columns[members].sum(axis=0)
            labels.append(canonical_class_label(key))
            sizes.append(len(members))
        modular, pivot_rows, pivot_classes = modular_ranks(
            class_matrix, target, args.primes)
        decision = decide_membership(class_matrix, target, pivot_rows, pivot_classes)
        solution = decision.pop("solution", None)
        dual = decision.pop("dual", None)
        rank_confirmation = exact_rank_confirmation(
            class_matrix, pivot_rows, modular[str(args.primes[0])]["rank_S"]
        )
        entry = {
            "coarsening": name,
            "description": DESCRIPTIONS[name],
            "classes": len(ordered),
            "rows": nrows,
            "modular": modular,
            "verdict": decision["verdict"],
            "certificate": decision["certificate"],
            "exact_rank": rank_confirmation,
            "class_sizes": sizes,
            "class_labels": labels,
        }
        if dual is not None:
            entry["dual_certificate"] = dual
        if solution is not None:
            entry["solution"] = {
                labels[i]: f"{solution[i].numerator}/{solution[i].denominator}"
                for i in range(len(ordered)) if solution[i] != 0
            }
        record_result(entry)
        del class_matrix

    payload = {
        "schema": SCHEMA,
        "n": args.n,
        "system": str(args.system),
        "system_sha256": system_digest,
        "witness": str(args.witness),
        "witness_sha256": sha256_file(args.witness),
        "records": len(records),
        "rows": nrows,
        "hinge_rows": len(order),
        "linear_rows": args.n,
        "target": "1 on the last linear row, 0 elsewhere",
        "rank_primes": list(args.primes),
        "structure": structure,
        "descriptions": DESCRIPTIONS,
        "results": results,
        "seconds": round(time.time() - started, 3),
    }
    out = args.outdir / f"class_sum_n{args.n}.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[n={args.n}] wrote {out} in {payload['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
