# Red-team review of the MAX_11 draft assessment

Everything below is checked or re-run. One of my own attacks (now #7) failed on the numbers and is retracted in place.

**New measurement.** I finished the n=10 loop-free probe (`probe10p.log`): 12,248 templates, 16,709 hinge rows, **rank(A) = rank([A|b]) = 2166, MEMBER, nullity 10,082** at p = 1000003. I also confirmed n=9 at a second prime (`probe9_p2.log`, rank 1506, MEMBER at p = 1000033).

## Objections, most severe first

### 1. The flagship experiment is a strict sub-case of a family the campaign already enumerated and already has a Rust oracle for

**Claim attacked.** "The campaign never enumerated or tested the complete loop-free family (462,627 templates / 754,017 loopless signed-W orbits)."

**Why it is wrong.** `artifacts/math/G-0027/README.md` is titled "exhaustive loopless signed degree-five function universe" and reports a completed nauty census of exactly **754,017 signed-graph classes**, with a cancelled-mass table (s=5: 735,732) and a topology table (β=0 trees: 12,459), frozen under SHA-256 `8cbb6a9f...`. `artifacts/math/G-0028/README.md` reports a Rust producer that **priced all 754,017 records at two primes in 1,201.017 s, 627.8 records/s**. The family was enumerated and swept. What was never done is a target-aware solve, registered as open gap `G-0014`.

The draft's family is also smaller and redundant. `enumerate_signed_loopless.py` enumerates signed **multi**graphs; a pair of 5-edge simple graphs gives W = B − A with entries only in {−1,0,+1}. So the 462,627 templates surject onto the ±1-multiplicity subset of the 754,017 classes: at least 291,390 classes are unreachable, and the 462,627 columns carry at most 462,627 distinct functions, almost certainly far fewer. A negative there is another subfamily null, the exact failure mode the draft condemns in the prior campaign, on a matrix the G-0027 quotient would have shrunk for free.

**Corrected statement.** "G-0027 enumerated and G-0028 priced the complete loopless degree-five universe against one rank-one dual; no target-aware solve has run on it (gap G-0014). The right experiment is that solve on the frozen 754,017-class universe plus the 5E/5L carriers, reusing the existing pricer."

### 2. The memory model is off by an order of magnitude, and "with care" hides the entire method

**Claim attacked.** "Feasible on 16 cores/62GB with care."

Take the draft's own shape: 100k sampled rows by 462,627 columns. As a dense flint `nmod_mat` at 8 bytes per entry that is **370 GB**, and 185 GB even at 4 bytes. It does not fit, and no amount of care makes a dense matrix of that shape fit in 62 GB.

The method that does fit is not stated in the draft: stream columns against a row-echelon basis of at most rank-many vectors. At a rank near 35,000 and 100k-long rows that basis is 28 GB, which fits. My n=10 run gives the throughput anchor the draft lacks: rank on a 16,719 x 12,249 matrix took 199.8 s, about 2.2e9 entry-operations per second. Streaming 462,627 columns against a 35k-pivot basis of length 100k is ~1.6e15 operations, so roughly 8 days on one core and perhaps 13 hours on sixteen if the axpy loop is blocked and vectorised. That is a real plan; the draft's sentence is not one yet.

**Corrected statement.** Name the algorithm as streaming echelon reduction with a rank-sized basis, state the 28 GB working set, and make the schedule conditional on a measured axpy rate.

### 3. A ten-fold error in the number that motivates the whole path

**Claim attacked.** "the 163,740 family is 2.2% of the loopless universe."

163,740/754,017 = **21.7%**. 163,740/7,015,841 = 2.33%. The draft divided by the *loop-inclusive* denominator and labelled it loopless. The frozen family already covers about a fifth of the loopless universe, not a fortieth, which materially shrinks the claimed headroom and weakens the case for the new build.

### 4. The one-prime double standard

The draft discounts a campaign negative as "one prime" while presenting its own one-prime positive as settled. Mod-p consistency does not imply consistency over Q: rank_p ≤ rank_Q, so a prime can collapse a genuine inconsistency.

I re-ran n=5,6,7,8 at p = 1000003, 1000033, 999983: ranks 8, 13, 90, 140, MEMBER at every prime, reproducing the draft exactly. n=9's 1506 came from one line at one prime, so I ran a second and it holds. The results survive; the draft asserted them before the check existed.

**Corrected statement.** "Consistent mod three primes for n ≤ 8, two primes for n = 9, one prime for n = 10. No rational witness at any n." The draft's "MAX11 witness (settles the rung)" outcome silently needs an exact-Q lift on a support of unknown size; the n=10 upstream witness has lcm denominator 304,819,200 over 402 terms, and a lift on a 30k support is a separate problem the two-week budget does not contain.

### 5. "No real-weight lower bound beyond one hidden layer exists for any CPWL function" is false as written

Safran (2601.01417, COLT 2026) gives width lower bounds at two hidden layers that are unconditional in the weight field; the lower-bound reviewer derives ≥25 first-layer neurons with 3-covering supports for MAX_11. Grillo, Hertrich and Loho (2502.09324) Theorem 5.2 states M²_Bd(2) = V_Bd(4), so no braid-conforming two-hidden-layer ReLU net computes max{0,x_1,...,x_4}.

**Corrected statement.** "No unconditional real-weight *depth* lower bound beyond one hidden layer is known. Real-weight *width* bounds at depth two, and fan-conditional depth bounds, do exist."

Related correction for the lower-bound reviewer: that report calls Theorem 5.2 "a genuine ... lower bound at exactly the campaign's target". The threshold is 4, so the same theorem excludes max of five numbers, which is representable. It cannot discriminate n=10 from n=11.

### 6. "Loops were never needed at any new-k arity (5,7,9)" conflates two statements

I ran `cert_stats.py` over the upstream certificates. The n=5 certificate has loops in 2 of 3 terms; **n=7 has at least one loop on side A in all 57 terms**; n=8 in 44 of 69. Only n=9 and n=10 are loop-free, `{(0,0): 337}` and `{(0,0): 402}`. Loops were used at new-k arities 5 and 7. The probe shows only the weaker "a loop-free span still contains MAX_n there".

The same run surfaces a sharper fact the draft under-uses: at n=9 and n=10 every certificate term has **both sides forests with dim Z_A = dim Z_B = k**. In W language that is the β=0 stratum, only **12,459** orbits at s=5 per G-0027, a 60x cheaper first experiment than 462,627.

### 7. Retracted: the rank extrapolation is sound, and I now have the missing anchor

I attacked "guess 11: 20k–60k" on the grounds that rank as a fraction of rows sat at 24% through n=9, which against the 657,822 rows of the campaign's import audit would put n=11 near 158,000 and above the proposed 100k sample. My n=10 run refutes that. The fraction is falling, not flat: 80%, 62%, 43%, 25%, 23.8%, **13.0%**. The stable statistic is the arity-jump ratio rank(n)/rank(n−2) = 11.25, 10.77, 16.73, 15.47, which puts n=11 near 30,000–38,000. **The draft's 20k–60k is well supported and its 100k row sample is roughly 3x the expected rank.** What remains is presentational: the draft reported one extrapolation without the check, and gives no bound on CEGIS iterations, so a solution on sampled rows is still not a certificate until the verify-and-add loop closes.

### 8. The universe counts are used interchangeably

12,179,657 (raw Rueß template orbits), 7,015,841 (loop-inclusive signed-W classes), 754,017 (loopless signed-W), 462,627 (simple-edge-set pairs) are four different quotients. The draft pairs the last two as if they count one set and switches denominators between paragraphs. I reproduced 12,179,657 and 462,627 with `count_simple_pairs.py`, and the whole loop-inclusive column of the campaign's import-audit table matches exactly, so the draft's finding (2) is verified.

### 9. P0 is not decomposed

70% in ReLU_2 with 50% in the loop-free span forces P(in ReLU_2 | not in that span) = 40%. Nothing in the draft names a mechanism by which MAX_11 fails to be in ReLU_2, and the refute track is priced at ≤3%. The 5–10 point gap between loop-free and loop-inclusive is unargued and cuts against the objection-6 evidence that loops are genuinely used at new-k arities.

### 10. Process points, confirmed with two corrections

`./skill-runtime verify-quick` is red on exactly one finding, **SE-10** on `ledger/gaps.toml` G-0015, contradicted by commit `7cf9d50deb61`. But STATUS.md claims "48 current claims" while the walker enumerates through C-0053, so the staleness is worse than reported. Check the proposed literature additions against `literature/bibliography.bib`, which already carries fifteen REF entries including Safran 2601.01417 and Grillo 2502.09324.

## Three paths the draft does not list

**A. Extrapolate the certificate instead of deciding the family.** The n=9 and n=10 witnesses use 337 and 402 terms out of 10,976 and 12,248 columns, about 3%. Both are entirely loop-free, both have every term with two rank-k forest sides, both have coefficient denominators supported on primes ≤ 7. That is a strong shape prior: the n=11 witness is plausibly a few hundred terms with denominators over {2,3,5,7,11}. Mechanism: assemble ~200k candidates from the S_11 edge-lift of the 402 n=10 templates, which is how G-0113 built its 163,740, plus the 12,459 β=0 tree orbits, then search for a *small-support* solution by greedy or L1-guided selection over the mod-p solution set rather than by full-rank elimination. A 500-column exact-Q solve is trivial, so the hard part becomes candidate selection, which is search, not linear algebra. This is the only route that delivers the exact witness the "settles the rung" outcome actually requires, and it costs hours.

**B. Find the invariant that collapses the columns.** My two new runs sharpen this: at n=9 the 10,976 columns span 1,506 dimensions and at n=10 the 12,248 span **2,166**, leaving nullities of 9,470 and 10,082. G-0027's common-edge cancellation explains one collapse but nowhere near that. Mechanism: compute those relations exactly at n=7 and n=8, where the nullities are 267 and 290 and the systems are seconds of work, identify their combinatorial support, and test whether they are generated by local moves on W such as edge swaps or degree-preserving rewirings. If so, the n=11 family collapses from 754,017 to O(rank) generators and the decision becomes a small exact solve. This is the only proposal here that changes the asymptotics rather than the constant.

**C. Column generation, not row CEGIS.** Keep a small row set, solve the restricted primal, take the dual functional, and price all 754,017 loopless records with the existing G-0028 Rust oracle to find the most violated column; add it and repeat. One full pricing pass takes about 20 minutes at the measured 627.8 records/s. The matrix is never materialised, memory stays bounded by the restricted basis, and each round yields either a new column or a complete zero census, which is exactly the separator certificate the negative branch needs. This is the strategy the campaign's own import audit recommended, and it inverts the draft's plan, which grows rows against a fixed column set.
