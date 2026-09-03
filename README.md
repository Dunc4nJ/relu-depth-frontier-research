# Exact shallow-ReLU frontier campaign — MAX_11 in two hidden layers

This repository is the complete, Git-backed record of an autonomous research campaign that
computed and independently verified an exact certificate for a frontier statement in neural
network expressivity:

> **The maximum of 11 real numbers is computed exactly by a ReLU network with two hidden layers and real weights.**

Two explicit certificates were found, lifted to exact rational arithmetic, translated into the
community's certificate format, and verified by two independent implementations from two
different model lineages, a method-disjoint falsifier, and planted-negative controls at every
stage. The whole campaign, from an empty preregistration to a refereed certificate, ran in
about fourteen hours of wall-clock time under the
`/frontier-research-with-epistemic-humility` protocol, with a swarm of AI workers and about
seventy dollars of rented GPU time.

The campaign's terminal target is the universal statement (every `n`), which remains open.
What follows is what was established, how, and what is outstanding.

---

## The result

| Certificate | Terms | Shape | Files |
|---|---|---|---|
| run7 (dense) | 15,896 | loop-free 5-edge branches, all pivot columns of stage A | `artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json` (SHA-256 `8bd2270a…`) |
| F2 (forest pairs) | 11,320 | every term is a pair of forests, as in the known `n = 9, 10` certificates | `artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json` (SHA-256 `767f9e66…`) |

Each certificate is a finite list of terms `(c_t, A_t, B_t)` with rational coefficients and two
5-edge multigraphs on 11 vertices, such that

```
sum_t  c_t · sum_{σ ∈ S_11}  max( f_{A_t}(σx), f_{B_t}(σx) )  =  max(x_1, …, x_11)   for all x ∈ R^11,
```

where `f_E(x) = Σ_{(i,j) ∈ E} max(x_i, x_j)`. Every atom on the left is a two-hidden-layer
ReLU network, so the identity is a two-hidden-layer representation of the maximum. The step
from the identity to the network is written out and refereed in
`artifacts/math/n11-ledger-recording/DEPTH2_REALIZATION_LEMMA.md`.

**Verify it yourself** (Rust toolchain; about 45 minutes at 4 threads for the dense certificate,
25 minutes for the forest-pair one):

```bash
cd tools/verify11 && cargo build --release --locked
target/release/max11-verify11 verify \
  --certificate ../../artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json \
  --threads 4 --output f2-report.json
# exit status 0 and VERIFY11_OK terms=11320/11320 means the identity holds exactly

# method-disjoint falsifier (exact counting on {0,1}^11 ∪ {0,1,2}^11, about 3 minutes)
.venv/bin/python tools/t2-referee/lattice_check.py \
  artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json --profiles both
```

Referee reports, with every hash, command, and residual doubt: `artifacts/math/t2-review/`.

---

## How the certificate was found

The search space is the "pairwise-max atom" ansatz: symmetrized functions
`max(f_A, f_B)` for pairs of 5-edge graphs. After quotienting by the symmetric group and
cancelling common edges, the loop-free family at `n = 11` has **754,017** orbits. Restricted to
the sorted cone `x_1 ≥ … ≥ x_11`, every atom is a piecewise-linear function encoded exactly by a
linear part plus hinge coefficients over primitive ambiguous directions, and `MAX_11` is the
single linear coordinate `x_1`. Finding a certificate is deciding whether one vector lies in the
span of 754,017 exact integer columns with hundreds of thousands of rows, and then recovering
rational coefficients.

The pipeline built for this, all in `tools/`:

1. **Exact column generation** (`tools/colgen`, Rust). Emits the exact sorted-cone column of any
   orbit; validated by reproducing every saved `n = 9, 10` column and the known certificates.
2. **Sketched streaming rank on GPU** (`tools/streamrank`, Rust + CUDA). Two independent ±1
   CountSketch hashes into 64,000–128,000 buckets, exact fp64 accumulation of modular products
   (the FFLAS trick), rank tracked incrementally modulo two large primes. A false MEMBER has
   probability about `1/p` per sketch; a false NON_MEMBER is impossible. Stage A (120,948
   columns) returned **MEMBER at rank 21,222 in 29 minutes**, identically on four modular arms.
   The full 754,017-column universe was ranked in 2.8 hours (rank 41,856).
3. **Exact rational lift** (`tools/exactlift`). Dense modular LU on the sketched pivot minor,
   Dixon p-adic lifting, rational reconstruction, then verification of the solution on **every**
   exact row (190,483 rows for run7, 162,091 for F2), with a planted +1 mutation shown to break
   tens of thousands of rows. The "insurance" run, budgeted for 40,000 lifting steps, reconstructed
   the full solution at step 2,000.
4. **Translation** to the community certificate format, re-derived byte-for-byte by a referee
   from the universe and the witness without the translation code.
5. **Sparse-witness descent.** Nested, certificate-shaped sub-families (forest pairs; full
   support) were ranked concurrently; the forest-pair family was MEMBER and produced the
   11,320-term certificate, whose reconstruction needed only 1,600-bit heights.

Every experiment was **preregistered** on its tracking bead before it ran: primes, seeds, bucket
counts, abort gates, the verdict rule, and a no-claim line. Amendments were recorded as dated
deviations, never silent edits.

---

## How it was verified

The protocol requires that standing be computed from artifacts and independent checks, never
asserted. The verification stack for each certificate:

- **T1 — campaign verifier.** `tools/verify11`, a Rust implementation of the community
  verifier's exact sorted-cone semantics (dynamic program over vertex placements; exact big-integer
  accumulation). Output: OK, zero bad rows across 11 linear and 169,166 hinge rows (run7),
  145,530 (F2). A 20-term sample was additionally checked by literal enumeration of all
  39,916,800 permutations per term, agreeing with the DP 20/20.
- **T2 — different-lineage referee.** A fresh-context referee from a different model family than
  the authors rebuilt the verifier from committed source (bit-identical binary), ran it in strict
  mode, re-derived the entire certificate file from the universe and witness with its own code
  (byte-identical), recomputed the whole identity with an independent Python implementation
  validated column-for-column against the reference on 373 columns, and predicted the residuals of
  a planted negative before running it. Verdict: PASS on both certificates, twice (before and after
  a verifier patch it requested).
- **Method-disjoint falsifier.** `tools/t2-referee/lattice_check.py` shares no method with the
  DP: it checks the identity exactly on all 179,195 symmetric lattice points of
  `{0,1}^11 ∪ {0,1,2}^11` by counting injective vertex placements. Built against the reference
  verifier, it passes all six known certificates, fails every mutant, and proved that the 0/1 cube
  alone would not be a sufficient falsifier.
- **Planted negatives everywhere.** Every rank run, lift, verifier run, and audit carried a
  control that had to fail, and did.
- **The realization lemma.** The step from the certified identity to a two-hidden-layer network
  was written as a lemma and refereed twice (one same-lineage, one different-lineage review; the
  first review caught a false sentence about weight magnitudes, which was corrected and re-refereed).

The ledger under `ledger/` records every trial, including six aborted lifts, a crashed arm, and
an out-of-memory run, with the standing of each claim computed by the workspace's verifier rather
than written by hand.

---

## What the campaign proved about the protocol

This repository is also a demonstration that `/frontier-research-with-epistemic-humility`
works as an operating system for autonomous research, not just as a checklist:

- **Preregistration held.** Four modular arms, two primes, two sketches: the verdict rule was
  fixed before the first column was generated, and every deviation is dated and reviewed.
- **Independence was real, not nominal.** When the depth-2 lemma's author and its first referee
  turned out to share a lineage, the ledger scribe refused the T2 label and a second-lineage
  referee was assigned. The campaign's own rails blocked promotion of the main claim with a typed
  refusal until a review was bound to the exact claim version.
- **Audits changed things.** An independent audit of the ledger found records that omitted the
  referee's non-verifications, a missing no-claim boundary, and custody manifests hashed from a
  mid-edit working tree; all were corrected, and the in-place edits themselves became a recorded
  deviation reviewed by a referee, because the walkers correctly refused to forget them.
- **Negative results were kept and published** (see below), each with an exact dual certificate
  and a retry predicate, rather than quietly dropped.
- **The novelty gate did its job on our own result.** Run after verification, the dated search
  (`literature/novelty-search-2026-09-03.md`) found that the authors of the `n ≤ 10` paper had
  posted a revision establishing `n ≤ 12` days before this computation finished. Our certificates
  were obtained independently, are structurally different (loop-free, and a forest-pair variant
  under a third the size of theirs), and are recorded as an independent replication with
  computed standing, not as a priority claim. A protocol that catches this on its own output is a
  protocol worth trusting.

---

## Structural findings toward the universal statement

All exact, all with re-executed evidence, all recorded in `artifacts/math/`:

| Finding | Where |
|---|---|
| Branch size 5 is necessary at `n = 11` within the loop-free ansatz: the complete 4-edge family is NON_MEMBER at two primes × two sketches (18,286 columns, rank 3,514 vs 3,515). | `n11-degree4/` |
| Certificate coefficients cannot be a function of a few graph invariants: at `n = 9, 10` every coarsening of the orbit set below ≈4,600 classes is NON_MEMBER with an exact dual; membership requires the isomorphism type of the unsigned union graph. | `class-sum-n9-n10/` |
| The lifted certificate spans the next maximum: adding one edge to each branch of every `n−1` certificate term yields a family that spans `MAX_n` at `9 → 10` (rank 17,127) and `10 → 11` (rank 30,200, two identical sketches). | `n11-lift-test/` |
| But no local recursion reproduces the coefficients: with the new coefficient equal to the parent coefficient times a weight depending on how the two new edges attach, the target sits exactly one dimension outside the span at every one of eight taxonomies (1 to 455 classes) and at both rungs, with exact duals; per-parent weights at the base taxonomy fail too. | `lift-recursion/` |
| `n = 12` stage A is MEMBER at two primes (rank 33,454; 148,629 columns). | `n12-stageA/` |

Read together: an inductive construction of these certificates must carry global isomorphism
data of the extended signed graph, not local attachment data. That rules out the cheapest route
to `n = 13` and shapes what a proof for all `n` would have to look like.

---

## The swarm

The campaign was run by a single orchestrating Claude session directing eight Codex workers
through NTM tmux panes, Agent Mail threads, and a beads task graph, plus fresh-context Opus agents
used strictly as referees, auditors, and one-shot experimenters. Rules that held throughout:
workers never close their own beads; every closure cites evidence the orchestrator re-executed;
process artifacts exist only when they gate a named decision; and every claim carries its
no-claim boundary. Rented compute: one H100 PCIe, one H100 NVL, one A100, all torn down at the
end. Engine work along the way doubled streamrank throughput (2.08×, byte-identical pivots).

---

## Outstanding

- **The universal statement is open.** No route to it survives with these methods; the tests
  above say what any recursion must carry.
- **`n = 13`** needs a structural principle relating solutions across arities; a brute-force
  rank at the required scale (rank ~100k) is beyond this engine.
- **Untested cells:** per-parent recursion weights at finer attachment taxonomies (6,419+
  unknowns) were not decided; a retry predicate is recorded on the bead.
- **Sparse, human-legible `n = 11` certificate** (target under 3,000 terms): the pipeline
  reproduced the known 424-term `n = 10` certificate as its control; the `n = 11` LP runs were paused.
- **Ledger close-out:** two referee reviews (claim version and deviation) are committed and await
  recording, after which the main claim's computed standing rises from its current frozen state.
- **Not done:** human refereeing, formalization in a proof assistant, and running the community's
  own Python verifier on a sparse certificate (projected 38 hours on the dense one).

---

## Repository map

- `RESEARCH_CHARTER.md`, `PROBLEM_SPECIFICATION.md` — exact target, cousin register, review bar
- `handoff/2026-09-02-RESUME-SYNTHESIS.md` — the dated, running record of every result and prior update (§11) and the operational state (§12)
- `artifacts/math/` — every experiment: inputs, outputs, hashes, controls, `RESULT.md` per bead
- `artifacts/math/t2-review/` — referee reports
- `tools/` — colgen, streamrank, exactlift, verify11, t2-referee
- `ledger/` and `CLAIMS_LEDGER.md` — claims, evidence, reviews, deviations; the view is generated, never hand-edited
- `literature/` — certified corpus, bibliography, dated novelty searches
- `AGENTS.md` — the swarm's operating law

## Cold start for a successor

1. Read `AGENTS.md`, `RESEARCH_CHARTER.md`, `PROBLEM_SPECIFICATION.md`, then §12 and §11 of the synthesis.
2. `source scripts/activate-toolchain.sh` and `./skill-runtime verify-quick` (expect the recorded immutable-history findings and nothing else).
3. Work only on a named bead; close rounds with the ledger, the verifier, and one commit.
