# G-0081 — complete native Schur rank/solve candidate

`full_dictionary_schur.py` is the frozen-source candidate for the decisive
finite-row calculation. It has **not** been registered or run. This directory
contains no preregistration and no scientific result.

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

## Input custody

The run binds the following exact inputs. Every file-level binding is rehashed
at start and end; embedded scientific-payload hashes and independently
recomputed semantic hashes are checked at their relevant gates:

| Input | SHA-256 |
|---|---|
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
| environment manifest | `12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c` |

The G-0079 owned-byte loader separately binds the transitive G-0075/G-0074/
G-0073 semantic source chain. Source bytes are read, hashed, and executed from
that owned buffer; project bytecode caches are not semantic inputs.

## All-column matrix construction

`FastEvaluator` caches exactly 364 four-profile assignment-code matrices and
78 three-profile assignment-code matrices. A Linux `fork` pool of exactly
eight workers evaluates deterministic eight-row chunks. Workers write only
disjoint slices of one `<u4` NumPy cache of shape `(16738,18582)`.

Progress is committed only after flushing and `fsync`ing a batch. Every
committed chunk has a SHA-256. Resume verifies every completed chunk before
continuing. Finalization writes an exclusive receipt containing the whole NPY
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

## Persistent native caches

All caches are under ignored `artifacts/math/G-0081/cache/` and are protected
by an exclusive `flock` during public execution.

1. `complete_new_matrix_p1000003_v1.npy`
   - shape `(16738,18582)`, dtype little-endian `uint32`;
   - complete new matrix `C mod p`, no filtering;
   - resumable chunk journal and final hash/custody receipt.
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
not treated as the endpoint.

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

Execution requires at least 12 GiB available RAM and 12 GiB free disk, with a
larger dynamic disk requirement when caches are absent. The complete kernel
runs in a new process group. At six hours the launcher terminates that group
and writes `RESOURCE_UNRESOLVED`; it never silently substitutes CEGIS. Native
matrices are confined to the child and cleared on every normal path. An
in-child `MemoryError`, `OSError`, or `TimeoutError` is likewise serialized as
`RESOURCE_UNRESOLVED`, with no membership or separation claim.

## Self-test and registration

The source-only self-test is safe to run now:

```bash
.venv/bin/python -B artifacts/math/G-0081/full_dictionary_schur.py --self-test
```

It covers native multiplication, in-place FLINT RREF member/separator
fixtures, target-last pivot scanning, free-zero solving, rank-full-Q logic,
cache mutation rejection, price-row scalar logic, and nine tiny non-outcome
fast/frozen/nested evaluator entries. It evaluates no actual quotient or
rank.

Public `--run` cannot execute without a separately committed preregistration
whose exact bytes and expected runner hash are both supplied on the CLI. That
artifact must bind the output path, cache directory, all hashes, dimensions,
resource gates, stage order, eight workers, and the prohibition on price
filtering. This candidate intentionally does not create that preregistration.
