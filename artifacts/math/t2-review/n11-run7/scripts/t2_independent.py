"""T2 independent re-implementation + differential test against the pinned upstream verifier.

py_column_literal  -> calls the PINNED upstream functions (reference semantics)
py_column_dp       -> my own subset DP, written from the upstream definition
"""
import importlib.util, itertools, json, math, random, sys
from fractions import Fraction
from pathlib import Path

REPO = Path("/data/projects/relu-depth-frontier-research")
spec = importlib.util.spec_from_file_location(
    "upstream", REPO / "literature/repos/max-relu-certificates/verify_certificate.py")
upstream = importlib.util.module_from_spec(spec)
sys.modules["upstream"] = upstream
spec.loader.exec_module(upstream)


def py_column_literal(left, right, n):
    """Reference column via the pinned upstream symmetrized_pair (0-based edges)."""
    linear, hinges = upstream.symmetrized_pair(tuple(map(tuple, left)),
                                               tuple(map(tuple, right)), n)
    return tuple(linear), dict(hinges)


def py_column_dp(left, right, n):
    """Independent subset DP: state = (placed mask, back-degree word of right-left)."""
    m = [[0] * n for _ in range(n)]
    for s, side in ((-1, left), (1, right)):
        for a, b in side:
            m[a][b] += s
            if a != b:
                m[b][a] += s
    # word[rank] = signed count of edges whose later endpoint is placed at rank
    states = {(0, ()): 1}
    for rank in range(n):
        nxt = {}
        for (mask, word), cnt in states.items():
            for v in range(n):
                bit = 1 << v
                if mask & bit:
                    continue
                inc = m[v][v] + sum(m[v][u] for u in range(n) if mask >> u & 1)
                key = (mask | bit, word + (inc,))
                nxt[key] = nxt.get(key, 0) + cnt
        states = nxt
    assert sum(states.values()) == math.factorial(n), "permutation census"

    # sum over permutations of left_form, analytically (carrier/loop split)
    loops = sum(1 for a, b in left if a == b)
    nonloops = len(left) - loops
    linear = [loops * math.factorial(n - 1) + nonloops * 2 * r * math.factorial(n - 2)
              for r in range(n)]
    hinges = {}
    for (_, word), cnt in states.items():
        nz = next((x for x in word if x), None)
        if nz is None:
            continue
        assert sum(word) == 0
        if nz < 0:                       # base is the right form: left + (right-left)
            for i, x in enumerate(word):
                linear[i] += cnt * x
        g = 0
        for x in word:
            g = math.gcd(g, abs(x))
        o = 1 if nz > 0 else -1
        d = tuple(o * x // g for x in word)
        pre = 0
        for x in d[:-1]:
            pre += x
            if pre < 0:
                hinges[d] = hinges.get(d, 0) + cnt * g
                break
    return tuple(linear), hinges


def load_pair(term, n):
    return upstream.read_pair(term["pair"], n)


def cross_check(tag, terms, n, limit=None):
    bad = 0
    for i, term in enumerate(terms if limit is None else terms[:limit]):
        left, right = load_pair(term, n)
        a = py_column_literal(left, right, n)
        b = py_column_dp(left, right, n)
        if a != b:
            bad += 1
            print(f"  MISMATCH {tag} term {i}")
    print(f"  {tag}: {len(terms) if limit is None else limit} columns, mismatches={bad}")
    return bad
