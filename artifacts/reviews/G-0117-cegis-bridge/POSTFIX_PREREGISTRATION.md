# G-0117 post-fix adversarial preregistration

Frozen before inspecting the newly added exact-replay implementation or its
post-fix outputs.  This addendum supplements `PREREGISTRATION.md`; it does not
replace the original controls or relax their failure criteria.

## Objects under test

1. The rebuilt standalone `global_modular_replay` executable.
2. The new standalone BigInt `global_exact_replay` executable.
3. The repaired production conversion/postprocessing path.
4. `NORMAL_FORM_UNIQUENESS_LEMMA.md`, statement-matched to the actual
   `active_direction` normalization and to every downstream use of a nonzero
   normal-form coefficient as a refutation.

## Frozen attacks and controls

1. **Strict schema:** certificates with unknown fields, missing verification
   fields, forged recomputation receipts, or mismatched embedded source/kernel
   bytes must be rejected without producing an output artifact.
2. **Executable/source binding:** successful output must identify the executable
   hash and must bind the runtime source and kernel to the bytes embedded at
   build time.  A stale executable must not silently attest to current source.
3. **Exact integer domain:** coefficients, scales, hinge coordinates, and linear
   coordinates must remain arbitrary-precision signed integers end-to-end;
   canonical parsing, positivity/nonzero constraints, duplicate/range checks,
   and the expected input census must be enforced.
4. **Independent arithmetic:** independently recompute the planted exact
   residual 662784 and mutant residual 786432.  Reduce exact coordinates modulo
   both replay primes and compare with the modular implementation.
5. **Exact-zero path:** exercise cancellation to exact zero through the same
   production aggregation/finalization code, then independently perturb a
   hinge coordinate and a linear coordinate.  Zero may not be inferred only
   from modular residues.
6. **Witness selection:** when nonzero, the reported witness must be the frozen
   first lexicographic hinge direction, falling back to the first nonzero linear
   coordinate only when all hinge coordinates vanish exactly.
7. **Large-integer control:** use a coefficient outside fixed-width integer
   range and compare the emitted decimal residual with an independent BigInt
   computation.
8. **Converter chain:** a clean rerun must rehash the actual artifact it consumed
   and reproduce the exact postprocessing receipt; a forged or mismatched
   postprocess artifact must be rejected.
9. **Lemma statement match:** verify that the normal-form uniqueness lemma uses
   exactly the representative and normalization implemented by
   `active_direction`; check boundary/tie cases, zero coordinates, orbit/stabilizer
   assumptions, and the passage from uniqueness to coefficientwise equality.
   A nonzero normal-form coefficient is a valid refutation only if the expansion
   lies in the lemma's stated function space and the compared identity is on the
   lemma's stated domain.
10. **Scope discipline:** finite controls validate the implementation only.
    Even a successful exact refutation is bounded to the frozen certificate,
    atom family, symmetry reduction, and target.  It is not by itself a theorem
    about unrestricted ReLU networks.

## Verdict vocabulary

- `PASS_BOUNDED`: every applicable frozen control passes, with scope stated.
- `PASS_WITH_OBLIGATIONS`: core arithmetic is supported but one or more named
  provenance, novelty, lemma-scope, or integration obligations remain.
- `FAIL_INVALID`: an arithmetic, schema, binding, or logical-scope attack
  invalidates the claimed certificate/result.

