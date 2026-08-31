# G-0133 source audit report — frozen G-0132 MEMBER replay

- Reviewer: `ProudMink` (Codex / GPT-5; fresh-context same-lineage T1)
- Preregistration commit: `279b431`
- Frozen producer commit: `618c5e7883bf6ee02f1a0f202dbec1f3a9e15a0b`
- Frozen source SHA-256: `27400fe972986ea29ff245059f6011bbf1a146511d30cfecbdfdd834c3a5115e`
- Frozen `Cargo.toml` SHA-256: `34f04114a5729d2fcd02edf4b544dda7f88762bb2decb1d6c9668375b536d2db`
- Frozen `Cargo.lock` SHA-256: `4b8685901b2e6783d0ffd51c2abe57d60a0e6c8a277473e28239a59dd48f77d7`
- Frozen release executable SHA-256: `8c556397e37e6d3f7bed9b8dae417cf4629c0a3fe3ce0537192d4a34662d6e64`

## Verdict

`PASS` for T1 source clearance of this exact committed producer and executable.
No scientific manifest or output was observed. This audit does not promote a
mathematical result.

The producer source files appeared before the G-0133 preregistration file was
written, but the reviewer had not opened, hashed, or inspected them. The
preregistration records that race explicitly and binds the prospective audit
boundary before the first source inspection.

## Evidence and findings

- G-0131 admission was independently revalidated: schema and frozen binding,
  `CONSISTENT_MEMBER`, all 380 coordinate solves, 21 rank trials ending at
  176/176, the selected 176-slot basis, 132 nonzero coefficients, 44 zero
  coefficients, primitive positive normalization, and its rejected mutant.
- All 22 direct frozen bindings and all 41 transitive G-0128 manifest bindings
  were independently rehashed. The union contains exactly 63 distinct
  path/SHA pairs.
- Static call-path review confirmed the exact 176-slot to 132-term projection;
  all `132 * 11! = 5,269,017,600` labelled contributions; dynamic complete
  primitive hinge support; all 11 linear coordinates; 68 carried directions
  checked by a second exact route; unconditional `num_bigint::BigInt` terminal
  aggregation; coordinate-10 target subtraction; and explicit exact-zero and
  residual outcomes.
- Static review also confirmed the preregistered coefficient, target,
  omission, direction, linear, orbit-receipt, branch/relabel, no-op, and prime
  collision mutants are reachable; modular arithmetic is only a collision
  control and never the scientific decision path.
- Source, package, lockfile, preregistration, candidate, kernel, uniqueness
  lemma, G-0131 receipt, and transitive-input drift checks are embedded before
  computation. Strict source-audit receipt validation precedes publication.
  Publication uses same-directory exclusive creation, file and directory
  synchronization, and opposite-branch guards.

## Executed checks

- Frozen release self-test: `PASS` with `G-0132 self-test PASS`.
- Targeted release producer self-test: 1/1 passed.
- Ignored maximum-support BigInt/pinned-kernel cross-check: 1/1 passed.
- `cargo clippy --release -- -D warnings`: passed.
- Real frozen-input `--preflight`: passed with 132 terms and 41 transitive
  inputs; it created no scientific artifact.
- Independent probe: `PASS`. It independently reconstructed the projection,
  digests, primitive normalization, full labelled census, 68 carry directions,
  G-0131 admission, residual/no-op controls, static reachability, and all 63
  frozen bindings.
- Four CLI path/branch mutants and six hostile source-audit receipt variants
  were rejected. The latter covered an unknown field, non-PASS/observation
  mutation, source SHA mutation, duplicate frozen binding, command mutation,
  and the uncommitted-artifact guard. Both prohibited scientific paths were
  absent after every probe.

## Boundary and residual risk

The source boundary is narrow: even a future exact-zero scientific result can
establish only the frozen 132-term orbit identity through the pinned uniqueness
and symmetry seam. It cannot by itself establish a compiled two-hidden-layer
network, family completeness, an unrestricted MAX11 theorem or lower bound,
the all-`n` target, `REFEREED` standing, or a Lean theorem.

Residual risk is limited to ordinary implementation/platform risk in the exact
frozen Rust toolchain and to mistakes outside the audited hashes. A changed
source, executable, input, audit artifact, command, or commit is outside this
clearance and must be reviewed again.

Promotion boundary: T1 source clearance for this exact committed producer and executable only; no scientific manifest or output was observed, and no mathematical result is promoted by this receipt.
