# relu-depth-frontier-research-330 — n=11 ledger recording

## Result

The canonical ledgers now record the n=11 rung as claim `C-0002@2`, with an exact
15,896-term rational witness and computed standing `REFEREED`. The standing is derived
from exact all-row verification, a same-lineage T1 replay, and a locally attributed
fresh-context Claude Opus T2 replay; the attribution is not provider-authenticated.

The ledger also records:

- `EXP-0036` and the four stage-A modular arms, CPU/CUDA pivot agreement, run7 exact lift,
  the separate F2 exact witness, and the bounded F1/F3 outcomes;
- exact-lift attempts run1 through run6 as aborted, full-universe pass 2 as aborted,
  the n=12 arm-3 GPU-gate crash as aborted, and the degree-four combined s1s2 CUDA OOM as
  aborted;
- deviations `X-0001` through `X-0004`, each reviewed by
  `orchestrator/amberbluff`, without changing the exact-verification gate;
- T1 review `V-0007` and transcript-bound T2 review `V-0008`;
- bounded-null claims `C-0055@1` through `C-0058@1` and dead ends `D-0008`
  through `D-0011`, each with a dormant machine-readable retry predicate.

The generated `CLAIMS_LEDGER.md` view was regenerated mechanically. No standing field was
written by hand.

## Custody

- code manifest:
  `sha256:0be971a951549342da6cc275078d032cc977dc1d807c5640b398fb497e7d526b`
- data manifest:
  `sha256:4a02a5bfdf880596a95b96eca530316d679ba0711e46d7c2bd5dfcf1274ec53c`
- environment record:
  `sha256:b2d950753b7e2166120e0145fe3f3a99a07597cb0a9fa96def2cc41173b8a914`
- run7 upstream-format witness:
  `sha256:8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5`
- run7 exact-lift report:
  `sha256:76e8661c95b063cea1c47ceee0bc1febb674996a86baf9cbc95b8f6afa106ff0`
- T1 full exact report:
  `sha256:5a2091d21725309e986407bf48f20cfa39b1e2468c4048b932bfc94f7ddd2b92`
- T2 independent Python recheck:
  `sha256:6829ef896af69f4906e5da3f2fafbf29e36817da61e87e027105a769d0ca6aac`
- T2 lattice report:
  `sha256:e808483d9d66969670adc9980be845c3a01e898d1e497b74002c6cb3704efc48`
- F2 upstream-format witness:
  `sha256:767f9e66fd3dcb7b5c43e5ffdbbfa50967684d7b263c41cbd7c35e2db7938670`

The direct T2 transcript inputs are the committed data manifest and the committed control
report. The oversized certificate is bound indirectly by the data manifest because the
transcript policy rejects direct inputs larger than 8,000,000 bytes.

## Controls

- run7 exact verification: 190,483/190,483 combined rows and 169,261/169,261
  real rows; a +1 coefficient mutation broke 29,917/190,483 rows;
- T1 verify11: 0/11 bad linear and 0/169,166 bad hinge rows; its +1 mutant had
  9/11 bad linear and 23,011/169,166 bad hinge rows;
- T2: 20/20 translation checks, 20/20 literal-versus-DP checks, two lattice passes
  covering 90/90 profiles and 179,195/179,195 points, plus the registered
  `known-answer` and `trivial-witness-null` control records;
- F2: 162,091/162,091 exact combined rows, with a +1 mutation breaking
  9,895/162,091 rows. F2 has no T1/T2 review and is not load-bearing for
  `C-0002@2`.

## Commands

```sh
source scripts/activate-toolchain.sh
scripts/verify-toolchain.sh
./skill-runtime gates list
python3 /home/ubuntu/.agent/skills/frontier-research-with-epistemic-humility/scripts/generate-ledger-view.py /data/projects/relu-depth-frontier-research
./skill-runtime verify-quick
```

## Verification

The final command exited 1 only because of the campaign's pre-existing allowed
`SE-10` on `G-0015`. The exact captured output below is 264 lines and has SHA-256
`6133f79adea3228d3599dbbbbcdcb66effc7939c3fc8cde04690b2eafe3b6991`.

```text
C-0001@1: own CITED -> ceiling CITED
C-0002@2: own REFEREED -> ceiling REFEREED
C-0003@1: own CITED -> ceiling CITED
C-0004@1: own CITED -> ceiling CITED
C-0005@1: own ASSERTED -> ceiling ASSERTED
C-0006@1: own ASSERTED -> ceiling ASSERTED
C-0007@1: own ASSERTED -> ceiling ASSERTED
C-0008@1: own CITED -> ceiling CITED
C-0009@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0010@1: own ASSERTED -> ceiling ASSERTED
C-0011@1: own ASSERTED -> ceiling ASSERTED
C-0012@1: own ASSERTED -> ceiling ASSERTED
C-0013@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0014@1: own ASSERTED -> ceiling ASSERTED
C-0015@1: own ASSERTED -> ceiling ASSERTED
C-0016@1: own ASSERTED -> ceiling ASSERTED
C-0017@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0018@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0019@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0020@1: own ASSERTED -> ceiling ASSERTED
C-0021@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0022@1: own ASSERTED -> ceiling ASSERTED
C-0023@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0024@1: own ASSERTED -> ceiling ASSERTED
C-0025@2: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0026@2: own ASSERTED -> ceiling ASSERTED
C-0027@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0028@1: own ASSERTED -> ceiling ASSERTED
C-0029@1: own ASSERTED -> ceiling ASSERTED
C-0030@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0031@1: own ASSERTED -> ceiling ASSERTED
C-0032@1: own ASSERTED -> ceiling ASSERTED
C-0033@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0034@1: own ASSERTED -> ceiling ASSERTED
C-0035@1: own ASSERTED -> ceiling ASSERTED
C-0036@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0037@1: own ASSERTED -> ceiling ASSERTED
C-0038@1: own ASSERTED -> ceiling ASSERTED
C-0039@1: own ASSERTED -> ceiling ASSERTED
C-0040@1: own ASSERTED -> ceiling ASSERTED
C-0041@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0042@1: own ASSERTED -> ceiling ASSERTED
C-0043@1: own ASSERTED -> ceiling ASSERTED
C-0044@1: own ASSERTED -> ceiling ASSERTED
C-0045@1: own COMPUTED_BOUNDED -> ceiling ASSERTED  ◄ weakest link: C-0043@1
C-0046@1: own ASSERTED -> ceiling ASSERTED
C-0047@1: own ASSERTED -> ceiling ASSERTED
C-0048@1: own ASSERTED -> ceiling ASSERTED
C-0049@1: own INDEPENDENTLY_REPLAYED -> ceiling INDEPENDENTLY_REPLAYED
C-0050@1: own ASSERTED -> ceiling ASSERTED
C-0051@1: own ASSERTED -> ceiling ASSERTED
C-0052@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0053@1: own ASSERTED -> ceiling ASSERTED
C-0054@1: own ASSERTED -> ceiling ASSERTED
C-0055@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0056@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0057@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
C-0058@1: own COMPUTED_BOUNDED -> ceiling COMPUTED_BOUNDED
COERCION E-0007: exploratory: informs, never promotes
COERCION E-0010: exploratory: informs, never promotes
COERCION E-0028: exploratory: informs, never promotes
COERCION E-0030: exploratory: informs, never promotes
COERCION E-0049: exploratory: informs, never promotes
novelty log: 6 dated search row(s), 3 REF id(s) cited
C-0001@1: class CITED
    blocked: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact
C-0002@2: class REFEREED
    blocked: REFEREED -> FORMALIZED: closed local formalization attestation
C-0003@1: class CITED
    blocked: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact
C-0004@1: class CITED
    blocked: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact
C-0005@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0006@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0007@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0008@1: class CITED
    blocked: CITED -> COMPUTED_BOUNDED: computation with domain_checked + detection_floor + repro + artifact
C-0009@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0010@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0011@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0012@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0013@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0014@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0015@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0016@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0017@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0018@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0019@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0020@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0021@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0022@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0023@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0024@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0025@2: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0026@2: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0027@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0028@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0029@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0030@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0031@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0032@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0033@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0034@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0035@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0036@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0037@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0038@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0039@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0040@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0041@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0042@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0043@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0044@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0045@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0046@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0047@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0048@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0049@1: class INDEPENDENTLY_REPLAYED
    blocked: INDEPENDENTLY_REPLAYED -> REFEREED: fresh-context referee verdict holds at tier T2+
TYPED_REFUSAL: promotion of C-0049@1 beyond INDEPENDENTLY_REPLAYED blocked — missing capability: fresh-context, cross-family T2+ review; the claim holds its rung rather than borrowing standing
C-0050@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0051@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0052@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0053@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0054@1: class ASSERTED
    blocked: ASSERTED -> CITED: retrieved citation with locator+excerpt
C-0055@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0056@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0057@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
C-0058@1: class COMPUTED_BOUNDED
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: clean-room replay CONSISTENT (replay-eligible: env pinned)
    blocked: COMPUTED_BOUNDED -> INDEPENDENTLY_REPLAYED: replay author differs
retry scan: 11 dead end(s), 0 fired
INFO round-boundary anchor compared 24 older committed version(s) of canonical paths (81 append-only)
INFO Git history anchor active at HEAD aac293ec8a97 for 9 canonical path(s)
SE-10 ledger/gaps.toml G-0015: gap history permits only open -> discharged with a set-once discharged_by, or open -> superseded; changed obligation; append/version/forward-lifecycle changes only (still contradicted by commit 7cf9d50deb61) (see references/CLAIMS-LEDGER-SPEC.md §8)
verify-ledger: 1 finding(s) [quick mode; 9 walkers + 1 domain checker aggregated]
  C-0001@1: challenged · class CITED · ceiling CITED
  C-0002@2: supported [UNCHALLENGED] · class REFEREED · ceiling REFEREED
  C-0003@1: challenged · class CITED · ceiling CITED
  C-0004@1: challenged · class CITED · ceiling CITED
  C-0005@1: quarantined [HEURISTIC] · class ASSERTED · ceiling ASSERTED
  C-0006@1: open · class ASSERTED · ceiling ASSERTED
  C-0007@1: open [UNCHALLENGED] · class ASSERTED · ceiling ASSERTED
  C-0008@1: open [UNCHALLENGED] · class CITED · ceiling CITED
  C-0009@1: challenged · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0010@1: open · class ASSERTED · ceiling ASSERTED
  C-0011@1: open [UNCHALLENGED] · class ASSERTED · ceiling ASSERTED
  C-0012@1: open · class ASSERTED · ceiling ASSERTED
  C-0013@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0014@1: open · class ASSERTED · ceiling ASSERTED
  C-0015@1: open · class ASSERTED · ceiling ASSERTED
  C-0016@1: open · class ASSERTED · ceiling ASSERTED
  C-0017@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0018@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0019@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0020@1: open · class ASSERTED · ceiling ASSERTED
  C-0021@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0022@1: open · class ASSERTED · ceiling ASSERTED
  C-0023@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0024@1: open · class ASSERTED · ceiling ASSERTED
  C-0025@2: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0026@2: open · class ASSERTED · ceiling ASSERTED
  C-0027@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0028@1: open · class ASSERTED · ceiling ASSERTED
  C-0029@1: open · class ASSERTED · ceiling ASSERTED
  C-0030@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0031@1: open · class ASSERTED · ceiling ASSERTED
  C-0032@1: open · class ASSERTED · ceiling ASSERTED
  C-0033@1: challenged · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0034@1: open · class ASSERTED · ceiling ASSERTED
  C-0035@1: open · class ASSERTED · ceiling ASSERTED
  C-0036@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0037@1: open · class ASSERTED · ceiling ASSERTED
  C-0038@1: open · class ASSERTED · ceiling ASSERTED
  C-0039@1: open · class ASSERTED · ceiling ASSERTED
  C-0040@1: open · class ASSERTED · ceiling ASSERTED
  C-0041@1: challenged · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0042@1: open · class ASSERTED · ceiling ASSERTED
  C-0043@1: open [UNCHALLENGED] · class ASSERTED · ceiling ASSERTED
  C-0044@1: open · class ASSERTED · ceiling ASSERTED
  C-0045@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling ASSERTED · weakest C-0043@1
  C-0046@1: open · class ASSERTED · ceiling ASSERTED
  C-0047@1: open [UNCHALLENGED] · class ASSERTED · ceiling ASSERTED
  C-0048@1: open · class ASSERTED · ceiling ASSERTED
  C-0049@1: supported [UNCHALLENGED] · class INDEPENDENTLY_REPLAYED · ceiling INDEPENDENTLY_REPLAYED
  C-0050@1: open · class ASSERTED · ceiling ASSERTED
  C-0051@1: open · class ASSERTED · ceiling ASSERTED
  C-0052@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0053@1: open · class ASSERTED · ceiling ASSERTED
  C-0054@1: open · class ASSERTED · ceiling ASSERTED
  C-0055@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0056@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0057@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
  C-0058@1: supported [UNCHALLENGED] · class COMPUTED_BOUNDED · ceiling COMPUTED_BOUNDED
Ledger discipline DOES NOT hold: the finding(s) above are unresolved. Nothing here is verified.
```

## No claim

This record establishes only the exact n=11 witness and the explicitly named finite
computations. It does not establish a construction for n>=12 or all n, minimal width,
minimal support, a sparse or uniform formula, provider-authenticated or human review,
proof-assistant formalization, or any unrestricted lower bound from a bounded null.

