# G-0189 result — seventeen independent exact zero identities

Let \(q_s\) denote the complete symmetrized piecewise-linear STAR atom with
frozen G-0179 record sequence \(s\). At ambient dimension eleven, each of the
following identities holds exactly:

\[
\begin{aligned}
-q_{235}+q_{1603}+q_{2077}-q_{2519}-q_{3488}+q_{3803}&=0,\\
-q_{260}+q_{519}+q_{1235}-q_{3544}-q_{3997}+q_{4004}&=0,\\
-q_{489}-q_{1435}-q_{2416}+q_{2836}+q_{3034}+q_{4144}&=0,\\
q_{1967}-q_{3597}+q_{3853}-q_{3863}-q_{4258}+q_{4320}&=0,\\
q_{383}+q_{1184}-q_{2831}-q_{3352}-q_{3987}+q_{4441}&=0,\\
q_{577}+q_{1929}-q_{2089}-q_{2565}-q_{2784}+q_{4535}&=0,\\
-q_{102}+q_{560}+q_{1497}-q_{3950}-q_{4218}+q_{5256}&=0,\\
-q_{607}+q_{3054}-q_{4161}+q_{4504}-q_{4507}+q_{5316}&=0,\\
-q_{526}+q_{1902}+q_{2609}-q_{3742}-q_{3854}+q_{5349}&=0,\\
-q_{102}-q_{526}+q_{879}-q_{1640}+q_{1902}+q_{5479}&=0,\\
q_{3074}-q_{3661}-q_{4063}-q_{4479}+q_{4924}+q_{5521}&=0,\\
-q_{1265}+q_{1430}+q_{5008}-q_{5045}-q_{5442}+q_{5549}&=0,\\
-q_{560}+q_{924}-q_{1080}-q_{2572}+q_{3742}+q_{5556}&=0,\\
q_{628}-q_{1616}-q_{4320}+q_{4812}-q_{4875}+q_{5568}&=0,\\
q_{2127}+q_{3116}+q_{3294}-q_{4277}-q_{5288}-q_{5635}&=0,\\
q_{3743}-q_{4258}-q_{4365}-q_{4763}+q_{5296}+q_{5725}&=0,\\
q_{3819}-q_{4537}-q_{4812}-q_{4868}+q_{4875}+q_{5296}&=0.
\end{aligned}
\]

These are respectively G-0187 basis columns
`12,15,17,21,24,28,68,72,75,82,87,90,91,108,117,121,122`. Because G-0187
certifies all 478 basis columns as independent over \(\mathbb Q\), these 17
identities are independent as coefficient relations among the frozen STAR
records. Each zero function lies trivially in the old-primary span \(O\).

Together with the three-dimensional retained signed-mass-at-most-three
subkernel already placed in \(O\) by G-0185, this classifies 20 independent
directions of the 478-dimensional retained restriction kernel. It leaves 458
global kernel directions unclassified.

## Exact evidence

The preregistered G-0189 scanner computed the complete G-0179 ordered-chamber
normal form once for each of 92 unique records. Exact signed-128-bit
aggregation found, for all 17 relations:

- zero nonzero hinge directions;
- zero in each of the eleven linear coordinates; and
- the canonical empty complete-residual SHA-256
  `fc576a729f405ea569b2b74bb60e2ecc4a4561688bf3abe3a5e33fe0131198f8`.

Adding one copy of \(q_{235}\) to the first relation produced 36,026 nonzero
hinges, including 13,720 with first primitive coordinate nonzero. The exact
mutant difference equals the independently computed normal form of
\(q_{235}\).

A fresh-context audit then used the unchanged historical G-0109 evaluator,
not the G-0179 library or G-0189 scanner. It independently reconstructed all
92 G-0113 representative graph pairs and their compact signed-edge semantics,
matched all 92 complete normal-form hashes to the registered run, and again
obtained zero complete residuals for all 17 relations.

| object | SHA-256 |
|---|---|
| registered outcome | `e90a79984c0dd7c582ca9dbbcb7f73b08c0c1505d0597bfcd98d44361ded8005` |
| independent audit source | `18f0febd95e3d490c3c4cd980cebafec9ae628b34a5155956b1edc273d05d067` |
| independent 92-record input | `67b4ada6a6c5b311de23ac7b5038ddd5940159cb7fda698f5db1b06c61aa2990` |
| independent audit receipt | `501bdfc8f6f406ea915e254caf6535bbfa101cd32cd6c8ef6afaaa8f7d5db014` |
| regenerated G-0109 output | `76a060bd88ac3bf6c46e5123b74cd701efff95b84c8335b0215c16d38bf595d4` |
| historical G-0109 source | `dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126` |
| historical G-0109 executable | `e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426` |

The 77.8 MB regenerated evaluator output is omitted because it is derived
deterministically; its exact hash, input, executable, audit source, and full
scientific receipt are retained.

## Claim boundary

This proves 17 fixed complete-function identities at \(n=11\). It does not
prove that the observed graph pattern is a uniform parameterized identity, an
all-\(n\) theorem, or novel in the literature. It does not classify the other
458 retained kernel directions, complete the STAR quarantine, decide MAX11,
establish ansatz completeness, or imply an unrestricted two-hidden-layer ReLU
lower bound.
