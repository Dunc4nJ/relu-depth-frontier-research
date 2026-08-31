# G-0139 preregistration — outcome-aware T1 audit of G-0135 Stage D

## Identity, disclosure, and fixed subject

- Registered `2026-08-31T17:09:13Z`, before writing or running the G-0139
  clean-room checker.
- Reviewer: `GoldenSnow` (Codex / GPT-5; same model lineage, T1 only). This
  reviewer previously performed the G-0136 Stage-A source audit. The reviewer
  did not author or execute the Stage-D scientific replay, but that earlier
  role makes this a same-campaign, outcome-aware audit rather than independent
  T2 review.
- Exact subject commit:
  `270a62455097cbaf0a8f80426c54b6121d1afcba`.
- Exact subject:
  `artifacts/math/G-0135/new_member_global_replay_v1.json`, SHA-256
  `d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875`.
- Exact Stage-C input commit:
  `2a567c1fcc8eed745235a50e638fc8c5e3ca83cc`; candidate
  `artifacts/math/G-0135/full_family_master_result_v3.json`, SHA-256
  `ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8`.
- Required Stage-D source-audit anchor:
  `artifacts/reviews/G-0138-g0135-stage-d-source/SOURCE_AUDIT_RECEIPT.json`,
  SHA-256
  `f4e62ee4cd5311f74393e3141161512b62c65ebc9409c1ba5a8811019a2ec944`.

The disclosed terminal branch is `EXACT_RESIDUAL_BATCH_CONTINUE`. This
preregistration is deliberately outcome-aware: it freezes the checks and
falsifiers before audit code exists, not before the result is known. The audit
must not import, invoke, translate, or copy Stage-D source, and must not rerun
the Stage-D executable. Scientific files are immutable.

## Exact bounded question and no-claim boundary

Does a separately written arbitrary-precision implementation, starting from
the Stage-C certificate and its frozen upstream records, reproduce the
delivered complete ordered-chamber residual and deterministic next Batch32?

A positive verdict is only `CONSISTENT_RESIDUAL_T1` for this exact 135-term
member and exact committed bytes. It does not establish family completeness,
frozen-family nonmembership, a MAX11 lower bound, unrestricted two-hidden-layer
nonrepresentability, the all-n target, `REFEREED`, `FORMALIZED`, or a Lean
theorem. A same-lineage result audit cannot supply T2 promotion.

## Frozen disclosed anchors

The checker must independently derive and then compare all of these values:

- 135 nonzero terms obtained by the order-preserving nonzero projection of
  Stage C's 204 selected coefficient slots; positive target scale and primitive
  denominator clearing;
- all 412 Stage-C rows exactly, split as 301 panel rows, 11 linear rows, and
  100 accumulated hinge directions;
- `135 * 11! = 5,388,768,000` labelled permutations, with no skipped,
  failed, unclassified, duplicated, or silently omitted contribution;
- exact zero on every accumulated direction and all 11 linear residuals;
- aggregate hinge support 147,062 and nonzero residual count 146,950;
- lexicographically first nonzero direction
  `[0,0,0,0,0,0,1,-2,-2,1,2]` with coefficient
  `511838695529252537134751622979004566912532181650940275812075139014937590867028110892243795641237175143066549672701558636166678186077128694292857947716107231627691338960`;
- aggregate, complete-residual, nonzero-residual, and per-term transcript
  SHA-256 values respectively
  `168f91bd8735c778b492fd7f2f7414d4428dfd1af8af21bd8afe294c1b2ecf60`,
  `3f9ca1a339ad8cdcb3260b12a48b554b4c5b401144cf5cd627f7ec1db30a7ce6`,
  `9d7dd907d6885ab5e5b5a5a783b0212da8f145c1202fdb4de2c90f44d55023aa`,
  and
  `7670731c72b64e89517d4d68d8ca44b73947db3c2a24938a4e843dfb9d8c1bbd`;
- the first 32 nonzero primitive active directions in strict signed tuple
  lexicographic order, excluding the accumulated set, with direction digest
  `b91dcdedc2834f6d0639846dc258cd6bf4aba42c0debae34761fd857f25384ce`
  and canonical decimal-LF coefficient digest
  `7a95296dc09b6a156f2ec385e1f6b4e94907a9c8c0ae0c18428d16a925903321`.

## Independent derivation and replay contract

1. Rehash the subject, Stage-C result, manifest, source-audit receipts, and
   every consumed transitive input at entry and exit. Reject path escape,
   symlinks, resolved duplicates, untracked substitution, malformed canonical
   integers, hash drift, or wrong Git ancestry.
2. Derive the 135 terms solely from Stage C's ordered sequences and exact
   integer coefficients. Check sequence/coefficient pairing, uniqueness,
   support projection, target scale, gcd/sign convention, and every Stage-C
   scientific digest whose serialization is specified.
3. Replay all 412 finite rows without trusting Stage D: decode the pinned
   sequence-major 301-row cache independently, reconstruct the 11 linear
   coordinates and 100 accumulated-direction prices by the new exact route,
   and compare the integer combination to the independently reconstructed
   Stage-C target on every row.
4. Reconstruct each term from the frozen family record. Enumerate active-label
   injections and inactive-label factorial multiplicity, using Python integers
   throughout. Canonicalize each nonzero hinge to primitive signed orientation,
   accumulate the full union dynamically, and compute linear terms by a second
   exact route. Producer term normal forms and residual fields are comparison
   outputs only, never inputs to the derivation.
5. Apply the target exactly once by subtracting `target_scale * 11!` from
   linear coordinate 10 only. Verify every accumulated direction and all 11
   linears, then serialize the complete direction-sorted residual stream,
   its nonzero projection, per-term transcript, and next Batch32 exactly as
   specified by the committed protocol.
6. Read the Stage-D result only for final field-by-field comparison. A partial
   replay, producer-code reuse, digest-only shortcut, bounded integer,
   floating-point tolerance, modular equality, or inferred firstness yields
   `CANNOT_VERIFY`, never consistency.

## Hostile controls fixed before execution

The actual acceptance path must reject at least: first coefficient `+1`;
omission of the final nonzero term; reversal of two term/sequence entries;
omission of one labelled contribution or a one-count global census decrement;
omission/mutation of one accumulated direction; target subtraction in the
wrong coordinate or target scale `+1`; direction sign/gcd corruption; reorder
of two next-selected rows; coefficient decimal missing its LF; one-unit first
residual mutation; subject or transitive-input SHA mutation; symlink/path
escape; and a false custody/ancestry binding. A small independently specified
zero/nonzero fixture must exercise both terminal directions.

One decision-bearing contradiction or one hostile mutant reaching acceptance
forces `INCONSISTENT`. Missing custody, unavailable inputs, or inability to
finish the full exact replay forces `CANNOT_VERIFY`. Only completion of every
frozen obligation permits `CONSISTENT_RESIDUAL_T1`.
