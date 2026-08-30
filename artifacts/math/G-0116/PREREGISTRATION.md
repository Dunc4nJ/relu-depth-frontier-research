# G-0116 — exact low-cycle panel evaluator gate

Registered before implementing or timing the evaluator.

## Question

Can the 301-row G-0113 target panel be evaluated exactly without the
`4^active_vertices` fallback on the cyclic signed graphs that dominate the
MAX10-to-MAX11 lift family?

For a loopless signed graph, choose a spanning forest of its absolute support
and put one endpoint of every non-tree edge into a feedback set `F`.  Since
removing `F` leaves a forest and the G-0113 census has absolute cycle rank at
most four, enumerate only the `4^|F|` colours of `F`.  Conditional on those
colours, compute the exact distribution of

```text
(four colour counts, three signed level coefficients)
```

by tree dynamic programming.  Fold this distribution into each formal-profile
row with the exact inactive-label multinomial.  Add the fixed degree-five
loopless base term.

## Frozen inputs

- G-0113 panel-solver preregistration and prepared-input schema;
- G-0113 signed-W representative map SHA-256
  `57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48`;
- G-0111 direct-profile source SHA-256
  `ea88f3ff0aa1051f0d2a54d035a092de4e8283dc459a4329b84817f78da7d29b`.

## Pass/fail

The implementation must:

1. agree entry-for-entry with independent exhaustive `4^active` colour
   enumeration on at least one record in every signed-mass stratum and on
   cyclic active-10 and active-11 controls;
2. reproduce the exact formal-assignment census for every checked profile;
3. reject an edge-sign mutation and preserve global branch swap;
4. show a median speedup of at least 10x on the frozen cyclic active-10/11
   controls, or be abandoned rather than integrated.

This is an evaluator/performance result only.  It proves no target membership,
global identity, completeness theorem, or MAX11 result.
