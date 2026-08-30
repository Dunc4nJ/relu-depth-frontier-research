# MAX6→MAX7 lower-n Y-spoke recurrence calibration

This isolated exact gate asks whether the pinned MAX6 certificate coefficients
can be lifted by one rational multiplier per
`cross/same × component topology × outer orientation`, together with the
three carriers `C_L`, `C_E`, and `C_Y`.

The seven Boolean Hamming rows admit interpolation.  Along the declared
profile sequence, `P012=(0,0,0,0,0,1,2)` and
`P013=(0,0,0,0,0,1,3)` still raise both ranks, while
`P023=(0,0,0,0,0,2,3)` raises only augmented rank.  The resulting exact
`10 × 11` matrix has rank 9 and augmented rank 10.  Its primitive row dual is

```text
[2016, 50400, -1240, -3020, -423, 6129, -3229, 50616, -2160, -48456]
```

in row order `B1,...,B7,P012,P013,P023`; it annihilates all eleven columns
and pairs with the MAX7 target by 17.

This is minimal only in that tested profile sequence.  No global search for
the smallest separating profile set was performed.  It excludes only the
displayed inherited, grouped coefficient class.  It says nothing about
arbitrary per-orbit coefficients in the complete cross+same family,
base-specific rules, additional carriers, degenerate source-term lifts, the
registered G-0079 result, or unrestricted networks.

The producer imports neither G-0078/G-0079 price data nor the registered
G-0079 runner.  A hostile semantic control changes the doubled anchor from
`2*x_k` to `x_k`; the row subject stays fixed while the frozen dual ceases to
annihilate the columns.

## Replay

```bash
.venv/bin/python -B \
  artifacts/math/G-0079/lower_n_calibration/max6_to_max7_recurrence_gate.py \
  --self-test

.venv/bin/python -B \
  artifacts/math/G-0079/lower_n_calibration/max6_to_max7_recurrence_gate.py \
  --check \
  artifacts/math/G-0079/lower_n_calibration/max6_to_max7_recurrence_gate_v1.json
```

## Frozen identities

- producer SHA-256:
  `67bf170730990ad985c88b9a556b272243125a163444849876904d0b6323aa91`
- result artifact SHA-256:
  `1f376e74f4f45b677291987961cce3c9cf3b4a2f252f047afa2efdd9bde4db3f`
- scientific payload SHA-256:
  `47b5f00067668b010c89b5485525c626bac26c70ce20015ded73fdf20ec9c036`
- exact matrix SHA-256:
  `81c2be9e9298a9f140b95056d2cf56487fc04d8ce1eab848d2e9cdab7b2b217d`
- exact target SHA-256:
  `1a180ae392d3da38b3c998c9bdcf9409e767d5b2132fe1e22b1dbdcd235d0948`
- eligible-base manifest SHA-256:
  `74a8e969477ef70128aaeec63e0313916741cfbe0b36064278c7d9bfe602984a`
- 180-seed manifest SHA-256:
  `81aeffc02a9462d12429e2b3dc3aec49d946a6087a9a8a50e3bf65c438a806cc`
- hostile-mutant matrix SHA-256:
  `faab2867ccc2d3f032430938ae39ad939804b7d997bb6b2fe438374078e6edc0`

The strict parser and both certificate byte/content hashes are recorded in
the result artifact.  Recomputing the producer after any source change makes
`--check` fail closed rather than silently refreshing this list.
