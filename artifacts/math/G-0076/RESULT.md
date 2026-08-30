# G-0076 result — target-aware complete-row resolver

## Registered outcome

The preregistered resolver found

```text
rank(A)       = 6,876
rank([A | b]) = 6,877
epsilon       = 1
```

modulo the registered prime 1,000,003 on the complete frozen system of
16,738 rows and 8,107 construction columns.  The canonical right kernels of
`A` and `[A | b]` both have nullity 1,231, and every coordinate of the target
projection of `ker([A | b])` is zero modulo that prime.

The registered decision is therefore
`MODULAR_TARGET_SEPARATED_EXACT_STATUS_UNRESOLVED`.

This is strong evidence that the MAX11 target is outside the frozen
8,107-column Y-spoke family, but it is **not** a rational nonmembership
theorem.  A single prime can create false separation.  Promotion requires an
exact rational left-dual `y` with

```text
y^T A = 0   on every one of the 8,107 columns,
y^T b != 0.
```

It would then be a no-go theorem for this bounded construction family only,
not an unrestricted two-hidden-layer ReLU lower bound.

## Complete replay and custody

The run regenerated all 15,360 G-0075 positive four-level rows and appended
all 1,378 G-0074 rows.  It rechecked the registered panel hashes, the complete
G-0075 prefix, the selected-460 projection, and the G-0074 suffix before
algebra.  All 1,231 archived kernel vectors annihilated all 16,738 augmented
rows modulo 1,000,003.

```text
full [A | b] int64 SHA-256:       41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095
H_N raw uint32 SHA-256:           48285ef0851adf4035439c27eb68a90de8a97c1b9b2ceac5a6b8b63e91f9563d
H_A raw uint32 SHA-256:           2cacedf021fe291dd0f19ba66f49f4c1d98dba6b922311a904654b66bb9c269d
kernel pivot-list SHA-256:        d64f759043785cebd3295c74ca5db8ccb72acc1ca21756dc9f57c55220cd8aac
target projection SHA-256:        d48eff25f43756ecb584984c4428e09c8cfd6429725e176b43bbd232a135f867
archived H_N gzip SHA-256:        53b2e58fb6737132d2da4fab8980f98977e04f06f57853234e55f915fd277170
outcome gzip SHA-256:             374d684459c12e76184dfc1da50e8993b1d4dbda474c13ea4319665997570bfb
scientific payload SHA-256:       e074cdbf1818f0eaa0f8d649371bf5f669207e3e9590d7d9a834618ae1e76e15
registered producer SHA-256:      1499b96abb926d54d96f2b3163748f40dfd5810325424dbb41409a829213c4e2
```

The registered run used 16 workers and completed in 4,011.7 seconds.  The
ignored cache is resumable but non-evidentiary; the outcome receipt and
deterministically compressed canonical kernel are the retained artifacts.

## Next discriminator

G-0077 must derive a canonical modular row basis and failing row from this
frozen outcome, lift the corresponding left dual over the rationals, and
replay it with exact integers against every frozen-family column and the
target.  No further random-panel sampling is warranted before that test.
