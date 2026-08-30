# G-0081 — complete native Schur rank/solve result

`run_isolated.sh` and `full_dictionary_schur.py` are the frozen launcher/runner
for the decisive finite-row calculation. The first outcome-producing run is
bound by `full_dictionary_schur_preregistration_v1.json`. The registered run
completed and its canonical result is
`full_dictionary_schur_result_v1.json.gz` (SHA-256
`61e9c63b974a64d0272569b5e71a04541d49d853a76ec31ca59a6b6d0d1b95ef`).

## Frozen outcome

Over `F_1000003`, the old 8,107-column matrix has basis rank 6,876. After
eliminating that basis, the complete 9,862 by 18,583 target-last Schur matrix
has new-column rank 1,992 and augmented rank 1,993; the target coordinate is a
pivot. Thus the full frozen dictionary has rank 8,868 and adjoining MAX11
raises the rank to 8,869. All 18,582 new columns were retained; price filtering
was disabled.

The child persisted the complete 733 MiB RREF. A separately supervised parent
recomputed it and obtained byte-identical output (`80.975 s` child,
`80.091 s` parent). Start/end custody receipts, the C-to-S-to-R hash chain, and
the registered input bindings agree. The scientific payload SHA-256 is
`6d8d9bb6406f26a1515d60ef8c1a366fb556d40207184fa17d776d1626a0a06a`.

This is exactly a one-prime, finite-row separation from the registered 26,689
columns. It is not characteristic-zero nonmembership: rank loss modulo this
prime could affect the dictionary and augmented matrices differently. It also
does not cover the complete degree-five universe, establish a global CPWL
identity, or imply an unrestricted two-hidden-layer ReLU lower bound.

## Exact subject and boundary

The runner tests all 26,689 frozen dictionary columns on all 16,738 frozen
rows over `F_1000003`:

- 8,107 old G-0077 columns, including the three carriers;
- all 18,582 G-0079 same-component representatives in their registered order;
- the target is always the last augmented coordinate.

The complete G-0079 price vector is a custody/control input. It never filters
columns: the 630 zero-price columns and 17,952 nonzero-price columns are all
retained.

A target pivot is only modular separation from this finite dictionary on
these rows. A nonpivot target is only modular compatibility unless the left
Schur rank is 9,862. In that full-row-rank branch, a raw integer block minor
also proves rational spanning of every target on the frozen rows. None of
these branches is by itself a global CPWL identity or an unrestricted depth-
two theorem.

## Frozen reduction

Let `P,R` be the ordered G-0077 old-column/row basis, `Q` the ordered
complement of `R`, and `B=A[R,P]`. The certified inverse cache supplies
`B^-1 mod p`. With the target last, the native child constructs

```text
Lambda = A[Q,P] B^-1
S = [C[Q,:] | b[Q]] - Lambda [C[R,:] | b[R]]  (mod p).
```

It then calls the bundled FLINT 3.6 ABI directly:

```c
slong nmod_mat_rref(nmod_mat_t A);
```

The call mutates `A` to RREF and returns its rank. The runner never invokes
the `python-flint` bulk matrix constructor and never switches to CEGIS or a
price-selected subdictionary.

## Input and preregistration custody

The preregistration is not accepted merely because the caller supplies its
SHA-256. The caller must also supply one full Git commit ID. Before execution,
the runner proves all of the following:

- the commit exists and is an ancestor of the exact execution `HEAD`;
- the preregistration is a regular tracked blob at both that commit and `HEAD`;
- the anchor blob, `HEAD` blob, and live preregistration bytes are identical;
- the runner's `HEAD` blob and live source bytes are identical;
- scoped `git status` for the runner and preregistration is empty, rejecting
  dirty, staged, deleted, and untracked versions.

Git is invoked only as fixed `/usr/bin/git` under an allowlisted environment,
with explicit no-follow-resolved `--git-dir` and `--work-tree` and a 120-second
per-command timeout. Inherited repository, index, object-alternate, namespace,
replacement-ref, configuration, and `PATH` selectors do not participate. Every
effective configuration row must report local scope and the single hash-bound
`.git/config` origin. Includes, `config.worktree`, URL rewrites, filters,
`core.fsmonitor`, hooks, and transport/object commands are rejected. The raw
origin value—not `remote get-url` after rewriting—must equal the registered
GitHub URL. The receipt binds the resolved worktree/Git/common-directory
identities, object format, exact publication URL, and the already-published
`refs/heads/master` commit.

Python startup is also outside ambient caller control. The committed launcher
has a static-BusyBox shebang and replaces the environment with exactly
`PATH=/usr/bin:/bin`, `LANG=C`, and `LC_ALL=C` before executing the registered
interpreter with `-I -S -B`. The runner checks those flags, the initial standard-
library-only `sys.path`, the absence of `site` initialization, and the exact
interpreter before manually adding only the registered venv site-packages path.
Thus `PYTHONPATH`, user/site customization, script-directory shadow modules,
`PYTHONHOME`, `LD_PRELOAD`, and `LD_LIBRARY_PATH` cannot select startup code.

The exact anchor commit, execution `HEAD`, Git object format, preregistration
blob IDs, runner blob ID, and SHA-256 values enter start/end custody and every
cache/result receipt. Any `HEAD` movement or byte/status drift during execution
fails closed. This establishes commit-before-computation precedence; a content
hash alone would not.

The run additionally binds the following exact inputs. Every file-level
binding is rehashed at start and end; embedded scientific-payload hashes and
independently recomputed semantic hashes are checked at their relevant gates:

| Input | SHA-256 |
|---|---|
| isolated startup launcher | `9f6d75a6cb6903e2165896b74f725a87a5cf8f8f740831ebc98aa977ead2b0bb` |
| static `/usr/bin/busybox` | `6c4a39ad9ab7071e4c0bdc3f61546b1526507e30a8f24886e4ef353d66e7398d` |
| G-0079 registered price runner | `7539515641c241a28be45cea88445bd4f598f7c0693ab521c31805530c9f67da` |
| G-0079 complete price artifact | `5d6754c91f7971aa3fdad2d1f171645f32fa57c26b4a001bb3b6ac9d5e802958` |
| price scientific payload | `357e2437849dac4074995892a6f174d9f225848280e2bf53d9f9ea1010d9e265` |
| 230-row raw support matrix | `a38b8237b108284ecafaa4f97a0c0c29a60b3a9dd58521389762effb4e4619b2` |
| native FLINT adapter | `bb7677f84865c0ec380237fddb94a05d4c0806c979f41c4eddd8f7b27fdf59cf` |
| inverse cache file | `2888960f52e64e36e8ab26c1fc69f65c8c53bda4d39a1a51ad17fbd759805e86` |
| inverse raw data | `4238321f534bd0005e0952019faf340b32669cce4041f252aa0f029215994af3` |
| inverse receipt | `9820a3afcb8e0cd453a7219703669867467291e94e439e7742eafda0c3a584c2` |
| G-0077 modular basis | `9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4` |
| G-0078 exact separator | `8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96` |
| old augmented matrix | `5c04ef6cadebf41e31cf01f822210305d4977ebbf0aebeba2bacc73e765c5c9f` |
| CPython 3.12/PyPI wheel manifest | `f17bb20bb817e5c4fe626f3782c3b382b1ba0cd2397b704def11a26df61ea1b4` |

The G-0079 owned-byte loader separately binds the transitive G-0075/G-0074/
G-0073 semantic source chain. Source bytes are read, hashed, and executed from
that owned buffer; project bytecode caches are not semantic inputs.

## All-column matrix construction

`FastEvaluator` caches exactly 364 four-profile assignment-code matrices and
78 three-profile assignment-code matrices. A Linux `fork` pool of exactly
eight workers evaluates deterministic eight-row chunks. Workers write only
disjoint slices of one `<u4` NumPy cache of shape `(16738,18582)`.

Progress is committed only after flushing and `fsync`ing a batch. Every
committed chunk has a SHA-256, but no later execution may resume it.
Finalization writes an exclusive receipt containing the whole NPY
hash, raw C-order data hash, evaluator manifests, dimensions, and start/end
custody, including the exact preregistration bytes. Final cache promotion uses
a same-filesystem, no-replace hard link; it cannot overwrite an existing final
path. Partial/final state mixtures fail closed instead of being repaired or
overwritten silently.

Before quotient use, the original direct nested-max evaluator independently
recomputes all `230 × 18,582 = 4,273,860` G-0078 support entries. Their raw
`int64` C-order hash must equal the frozen `a38b...19b2`; every residue must
equal the corresponding C-cache entry; and the exact price and target vectors
must replay. The artifact-specified G-0078 failing row is then recomputed as a
Schur row and must be one common nonzero scalar multiple of the complete price
row and target modulo `p`.

## Fresh-only native caches

Every preregistration chooses a 32-hex run ID and the ignored namespace
`artifacts/math/G-0081/cache-<run-id>/`. It must not exist, even if empty. The
public supervisor creates it once with `mkdirat`/no-follow checks and mode
`0700`, then creates the lock with `O_EXCL|O_NOFOLLOW` and verifies the inode
before mutation. Completed, partial, and caller-authored caches are never
loaded. An interruption spends the registration; a new registration recomputes
from zero in a new namespace.

1. `complete_new_matrix_p1000003_v1.npy`
   - shape `(16738,18582)`, dtype little-endian `uint32`;
   - complete new matrix `C mod p`, no filtering;
   - within-run chunk journal and final hash/custody receipt.
2. `pre_rref_schur_augmented_p1000003_v1.npy`
   - shape `(9862,18583)`, dtype little-endian `uint32`;
   - exact pre-RREF modular `S`, target last;
   - exclusive whole-file/raw-data receipt.
3. `in_place_rref_augmented_p1000003_v1.npy`
   - the full FLINT-mutated target-last RREF, same shape/dtype;
   - receipt binds the source-S hash, both ranks, target-pivot bit, ordered
     pivot columns, and ordered free new columns;
   - this is sufficient to recover the complete finite-row nullspace without
     paying for rank again: for free column `f`, set `x_f=1`, other free
     coordinates zero, and `x_p=-RREF[pivot_row(p),f] mod p`.

The third cache is the bridge to later global gated-facet CEGIS. Rank alone is
not treated as the endpoint. Before the final gzip is created, a separately
supervised, still-locked verifier re-proves the lock/namespace identity,
rehashes the C→S→R source/receipt chain, recomputes the complete RREF from S,
compares every persisted entry, derives every branch-bearing projection
independently, and on a member branch repeats all 16,738 rows and the determinant
evidence.

## Decision and replay

Pivots are scanned left-to-right with the target last.

- Target pivot: emit `MODULAR_SEPARATION_DISCOVERY` only.
- Target nonpivot: choose the canonical free-zero new solution, derive old
  basis coefficients with `B^-1`, and replay all 16,738 raw rows from the old
  and new caches.
- If `rank(S_new)=9862`: recompute `det(B) mod p` and
  `det(S[:,pivot_new]) mod p`. Their nonzero product is the determinant modulo
  `p` of the 16,738-square **integer** raw-column minor
  `[A[:,P] | C[:,pivot_new]]` in row order `[R,Q]`. Therefore that integer
  determinant is nonzero over `Q`, proving rational finite-row spanning. The
  cached modular Schur matrix is explicitly not claimed to be an integer
  Schur matrix over `Q`.

The displayed modular solution is not called a rational lift. An explicit
exact-Q lift and all-row replay are still required for rational coefficients;
global chamber/facet replay is still required for a CPWL identity.

## Resource and failure contract

The frozen preflight records:

- 183,265,546 Schur entries;
- projected dense multiplication: 538.054 s;
- projected native rank: 408.360 s;
- conservative whole-kernel projection: 10,710.702 s;
- projected native minimum peak: 3,755,753,472 bytes.

Execution requires at least 12 GiB available RAM and 12 GiB free disk. The
scientific child has a separately registered 21,600-second ceiling. Independent
parent-authorized finalization has its own registered 3,600-second ceiling and
runs in another supervised session/process group, so a blocked second FLINT
RREF can be killed and reaped. Each Git command has a registered 120-second
timeout. These are deliberately separate allowances; there is no misleading
single total-CLI wall-time claim. The CLI exposes `--startup-probe`,
`--self-test`, `--check-registration`, and `--run`; ordinary Python import fails
before helpers are defined. There is no module-level scientific kernel,
capability class, consumer, or child entry. Only after public revalidation,
fresh namespace creation, and acquisition of the derived lock does `public_run`
define its child/science closure and fork it. A random one-shot frame passes
through an inherited anonymous pipe. Before scientific work, the child
revalidates the registration, consumes and closes that pipe, verifies its
PID/session/process group, and proves that the inherited descriptor is the
exact lock inode derived from the registered cache path.

The child arms Linux `PR_SET_PDEATHSIG=SIGKILL` and rechecks its parent PID to
close the fork/parent-death race. Each later fork worker independently arms the
same death signal against the kernel parent. Thus a wrapper crash cannot leave
the kernel or cache workers running; ordinary `Pool.terminate()` behavior is
restored in workers. A parent-side exception or cancellation also kills and
reaps the child before releasing the lock. At the scientific child's six-hour
deadline the wrapper terminates and reaps that group. It then accepts no branch
until the separately supervised finalizer succeeds within one hour. A timeout,
signal, or resource failure in either supervised process writes only
`RESOURCE_UNRESOLVED`; if the scientific child had produced a candidate, that
candidate is explicitly discarded without preserving its branch fields. The
runner never silently substitutes CEGIS. Native matrices are confined to the
two supervised processes and cleared on normal paths.

This protocol proves precedence for artifacts accepted by this committed
runner. It cannot prove that nobody independently computed the same mathematics
with altered code or an older checkout; that broader operational claim requires
external audit and custody, not a local program alone.

## Self-test and registration

The source-only self-test is safe to run now:

```bash
artifacts/math/G-0081/run_isolated.sh --self-test
```

It covers native multiplication, in-place FLINT RREF member/separator
fixtures, target-last pivot scanning, free-zero solving, rank-full-Q logic,
cache mutation rejection, price-row scalar logic, and nine tiny non-outcome
fast/frozen/nested evaluator entries. Must-fail controls reject a dirty runner,
dirty or untracked preregistration, clean post-anchor preregistration mutation,
a foreign Git database, included/config.worktree URL rewriting, executable
`core.fsmonitor`, ambient `sitecustomize`, unsafe import shadows, the removed
internal CLI, ordinary import, any module-level scientific entry, an existing
or symlink cache namespace, and a symlink lock without changing its victim.
Production-factored controls reject branch-reversing RREF bytes and mutated
outer/receipt pivot projections. Fork fixtures exercise both deadlines,
post-`prctl` parent-death races, process-group termination, verifier/worker
death, and child reap. They evaluate no actual quotient or rank.

Public `--run` cannot execute without the separately committed preregistration
whose exact bytes and expected runner hash are both supplied on the CLI. That
invocation must also supply the full commit ID anchoring the preregistration via
`--preregistration-commit`. The artifact must bind the output path, cache
directory and run ID, all hashes, dimensions, resource gates, stage order,
eight workers, the single-origin Git protocol and timeout, isolated startup
launcher, fresh-only and spent-on-interruption cache policies, both supervised
wall allowances, the complete parent-verification/output stage order, and the
prohibition on price filtering. The frozen v1 preregistration satisfies those
bindings and is the only registration used by the canonical result above.
