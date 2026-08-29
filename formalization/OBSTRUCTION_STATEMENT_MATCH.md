# Statement-match review for `Formalization.Obstruction`

Cold-context verdict: **the eight declarations match their abstract logical
schemas; they do not formalize the concrete G-0015 certificate or MAX11.**

- `max_add_common` proves exactly
  `max (u+h) (v+h) = h + max u v`; its function, finite-sum, and finite
  function-sum variants are valid generalizations.  They do not define the
  multiset atoms, prove the `2 * 9!` orbit multiplicity, or derive the complete
  common-edge mapping.
- `not_mem_span_range_of_linear_separator` uses `Submodule.span R`, hence
  arbitrary real coefficients, and proves the separator implication for an
  arbitrary indexed family.  The `Fin n` declaration is a genuine finite
  specialization (with an unnecessary but harmless finite-dimensional ambient
  assumption).
- `span_range_eq_of_pointwise_eq` and
  `span_union_range_eq_of_replacement` prove the advertised abstract span
  preservation steps, including function-valued instances after `funext`.

Independent re-execution under the pinned environment produced Lean 4.33.1
(commit `819816b2e0a3bf405af45ae5c7af2491d8f5bee6`) and
`Build completed successfully (1543 jobs)`.  A textual scan found no `sorry`,
`admit`, `axiom`, `unsafe`, or `native_decide`.  `#print axioms` reported only
`propext`, `Classical.choice`, and `Quot.sound`.  An explicit negative control
asking for `ReluDepth.MAX11` was rejected as an unknown identifier.

The Lean development contains no frozen `7146 x 9804` matrix, rational dual,
9,804 annihilation checks, graph enumeration, common-edge orbit mapping, or
premise hashes.  Kernel acceptance therefore establishes reusable abstract
lemmas only—not G-0015, unrestricted MAX11, or a depth lower bound.
