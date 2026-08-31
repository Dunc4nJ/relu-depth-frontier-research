# G-0126 complete global replay result

## Decision

The sealed 131-term G-0121 finite-row member is **not** a global ordered-cone
identity.  The preregistered complete replay returned
`GLOBAL_MODULAR_RESIDUAL`.

This is an exact refutation of that coefficient vector: a residue nonzero
modulo either prime proves the corresponding integer normal-form coefficient
is nonzero, and the bound normal-form uniqueness lemma makes a nonzero active
hinge coefficient incompatible with the linear MAX11 target.

It is not a refutation of the 163,740-record family, MAX11, any broader atom
family, or two-hidden-layer realizability.

## Sealed evidence

```text
candidate:
  artifacts/math/G-0121/full_family_master_result_v1.json
  sha256 53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036

preregistration:
  artifacts/math/G-0126/GLOBAL_REPLAY_PREREGISTRATION.md
  sha256 d6dd969ae558c7e36eb420c1fa4fa2c1254875eeff073b8580809b6a50a2fadb
  commit ccfa8dd

producer:
  artifacts/math/G-0126/src/main.rs
  sha256 a59f51ed491d50fb8d8e3e93e1a0f53dbc351a67a84fc2ae1f51bd18f74991f3
  commit c323662

release executable:
  artifacts/math/G-0126/target/release/g0126-global-replay
  sha256 ae7f64ce737d8f12d9f4a3d5695fe8ded4b5a89720eff8a0f5a537b2126bfa28

result:
  artifacts/math/G-0126/global_replay_v1.json
  sha256 bd0410d861978956502e9d4c4fc1cd159565f2e170d70509abd0f3eb21b771ea
```

The one scientific invocation processed all 131 terms, 4,667,940 generated
hinge entries, and exactly `131 * 11! = 5,229,100,800` labelled
permutations.  The aggregate contained 178,145 hinge directions, of which
178,040 were nonzero modulo at least one of the ordered primes
1,000,000,007 and 1,000,000,009.

All 36 previously accumulated hinge rows replayed to `[0,0]`.  Both complete
11-coordinate linear residual vectors were zero.  Thus this is a new global
falsifier, not a failure to reproduce the 348-row master input.

The deterministic first violation is

```text
direction = (0,0,0,0,0,0,0,1,-4,3,0)
residues  = (43,548,241, 159,884,126)
exact residual =
  16043724992398578850227458322701984858030245826360603758987576940974049818167608600182090787340833997661796968443242038163661938484788491372451876563071360
```

All 32 preregistered selected directions were priced as exact nonzero integer
candidate residuals and independently re-reduced to both recorded primes.

```text
selected direction/residue stream sha256:
  0cd2699dec0bc5ffd7cb81c1454aac79143ae4a37c571fcb707c85a55a5c459e

exact decimal-LF residual stream sha256:
  000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b
```

The in-memory `+1` mutation of coefficient sequence 0 changed the
carry-forward receipt, the linear receipt, the nonzero census, and the
selected prefix; it was rejected.  The output was pre-serialized and
published through an exclusively created same-directory temporary file plus
an atomic no-overwrite hard link.  Independent receipt validation found no
temporary or partial output and rechecked every bound source/executable hash.

Exact full-normal-form replay was correctly not triggered: modular nonzero is
already an exact nonzero certificate.  Lean formalization is not triggered,
because there is no true global identity to formalize.

