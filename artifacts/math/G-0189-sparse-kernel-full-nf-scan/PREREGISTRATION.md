# G-0189 outcome-blind scan contract: sparse mass-four STAR circuits

## Question

For the deterministic G-0187 stratum consisting of exact sparse-basis
relations with coefficient support at most six and with every incident STAR
record having signed mass four, does the complete G-0179 ordered-chamber
normal form of any relation contain a nonzero hinge whose primitive direction
has first coordinate `d[0] != 0`?

This is a falsification gate for extending face-confined reasoning. It is not
a test of old-primary membership and cannot by itself prove MAX11
representability or a lower bound.

Frozen by the research lead at `2026-09-01T11:01:52Z`, before any selected
full normal form was computed.

## Frozen structural expectations

- G-0187 candidate SHA-256:
  `24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe`
- G-0179 STAR records SHA-256:
  `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4`
- G-0180 quotient receipt SHA-256:
  `6e7d58666b9a58d1ea68141595bdd1404a519f10e7f47068166c7d7a290864d5`
- G-0179 `src/lib.rs` SHA-256:
  `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73`
- exactly 478 basis relations in 5,769 retained coordinates;
- retained-row mapping deletes STAR sequences `1548,3140,4259,5656`;
- deterministic selected basis columns:
  `12,15,17,21,24,28,68,72,75,82,87,90,91,108,117,121,122`;
- exactly 17 selected relations, 102 term incidences, and 92 unique records;
- each selected relation has six terms and every coefficient is `+1` or `-1`.

## Frozen implementation

- `src/main.rs` SHA-256:
  `f6961f8e97ae08a245fac9f2410813e1088e9ea3b4b043d5e04b82b6f9f98e2b`
- `Cargo.toml` SHA-256:
  `1921f8fa109a7a40249b1448a3ec88a4d1b64b6135b479c862cf94786343f1de`
- `Cargo.lock` SHA-256:
  `36b1d281393cbcc5b1bc0ed7ac3118a7a0c8bfec7104ec4b4b9b48ecdce7d266`
- frozen release binary SHA-256:
  `4bab8c77304c4cd7de840a1ac7082d0b2b2d113842e0e97046cff8e54d5b152f`

Before the freeze, two outcome-blind unit tests passed, Clippy passed with
warnings denied, and the release build completed. None evaluates a selected
STAR normal form.

## Frozen computation

1. Re-hash and validate every input and the retained row-to-sequence mapping.
2. Compute `g0179_star_loop_pricer::full_normal_form` once for each of the 92
   unique records, in a deterministic Rayon collection.
3. Aggregate exact linear coordinates and hinge coefficients in `i128` for
   every relation, deleting exact zeros only after the sum.
4. For every relation report the total nonzero residual hinges, the count with
   `d[0] != 0`, a SHA-256 binding the complete sorted residual, and the first
   lexicographic `d[0] != 0` witness when one exists.
5. Re-hash every input before creating the output and refuse overwrite.
6. Mutate the first relation by adding one copy of its first STAR atom and
   require the exact change in the aggregated `d[0] != 0` map to equal that
   atom's independently computed map.

## Decision rule

- Any exact nonzero residual hinge with `d[0] != 0` is a decisive witness that
  the corresponding relation is not confined to the `d[0]=0` hinge face. Since
  every loopless old-primary atom has first signed increment zero and hence no
  such hinge, this also proves that relation is not in the old-primary span
  `O`.
- No such hinge across all 17 relations advances, but does not finish, the
  face-gluing route. It does not imply that the relations vanish completely or
  lie in the old-primary span.

No selected full-normal-form computation may be run until the source and this
contract have been frozen by the research lead.
