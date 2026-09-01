# G-0185 freeze — complete low-mass STAR-kernel quarantine

Frozen at `2026-09-01T10:33:40Z`, after exploratory rank calculations and the
three generator lifts existed but before a fresh theorem-composition replay.
This is a post-discovery verification freeze.

## Candidate theorem

The frozen candidate is `theorem_candidate.json`, SHA-256
`7d3f6c5e78934fa57c08326d2ea9a8543d07c538a47be45e5f70d5b112e3d0e2`.
Let \(A_{\leq3}\) be the rows of the frozen G-0180 5,769 by 6,795
restriction matrix corresponding to retained G-0179 STAR records of signed
mass at most three. The candidate asserts

\[
\operatorname{rank}_{\mathbb Q}(A_{\leq3})=67,
\qquad
\ker_{\mathbb Q}(A_{\leq3}^{T})
=\operatorname{span}_{\mathbb Q}\{c_0,c_{15},c_{130}\},
\]

where the \(c_j\) are exact G-0181 basis columns. G-0182, G-0183, and
G-0184 respectively certify \(c_{15},c_0,c_{130}\in O\). Consequently every
rational relation supported only on these low-mass STAR records is in the
old-primary span \(O\).

Exploratory calculations had already observed 70 selected rows, modular rank
67 at two primes, and the three exact null vectors. They are not the promotion
gate.

## Frozen inputs

| object | SHA-256 |
|---|---|
| theorem candidate | `7d3f6c5e78934fa57c08326d2ea9a8543d07c538a47be45e5f70d5b112e3d0e2` |
| G-0180 restriction matrix | `d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd` |
| G-0179 STAR census | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0181 exact kernel basis | `56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232` |
| G-0182 lift receipt | `f92635277b6d24c8c69eac2048af1152008ef5626ab96cc7a41403a7d520aa3d` |
| G-0183 lift receipt | `c3dd7eb92a906b3ad2563dea96f02ec3cbfb51777f34dc681840de7e6e6419e1` |
| G-0184 lift receipt | `5860b2b15c01b5951f76d82751451d450a62b03c4b9c9f576e96fbee62555898` |

## Fresh promotion gate

A verifier written after this freeze must:

1. bind and re-hash every frozen input, require the complete STAR sequence
   census, remove exactly sequences 1548, 3140, 4259, and 5656, and select
   exactly the 70 records with signed mass at most three (four mass-two and 66
   mass-three records);
2. extract those exact 70 rows from the 5,769 by 6,795 integer matrix and
   record a canonical selected-row digest;
3. independently row-reduce the selected matrix modulo 1,000,003 and
   1,000,033, require rank 67 at both primes, and require identical pivot
   columns;
4. parse exact G-0181 basis columns 0, 15, and 130, require every term to be
   supported on the selected rows, and replay all 3 by 6,795 characteristic-zero
   equations exactly;
5. require the 3 by 3 restriction to STAR sequences 2124, 3944, and 5155 to
   be the identity, proving exact independence;
6. apply the rank sandwich in the correct directions: three independent exact
   null vectors give rational rank at most 67, while either rank-67 modular
   minor gives rational rank at least 67;
7. bind the three promoted full-function lift receipts, require their left
   sides to be nonzero scalar multiples of the matching exact kernel columns,
   and require zero complete-normal-form residuals and successful hostile
   controls;
8. reject a one-unit mutation of the first coefficient of \(c_0\) against the
   selected integer matrix; and
9. re-hash every input at exit and refuse to overwrite an output.

## Claim boundary

The theorem classifies only relations whose support is contained in the 70
retained signed-mass-at-most-three STAR records. A relation mixing even one
higher-mass STAR record is outside scope. The result does not prove the full
5,769-row STAR quarantine, decide MAX11 membership, establish ansatz
completeness, or give an unrestricted ReLU lower bound.
