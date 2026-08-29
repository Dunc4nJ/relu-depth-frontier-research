# G-0061 clean-room audit

## Verdict

The frozen subject at commit `04ff8cfaec3ac3eddfa7f78ae36a8cd783fe3a74` is **consistent with the exact bounded claim**:

- the 1,358-column S1 integer hinge matrix has `rank_Q = 1,288`;
- its exact kernel dimension is 70;
- all 70 displayed relations have zero hinge residual on all 99,858 degree-four primitive rows and zero exact `Lambda` residual.

This is a same-model-lineage T1 clean-room consistency result, not a T2 review or a method-disjoint T3 replication. It does not settle unrestricted MAX11.

## Decisive evidence

`independent_s1_audit.py` does not import or execute the G-0061 or G-0057 producer programs. It independently enumerates the complete row universe and reconstructs pair-atom semantics using a subset-state rank-word dynamic program, primitive chamber-hinge reduction, injection embedding, and direct binary finite differences. Older hash-bound G-0050/G-0056 manifests provide the descriptor identities.

The replay matched these frozen values exactly:

- row universe: 99,858 rows, SHA-256 `500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2`;
- ordered sparse stream: `b24a0a63100839f9661377b5ffa2c266752b139592b13eed27cfb553ffaf6ce8`;
- integer matrix: `1a2fd2a5fcb702ffe747c9e20f1234d4d43316975eff1b4669337e945f2f467d`;
- `Lambda` row: `8099a522ff5d56e27fc120e285ad5446347b72c0c69f7d25f4728eddafab1600`;
- relation manifest: `9a22ea731d4c19f14fee3f84bd8f005a2df92e2e088b0fe37c419a4d5df65722`;
- 1,288-square integer minor: `a810638ff03e4f44a1c0321a44318199c580dc291f4efa494853cdc597657991`.

The exact minor has residues 431,384 modulo 1,000,003 and 555,451 modulo 1,000,033. Either nonzero residue proves rank at least 1,288 over the rationals. The 70 exact relations are triangular on 70 distinct free coordinates, proving their independence and rank at most 1,288. Together these give exact rank 1,288 and nullity 70.

The audit also checked exact rational-to-integer relation normalization, canonical pivot row and column hashes, both G-0059 prime manifests and their full pivot arrays, all twelve upstream byte bindings, and the producer scientific payload hash. A Python-integer bound proves every relation replay stays below 6,526,464 in absolute value, far below the signed-`int64` limit; the largest observed intermediate was 1,155,840.

Deliberate mutants were rejected: a relation coefficient increment, a `Lambda` increment, a dropped universe row, a duplicate minor row, and a multiplicity perturbation in the small independent semantic control.

## Reproduction

From the repository root, with a fresh output filename:

```bash
source scripts/activate-toolchain.sh
python artifacts/cleanroom/G-0061/independent_s1_audit.py --self-test
python artifacts/cleanroom/G-0061/independent_s1_audit.py \
  --workers 8 \
  --output artifacts/cleanroom/G-0061/audit_report_replay.json
```

Frozen audit artifacts:

- script SHA-256: `ea5067a4b1aef174845deeb11f46214ab852799804193007afe4f95ed95e092d`;
- report SHA-256: `ea18ad48ffde6ef7abd8beecbea6ef287fcbe162c20ff2773cb300aa147d9c30`;
- report scientific payload SHA-256: `11987abce0b55b7acc3ee17727c70196d0d5a717be95026bd2f4dcb05225955d`.

## Boundaries and caveats

- The claim covers only the frozen 1,358-column S1 family. It excludes sequence 92,489, the 328 MAX10-induced columns, remaining proper mass-four atoms, higher masses, arbitrary weights, and nonsymmetric models.
- The raw G-0038 descriptor stream is SHA-256-bound by G-0050 but is untracked at producer commit `04ff8cf` in the observed worktree. A clone of that commit alone therefore cannot replay the selected low-mass descriptors without separately restoring those bound bytes.
- Published wire-format hashes were used as comparison targets, so this audit deliberately claims semantic clean-room replay but not full method-disjoint independence.

## Honesty and real-work audit

No producer file, test, threshold, or acceptance gate was changed. No mock, cached expected output, or producer semantic routine was substituted for the decisive replay. The only initial failure was a self-test fixture that accidentally had no positive hinge; it was replaced with a fixture containing a real nonzero hinge before the full run, strengthening rather than relaxing the positive control. The substantive audit is a bounded research deliverable consumed by the G-0061 standing adjudication; it should be retired or superseded when that adjudication completes or the frozen subject hashes change.
