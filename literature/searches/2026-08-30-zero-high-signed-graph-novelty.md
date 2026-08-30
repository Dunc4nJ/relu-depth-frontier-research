# Zero-high signed-graph novelty search — 2026-08-30

## Question searched

Does the following order criterion already occur in the signed-graph,
bicolored-graph, elimination-order, or oriented-matroid literature?

For a loopless graph with equally many positive and negative edges, order the
vertices; when a vertex is added, count the incident edges of each sign whose
other endpoint is already present.  Seek an order in which every step closes
edges of at most one sign and the signed induced-edge prefix count visits both
positive and negative values.

This is the exact combinatorial criterion independently derived for the
degree-five-only signature in G-0068; the prime signed mass five is an
additional hypothesis in its hinge interpretation.

## Searches run

- Multi-source paper metadata search (arXiv, OpenAlex, Semantic Scholar):
  `bicolored signed graph alternating cycle vertex ordering induced edge imbalance`.
  It returned no direct result; Semantic Scholar was rate-limited, so this is
  not an exhaustive database negative.
- Perplexity Sonar Pro literature synthesis using the full criterion and the
  neighborhoods “signed graphs”, “bicolored graphs”, “elimination orderings”,
  “alternating cycles”, and “oriented matroids”.
- Direct arXiv verification of the closest returned primary source:
  Koji Nuida, *A Characterization of Signed Graphs with Generalized Perfect
  Elimination Orderings*, Discrete Mathematics 310 (2010), 819–831,
  arXiv:0712.4118v3: <https://arxiv.org/abs/0712.4118>.

## Finding and boundary

No source located in this search states the G-0068 closure/prefix-imbalance
criterion.  Nuida's signed elimination ordering is a local chordality and
sign-compatibility condition on triples; it does not count newly closed edges
or require the cumulative signed induced-edge count to visit both signs.
Likewise, standard balanced/antibalanced-cycle and oriented-matroid circuit
terminology is adjacent but does not match the criterion as searched.

This is **novelty evidence, not a novelty proof**.  Synonyms, older graph-order
literature, or a theorem stated in a different language may have been missed.
Any paper should describe the criterion as apparently absent from the searched
literature and should solicit expert review before making a priority claim.

## Immediate implication

Use the criterion as a self-contained lemma with a direct proof and executable
finite-family verifier.  Do not claim that the observed “alternating unique
cycle iff zero-high” converse is a general graph theorem: its converse has so
far been exhaustively certified only for the 11,542 registered natural lifts.
