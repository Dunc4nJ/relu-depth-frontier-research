# Loop-inclusive degree-4 MAX11 replication (stopped at novelty gate)

Bead: `relu-depth-frontier-research-sou`

Worker: PurpleWolf

Outcome: **REPLICATION OF A PUBLISHED COROLLARY; STOPPED BY ORCHESTRATOR
AFTER THE NOVELTY GATE FAILED.**

## Result

One preregistered n=11 CUDA sketch completed at prime 1,000,003:

| n | family | p | seed | source columns | m | rank(A) | rank([A\|MAX]) | verdict |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 11 | all 137,504 loop-inclusive degree-4 records + 4L | 1,000,003 | 2,026,090,201 | 137,505/137,505 | 32,768 | 8,667 | 8,668 | **NON_MEMBER** |

The run was unsaturated. Its ordered pivot-source SHA-256 is
`4576b9e56ab3ecdb8267819521a0eb9bca21bd16b146317c4604b83b52adb45b`.
The emitted left separator annihilated all 8,667 verified basis columns and
had target dot product 176,191 modulo 1,000,003. The report SHA-256 is
`43f3b3a78c0f3117271e89cea2695126532428404821f535c68bafa915c438c0`;
wall time was 2,675.836 s, process high-water RSS was 1,791,228 KiB, and
reported peak CUDA basis storage was 6,652,428,800 bytes. The enforced rank
gate gives `3 * 8667 = 26001 < 32768 = m`.

This completed computation is a **bounded one-prime modular null**, not the
preregistered two-seed/two-prime result. The second primary sketch was stopped
on the orchestrator's order at 117,760/137,504 universe records (partial rank
4,209, before 4L); it emitted no JSON and receives no verdict. Neither
second-prime sketch was started.

## Why the campaign stopped

Rueß et al., *Shallower ReLU Network Representations via Exact Linear
Algebra*, arXiv:2607.21651v1, Corollary 4.3, already proves for the exact
pairwise-max ansatz that

`k >= floor((n - 1) / 2)`.

At n=11 this forces k>=5 and therefore already excludes the loop-inclusive
degree-4 family tested here. Their proof represents each atom as the support
function of `conv(Z_A union Z_B)`, whose dimension is at most `2k+1`, and
uses the obstruction to expressing an `(n-1)`-simplex as a signed Minkowski
combination of lower-dimensional polytopes. The result appears in the
certified local v1 text at `literature/papers/2607.21651.txt`, physical pages
8--9 / extracted lines 453--486. That text has SHA-256
`a92c482f9e5a11fb1b0b54dc6945e410f83cfd84a00382ee2bcc7d692b817d0a`;
the source card is `literature/source-cards/REF-0001.md`.

Thus the completed sketch agrees with, but does not add to, the published
corollary. On learning this, AmberBluff ordered the running seed-2 process
stopped and the second prime cancelled.

## Universe and carriers

The independent degree-4 census produced 137,504 n=11 signed-W orbit records.
Adding the separate 4L carrier gives 137,505 streamed source columns. Record
zero is the degree-4 empty carrier 4E; 4L is appended at source index 137,504
with exact coefficient 14,515,200 on each of the 11 coordinates.

| artifact | records | columns with 4L | loop-bearing records | SHA-256 |
|---|---:|---:|---:|---|
| n=11 universe | 137,504 | 137,505 | 119,219 | `e507784414e85667cfe18f68e55b2db22015cf112f05ea110f5ccf388dafb5c0` |
| n=10 projection | 136,036 | 136,037 | 118,261 | `e739d8671b91b51dbdcff8e131ab65e3ffac22972ccd7cbb3489347aaa7b590f` |

The n=11 signed-mass counts are 1, 5, 107, 3,198, and 134,193 for
masses 0 through 4. All 137,504 n=11 records and all 136,036 n=10 records
match the corresponding prefix of the pinned independent degree-5 stream,
SHA-256
`e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd`.
The independent source used by the enumerator has SHA-256
`16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb`.

The enumeration manifest SHA-256 is
`9bb5f777a2854a25253207adfef555017621c15bf996b9efcbe80972ae631ca7`.
The independent verifier passed both universes and rejected 2/2 planted
mutants; its report SHA-256 is
`fc6d00da8a7d10e15cab0a5a7271c44016257fe81ffb53be6f06012a38e74523`.

## Known-answer controls

The loop-aware generator replayed the pinned upstream exact rational
certificates before the target:

| control | exact DP/literal columns | exact MAX identity | diagonal-sign mutant |
|---|---:|---|---|
| n=7, degree 3 | 57/57 | PASS | rejected |
| n=8, degree 3 | 69/69 | PASS | rejected |

The n=7 and n=8 certificate input SHA-256 values are respectively
`b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be`
and `68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3`.
Including the legacy n=5 control, the replay passed 129/129 template checks,
3/3 exact identities, and 3/3 mutant rejections. The replay report SHA-256 is
`faa617939161e0acb0dcaa0609c4cf9390faf513d109eafdbc7c18390248bfe6`.

The full n=10 loop-inclusive degree-4 known-answer control at p=1,000,003,
m=32,768, seed 2,026,090,201 processed 136,037/136,037 columns and returned
rank 7,867, augmented rank 7,867, **MEMBER**. It was unsaturated; its ordered
pivot-source SHA-256 is
`0054d6c1baea31ad6fb9cd5e10ee925687e66c22b1fd4838427f1200c96e7717`.
The report SHA-256 is
`65a93f4097d35c7717f2f94c470645081ab52652430f9aad7ee80a5226455ed5`;
wall time was 619.079 s and high-water RSS was 1,621,052 KiB.

## Commands

Universe enumeration and independent verification:

```sh
python artifacts/math/n11-degree4-loops/enumerate_loop_inclusive_degree4.py \
  --output-n11 artifacts/math/n11-degree4-loops/loop_inclusive_signed_degree4_n11_v1.json.gz \
  --output-n10 artifacts/math/n11-degree4-loops/loop_inclusive_signed_degree4_n10_v1.json.gz \
  --manifest artifacts/math/n11-degree4-loops/enumeration_manifest_v1.json \
  --progress-every 10000

python artifacts/math/n11-degree4-loops/verify_loop_inclusive_degree4.py \
  --universe artifacts/math/n11-degree4-loops/loop_inclusive_signed_degree4_n11_v1.json.gz \
  --universe artifacts/math/n11-degree4-loops/loop_inclusive_signed_degree4_n10_v1.json.gz \
  --output artifacts/math/n11-degree4-loops/universe_verification_v1.json
```

Exact certificate controls:

```sh
tools/colgen-loops/target/release/max11-colgen-loops validate-certificates \
  --certificate-n5 literature/repos/max-relu-certificates/certificates/certificate_5_2.json \
  --certificate-n7 literature/repos/max-relu-certificates/certificates/certificate_7_3.json \
  --certificate-n8 literature/repos/max-relu-certificates/certificates/certificate_8_3.json \
  --output artifacts/math/n11-degree4-loops/upstream-degree3-certificate-replay.json
```

The frozen H100 launcher (SHA-256
`31ea26eda03bf4c1b87337b6ec6b7fd9b300c7bef7179834e02774c2cad9beea`)
was invoked sequentially as:

```sh
artifacts/math/n11-degree4-loops/run_remote_n11_seed.sh \
  1000003 2026090201 n11-loop-degree4-m32768-p1000003-s1-cuda

artifacts/math/n11-degree4-loops/run_remote_n11_seed.sh \
  1000003 2026090202 n11-loop-degree4-m32768-p1000003-s2-cuda
```

It expands to `max11-streamrank run-universe` with CUDA, n=11,
`--branch-edges 4`, `--buckets 32768`, batch 1,024, GEMM block 8,192, rank
panel 64, four threads, `--loop-inclusive true`,
`--include-linear-carrier true`, rank abort 10,922, RSS abort 25,165,824
KiB, and expected column count 137,505. The second invocation was terminated
by the orchestrator order. The p=1,000,033 invocations recorded in the
preregistration were never executed.

## Implementation and execution custody

- `3f437f40297b49cac976876eb2b1b86f076cce7b`: n=8 certificate replay and
  loop-generator tests (5/5 release tests PASS).
- `5ef65a33b773c62224c418fe838c949310015665`: explicit loop-inclusive
  streamrank dispatch (9/9 release tests PASS; default clippy PASS).
- `e70a53244f4af60fb079084cc9d146880e972883`: universes, controls,
  preregistration, and independent verifiers.
- `0369e8c0f71e0c4c43eab3b3b95a2db5fe2da544`: frozen target launcher.
- Isolated H100 CUDA binary SHA-256:
  `80cde98e172b79a4afdc816650fa1ce7b4deb4af99a132895843465bc4aa0a94`.
- Local all-features clippy could not start because the CPU host lacks
  `nvcc`; the isolated H100 CUDA build and record-zero-plus-4L smoke test
  passed. All failed, stale-binary, smoke, complete, and stopped attempts are
  retained or narrated in `TRIALS.md`.
- Seed-2 partial stderr SHA-256:
  `96cd9d9d80c16e6e516bc75508780dc831f9d23ebd27a5c2a148202522d1b159`;
  its empty stdout has the standard empty-file SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Handoff checks: the bead-local hash/result assertions and
  `git diff --check` passed; the remote process scan found no sou streamrank
  process and no p=1,000,033 artifact. `./skill-runtime verify-quick` exited
  1 on 24 findings in concurrently changed canonical ledger files. Those
  findings are outside this bead's edit authority and are recorded as T10 in
  `TRIALS.md`; no canonical or generated ledger file was edited here.

## No-claim

This result does **not** complete the preregistered two-seed/two-prime
decision, independently prove Rueß et al. Corollary 4.3, establish exact
rational non-membership from the modular computation, or prove an
unrestricted two-hidden-layer lower bound. It records one completed
one-prime modular null for the named finite loop-inclusive degree-4 signed-W
family and a computation stopped because the same degree exclusion was
already published. The partial seed-2 rank is not a verdict and is not used
as evidence.
