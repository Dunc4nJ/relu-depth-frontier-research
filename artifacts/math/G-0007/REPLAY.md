# Replay instructions

## Environment observed at freeze

- Repository: /data/projects/relu-depth-frontier-research
- CPython: 3.13.7
- System NetworkX: 3.6.1
- Project-venv python-flint: 0.9.0
- Project-venv tqdm: 4.70.0

The graph scripts use system python because NetworkX is installed there.
The rank and solve scripts use .venv/bin/python because python-flint is
installed in the project environment. Intermediate generated data is
written only inside a fresh run-owned directory.

Run every command from the repository root.

Create one isolated run directory and keep this variable in the same shell:

    G0007_RUN_DIR="$(mktemp -d /tmp/g0007-replay.XXXXXX)"
    export G0007_RUN_DIR
    chmod 700 "$G0007_RUN_DIR"

Every G-0007 generator/rank/solve command below must inherit this variable.
The scripts fail closed if the directory is absent, symlinked,
foreign-owned, or not mode 0700.

## 1. Check pinned inputs

    sha256sum \
      literature/repos/max-relu-certificates/verify_certificate.py \
      literature/repos/max-relu-certificates/certificates/certificate_8_3.json \
      literature/repos/max-relu-certificates/certificates/certificate_9_4.json \
      literature/repos/max-relu-certificates/certificates/certificate_10_4.json

Expected hashes are listed in REPORT.md.

## 2. Structural census and cross-n matching

    python3 artifacts/math/G-0007/scripts/summarize_beta.py
    python3 artifacts/math/G-0007/scripts/match_n9_n10.py
    python3 artifacts/math/G-0007/scripts/test_bridge_lift.py

Key checkpoints:

- MAX9 beta histogram: 0:151, 1:123, 2:53, 3:9, 4:1.
- MAX10 beta histogram: 0:252, 1:104, 2:37, 3:8, 4:1.
- 119 MAX9 types match a MAX10 type; raw coefficient ratios have 71
  distinct values.

The exhaustive full-edge-extension script is intentionally separate
because its NetworkX isomorphism loop is slow:

    python3 artifacts/math/G-0007/scripts/test_full_edge_extension.py

## 3. Enumerate colored trees and bridge closures

    python3 artifacts/math/G-0007/scripts/colored_tree_closure.py

This emits deterministic representatives under $G0007_RUN_DIR plus
tree_reps_manifest.json, and should report:

- MAX9 universe 739; bridge closure 710; public-tree coverage 149/151.
- MAX11 universe 12,459; bridge closure 11,072.
- max9_extra_tree_reps.json contains the 29 MAX9 tree types outside
  the bridge closure.

## 4. Build exact expansion columns

    .venv/bin/python artifacts/math/G-0007/scripts/n9_mod_rank.py
    .venv/bin/python artifacts/math/G-0007/scripts/n9_bridge_rank.py
    .venv/bin/python artifacts/math/G-0007/scripts/n9_cached_verify.py

On a cold run these invoke the pinned upstream expansion kernel across
many atoms and always regenerate provenance-keyed files of the form:

- $G0007_RUN_DIR/n9_columns_<metadata fingerprint>.pkl
- $G0007_RUN_DIR/n9_bridge_columns_<metadata fingerprint>.pkl

The cached verifier should print the linear vector
0,0,0,0,0,0,0,0,1 and zero nonzero hinge residuals for the published
MAX9 certificate.

The scripts inject only a no-op progress wrapper under the module name
tqdm; the mathematical functions are loaded unchanged from the pinned
upstream verifier.

The fresh 0700 directory, fingerprint, and embedded metadata bind each cache to its schema,
producer and contract scripts, kernel, source certificate or representative
set, and expected column count. Tree-representative files are separately
bound to their generator, input certificates, hashes, byte sizes, and
counts. Cache writes use atomic replacement. A cache index records each
completed byte hash; downstream scripts securely read and hash bytes before
unpickling and fail closed if any cache or representative provenance is
absent or mismatched. Legacy predictable /tmp cache files are ignored.

## 5. Exact tree obstruction and hybrid-family rank

    .venv/bin/python artifacts/math/G-0007/scripts/n9_bridge_rank_exact.py
    .venv/bin/python artifacts/math/G-0007/scripts/n9_alltree_rank.py
    .venv/bin/python artifacts/math/G-0007/scripts/n9_hybrid_rank.py
    .venv/bin/python artifacts/math/G-0007/scripts/n9_support_uniqueness.py

Expected exact-Q checkpoints:

    bridge trees: rank 360; rank plus target 361
    all 739 trees: rank 360; rank plus target 361
    hybrid family: rank 505; rank plus target 505

The modular outputs are screening diagnostics. The lines explicitly
labeled exact rank or rank_Q are the rational-rank claims.

## 6. Reconstruct and compare the exact certificate

    .venv/bin/python artifacts/math/G-0007/scripts/n9_hybrid_solve.py
    sha256sum "$G0007_RUN_DIR/n9_hybrid_solution.json" \
      "$G0007_RUN_DIR/n9_hybrid_certificate.json"
    cmp "$G0007_RUN_DIR/n9_hybrid_solution.json" \
      artifacts/math/G-0007/data/n9_hybrid_solution.json
    cmp "$G0007_RUN_DIR/n9_hybrid_certificate.json" \
      artifacts/math/G-0007/data/n9_hybrid_certificate.json

Expected hashes:

    834bacdf69a1b19ba65f27d85df1947aa2c99221db59e202278f4b52a6a49d2c
    308378e362201f6ef97d5963f107af14748e38dc21556c31134f936eaa58ed42

Both cmp commands should exit with status zero.

Freeze and compare the run attestation:

    .venv/bin/python artifacts/math/G-0007/scripts/attest_run.py
    sha256sum "$G0007_RUN_DIR/replay_attestation.json"
    cmp "$G0007_RUN_DIR/replay_attestation.json" \
      artifacts/math/G-0007/data/replay_attestation.json

Expected attestation hash:

    0b4aeb0e9929fc4528827fc4a513f6e285e56c615d5f4884e53eda8420b0e9a8

## 7. Run the upstream verifier

    .venv/bin/python \
      literature/repos/max-relu-certificates/verify_certificate.py \
      artifacts/math/G-0007/data/n9_hybrid_certificate.json

Expected final line:

    OK

This direct verifier is exact but slow because it expands every term over
all 9! coordinate orders. The exact all-coordinate verification in step 6
checks the same expansion through cached columns and is much faster.

## Certification boundary

Successful replay establishes reproducibility against the pinned upstream
kernel. It does not provide independent implementation diversity. A
clean-room evaluator and orbit generator remain required for stronger
certification.
