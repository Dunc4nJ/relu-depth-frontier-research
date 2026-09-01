# G-0177 bounded independent result audit

Verdict: **mathematical outcome PASS (bounded); source/custody and promotion BLOCK.**

The current bytes establish a real but negative result. The 924-row member is exactly valid on all 924 finite constraints, but a clean direct calculation finds an exact nonzero global hinge. It is therefore not a global identity and does not solve the target problem.

## Decisive checks

- All input and output hashes in `AUDIT.json` matched the files actually read and remained stable during replay.
- The member has 659 distinct selected columns and 349 correctly associated nonzero terms. Its integer coefficients and positive target scale are primitive.
- An independent arbitrary-integer reconstruction replayed all 924 rows: 924 zero residuals, with residual digest `e2690d85858011be129c55979a28e5a651ce4f964ffbf5df90079d5ecefd6eb1`.
- The explicit 659 by 659 integer minor has rank 659 modulo both 1,000,003 and 1,000,033, so it has rank 659 over the rationals.
- A complete independent scan of all 163,740 family columns found quotient rank 64 and residual-augmented rank 64 at both primes. Both hardened results use the same valid 64-sequence witness.
- The raw pair matrix passed all 128 exact predecessor-member dot bridges and 48 clean-formula raw-entry spot checks.
- A clean injection-completion implementation directly recomputed all 349 support contributions at
  `(0,0,0,0,0,1,-3,1,1,-2,2)` and obtained exactly the reported nonzero coefficient. This alone establishes `EXACT_GLOBAL_NONZERO` for the current member.

## Corrected pair interpretation

The heuristic pair selection does **not** produce 64 literal global pair identities. The independent full scan found 328 nonzero pair-difference quotient entries at each prime. The actual structure is:

- even representative quotient block: rank 63;
- pair-difference quotient block: rank 1;
- combined quotient and residual-augmented rank: 64.

Every one of the 163,740 rows reduced into those reconstructed subspaces at both primes. Thus the rank and compatibility claims survive, while the simpler “64 exact pair relations” explanation does not.

## Exact limits

The audit did not independently reproduce the complete 162,522-direction global census, the 11,239,811 processed hinge-entry count, the complete residual digest, every stored prefix coefficient, or the absence of a lexicographically earlier nonzero hinge. Those fields retain only same-run support here.

The digest implementation also uses the stale domain separator `G0168-PROVISIONAL-668-MEMBER-COMPLETE-EXACT-RESIDUAL-V1\0` for the 924-row member. This does not change the directly checked nonzero witness, but it prevents treating that digest as clean 924-member certification.

## Custody block

The decisive artifacts remain mutable `/tmp` files. The exploratory pair-pricing, quotient, lifting, and generic replay sources have not been freshly frozen and source-certified against these outputs. This audit therefore supports the bounded current-byte mathematical findings only; it does not authorize promotion, claim a global solution, or substitute for immutable custody and independent full-census review.
