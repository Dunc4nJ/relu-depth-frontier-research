# G-0085 — RANGE11 defeats projected-facet reconstruction

## Result

Let `U=[n]` and define

\[
R_n(x)=\sum_{\varnothing\ne S\subsetneq U}
(-1)^{|S|+1}\max_{k\in U\setminus S}x_k.
\]

Then, for every `n>=2`,

\[
R_n(x)=\max_i x_i+(-1)^n\min_i x_i.                 \tag{1}
\]

In particular,

\[
R_{11}(x)=\max_i x_i-\min_i x_i.                    \tag{2}
\]

Every maximum on the left side of (1) has arity between one and `n-1`.
Consequently, conditional on the retrieved exact two-hidden-layer
representations of `MAX_k` for `k<=10`, `R_11` has an exact finite
two-hidden-layer representation: embed the smaller networks by coordinate
selection, stack their first layers, take the block-diagonal union of their
second layers, and form the alternating signed sum in the affine output.

This function is an exact counterexample to the proposed implication

> eleven independently translation-normalized MAX10 exposed-face shapes
> determine the global centered MAX11 virtual polytope.

It is not a counterexample to the MAX11 representability conjecture.

## Proof of the alternating identity

Order the coordinates as

\[
x_{(1)}\le\cdots\le x_{(n)}.
\]

Assign each subset maximum in (1) to its highest-ranked surviving coordinate.
The coefficient of `x_(j)` is

\[
c_j=\sum_{t=1}^{\min(j,n-1)}
(-1)^{n-t+1}\binom{j-1}{t-1}.                         \tag{3}
\]

The alternating binomial identity gives

\[
c_1=(-1)^n,\qquad c_j=0\ (1<j<n),\qquad c_n=1,
\]

which proves (1), including ties by continuity.  The parity is essential:
even `n` gives `max+min`, while odd `n` gives `max-min`.

## Exact projected-face collision

Work in

\[
H=\{z\in\mathbb R^{11}:\sum_i z_i=0\},\qquad
\mu=\tfrac1{11}{\bf1},\qquad a_i=e_i-\mu,
\]

and put

\[
\Delta^0=\operatorname{conv}\{a_i:i\in[11]\},
\qquad u_i=\mu-e_i=-a_i.
\]

Here `-Delta^0` means geometric reflection, not the additive inverse in the
Grothendieck group.  The centered support functions are

\[
h_{\Delta^0}(x)=\max x-\bar x,
\qquad
h_{-\Delta^0}(x)=\bar x-\min x.
\]

Thus the centered polytope for (2) is the difference body

\[
D=\Delta^0+(-\Delta^0).                                \tag{4}
\]

At the normal `u_i`,

\[
F_{u_i}(\Delta^0)=\operatorname{conv}\{a_k:k\ne i\},
\qquad
F_{u_i}(-\Delta^0)=\{u_i\},
\]

and therefore

\[
F_{u_i}(D)=F_{u_i}(\Delta^0)+u_i.                       \tag{5}
\]

The support heights differ:

\[
\|u_i\|^2=\frac{10}{11},\qquad
h_{\Delta^0}(u_i)=\frac1{11},\qquad h_D(u_i)=1.         \tag{6}
\]

However, let `Pi_i` be orthogonal projection to `u_i^perp`.  Equation (6)
gives

\[
\Pi_i(F_{u_i}(D))
=F_{u_i}(\Delta^0)+u_i-\frac{11}{10}u_i
=\Pi_i(F_{u_i}(\Delta^0)).                              \tag{7}
\]

The projected vertices have coordinate `i=0` and the remaining coordinates
`delta_kj-1/10`: exactly the centered MAX10 simplex, with no scale error.
Hence all eleven projected target faces collide even though `D!=Delta^0`.

The collision survives the stronger demand that the local certificates come
from one global two-hidden-layer network: `R_11` itself is that global network.
What fails is precisely the information discarded by independent normal
translation/projection.

## Small exact discriminators

Support height already separates the two objects by (6).  Globally, the
difference body has a facet for every nontrivial two-level partition,

\[
2^{11}-2=2046,
\]

whereas the simplex has eleven facets.  At `x=e_p-e_q`, the centered MAX11
value is one and the range value is two.  Equivalently, in a unique-maximum
cone, a tie among the minimum coordinates creates a RANGE11 wall while MAX11
remains affine.

If raw translation covariance is required, use

\[
\widetilde R_{11}(x)=\bar x+\max x-\min x.
\]

It obeys `Rtilde(x+t*1)=Rtilde(x)+t`, retains the same centered polytope and
projected-face collision, and is still not MAX11.

## Consequence for G-0064

The G-0064 necessary exposed-face theorem remains valid.  What is refuted is
only a sufficiency step based on the eleven independently normalized face
shapes.  A viable unrestricted bridge must retain at least one of:

1. facet support heights or selected endpoint translations;
2. additional normal directions;
3. the complete global wall/normal-fan data;
4. exact affineness throughout every unique-maximum cone.

The mandatory negative control for any replacement criterion is that it must
reject `R_11` (or `Rtilde_11`) while accepting the simplex.

## Epistemic boundary

- The alternating identity and face calculation received a fresh-context
  same-family T1 hostile review.
- Same-depth representability depends on the retrieved MAX1--MAX10
  construction claim `C-0003@1`; those certificates are not independently
  replayed here.
- No novelty or priority claim is made.  Inclusion-exclusion identities for
  order statistics are classical territory, and a dated novelty search has
  not yet been run for this exact use.
- This result neither constructs MAX11 nor proves it impossible.

## Falsifiers

The result fails if (3) has another nonzero interior coefficient, one
complement has arity eleven, same-depth parallel composition adds a hidden
layer, (5)--(7) contain a sign or scaling error, or the G-0064 normalization
retains support height rather than projecting it away.  The hostile review
attacked each of these points and found no failure.
