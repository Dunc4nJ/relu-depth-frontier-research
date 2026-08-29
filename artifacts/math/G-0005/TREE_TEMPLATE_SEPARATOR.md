# A four-point separator for balanced two-coloured tree templates

Status: **independently re-derived and exhaustively audited PASS (bounded)**
Scope: an exact obstruction for one natural subfamily of the pair-atom ansatz; not a MAX11
lower bound for unrestricted two-hidden-layer ReLU networks and not an obstruction to the full
pair-atom ansatz.

## Theorem

Let `n >= 5` be odd and put `k = (n - 1) / 2`.  Let `T` be a simple spanning tree on
`V = {1,...,n}` whose edges are partitioned into two colour classes `A` and `B`, with
`|A| = |B| = k`.  Define

\[
 \Phi_{A,B}(x)=\max\!\left\{
   \sum_{ij\in A}\max(x_i,x_j),
   \sum_{ij\in B}\max(x_i,x_j)
 \right\}
\]

and its unnormalised symmetrisation

\[
 F_{A,B}(x)=\sum_{\sigma\in S_n}\Phi_{A,B}(\sigma x).
\]

Consider the four sorted points

\[
\begin{aligned}
 z&=(0,0,1,1,2^{n-4}),\\
 u&=(0^4,2^{n-4}),\\
 v&=(0^3,2^{n-3}),\\
 w&=(0^2,2^{n-2}),
\end{aligned}
\]

where exponents denote repetition.  Set

\[
\begin{aligned}
 C_z&=12n(n-2)(n-3),\\
 C_u&=-5n(n-2)(n-3),\\
 C_v&=-4n(n-4)(n-2),\\
 C_w&=-(n-3)(3n^2-2n+4).
\end{aligned}
\]

Then every such tree block satisfies

\[
 C_zF_{A,B}(z)+C_uF_{A,B}(u)+C_vF_{A,B}(v)+C_wF_{A,B}(w)=0. \tag{1}
\]

But

\[
 C_z+C_u+C_v+C_w=12,
\]

so the same functional evaluates to `24` on `MAX_n`, because `MAX_n` equals `2` at all four
points.  Consequently, no finite signed linear combination of symmetrised balanced two-coloured
spanning-tree blocks can equal `MAX_n`.

For `n=11`, division by the common factor `12` gives the particularly small separator

\[
 792F(z)-330F(u)-231F(v)-230F(w)=0,
\]

while the left-hand side is `2` for `MAX_11`.

## Proof

For an assignment `c : V -> {0,1,2}`, write

\[
 \phi(c)=\max\!\left\{
   \sum_{ij\in A}\max(c_i,c_j),
   \sum_{ij\in B}\max(c_i,c_j)
 \right\}.
\]

Let `S_{m,h}` be the sum of `phi(c)` over assignments with exactly `m` vertices labelled `1`
and `h` vertices labelled `2`.  Each such assignment occurs
`(n-m-h)! m! h!` times in the permutation sum, hence

\[
 F_{A,B}(x_{m,h})=(n-m-h)!m!h!\,S_{m,h}. \tag{2}
\]

For a vertex set `R`, let `e_A(R)` and `e_B(R)` be the numbers of edges of the two colours
induced by `R`, and define

\[
 A_r=\sum_{|R|=r}\min\{e_A(R),e_B(R)\}.
\]

If an assignment has only zeroes and twos and its zero set is `R`, then a colour-`C` edge
contributes zero exactly when both endpoints lie in `R`.  Therefore

\[
 S_{0,n-r}=2\left(k\binom nr-A_r\right). \tag{3}
\]

Because `T` is simple and the colour classes are disjoint, `A_2=0`.  Let `P` be the number of
adjacent cross-colour edge pairs.  A three-vertex induced forest contains both colours exactly
when it is a two-edge path with one edge of each colour, so

\[
 A_3=P. \tag{4}
\]

Now consider an assignment counted by `S_{2,n-4}`.  Let `R` be its four non-`2` vertices and
let `L` be its two zero vertices; the two vertices in `R-L` carry value `1`.  The colour-`C` side
has value

\[
 2k-e_C(R)-e_C(L).
\]

Thus, with

\[
 B_4=\sum_{|R|=4}\sum_{\substack{L\subset R\\|L|=2}}
 \min\{e_A(R)+e_A(L),e_B(R)+e_B(L)\},
\]

we have

\[
 S_{2,n-4}=12k\binom n4-B_4. \tag{5}
\]

It remains to evaluate `B_4`.  Since `T[R]` is a forest on four vertices, it has at most three
edges.  If its colour counts are `(1,1)`, its six choices of `L` contribute `6` in total to
`B_4`; if they are `(1,2)` or `(2,1)`, they contribute `7`; if either colour count is zero, they
contribute zero.  Let `N_11` and `N_12` count the first and second cases.  Then

\[
 A_4=N_{11}+N_{12},\qquad B_4=6N_{11}+7N_{12}. \tag{6}
\]

Count incidences between a cross-colour edge pair and a four-vertex set containing all of its
endpoints.  There are `k^2` cross-colour pairs.  Each of the `P` adjacent pairs has three vertices
and lies in `n-3` four-sets; every disjoint pair determines one four-set.  Hence the incidence
count is

\[
 (n-3)P+(k^2-P)=k^2+(n-4)P.
\]

On the other hand, a four-set of type `(1,1)` contributes one incidence and a set of type
`(1,2)` or `(2,1)` contributes two.  Therefore

\[
 N_{11}+2N_{12}=k^2+(n-4)P. \tag{7}
\]

Combining (4), (6), and (7) yields

\[
 B_4=5A_4+k^2+(n-4)A_3. \tag{8}
\]

Substitute (3), (5), and (8), with `k=(n-1)/2`, into

\[
\begin{aligned}
 &24nS_{2,n-4}-60nS_{0,n-4}-12n(n-4)S_{0,n-3}\\
 &\hspace{45mm}-(n-3)(3n^2-2n+4)S_{0,n-2}.
\end{aligned} \tag{9}
\]

The `A_4` coefficients are `-120n+120n=0`, the `A_3` coefficients are
`-24n(n-4)+24n(n-4)=0`, and the remaining binomial expression is zero.  Thus (9) vanishes.

Finally, use the four multiplicities in (2):

\[
 2!2!(n-4)!,\quad 4!(n-4)!,\quad 3!(n-3)!,\quad 2!(n-2)!.
\]

After multiplication by the common factor `2(n-2)!`, equation (9) becomes exactly (1).
Direct expansion gives `C_z+C_u+C_v+C_w=12`, completing the separation from `MAX_n`.

## Consequence for the MAX11 search

The dominant full-vertex terms in the known MAX9 and MAX10 certificates are minimally cyclic
forests.  The most obvious `n=10 -> 11` lift joins the two components of a MAX10 forest through
the new vertex with one edge of each colour, producing precisely a balanced two-coloured spanning
tree.  The theorem rules out not only the 9,200 raw templates produced by that lift, but the span
of **all** balanced two-coloured spanning-tree templates.

Therefore a successful `k=5` pair-atom certificate for MAX11 must use some template outside this
subfamily—for example a cycle, a disconnected union graph, a loop, a repeated edge, or overlap
between the two colour multisets.  This is a disjunction, not a claim that every listed feature is
individually necessary.

## Evidence boundary

- The proof is exact and uses no numerical sampling.
- `check_tree_separator.py` independently evaluates the four permutation orbits on exhaustive
  labelled `n=5` trees, deterministic random trees at `n=7,9,11`, and a non-tree negative control.
- `ADVERSARIAL_AUDIT.md` records an independent derivation, exhaustive checks over every
  unlabelled tree shape and balanced colouring through `n=11`, and explicit outside-family
  counterexamples.
- The dated novelty verdict is only `NO_PRIOR_FOUND`; it is not proof of novelty or priority.
