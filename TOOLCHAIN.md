# TOOLCHAIN — relu-depth-frontier-research

Pinned tools for replay. Run `source scripts/activate-toolchain.sh` before local work. The project-local `.venv/` and `.toolchains/` directories are deliberately untracked. `requirements-solvers.lock` hash-pins the CPython 3.13 Linux x86_64 wheels; ambient executables are version-recorded capability dependencies, not bit-reproducible contents.

| Tool | Version | Pin / location | Purpose |
|---|---:|---|---|
| Python | 3.13.7 | project `.venv`; `requirements-solvers.lock` | orchestration and exact/symbolic computations |
| Lean | 4.33.1 | `leanprover/lean4:v4.33.1`, commit `819816b2e0a3bf405af45ae5c7af2491d8f5bee6` | proof checking |
| Mathlib | v4.33.1 | commit `0df444a360eaa60ab8c11dca51a86af692955474` | formal mathematics library |
| Elan | 4.2.4 | `.toolchains/elan`; installer SHA-256 in environment manifest | Lean toolchain manager |
| Lake | 5.0.0-src+819816b | bundled with pinned Lean | Lean build and dependency manager |
| Z3 | 5.1.0 | `z3-solver==5.1.0.0` | exact rational SMT and bounded feasibility controls |
| cvc5 | 1.3.4 | official static CLI asset plus `cvc5==1.3.4`; asset hash in environment manifest | independent exact rational SMT path |
| SymPy | 1.14.0 | `sympy==1.14.0` | symbolic identities and rational matrices |
| python-flint | 0.9.0 | `python-flint==0.9.0` | fast exact integer/rational arithmetic |
| HiGHS | 1.15.1 | `highspy==1.15.1` | floating sparse LP discovery only |
| tqdm | 4.70.0 | hash-pinned wheel in `requirements-solvers.lock` | progress dependency required by the upstream verifier; no mathematical standing |
| SQLite | 3.46.1 | ambient executable | local indexes, not proof |
| Git | 2.51.0 | ambient executable | versioned campaign state |
| Poppler tools | 25.03.0 | ambient `pdftotext`, `pdfinfo` | literature extraction/integrity checks |
| curl | 8.14.1 | ambient executable | primary-source retrieval |
| sha256sum | uutils 0.2.2 | ambient executable | byte-level manifests |

Machine-readable retry inventory:

<!-- TOOL-VERSIONS-V1:BEGIN -->
TOOL-VERSION-V1 python3 3.13.7
TOOL-VERSION-V1 lean 4.33.1
TOOL-VERSION-V1 lake 5.0.0
TOOL-VERSION-V1 z3 5.1.0
TOOL-VERSION-V1 cvc5 1.3.4
TOOL-VERSION-V1 sympy 1.14.0
TOOL-VERSION-V1 python-flint 0.9.0
TOOL-VERSION-V1 highspy 1.15.1
TOOL-VERSION-V1 tqdm 4.70.0
TOOL-VERSION-V1 sqlite3 3.46.1
<!-- TOOL-VERSIONS-V1:END -->

Python wheel receipt: `environment/python-wheel-hashes.txt`. Recreate the environment with
`python -m pip install --require-hashes -r requirements-solvers.lock` on the recorded platform.

Environment manifest: `environment/toolchain-manifest.txt` · SHA-256 `a4e7b09efb4d445b9a34217f0aff478771c36542ca8c4d58e5b15e9d6273b81e`.

Local replay execution remains disabled until a handle-specific authorization row is added after preregistration.

<!-- REPLAY-AUTHORIZATIONS-V1:BEGIN -->
<!-- REPLAY-AUTHORIZATIONS-V1:END -->

Install policy: project-local installs are allowed; no `sudo` or ambient package mutation. Every change must update the lock, manifest, hashes, trust rows, and a known-answer control in the same round.
