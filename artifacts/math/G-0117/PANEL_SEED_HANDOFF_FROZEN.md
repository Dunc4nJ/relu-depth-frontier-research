# G-0117 panel-seed handoff — frozen execution

## Subject

The production converter was run on the completed corrected G-0113 artifacts,
not on a synthetic receipt:

```text
panel exact postprocess  7bb06fc52d9ee5a69cab96bd4b80c5bf8514fa1be6c5f346091ae8fc24da35ff
scan report              6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e
retained columns         615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393
panel input              093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8
```

The converter reran the frozen exact postprocessor using those actual paths
and compared its decision projection before writing output.

## Frozen producer and output

```text
advance_panel_seed.py                    934912aac2c89d25223725d3ff4510275b67f13a781f37e94b5ee165949e8e1e
PANEL_SEED_HANDOFF_PREREGISTRATION.md    fd9704da88a7b4a21d82e5589b722078d8335786c47b2c87db3e488f0842a923
panel_seed_certificate_v2.json           63dd98a3021f1e48a45733845d5740d96862e0131c57903c36fec69609586618
```

The v2 certificate contains 92 nonzero integer coefficients and target scale

```text
1925109807278316085046256508006783368132160984259895048513502796983568520
```

Its claim boundary is an exact-Q finite-panel seed for global replay.  It is
not itself a global identity.

## Executed controls

- The converter self-test passed and rejected seven planted mutants.
- A forged postprocess document accepted by the pre-review converter is
  preserved in the review directory as the falsifier that caused the repair.
- Under the frozen production CLI, fabricated hashes, a mismatched
  recomputation receipt, a stale source, malformed coefficients, and unknown
  fields are rejected before scientific output.
- Denominator clearing is checked exactly: if the rational coefficient vector
  is `c` and `L` is the positive common denominator, the emitted integer
  coefficient is exactly `L*c` and the target is scaled by exactly `L`.

## Boundary

This artifact certifies the provenance and arithmetic of one finite-panel
handoff.  Mathematical truth is checked separately by complete global replay;
indeed, that replay refuted this seed at a new hinge direction.
