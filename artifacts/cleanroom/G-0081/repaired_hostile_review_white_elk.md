REVISE

# G-0081 repaired hostile source review — WhiteElk

## Scope and pinned identity

This is a source-only hostile review of commit
`e7117c50cde00908dbea4afa95623b1856d57e51`.

- Git root: `/data/projects/relu-depth-frontier-research`
- `origin`: `git@github.com:Dunc4nJ/relu-depth-frontier-research.git`
- runner: `artifacts/math/G-0081/full_dictionary_schur.py`
- runner tree blob: `dee73e0923d772fc408f482ab508a11ef168cf44`
- runner SHA-256: `03c0e5e5649ad1ba18842167708d50447f901d733388600297fcb61696ba36fc`
- README tree blob: `22b74d5b01e5018e895a24f911595a86015c9597`
- prior hostile report: `artifacts/cleanroom/G-0081/t1_hostile_verifier_magenta_puma.md`

At review start, both `HEAD` and `origin/master` contained the pinned commit and
the live runner/README were clean and byte-identical to it. All substantive
source reads used `git show e7117c50...:<path>`; concurrent later repository
movement was not used as review input.

I did not invoke `--run`, compute the actual quotient/rank, inspect a branch
outcome, create a real preregistration, or inspect any later G-0081 outcome.

## Verdict

The patch materially repairs the *surface* failures in the prior hostile
report, but three caller-forgeable trust roots still permit an unauditable or
steered execution. The preregistration must **not** be frozen and the full run
must **not** be executed yet.

## Fatal blockers

### 1. The fork capability is caller-constructible and is not bound to the registered cache lock

`KernelCapability` exposes every authority-bearing field as ordinary
constructor input (`full_dictionary_schur.py:224-232`).
`consume_kernel_capability` checks only consistency among those caller-supplied
fields and caller-creatable OS resources (`:738-802`): a pipe, a frame, a
parent PID, and an exclusively flocked inode. It receives no `Registration`
and never derives the required lock as
`cache_paths(registration.cache_dir).lock`. The scientific entry remains a
module-level callable (`internal_kernel`, `:2193-2307`); only the CLI spelling
was removed.

A tiny non-outcome fork fixture constructed a frame, pipe, process group,
PDEATHSIG, and an unrelated attacker-selected lock file, then called
`consume_kernel_capability`. It was accepted:

```json
{"accepted":true,"lock_bound_to_registration_cache_dir":false,"scientific_kernel_called":false}
```

An importing caller can therefore construct a `Registration` and capability
and enter `internal_kernel` without `public_run`'s real cache lock,
parent-enforced whole-kernel timeout, final-output transaction, or launcher
resource/failure report. The in-kernel deadline is not enforced over every
Schur/RREF stage. This is the deeper form of the prior hidden-CLI failure.

Required repair:

- eliminate every module-level callable route to scientific work, or make
  every such route enter the same supervisor before any scientific/cache work;
- mint the process-local/fork-only authority inside a `public_run` closure (not
  through an exported constructible dataclass), consume it exactly once in the
  fork child, and keep the raw kernel invocation unreachable by import;
- derive the expected lock path from a freshly revalidated registration and
  require the inherited descriptor to be the exact inode opened for that path;
- revalidate that `output`, `cache_dir`, document, Git anchor, and hashes still
  equal the registered values inside the sole public entry.

Must-fail fixture after repair: import the module, create a pipe/frame and an
exclusive unrelated lock exactly as above, then attempt the internal entry.
It must fail before custody, cache, or scientific work. A caller-created
`Registration` must fail likewise. Only the child forked by the already-locked
public supervisor may pass.

### 2. Git anchoring trusts caller-controlled Git environment and object storage

`git_process` copies all of `os.environ` and changes only
`GIT_OPTIONAL_LOCKS` (`:465-478`). Consequently `GIT_DIR`, `GIT_WORK_TREE`,
`GIT_INDEX_FILE`, object-directory/alternate settings, replacement refs,
configuration, and even Git executable lookup remain caller-controlled.
`verify_git_anchor` (`:518-618`) proves anchor/HEAD/live equality only in the
Git database selected by that environment. It does not bind the campaign's
resolved worktree/common Git directory or expected remote identity.

A tiny fixture created an actual campaign repository in which
`preregistration.json` was untracked, committed the same bytes only in a
foreign object database, exported `GIT_DIR` and `GIT_WORK_TREE`, and called
`verify_git_anchor`. The validator accepted the foreign anchor:

```json
{"actual_campaign_status":"?? preregistration.json","actual_campaign_preregistration_committed":false,"foreign_anchor_accepted":true}
```

Thus the new byte-equality checks are internally correct but do not yet prove
that the preregistration was committed in the campaign repository before
execution.

Required repair:

- invoke a fixed/verified Git executable under an allowlisted environment;
  remove every inherited `GIT_*` selector and disable replacement objects,
  alternate object directories, hooks/config surprises, and optional locks;
- resolve the campaign `.git`/worktree/common-directory identity from the
  filesystem under no-follow checks, then pass explicit trusted
  `--git-dir=<...>` and `--work-tree=<ROOT>` on every Git call;
- bind the resolved worktree, Git/common-directory identity, object format,
  and expected `origin` URL/ref policy into the registration/receipt; for the
  claimed external precedence boundary, require the anchor to be reachable
  from the designated already-published remote or another immutable external
  anchor.

Must-fail fixture after repair: leave the preregistration untracked in the
actual fixture repository, commit it only in a foreign Git directory, set
`GIT_DIR`, `GIT_WORK_TREE`, index/object/replace/config overrides, and invoke
the validator. It must reject and identify the real campaign repository.

### 3. Reused cache receipts are self-authenticating; a forged RREF can reverse the decision

`validate_complete_cache` accepts a cache when its bytes match digests written
in the adjacent receipt (`:1205-1242`). All custody values and digests needed
to author such a receipt are public and reproducible. There is no
preregistered expected cache digest, signature, or full deterministic replay.
This affects completed C reuse (`:1251-1262`), S reuse (`:1654-1665`), and RREF
reuse (`:1906-1935`); the resumable C journal is similarly self-authored.

For RREF reuse, the code checks that the receipt repeats the current S file
hash and that the supplied matrix looks like an RREF, but never proves that
the RREF is row-equivalent to S. A tiny fixture used a source S with a
nonpivot target and a caller-authored, non-row-equivalent RREF/receipt with a
target pivot. `load_or_compute_rref` accepted it:

```json
{"forged_rref_receipt_accepted":true,"accepted_rref_row_equivalent_to_source_s":false,"accepted_target_pivot":true,"source_s_actual_target_pivot":false,"scientific_outcome_computed":false}
```

An even smaller generic fixture confirmed that arbitrary data plus a matching
caller-authored receipt passes `validate_complete_cache`. The 230-row C replay
and one failing-row S replay do not authenticate all other entries. Therefore
a prepopulated ignored cache directory can steer the registered branch while
all displayed custody hashes remain self-consistent.

Required repair:

- reuse a final cache only when its exact digest was frozen in the committed
  preregistration or authenticated by a genuinely external trust root;
  otherwise start empty or deterministically recompute every entry before use;
- on C resume, recompute each purportedly completed chunk rather than trusting
  its journal digest alone;
- fully recompute S from trusted inputs, or verify a complete deterministic
  transform/certificate;
- recompute the target-last RREF from S and compare byte-for-byte, or verify a
  complete two-sided row-space transformation certificate. Repeating S's hash
  in the R receipt is not an RREF-to-S binding.

Must-fail fixture after repair: supply the two-row S and non-row-equivalent
canonical-looking RREF/receipt above. Cache loading must reject it. Equivalent
must-fail fixtures must cover a caller-authored final C pair, final S pair, and
fully marked C partial journal.

## Additional hostile path defect

`exclusive_cache_lock` follows a final-component symlink, does not verify a
regular inode before mutation, and immediately calls `ftruncate`
(`:701-719`). A safe fixture made `execution.lock` a symlink to a victim file;
the context entered and rewrote the victim to `pid=...`. The later child-side
no-follow identity check (`:769-788`) occurs after the damage. More generally,
containment is checked by `resolve()` and paths are reopened later, leaving
intermediate-component rename/symlink races.

Open the cache directory once with no-follow directory descriptors and perform
lock/cache/output operations relative to those descriptors. The lock open must
use `O_NOFOLLOW`, then verify `fstat`/`lstat` device+inode and regular-file mode
before truncation. A symlink-lock fixture must fail with the victim unchanged.

The final gzip output's existing-symlink control did pass: `O_EXCL`/prechecks
rejected it without changing the target. Final cache promotion is also
no-replace by hard link. Those controls do not cure the lock and intermediate
path races.

## Controls that passed

- `--self-test`: PASS in 20.9 seconds; it reported
  `actual_quotient_or_rank_evaluated=false` and
  `actual_result_artifact_created=false`.
- `--check-registration`: PASS in a temporary isolated Git repository whose
  synthetic preregistration was committed before invocation; anchor and HEAD
  matched, output was unused, and no quotient/rank was evaluated.
- Python compile/static parse and `--help`: PASS. `ruff` was not installed.
- Full evaluator-plan census: 18,582 entries, 18,582 unique local columns,
  exactly `0..18581`.
- Bound price-vector census: 18,582 exact/modular-congruent entries and global
  IDs exactly `8107..26688`; 630 prices are zero and 17,952 are nonzero. No
  source path filters on price.
- Target-last construction and pivot logic are consistent. The persisted
  transform is sufficient for the advertised finite-row nullspace only when
  it was honestly computed from S.
- The Schur/block determinant implication is correctly one-sided: a nonzero
  raw integer block minor modulo 1,000,003 proves that integer determinant is
  nonzero over Q. The code does not call the modular Schur cache an integer
  Schur matrix.
- Claim boundaries are appropriate: modular separation is not promoted across
  a possibly exceptional prime; ordinary modular membership is not called a
  rational/global identity; the full-row-rank minor branch claims only
  rational finite-row spanning, still requiring an explicit exact lift/global
  CPWL replay for stronger conclusions.
- Under the honest public wrapper, the fork/`PDEATHSIG`/process-group timeout
  and worker-cleanup fixtures pass, and final output creation is exclusive.

## Comparison with the prior hostile report

The previous report's two exact surface findings were addressed: a normal
honest-environment invocation now requires an ancestor commit with
anchor/HEAD/live byte equality, and the caller-controlled hidden internal CLI
was removed in favor of a parent fork, group timeout, and inherited pipe.
However, the imported module can forge that pipe/lock authority, Git can be
redirected to a caller-selected database, and cache receipts can be forged.
These are material blockers, not observations about either scientific outcome.

## Freeze decision

**Do not freeze the preregistration and do not run the full calculation.** The
scientific design is worth executing after the process-entry, Git-identity,
cache-provenance, and lock-path repairs pass the stated must-fail fixtures. In
the present runner, a successful full run would not be auditable evidence of
the registered calculation.
