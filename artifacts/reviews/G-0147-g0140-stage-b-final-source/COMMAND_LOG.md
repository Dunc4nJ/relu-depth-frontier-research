# G-0147 command and result log

Only source/custody inspection, checker controls, producer self-test, and outcome-blind static
preflight ran. Stderr was captured, not suppressed. No scientific mode ran.

## Outcome-blind checkpoint

```text
git commit -m "G-0147 preregister final Stage-B source audit"
  [master 84482f3] G-0147 preregister final Stage-B source audit
git push origin master
  381adc6..84482f3 master -> master
```

This completed before subject source inspection or runtime checks.

## Four-file frozen custody

```text
frozen commit: f55df23361382a9b99b5ca3c07794611a7253c6c
main.rs:    f6c4c4b210a32c8453626fd9a63bfde8a3083f6fb083dce56646a3361289390a; commit=working=isolated
Cargo.toml: 425d82de4e6d5902e2d3d7b005c5473225c4d6f197752590e89d7be670b2685c; commit=working=isolated
Cargo.lock: 8875e1375a361873ac13bbcdf9e14c8ca7b34afa1438dfae9a6800f31325365a; commit=working=isolated
executable: 0dcb50e154797ee8104457a93ce172a46054d9a5836c499cf31796134ccb5050; commit=working=isolated
```

The checker repeated this snapshot at audit end; all four remained equal.

## Allowed producer modes

```text
g0140-stage-b-pool128-coordinate-pricer --self-test
  exit 0
  stdout: G-0140 Stage-B Pool128 self-test PASS
  stderr: empty
  stdout SHA-256: cff85a3944d8d59d9e0722af5c317367d749e2cb6c3df3144be633ac3cc45f0c

g0140-stage-b-pool128-coordinate-pricer --preflight-static \
  artifacts/math/G-0113/panel_solver_input_v1.json \
  artifacts/math/G-0135/full_family_master_result_v3.json
  exit 0
  stdout: G-0140 Stage-B static preflight PASS: 163740 records; 135 candidate terms; future manifest/Stage-A/G-0142 receipts not consumed
  stderr: empty
  stdout SHA-256: f0b63fe1e84bf1280bd59f4e5484a9dbe341d202fe626e1f7f352d629b557f31
```

Two manual static-preflight runs produced identical stdout; the independent checker ran the same
mode once more from an isolated executable copy with the same stdout hash.

## Independent checker

```text
python3 -B artifacts/reviews/G-0147-g0140-stage-b-final-source/audit_stage_b_final_source.py --self-test
  exit 0
  stdout: G-0147 independent checker self-test PASS

python3 -B artifacts/reviews/G-0147-g0140-stage-b-final-source/audit_stage_b_final_source.py \
  --static-audit \
  --output artifacts/reviews/G-0147-g0140-stage-b-final-source/CHECK_RESULTS.json
  exit 1 (expected subject FAIL)
  failed checks: STAGE_A_RECEIPT_MISSING_NULL_FIELD_REJECTED,
                 STAGE_A_MUTATION_CONTROL_SCHEMAS_COMPLETE_AND_VALIDATED,
                 SOURCE_AUDIT_CLOSED_SCHEMA_AND_BINDING_PLACEMENT
  failed hostile controls: none
```

An earlier uncommitted checker run wrote its result and then crashed while formatting a relative
path; its deny-unknown mutant also exposed an overbroad checker attribute detector. That generated
result was deleted, both checker defects were fixed, and the clean command above was rerun from
scratch. The retained result is only the clean rerun.

## Terminal upstream verification

```text
git rev-parse 495d36c^{commit}
  495d36c5d403bc678493dd823776d97ea03041b3
git log -1 --format=%H -- artifacts/reviews/G-0146-g0140-stage-a-final-source/SOURCE_AUDIT_RECEIPT.json
  495d36c5d403bc678493dd823776d97ea03041b3
working SHA-256: dc01ef4b4dcfaf8fa03662350b7cd5544c317599e7c640f29d71ad3c74d68e8d
commit  SHA-256: dc01ef4b4dcfaf8fa03662350b7cd5544c317599e7c640f29d71ad3c74d68e8d
schema:  max11-g0146-g0140-stage-a-final-source-audit-v1
verdict: FAIL
result:  SOURCE_CUSTODY_AUDIT_FAIL_RECURSIVE_BINDING_LOOKALIKE
```

After this deterministic blocker was confirmed, no further broad audit or runtime check ran.
