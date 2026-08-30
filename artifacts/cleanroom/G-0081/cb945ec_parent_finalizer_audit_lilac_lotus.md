# G-0081 parent-finalizer hostile audit — LilacLotus

## Verdict

**REVISE. Do not preregister and do not invoke `--run` at this commit.**

The fresh namespace, fork-local authority, and parent RREF replay close the
three earlier caller-forgery routes under the campaign's stated
honest-but-fallible, same-filesystem threat boundary. The remaining fatal issue
is narrower: the load-bearing parent finalizer is outside the registered hard
wall-time boundary and outside the isolated child. Consequently a nominally
successful public run can exceed `maximum_wall_seconds`, while a stuck or
crashing second FLINT RREF is neither timed out nor serialized as
`RESOURCE_UNRESOLVED`.

This is a source/protocol verdict. It says nothing about whether the actual
finite system is a member or separator.

## Pinned scope and custody

- reviewed commit: `cb945ece2364ff84053fa7cb86825c33a8ba30df`
- `HEAD` and `origin/master` at review: the same full commit above
- Git root: `/data/projects/relu-depth-frontier-research`
- origin: `git@github.com:Dunc4nJ/relu-depth-frontier-research.git`
- runner tree blob: `88b1a0946bbed40f690f14a9731d5c9a540638f4`
- runner SHA-256:
  `db58d9fb796faf2adccab4a08fa9460dc7d36477359f873dfc74ca8f2bed6fd4`
- README tree blob: `5b7383e6d8326134e48e2ad9912d614ddbdf688d`
- README SHA-256:
  `b10e8bd1ffb2487c189a1af81a5db79ee67185a12c3fd9285c564ecd2036c591`

The live producer files were clean and byte-identical to the pinned commit.
This audit did not create a preregistration, invoke `--run`, compute the actual
quotient or rank, inspect an outcome, or create an actual G-0081 result. The
source-only `--self-test` passed in 21.4 seconds and explicitly reported
`actual_quotient_or_rank_evaluated=false` and
`actual_result_artifact_created=false`.

## Fatal blocker: the registered hard deadline ends before parent finalization

The preregistration validator requires the generic field
`maximum_wall_seconds = 21600` (`full_dictionary_schur.py:1047`). The public
launcher sets `absolute_deadline = begun + 21600` (`:2657-2658`) and enforces it
only while waiting for the scientific child (`:2979-3003`). Once that child
exits successfully, the parent calls `parent_finalize_cache_chain`
(`:3065-3073`). That function then:

1. rehashes and scans the complete C, S, and R caches (`:2481-2524`);
2. loads the full `9862 x 18583` S matrix into FLINT (`:2539-2548`);
3. performs a second blocking `nmod_mat_rref` (`:2551`);
4. compares all 9,862 persisted RREF rows (`:2552-2560`); and
5. on membership, replays all 16,738 rows and recomputes the determinant
   evidence (`:2586-2613`).

No deadline is passed to this function, checked inside it, or enforced by a
supervising process. A child that exits just before the six-hour boundary can
therefore produce a successful final gzip more than six hours after `begun`.
A blocked FLINT call can run indefinitely. A segfault or OOM in this parent-side
native call kills the wrapper without the registered resource-null result.

The ambiguity cannot be repaired by saying that 21,600 seconds meant only the
child. The registered field is named `maximum_wall_seconds`, launcher receipts
call it `hard_timeout_seconds` (`:2671`, `:3022`, `:3082`), and the README says
that at the absolute six-hour deadline the wrapper terminates the computation
(`README.md:195-205`). There is no separately registered parent-finalization
allowance. The registered `stage_order` (`full_dictionary_schur.py:1056-1062`)
also ends at member/separator discovery and omits the parent finalization that
is required before output.

Two emitted/documented assertions are additionally false in the present call
graph. The successful launcher writes
`native_cleanup_confined_to_child=true` (`:3083`), and the README says native
matrices are confined to the child (`README.md:203`). The parent finalizer
itself constructs native FLINT matrices at `:2544-2548` and, on the full-rank
member branch, at `:2248-2278` through the call at `:2603-2610`.

### Required repair

Use one unambiguous registered execution contract. The strongest small design
is:

1. register a single `maximum_public_run_wall_seconds` covering child,
   parent-verification, and final-output transaction, or register separate
   child and finalizer maxima whose sum is also bounded;
2. include `parent-stage-chain-and-independent-rref-replay` in the exact
   registered stage order;
3. run parent finalization in a separately supervised verifier process with an
   inherited, re-proved lock descriptor, fresh process group, parent-death
   guard, exclusive scratch result, and the remaining absolute deadline;
4. terminate and reap that verifier on deadline, signal, OOM-like failure, or
   malformed scratch, emitting only `RESOURCE_UNRESOLVED` and no branch claim;
5. record child wall time, complete finalizer wall time, and total public-run
   wall time; and
6. rename or remove `native_cleanup_confined_to_child` unless every native call
   is actually confined to a supervised child/verifier process.

A check immediately before or after `nmod_mat_rref` is not a hard timeout: it
cannot interrupt a blocking native call.

### Mandatory falsifier

Add a tiny source-bound fixture in which the finalizer's RREF backend blocks
past a 0.2-second registered allowance. The supervisor must terminate and reap
the verifier process group, leave no live worker, emit no membership/separation
projection, and finish within a small scheduling tolerance. The opposite
fixture uses a fast two-row RREF and must pass. A second boundary fixture should
make the scientific child finish immediately before the total deadline; the
finalizer must not be allowed to publish a branch after the total maximum.

## Material test gap: the branch-reversal control does not exercise the finalizer

`self_test_logic` constructs a true member S and a non-row-equivalent forged
target-pivot RREF (`:3310-3325`). It proves only that the two tiny arrays differ
and that their pivot bits are opposite. It never calls
`parent_finalize_cache_chain`, its RREF replay loop, or even a factored
dimension-independent form of that loop. Thus the new load-bearing mechanism
has no direct must-fail regression, despite the source inspection showing that
the production loop should reject the attack.

Required two-direction fixture:

- source S: `[[1,0,1],[0,1,1]]` over a small prime;
- positive R: the independently computed canonical RREF of S;
- hostile R: `[[1,0,0],[0,0,1]]`, with a self-consistent receipt and a forged
  separation declaration;
- positive leg: the finalizer accepts the true R and derives membership;
- hostile leg: the same finalizer rejects the forged R byte-for-byte before any
  final branch output.

The test should exercise the production comparison/decision routine after a
small dimension-parameterized refactor, not merely assert that two fixture
arrays are unequal. A nonempty caller-authored fresh-namespace fixture should
also confirm that coherent forged C/S/R files cannot reach this routine through
`public_run`.

This gap is not itself evidence that the current RREF replay is wrong. It means
the claimed enforcement lacks the hostile regression required for a
load-bearing trust-boundary change.

## Additional projection gaps

After independently deriving `parent_result`, the finalizer checks the nested
`native_decision.result`, ranks, pivot bit, and pivot list (`:2573-2584`). It
does **not** check:

- `scientific_payload.result == parent_result`;
- the outer and nested claim-boundary projections;
- the receipt's `ordered_pivot_local_new_columns` and its digest;
- the receipt's `ordered_free_local_new_columns` and its digest; or
- `pivot_global_new_columns` and the pivot-list digest in the nested decision.

The exact current child constructs these fields consistently, so this is not a
caller exploit under the explicitly excluded active-same-UID threat. It does,
however, mean the parent finalizer does not fully root every branch-bearing and
future-nullspace projection it preserves. Minimal hostile regressions should
mutate each projection while recomputing the enclosing JSON hash and require
parent rejection. In particular, flipping only the outer scientific result
must not survive merely because the nested decision is correct.

## Defenses confirmed by source and safe controls

Within the stated threat model, the following repairs are substantively sound:

- A registered cache namespace must be absent. `mkdirat` plus no-follow inode
  checks creates it once; even an existing empty directory is rejected.
- The lock is `O_EXCL|O_NOFOLLOW`, checked by descriptor/path inode identity
  before mutation, and proved held in the fork child.
- Ordinary import fails before helper definitions. The complete scientific
  kernel, capability consumer, and child entry are closures created only inside
  `public_run`; the one-shot pipe frame is random and consumed once.
- The child revalidates the committed registration and derives the exact lock
  path from it before science.
- A successful namespace has an exact seven-name file census; journals,
  pending receipts, logs, and scratch files cannot survive success.
- C, S, and R bytes have whole-file and raw-data hashes plus capability and
  start/end custody bindings. S binds the current C transaction and R binds the
  current S transaction.
- The still-locked parent recomputes the complete RREF from S and compares every
  persisted entry. It independently derives the target-pivot branch.
- On membership, it reconstructs the free-zero coefficients, replays all
  16,738 original rows from old/C data, and independently recomputes the
  full-rank block-minor evidence.
- The full-row-rank determinant implication and all branch boundaries remain
  correctly one-sided. No modular branch is promoted to a global CPWL identity
  or unrestricted theorem.
- Resource-null paths state that no scientific outcome was computed.

The parent intentionally does not independently recompute every C entry or the
complete Schur transform S from C. Fresh-only production prevents
caller-authored cache reuse, but it does not turn this run into a clean-room
replication of the evaluator or Schur implementation. Any later evidence claim
must preserve that boundary.

## Threat-boundary adjudication

Path-based hashing/loading still has ordinary TOCTOU windows after no-follow
checks. An active process with the same UID (or root) could race path
replacement, rewrite the source and witnesses together, or tamper with scratch
state. The result explicitly excludes that actor, consistently with the
campaign threat model. Those possibilities are therefore residual `OUTSIDE`
risks, not reasons for this REVISE verdict.

The wall-time failure is different: it occurs in the honest, intended call
graph with no adversary and contradicts a registered resource contract. It is
inside scope and must be repaired before preregistration.

## Freeze decision

The mathematical reduction and fresh-cache provenance design remain worth
executing. Freeze only after the entire public execution, including independent
parent finalization, has a registered and mechanically enforced time/failure
boundary; the stage order and native-process claims match the call graph; and
the actual finalizer passes the two-direction branch-reversal fixture. Then
obtain a fresh exact-commit hostile review before creating the preregistration.
