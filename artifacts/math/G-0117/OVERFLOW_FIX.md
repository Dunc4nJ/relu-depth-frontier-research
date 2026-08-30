# G-0117 adversarial overflow correction

The clean-room reviewer found that the public `hinge_coefficient` API accepted
primitive active directions with coordinates outside `[-5,5]`, but computed
`scale * coordinate` in `i8`.  The valid direction

```text
(0,1,-26,25,0,0,0,0,0,0,0)
```

therefore panicked in debug mode at scale `-5` and wrapped in release mode.
Its true coefficient is zero for every degree-five atom because every raw
back-degree increment lies in `[-5,5]`.

The multiplication is now performed in `i16`, and raw `i8` increments are
promoted before comparison.  A regression test validates the direction and
requires an exact zero.  All ordinary, frozen-G0109, panel-bridge, and clippy
checks pass after the change.  The current-source v2 full-family benchmark
reproduces the v1 hinge and linear hashes exactly; v1 is retained but
superseded because it binds the narrower pre-fix source.
