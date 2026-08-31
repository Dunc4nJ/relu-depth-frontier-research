# G-0125 clean-room audit — G-0121 finite-family member

## Verdict

**Mathematical certificate: `CONSISTENT` on the frozen 348-row system.**

**Artifact-contract verdict: `INCONSISTENT` under the independently frozen
audit preregistration.**  The only inconsistency is non-load-bearing schema
semantics: `support_sequences` contains all 156 selected basis sequences,
including 25 positions whose integer coefficient is zero.  The actual nonzero
support is the 131-entry `terms` list.  Thus the field named
`support_sequences` is a selected-basis transcript, not mathematical
coefficient support.  The two lists are internally coherent, but they do not
satisfy the audit's preregistered requirement that a field called support equal
exactly the nonzero coefficient positions.

This is a fresh-context, same-OpenAI-lineage audit and is at most T1.  It did
not import or call the G-0123 master solver and did not run global replay.

## Exact checks

- Rehashed 29 bound files before reconstruction and rehashed the eight
  load-bearing scientific inputs again before writing the receipt; no drift.
- Read the 301 panel coordinates directly from the 788,571,840-byte frozen
  signed-i128 little-endian cache.  All eight cache control-vector digests
  matched, and all 163,740 panel-record sequence labels were exactly ordered.
- Independently recomputed every i64 stream digest for the four accumulated
  rows, all 32 Batch32 rows, and the shared 163,740-by-11 linear stream.  The
  Batch32 direction/residue order and selected-prefix digest matched.
- Reconstructed all 156 selected columns on all 348 rows.  The
  denominator-cleared identity has exactly zero residual on every row.
- The target was independently rebuilt as the 301-entry panel target, ten
  linear zeros, `11! = 39,916,800`, and 36 hinge zeros.
- The target scale is positive and its gcd with all 156 integer coefficients
  is one.  The 131 `terms` entries equal exactly the nonzero selected
  coefficients in increasing family order.
- Adding one to the first nonzero coefficient was rejected on 319 rows; the
  first mismatch is row 0 with residual `1,269,724`.
- All 42 exact FLINT rank pairs were independently recomputed from the
  seed-plus-trial transcript.  Trials 0–40 reproduce `(115,116)` through
  `(155,156)`; trial 41 reproduces `(156,156)`.  Every appended column raises
  exact column rank by one.
- The 156-by-156 coordinate square has exact rank 156.  Of four natural
  signed-i128 little-endian traversals tested without consulting producer
  code, exactly the full 348-by-156 row-major stream matches the reported
  selected-basis digest
  `03d05477b7ac12641fac6b3ebe953d356fc89c4fe70d5ee03535a371d71fe0ac`.
  The producer preregistration does not explicitly spell out this traversal,
  so the matching serialization is evidence of consistency rather than an
  independently specified wire-format contract.

## Custody

```text
3a19573c37f5bcfb308b7e5d54e3b999661d5f48c9def4b87c47252873576aa4  PREREGISTRATION.md
53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036  source G-0121 result
cc02654d9a85a0b910c77e5e224b08e2d677deadda491611eeac0ce44701c0bf  replay_member_cleanroom.py
a24ad787748f0d79aea5ee9fc9a3724a8a5585855cf8ea86bbc8fb7bc3467871  cleanroom_receipt_v1.json
```

The source result is committed at `492462854538c563f57cbf77f87283305e18a36e`.

## Execution record

Five fail-closed development runs wrote no scientific receipt: a local/source
manifest-boundary mistake; two wrong assumptions about sorted-basis versus
CEGIS append order; a success-path error-message indexing bug after the
348-zero replay; and an incorrect first assumption that the selected-basis
digest covered the coordinate square.  A complete pre-hardening run was
preserved as `cleanroom_receipt_pre_hardening_v0.json`; the final run added an
ordering hostile control and an explicit Batch32 residual-digest binding.

## Boundary

The audit establishes consistency only on these frozen 348 rows and this
frozen 163,740-column family.  It does not establish a global functional
identity, compile a two-hidden-layer ReLU network, prove family completeness,
settle MAX11, or warrant Lean formalization of a global statement.
