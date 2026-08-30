# G-0081 cold hostile source review — `cb945ec`

## Verdict

**REVISE. Do not preregister or execute this revision.**

This verdict is pinned to:

- commit: `cb945ece2364ff84053fa7cb86825c33a8ba30df`
- runner: `artifacts/math/G-0081/full_dictionary_schur.py`
- runner SHA-256: `db58d9fb796faf2adccab4a08fa9460dc7d36477359f873dfc74ca8f2bed6fd4`
- review time: `2026-08-30T16:17:22Z`

I did not create a preregistration, invoke `--run`, evaluate the actual quotient,
compute a rank, or inspect any later G-0081 outcome. The pinned `--self-test`
passed and explicitly reported `actual_quotient_or_rank_evaluated=false` and
`actual_result_artifact_created=false`. All additional reproductions below used
temporary toy repositories or interpreter-startup fixtures and computed no
G-0081 scientific outcome.

## Blocking finding 1 — effective Git configuration is not closed

### Defect

`verify_git_anchor` hashes only `.git/config` and searches forbidden keys with

```text
git config --local --get-regexp ...
```

at pinned lines 627–646. Ordinary Git commands later consume the *effective*
configuration, including included files and per-worktree configuration. The
forbidden-key probe does not traverse either source, and neither source's bytes
enter `git_config_sha256`.

This is exploitable against the exact function, not merely a theoretical Git
configuration discrepancy.

### Exact include-chain reproduction

In a temporary repository with a tracked runner and preregistration, commit the
files on `master` and clone that commit into a local bare repository
`$attacker`. Store the apparent origin as `alias://origin`. Put these two
nonrecursive rewrite rules in an included config file:

```bash
git config --file "$included" \
  'url.git@github.com/Dunc4nJ/relu-depth-frontier-research.git.insteadOf' \
  'alias://origin'
git config --file "$included" \
  "url.file://$attacker.insteadOf" \
  'git@github.com:Dunc4nJ/relu-depth-frontier-research.git'
git -C "$actual" config --local include.path "$included"
```

The first rewrite makes `remote get-url origin` display the registered GitHub
URL. Git does not recursively apply the second rewrite to that already-rewritten
value. A direct `ls-remote` of the registered GitHub URL does apply the second
rule and therefore reads the local attacker repository.

Observed under the runner's `clean_git_environment()`:

```text
git config --local --get-regexp <runner-forbidden-regex>
  exit 1, stdout empty

git remote get-url origin
  git@github.com:Dunc4nJ/relu-depth-frontier-research.git

git ls-remote --exit-code \
  git@github.com:Dunc4nJ/relu-depth-frontier-research.git refs/heads/master
  <attacker-copy-of-HEAD> refs/heads/master
```

I then loaded the pinned source only through its allowed `--self-test` path and
called its exact `verify_git_anchor` on this fixture. It returned successfully:

```text
exact_verify_git_anchor_accepted = True
forbidden_probe_returncode = 1
forbidden_probe_stdout = ""
reported_origin_url = git@github.com:Dunc4nJ/relu-depth-frontier-research.git
reported_published_ref = refs/heads/master
reported_published_head = <fixture HEAD copied to attacker.git>
scientific_outcome_computed = False
```

Thus the receipt can assert the expected publication remote while the actual
publication query was serviced by attacker-controlled local bytes.

### Independent `config.worktree` variant

The same bypass works without `include.path`:

```bash
git -C "$actual" config extensions.worktreeConfig true
git -C "$actual" config --worktree \
  'url.git@github.com/Dunc4nJ/relu-depth-frontier-research.git.insteadOf' \
  'alias://origin'
git -C "$actual" config --worktree \
  "url.file://$attacker.insteadOf" \
  'git@github.com:Dunc4nJ/relu-depth-frontier-research.git'
```

The pinned `--local --get-regexp` again emitted nothing, while effective
`remote get-url` and `ls-remote` followed the two different rewrites.
`.git/config.worktree` is not hashed or inspected.

### Executable-config consequence

`core.fsmonitor` is also neither rejected nor overridden. A temporary repo with

```bash
git config core.fsmonitor "/usr/bin/touch $marker"
git status --porcelain=v1
```

created `$marker`, proving that the security-critical scoped `status` call can
execute caller-selected local-config code. A valid fsmonitor hook can also
affect the status view. This is not repaired by clearing inherited Git
environment variables.

### Required repair/gate

At minimum:

1. Refuse every local `include.*` and `includeIf.*` directive before any Git
   command whose result carries custody.
2. Refuse `extensions.worktreeConfig` and any `.git/config.worktree` object
   (including a symlink), or fully bind and inspect it.
3. Enumerate effective config with origin/scope and fail unless every origin is
   the one expected no-follow local config. Hash every admitted config source.
4. Disable/refuse executable or view-changing settings, especially
   `core.fsmonitor`; add a planted hook fixture that must not execute.
5. Re-run the two-step URL fixture against the exact validator and require a
   fail-closed verdict before any network query.

Rejecting only direct `url.*.insteadOf` rows in `.git/config` is insufficient.

## Blocking finding 2 — Python startup/import custody is ambient

### Defect

The documented and registered invocation is `.venv/bin/python -B`, not an
isolated interpreter. Python startup processes caller-selected `PYTHONPATH`,
user-site `sitecustomize`/`usercustomize`, and unsafe import search paths before
the runner executes. The pinned runner imports NumPy and its other dependencies
at lines 15–46; the CLI-only guard is only lines 48–51. Later checking
`sys.executable` and `platform.python_version()` (lines 1078–1081) cannot undo
code that has already run.

Exact no-outcome demonstration:

```bash
tmp=$(mktemp -d)
ln -s "$PWD/artifacts/math/G-0081/full_dictionary_schur.py" \
  "$tmp/sitecustomize.py"
PYTHONPATH="$tmp" .venv/bin/python -B -c \
  'print("interpreter-reached-user-code")'
```

Observed:

```text
Error in sitecustomize; set PYTHONVERBOSE for traceback:
RuntimeError: G-0081 is a CLI-only registered runner; importing it exposes no scientific entry
interpreter-reached-user-code
```

The symlink deliberately used the pinned runner merely as a visible canary. An
actual `sitecustomize` has arbitrary Python execution before every in-process
hash, Git check, closure, or native call; it can monkeypatch `subprocess`,
`hashlib`, `pathlib`, NumPy, or import machinery. Likewise an untracked module
in the script directory can shadow a non-builtin import, while the scoped Git
status examines only the runner and preregistration.

### Required repair/gate

Use and bind a clean launcher rather than relying on late in-process checks:

1. Require an isolated/safe-path invocation, at least `python -I -B`, and verify
   the corresponding `sys.flags`.
2. Launch under an allowlisted environment that removes Python startup and
   dynamic-loader selectors (`PYTHON*`, `LD_PRELOAD`, `LD_LIBRARY_PATH`, and
   equivalents relevant to the pinned platform).
3. Bind launcher bytes, exact argv, environment policy, interpreter, imported
   dependency origins, and versions in the preregistration/receipt.
4. Add must-fail `sitecustomize`, script-directory shadow-module, and dynamic
   loader fixtures.

Checking these variables after ordinary Python startup is not a security
boundary; isolation must be in force before startup customization is possible.

## Material finding 3 — 21,600 seconds is not a total wall-time bound

`public_run` performs `validate_registration()` before creating `begun` and
`absolute_deadline` (lines 2653–2658). Registration includes Git subprocesses
and the publication query; `git_process` supplies no subprocess timeout.

After a child exits just before the deadline, the parent performs another
custody pass and `parent_finalize_cache_chain` (lines 3055–3073). Finalization
recomputes the complete FLINT RREF from S, compares every persisted row, and on
a member branch repeats the 16,738-row solution replay and determinant checks
(lines 2454–2650). It receives no deadline and performs no deadline check.

Consequently the registered `maximum_wall_seconds = 21600.0` is a child-wait
cutoff, not a bound on CLI invocation, publication validation, parent replay,
or final artifact creation. A Git fsmonitor command can also hang a parent-side
custody call outside the child watchdog.

This does not reverse the algebraic branch, but it falsifies an advertised
resource/custody contract. Either:

- define and preregister separate, honestly named bounds for registration,
  child science, and parent finalization; or
- enforce one deadline from a clean launcher through final output, pass it to
  finalization, and give every Git/native subprocess or replay a bounded
  watchdog.

Add a no-science fixture in which the child returns one tick before the cutoff
and parent finalization blocks; it must terminate or produce the registered
typed resource-null result within the stated total bound.

## Checks that survived this review

Subject to the blocking startup/configuration defects above and the explicit
exclusion of an active same-UID/root cache attacker:

- The old caller-forgeable internal CLI/token is gone. Ordinary import fails,
  and the scientific closure/capability is local to `public_run` after public
  validation and fresh-namespace creation.
- A fresh absent cache namespace is created once; pre-existing empty,
  completed, partial, lock-symlink, and namespace-symlink states are refused by
  the shipped controls.
- The fork child consumes the one-shot anonymous-pipe frame, checks PID/session/
  process group and the inherited held lock inode, arms `PDEATHSIG`, and the
  timeout control reaps the child and kills the worker.
- Parent finalization does recompute RREF from the frozen S cache and compares
  every R entry. A forged branch-reversing R cache cannot attest to itself.
- Target-last branch logic is correct: a target pivot means rank augmentation
  and finite modular separation; a nonpivot gives a free-zero modular member
  solution which is replayed on all 16,738 rows.
- In the full-new-row-rank member branch, the block determinant implication is
  correct and one-sided: a nonzero determinant modulo `1,000,003` of the raw
  integer minor proves nonzero determinant over `Q`, but does not supply an
  explicit rational lift or a global CPWL identity.
- The reviewed unsigned-64-bit dot products are bounded below `2^64` (the
  largest relevant conservative sum is below roughly `1.7e16`), so the NumPy
  modular replays do not silently wrap at this registered dimension/prime.
- Claim boundaries remain appropriately narrow: neither branch establishes an
  unrestricted two-hidden-layer theorem or global identity.

These survivals do not offset the blockers. The exact revision is not safe to
register because both the publication anchor and the executing Python process
can be selected outside the bytes the receipt claims to bind.

## Re-review scope

Any source change mints a new runner hash and requires a fresh review. A repair
should be attacked first with:

1. included and worktree config URL-chain publication redirects;
2. executable/hanging fsmonitor configuration;
3. `PYTHONPATH` sitecustomize and script-directory dependency shadowing;
4. total-wall finalization at the deadline boundary;
5. the existing pipe/lock/cache/RREF branch-reversal controls.
