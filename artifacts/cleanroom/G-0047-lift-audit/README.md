# G-0047 lower-certificate lift audit

This clean-room artifact asks whether the frozen public MAX10 certificate can
be generated from the public MAX5/MAX6 certificates by several precisely
defined graph operations.  It does not edit or depend on the producer's
G-0047 construction files.

Run:

```bash
.venv/bin/python -B artifacts/cleanroom/G-0047-lift-audit/certificate_lift_audit.py --self-test
.venv/bin/python -B artifacts/cleanroom/G-0047-lift-audit/certificate_lift_audit.py
```

The first command exactly decodes the published MAX5 and MAX6 identities,
rejects one-coefficient mutants, rejects a malformed endpoint, and checks the
small-graph automorphism kernel against direct permutation enumeration.  The
full command renders all 409 certificate terms symbolically and tests exact
rational coefficient membership in the declared lift-incidence spaces.

The subsequent adversarial audit of the producer's stronger G-0047 theorem is
separate:

```bash
.venv/bin/python -B artifacts/cleanroom/G-0047-lift-audit/audit_g0047_theorem.py --self-test
.venv/bin/python -B artifacts/cleanroom/G-0047-lift-audit/audit_g0047_theorem.py --workers 8
```

It independently replays MAX5/MAX6/MAX10 with a signed-direction DP, checks the
normalizations, and proves the stronger proper-signed-core U-statistic theorem
in `PROPER_CORE_THEOREM.md`.  Its finite scan is a control; the universal
statement rests on the exact polynomial argument.

`NO_EXACT_RECURRENCE_IN_TESTED_OPERATOR_LANGUAGE` is a bounded negative.  It
does not exclude a different MAX10 certificate, a topology-dependent or
nonlinear recurrence, a new MAX11 pair-atom identity, or an unrestricted
two-hidden-layer representation.
