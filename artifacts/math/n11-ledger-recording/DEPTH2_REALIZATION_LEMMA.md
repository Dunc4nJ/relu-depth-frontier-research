# Depth-2 realization lemma (proof note)

Author: orchestrator AmberBluff (Claude Fable 5.1), 2026-09-03. Status: proof written here; awaiting an independent T2 review (Claude-lineage referee, fresh context) before the ledger records it as PROVED_HERE. Consumer: claim C-0002 (MAX_11 in ReLU_2), whose verifier-certified content is an algebraic identity, not a network.

## Statement

Fix n >= 2. For a finite multiset E of unordered pairs (i, j) of indices in [n] (repeats and loops i = j allowed), write f_E(x) = sum over (i,j) in E of max(x_i, x_j). For two such multisets A, B define the atom Phi_{A,B}(x) = max(f_A(x), f_B(x)). For a permutation sigma of [n] write (sigma x)_i = x_{sigma(i)}.

**Lemma.** Let T be a finite list of triples (c_t, A_t, B_t) with real coefficients c_t, and suppose the identity

    sum over t of c_t * sum over sigma in S_n of Phi_{A_t,B_t}(sigma x)  =  max(x_1, ..., x_n)      for all x in R^n

holds. Then the function x -> max(x_1, ..., x_n) is computed exactly by a feed-forward network with exactly two hidden layers of ReLU units, affine (biased) pre-activations, an affine output unit, no skip connections, and finite widths. If all c_t are rational, all weights and biases can be taken rational.

The verifier-certified content of the n = 11 certificate is precisely the displayed identity (the pinned upstream verifier checks it on the sorted cone in a normal form; both sides are symmetric functions, and a symmetric function is determined by its values on the sorted cone, so the identity holds on all of R^n). This lemma is the only step between that identity and the sentence "MAX_11 is in ReLU_2".

## Proof

Two elementary facts are used throughout.

(F1) For reals u, v: max(u, v) = (u + v)/2 + (ReLU(u - v) + ReLU(v - u))/2, since ReLU(w) + ReLU(-w) = |w| and max(u, v) = (u + v)/2 + |u - v|/2.

(F2) For any real w: w = ReLU(w) - ReLU(-w). Hence any affine function of the outputs of one layer can be passed unchanged through the next ReLU layer using two units, so no skip connections are needed.

**Hidden layer 1.** For every ordered pair (i, j) with i != j put two units ReLU(x_i - x_j) and ReLU(x_j - x_i) (these are the same pair of units for (i, j) and (j, i); n(n-1) units in total), and for every k in [n] put the two units ReLU(x_k) and ReLU(-x_k) (2n units). All pre-activations are linear in x. For a loop (k, k) the summand max(x_k, x_k) = x_k needs no extra unit.

By (F1) and (F2), for every multiset E and every permutation sigma, the function x -> f_E(sigma x) is an affine combination of layer-1 outputs:

    f_E(sigma x) = sum over (i,j) in E of [ (x_{sigma(i)} + x_{sigma(j)})/2 + (ReLU(x_{sigma(i)} - x_{sigma(j)}) + ReLU(x_{sigma(j)} - x_{sigma(i)}))/2 ],

where each x_k is realized as ReLU(x_k) - ReLU(-x_k). Call this affine map L_{E,sigma} (a fixed linear form in the layer-1 outputs; there is no bias).

**Hidden layer 2.** For every t and every sigma in S_n put the two units

    ReLU( L_{A_t,sigma} - L_{B_t,sigma} )   and   ReLU( L_{B_t,sigma} - L_{A_t,sigma} ),

and for every t and sigma also the two pass-through units ReLU( L_{A_t,sigma} + L_{B_t,sigma} ) and ReLU( -(L_{A_t,sigma} + L_{B_t,sigma}) ). All pre-activations are linear in the layer-1 outputs.

By (F1) applied to u = f_{A_t}(sigma x), v = f_{B_t}(sigma x) and by (F2) for the pass-through pair,

    Phi_{A_t,B_t}(sigma x) = (1/2) [ ReLU(L_A+L_B) - ReLU(-(L_A+L_B)) ] + (1/2) [ ReLU(L_A - L_B) + ReLU(L_B - L_A) ]     (with A = A_t, B = B_t, evaluated at sigma),

which is a linear combination of layer-2 outputs.

**Output.** The output unit computes sum over t of c_t * sum over sigma of Phi_{A_t,B_t}(sigma x) as the corresponding linear combination of layer-2 outputs, with zero bias. By hypothesis this equals max(x_1, ..., x_n) for all x.

The network has exactly two hidden ReLU layers, widths n(n-1) + 2n and 4 * |T| * n!, all weights in {0, +-1, +-1/2} except the output weights c_t/2 and -c_t/2, and no skip connections. If the c_t are rational so are all parameters. QED.

## Remarks (not part of the claim)

- Widths are not minimal and are not claimed to be; the certificate at n = 11 has |T| = 15,896 terms and the construction above would use 4 * 15,896 * 11! layer-2 units. Symmetry can reduce this enormously (one may symmetrize over the stabilizer of each term's active vertex set instead of all of S_n), but no such reduction is claimed here.
- The reduction is the standard one used by the upstream authors for n <= 10 (Rueß et al., arXiv:2607.21651) and is textbook; it is written out because the campaign's ledger requires that every step between a verified artifact and a stated claim be recorded and reviewed.
- Nothing here bears on n >= 12 or on any lower bound.
