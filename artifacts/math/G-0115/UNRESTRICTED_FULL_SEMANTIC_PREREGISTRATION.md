# G-0115 unrestricted 22,666-class full-semantic preregistration

Timestamp: 2026-08-31T01:58+02:00. This document was written after the
coefficient-frozen residual repair and its mixed-degree compilation passed,
but before the unrestricted all-class matrix was materialized or any rank or
membership outcome for the test below was observed.

## Question

Let the candidate family be every one of the 22,666 signed-`W` equivalence
classes arising from the one-edge-per-branch lifts of the public degree-three
MAX8 certificate to nine labels. Give every class an independent rational
coefficient. Does their degree-four span contain the **full** MAX9 semantic
target?

The target coordinate vector has 20,694 entries:

1. zero on every one of the 20,685 complete ordered-cone hinge directions;
2. linear coordinates `(0,0,0,0,0,0,0,0,1)`.

This is deliberately stronger than a hinge-plus-Lambda test. The latter is
already implied by the coefficient-frozen positive and would provide no new
information. A positive here would eliminate the 137 mixed lower-degree
correction terms and produce a degree-four-only MAX9 identity inside the
complete lift-class span.

## Frozen family and order

The census and representative stream remain the bound G-0115 artifacts. The
column order is:

1. the 328 classes containing public MAX9 terms, in representative-stream
   order;
2. the 22,338 outside-public-support classes in the already frozen
   `(topology_distance, signed_certificate_sha256)` order.

No coefficient is fixed. The first block is only an ordering convention.

The existing exact repair caches will supply, without refitting, the 20,685
hinge coordinates and nine linear coordinates of the outside-support block.
The retained 328 columns will be independently regenerated from their
serialized representatives with the clean-room normal-form DP. The complete
matrix will be stored as signed little-endian int32 after range checks and
will be hash-bound before solving.

## Frozen CEGIS and exact decision rule

- Prefixes: `328,1024,2048,4096,8192,16384,22666`.
- Initial rows: all nine linear coordinates plus 247 evenly spaced hinge
  coordinates, for 256 rows total.
- Residual additions: up to 256 evenly spaced previously unseen nonzero rows.
- Finite fields: `1000003,1000033,1000037`.
- Projection backend: bound parallel FFLAS-FFPACK PLUQ/fgetrs.
- Every modular candidate is replayed on all 20,694 coordinates by the bound
  native integer replay kernel, with sampled Python cross-checks.
- A modular full replay with zero residual triggers native pivot-row
  selection, determinant-free exact `fmpz_mat.solve`, and exact rational
  replay on all 20,694 coordinates.

An **exact positive** requires a serialized nonzero rational coefficient list,
zero exact residual on every hinge and all nine linear coordinates, three
independent zero-residual modular replays, and a coefficient-mutation failure.
It must then be replayed from serialized representative pairs without loading
the solve matrix.

A finite-field full-family failure is only a modular gate; it is not a
characteristic-zero nonmembership theorem. An exact negative requires a
rational separating functional annihilating all 22,666 columns and pairing
nontrivially with the full MAX9 target.

## Bound evidence and claim boundary

- representative stream: `2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148`
- census: `844dba5cf023f68a083261dd1612503c16309297f21ca57e26497f7a6df28d7a`
- semantic kernel: `e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d`
- repair matrix cache: `9342b7cd7b8e048b5ae38a3626766827e196c076be5fddaa94e0cb008ade49e5`
- repair linear cache: `4d98c6e6c2aa1a3317c13c541c50d25a025b6211ece448803462371a45a56100`
- native projection solver: `8c5f71a8089f0ce9ad712de215043d3e076aae14187794072f79fc5271d907a9`
- native replay kernel: `0725a2cb305f89fc92f98b1ac45e59f6feafa684b26a3bd0e3765168c8ee9f31`
- corrected residual certificate: `ec0120da03f777a8e2497bea23809d96752b4389d217099d1e037cb264a873ab`
- compiled mixed-degree MAX9 certificate: `93ffa8bb00c6b774619f840b1de767c15ff98eb7b7c3f9a77ad73471f61bce32`
- independent full compilation replay: `75e0442e2fdbe03b6bfb86a7b188d3db870a482371e3884234b29cefe82bd2b6`

Either outcome is confined to this complete degree-four lift-class span at
MAX9. It does not establish a coefficient transport law, MAX10/MAX11 result,
or induction theorem.
