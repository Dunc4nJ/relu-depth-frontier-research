# Recovery of the G-0008 obstruction extractor

The frozen modular obstruction
`G-0008/mod_obstruction_01_02_03_04_p1000003_v1.json` records extractor
SHA-256
`ccb12f782ed85ac615f60e67a414f27ed82ca4b321afdc93c72cebe2d9887adb`.
The later working file `extract_modular_obstruction.py` has different bytes
because it was subsequently upgraded to a v2 schema.

The exact v1 source was recovered from the original local Codex
`patch_apply_end` write event at `2026-08-29T09:07:14.970Z`, call
`exec-dc9bca44-7b79-4c07-92ee-f93f074c5326`.  The event contained the full
added-file payload, not a diff or reconstruction.  Those bytes are frozen as
`G-0008/extract_modular_obstruction_v1.py`.

Checks performed:

- recovered byte length: 10,947;
- recovered SHA-256: exactly the obstruction's recorded `ccb12f…` digest;
- byte comparison against the event payload: exact;
- Python compilation: pass;
- G-0017 verifies the recovered extractor, its modular-solution input, and
  each immediate source hash recorded by both the solution and obstruction.

This recovery restores provenance for the modular discovery step.  The final
real-span theorem does not rely on finite-field soundness alone: G-0011 and
G-0012 separately establish and replay the exact rational left dual, while
G-0014 separately owns graph-to-matrix semantic regeneration.
