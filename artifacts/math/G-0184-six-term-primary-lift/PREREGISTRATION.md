# G-0184 freeze — third exact kernel-to-primary lift candidate

Frozen at `2026-09-01T10:26:57Z`, after exploratory discovery but before an
independent replay. This is a post-discovery verification freeze, not an
outcome-blind discovery preregistration.

## Frozen candidate

The candidate file is `candidate_identity.json`, SHA-256
`6ce618ddf34b00ec442e8a0d533eb3caef54b91245c6be626dcf3834125728bc`:

\[
\begin{aligned}
2(q_{447}+q_{821}-q_{1418}-q_{1630}-q_{2570}+q_{5155})
={}&-5p_{1336}-2p_{1520}+7p_{1722}+2p_{4533}-p_{5341}-9p_{7087}\\
&+4p_{9256}-5p_{11134}-5p_{12930}+9p_{15947}+p_{16542}\\
&-3p_{16701}+2p_{17761}-2p_{18041}-2p_{20267}+2p_{20675}\\
&+4p_{22121}-3p_{22895}+6p_{32861}.
\end{aligned}
\]

The left side is twice G-0181 basis column 130. The six \(q\)'s are frozen
G-0179 STAR records; the 19 \(p\)'s are G-0113 old-primary records of signed
mass at most three.

The exploratory route reused the already computed 495 mass-at-most-three
primary normal forms, computed the new six-term target, observed equal
primary/augmented ranks at two primes, and found and exactly replayed the
displayed rational solution. Those diagnostics are not a rational-rank upper
bound and are not the promotion gate.

## Decisive frozen inputs

| object | SHA-256 |
|---|---|
| candidate identity | `6ce618ddf34b00ec442e8a0d533eb3caef54b91245c6be626dcf3834125728bc` |
| G-0181 exact rational kernel basis | `56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232` |
| G-0113 old-primary solver input | `093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8` |
| G-0179 STAR record census | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0109 evaluator source | `dfe2638f33c58fd3dfc6c5bd8e6f6ad2059a6eb47986a7e9b76f255b72da2126` |
| G-0109 evaluator binary | `e487f78b5f8c4f2f5b3b7764abbb742c6b2a47007d78561e4e125fc829498426` |
| G-0179 evaluator library | `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73` |
| G-0179 evaluator CLI source | `128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2` |
| G-0179 evaluator binary | `ba629a044408e170235523a6f578c55d3201d7be37bb07acf86e27d409a00824` |

## Independent promotion gate

A fresh verifier written after this freeze must consume no exploratory matrix,
normal form, or solve receipt. It must reconstruct all 25 controlled records
from the frozen censuses and:

1. require every frozen hash and confirm the left side equals twice exact
   G-0181 basis column 130;
2. validate old-primary membership, looplessness, signed mass at most three,
   and exactly one residual loop in every STAR record;
3. require literal equality of both frozen complete-normal-form evaluators;
4. require exact cancellation on every hinge direction in the raw union and
   on all eleven linear coordinates;
5. add one to the coefficient of \(p_{1336}\) and require a nonzero residual;
6. re-hash every frozen input at exit.

Any failed gate rejects the candidate. Altering a coefficient or selected
record requires a new freeze.

## Claim boundary

A pass would certify a third independent G-0181 kernel direction in \(O\),
not the other 475 directions, full STAR quarantine, MAX11 membership, ansatz
completeness, or an unrestricted neural-network lower bound.
