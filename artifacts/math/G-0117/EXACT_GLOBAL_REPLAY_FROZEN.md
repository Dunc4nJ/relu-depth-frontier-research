# G-0117 exact global replay — frozen execution

## Frozen implementation

```text
EXACT_GLOBAL_REPLAY_PREREGISTRATION.md  a76f3ee0bf77f8c5a2180830b2879cf9b1b75fbac797a166a19fb605706a0a12
global_exact_replay.rs                 1232548952fee91827f8dfddf26dd01eacfc49c57a448f6d258add9b778f414a
release exact executable               3dcb3b43c4075f1206ecda874bd9013dd9328eb67e1b9a2f59b21391882c4574
global_modular_replay.rs               d27ece785362d84aea134e04893449f4bca926243aba29ec4fef377fb7a7003e
release modular executable             7c8c83b668026e1e15be89a1459c8e23c79937582d245464ce0a6b5e49b9925b
normal-form kernel                     84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa
NORMAL_FORM_UNIQUENESS_LEMMA.md         39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17
```

Both executables embed their producer, kernel, and uniqueness-lemma bytes and
refuse to run if the corresponding runtime source differs.  Outputs bind the
executing binary as well as the sources and input.

## Exact and hostile controls

The planted v2 certificate `7 F_0 - 6 F_1 = 14 T` produced first hinge
residual 662,784 under exact BigInt replay.  Changing the first coefficient
from 7 to 8 changed it to 786,432.  Both values matched the two modular fields.
Additional executed controls covered:

- exact-zero, first-hinge, and first-linear residual branches;
- a hinge-free atom taking the linear fallback branch;
- a coefficient with more than 79 decimal digits;
- unknown fields and noncanonical integers;
- duplicate sequences and a coefficient-plus-one mutant;
- stale executable source, stale kernel, and stale uniqueness lemma;
- forged and mismatched recomputation receipts.

Release tests and clippy with warnings denied passed.  The two ignored
full-artifact integration tests were also invoked explicitly and passed.

## First real seed

```text
certificate                             63dd98a3021f1e48a45733845d5740d96862e0131c57903c36fec69609586618
panel_seed_global_modular_replay_v1.json cbd3b9aadbfbf8fb6ae29edce67261a2207d8334887487339db4bd127e33795b
```

The replay processed 92 terms and 3,672,345,600 labelled permutations.  It
found the first canonical residual direction

```text
(0,0,0,0,0,0,0,0,1,-5,4)
```

with nonzero residues 482,908,994 and 83,090,671.  Therefore the cleared
integer residual is nonzero and this seed is exactly refuted.  Running the
BigInt implementation on this seed would not change that decision and was not
used as decorative confirmation.

## Independent review and boundary

Fresh-context review is recorded in
`artifacts/reviews/G-0117-cegis-bridge/REPORT.md` and
`postfix_controls.json`.  It assigned `PASS_BOUNDED` to the exact replay plus
uniqueness seam and found no arithmetic or lemma defect after the repairs.

This standing is bounded to verification of certificates in the frozen
163,740-atom family.  It proves neither family completeness nor a MAX11
identity.  Exact global zero would still require symmetry and architecture
compilation audits before formalization.
