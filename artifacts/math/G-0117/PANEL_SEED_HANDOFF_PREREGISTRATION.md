# G-0117b preregistration — denominator-cleared panel-seed handoff

Registered while the corrected G-0113 scan was live at or below its observed
60,000/163,740 checkpoint, before the DISJOINT boundary and before any modular
or exact target-membership decision.

## Question and fixed branch

If the frozen G-0113 exact-Q postprocessor returns
`EXACT_Q_MEMBER_FINITE_PANEL`, convert that exact rational solution into a
binding-clean input for G-0117 global replay without relying on any rational
denominator being invertible modulo the replay primes.

This branch must refuse a nonmember result.  It creates only a candidate seed:
it does not promote finite-panel membership to a global identity.

## Input obligations

The converter must require all of the following before writing output:

- schema `max11-g0113-panel-exact-postprocess-v1`;
- the frozen 163,740-record G-0113 input SHA-256
  `093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8`;
- frozen exact-postprocessor SHA-256
  `07f20ee167483aedc0c06f40650fd3edc671ef7fc5cf1e1050b1ad388ba3ec48`;
- `exact_target_member = true`, equal exact candidate and augmented ranks,
  payload result `EXACT_Q_MEMBER_FINITE_PANEL`, exact replay of all 301 rows,
  and rejection of the registered coefficient-plus-one mutant;
- equal nonempty support/coefficient lengths, equal to the reported exact
  rank; unique in-range support sequences; and canonical reduced rational
  coefficient strings.

Any mismatch is a fail-closed error and must leave no output file.

### Adversarial provenance addendum, still before the scan decision

A fresh-context reviewer demonstrated that checking only the hash strings
inside a supplied postprocess JSON admits a fabricated postprocess with
well-formed fake hashes.  The production CLI therefore additionally requires
the actual G-0113 scan report and retained-column paths.  It must hash-check the
actual frozen input, rows, exact-postprocessor source, postprocessor
preregistration, scan report, and retained columns against the supplied
postprocess bindings; then re-run the frozen exact postprocessor on that report
and retained file and require equality of every output field except runtime and
peak-RSS measurements.  Only that recomputed decision projection may advance.

The generic global replay remains a verifier of the certificate it is given;
the recomputed converter artifact is what proves that certificate came from
G-0113.  Exact global replay independently proves or refutes the emitted
identity, so provenance metadata alone never creates mathematical truth.

## Denominator-cleared certificate

Let the exact panel solution be `c_j = n_j / q_j`, with positive reduced
denominators.  Set

```text
L   = lcm_j(q_j),
a_j = L c_j in Z.
```

Remove zero `a_j`, require at least one term, and divide neither `L` nor the
`a_j` by a common factor: preserving the exact equation is more important than
primitive normalization.  Emit schema
`max11-g0117-global-replay-certificate-v2` with decimal integer
`target_scale = L` and decimal integer term coefficients `a_j`, in the frozen
support order.  Bind the source postprocess file by SHA-256 and carry its input,
report, retained, and producer bindings verbatim.

The equation tested by global replay is exactly

```text
sum_j a_j F_j(x) = L * 11! * x_11.
```

The v2 replay parser must reject noncanonical integers, nonpositive
`target_scale`, duplicate or out-of-range sequences, empty terms, and any
fractional v2 coefficient.  Existing v1 rational certificates retain implicit
`target_scale = 1` and their prior semantics.

## Controls fixed before implementation

1. A planted rational member with coefficients `1/2, -3/7, 0` must become
   integer coefficients `7, -6`, target scale `14`, preserving support order.
2. A v1 certificate and its denominator-cleared v2 equivalent must produce
   identical zero/nonzero modular decisions after the v1 residual is multiplied
   by `L` fieldwise.
3. A nonmember postprocess, duplicate sequence, malformed/noncanonical
   rational, rank/length mismatch, missing mutant rejection, or binding drift
   must be refused without output.
4. Adding one to the first nonzero cleared coefficient must change at least one
   planted replay residual.

## Decision and scope

A nonzero modular residual still exactly refutes only this rational seed.  A
two-prime zero still requires an exact magnitude bound or exact replay.  A
global identity in this fixed family still requires algebraic compilation into
the declared two-hidden-layer ReLU architecture and independent review; it is
not a family-completeness or all-arity result.
