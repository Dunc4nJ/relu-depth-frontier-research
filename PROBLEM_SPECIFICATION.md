# PROBLEM SPECIFICATION — relu-depth-frontier-research

## Definitions

- `ReLU(t) = max(t,0)`, coordinatewise on vectors.
- A network with **exactly two hidden ReLU layers** has the form `x -> W1 x+b1 -> ReLU -> W2 h1+b2 -> ReLU -> a^T h2+c`. The output layer is affine and not counted as hidden. Skip connections, max gates, and other activations are absent from the target architecture unless eliminated by an exact audited conversion.
- All widths are finite positive integers but otherwise unrestricted and may depend on `n`.
- All parameters are arbitrary real numbers. A rational witness is a sufficient special case; rational impossibility is not real impossibility.
- `MAX_n : R^n -> R` is `MAX_n(x)=max{x1,...,xn}`.
- **Exact/global** means equality for every real input, not approximation and not equality on a test set, cube, Boolean domain, or almost everywhere.

## The statement, exactly

`forall n in N, n >= 1, exists m1,m2 in N_{>0}, W1,b1,W2,b2,a,c over R, forall x in R^n`, the two-hidden-layer formula in the charter equals `MAX_n(x)`.

The first bounded claim is the same statement with `n=11`. Settling that instance is the next frontier rung, not the universal theorem.

## Cousin register

| Cousin | Why it is not the target | Invalid inference to refuse |
|---|---|---|
| Approximation on a compact set or in Lp | relaxes exact global equality | “small error implies exact representability” |
| Equality on `{0,1}^n`, a finite sample, or one cone | changes the domain | “passed all sampled points, so the functions are equal” |
| One hidden layer | different depth class | “a one-layer lower bound applies unchanged to two layers” |
| Three or more hidden layers | deeper architecture | “a deeper construction is a shallow construction” |
| Fixed/polynomial/factorial width | adds a width constraint | “no narrow network means no finite-width network” |
| Integer, rational, decimal, or bounded-bit weights | strict parameter subclass | “a subclass lower bound holds for arbitrary reals” |
| Pairwise-comparison first layer | structural ansatz used by current certificates | “ansatz UNSAT refutes all two-layer networks” |
| Permutation-symmetric/orbit-reduced coefficients | symmetry restriction or quotient | “no symmetric witness means no witness” |
| Maxout/max gates | stronger primitive unless exactly compiled | “one maxout layer is one ReLU layer” |
| General CPWL representation | related through a decomposition theorem with hypotheses | “MAX11 alone settles every CPWL function in every dimension” |
| Trainability/sample complexity/generalization | optimization/statistical questions | “expressive existence gives an efficient learning algorithm” |

## Frontier anchors and barriers

- Exact two-hidden-layer witnesses are known through `n=10`; any claimed unrestricted obstruction at `n<=10` is presumptively an encoding or convention failure.
- One-hidden-layer insufficiency and lower bounds for integer/rational/restricted architectures do not transport automatically to unrestricted real weights.
- The current constructive method uses exact linear algebra, pairwise comparisons, symmetry, and large certificate systems. Its scale bottleneck is evidence about that route, not a theorem about all networks.
- The CPWL bridge uses generalized hinging-hyperplane representation; its precise arity/dimension hypotheses must be cited and audited.
- Isolated MAX11 success is scientifically meaningful but the terminal target requires a scalable mechanism or proof for all `n`.

Source anchors are assigned `REF-####` identifiers in `literature/bibliography.bib` and source cards; this section never substitutes for those exact locators.

## Escalation tripwires

| Condition | Consequence |
|---|---|
| A method rules out a known `n<=10` certificate | freeze; audit statement, architecture conversion, and encoding before any interpretation |
| A candidate is supported only by floating residuals | label discovery-only; exact reconstruction required |
| A solver returns UNSAT for a restricted ansatz | record a bounded null naming every restriction; never call it a depth lower bound |
| A proof step uses rational/integer structure against arbitrary reals | cousin trap fired; transport lemma required |
| A paper/preprint explicitly settles MAX11 or all `n` | freeze novelty language; retrieve, hash, statement-match, and redirect to independent verification |
| A universal construction lacks explicit finite widths/parameters or an existence proof | remains a heuristic route, not a witness |
| A CPWL conclusion changes `d`, affine arity, depth counting, or skip conventions | statement-match review required before citation use |
| A T2+ promotion is attempted with only GPT-5-family reviewers | typed refusal; cross-family bar is unmet |
