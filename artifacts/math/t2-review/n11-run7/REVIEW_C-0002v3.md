# T2 review of ledger claim C-0002@3

- **Reviewer lineage:** Claude, Opus 5 (1M context). Same referee that produced
  V-0008 on C-0002@2 and the two-part certificate review in `RESULT.md`.
- **Review date:** 2026-09-03.
- **Repository HEAD at review:** `28b81867350aa8f3f29278da66303a1669142732`.
- **Scope:** the ledger claim text only, plus whether my existing certificate
  findings carry over. No new computation on the certificate was performed for
  this review; the runs it relies on are those recorded in `RESULT.md` Parts I
  and III.

**Verdict: holds.**

---

## 1. Claim-version texts and their hashes

Both blocks were extracted from `git show HEAD:ledger/claims.toml` as the exact
14 lines from `[[claim]]` through `created = …` inclusive, with no trailing blank
line: lines 775-788 for `@2` and lines 870-883 for `@3`.

| object | SHA-256 |
| --- | --- |
| C-0002@2 TOML block (14 lines) | `d1e09ca844400cb700f9c3d400e851e313e13f5f57b46d7d26db7362597e87c0` |
| C-0002@3 TOML block (14 lines) | `68ac3cd2e2a21aa07e95e044201bf8d9addd4d185ac979da5385c492a91faa14` |
| `statement` value, identical in both | `1b3498d711234ce8d4c47d11212df5fa8a07c5e3f987307c8e7e93ed5f47fc5c` |

**The statement text is byte-identical between `@2` and `@3`.** Compared as
parsed field values, not as a visual diff. The pinned witness SHA-256 inside the
statement is still `8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5`,
which is the certificate I verified.

Unchanged fields: `id`, `statement`, `role`, `domain`, `falsifier`,
`not_equivalent_to`, `origin_round`, `author_path`.

## 2. The diff, and two changes that were not in the description

I was told the diff was "same statement, plus a dependency on C-0059@1 and an
added no_claim sentence". That is most of it, but not all of it. The complete set
of changed fields is:

| field | `@2` | `@3` | described? |
| --- | --- | --- | --- |
| `version` | 2 | 3 | implied |
| `supersedes` | `C-0002@1` | `C-0002@2` | implied |
| `created` | 2026-09-02T23:46:15Z | 2026-09-03T02:12:00Z | implied |
| `depends_on` | `["C-0054@1"]` | `["C-0054@2", "C-0059@1"]` | **partly** |
| `no_claim` | one paragraph | same paragraph plus **two** sentences | **partly** |

**Undescribed change 1: the C-0054 dependency was also bumped, `@1` to `@2`.**
The description mentioned only the addition of `C-0059@1`. C-0054 is the
implementation/manifest claim, and `@2` is a genuinely different object: it
extends the manifest to cover "aborted-run custody, depth-2 proof, and
overflow-control sources", and it carries a different `code_hash`
(`464acf99…` versus `0be971a9…`), `env_digest`, and `data_snapshot`.

This matters to me specifically, because my V-0008 record binds to
`implementation_claim = "C-0054@1"` with that older snapshot triple. So my
original evidence was produced against the `@1` bundle, not the `@2` bundle that
`@3` now depends on. It is nonetheless safe, and the reason is recorded in
`RESULT.md` Part III: after `tools/verify11` was patched (commit `392aeb6`,
the checked-multiply fix that is part of what C-0054@2's "overflow-control
sources" refers to), I rebuilt from HEAD and re-ran the full verification, and
the run7 report was `OK`, exit 0, with all 32 compared fields identical to the
original. That re-run is what carries my findings onto the newer bundle. Without
it I would have flagged the C-0054 bump as leaving `@3` resting on evidence
gathered under a superseded toolchain.

**Undescribed change 2: `no_claim` gained two sentences, not one.** The described
one is present and correct:

> The step from the certified identity to a two-hidden-layer network is the
> depth-2 realization lemma recorded separately; the verifier checks the identity
> only.

There is a second:

> The unresolved completeness of restricted ansatzes, degree-four circuits,
> zonotope wall cancellation, and pricing of broader degree-five universes bears
> on attempted null directions only and does not cap this positive witness.

I have no objection to it. It is logically sound: incompleteness of attempted
refutation routes cannot bound a positive witness, and the sentence sits in
`no_claim`, so it narrows rather than broadens. But it is an editorial assertion
about four work items I have not refereed, and my verdict does not extend to
them.

**Direction of every change is narrowing or neutral.** Nothing in `@3` broadens
the claim, weakens `not_equivalent_to`, drops a caveat, or extends the scope
beyond n = 11.

## 3. Do my V-0008 findings apply unchanged to @3?

**Yes.** The statement is byte-identical, so every finding in V-0008 attaches to
the same proposition and the same pinned certificate. Concretely, still standing
for `@3`:

- zero exact residual on all 11 linear rows and all 169,166 hinge rows across all
  15,896 terms, from my own clean build of `verify11` (`OK`, exit 0);
- the same totals reproduced by an independently written implementation validated
  against the pinned upstream verifier on 373 columns at n = 5 to 8;
- translation reproduced byte-for-byte for all 15,896 terms, plus a 20/20 seeded
  spot check;
- 20/20 literal-versus-DP column agreement over 798,336,000 permutations;
- two method-disjoint lattice runs, 90 profiles and 179,195 points each, PASS;
- a planted `1e-35` coefficient perturbation rejected with a residual matching an
  independent prediction exactly;
- and, added after V-0008 was written, the full re-verification against the
  patched `verify11` with results identical field-for-field.

`@3` also adds the dependency that corresponds to my V-0008 residual doubt about
depth-2 realization. C-0059@1 carries T1 `holds` (V-0013, Claude Opus) and T2
`holds` (V-0015, IndigoCarp, GPT lineage), on lemma revision 2b at commit
`a1a70ba`, file SHA-256 `dedd94b2e85cd282e6da6eed64200ae354a4cbf290c1d92dd2979d97609b6007`.
Note the lineage arrangement is the mirror of the certificate review: for the
lemma, the same-lineage tier is mine and the cross-lineage tier is GPT. I did not
referee the lemma myself, so my verdict on `@3` is conditional on that lemma
being correct; I am relying on the ledger records for it, not on my own reading.

## 4. G-0016 closes my residual doubt 2

My second residual doubt on the certificate was that the run7 lift report claims
`union_hinge_rows = 169,250` while both `verify11` and my independent
implementation count 169,166 distinct hinge directions, a gap of 84 rows I could
not explain.

`artifacts/math/n11-hinge-union-84/RESULT.md` (IndigoCarp, GPT lineage, verdict
CONFIRMED, discharging G-0016 via E-0057) resolves it by streaming the 12.9 GB
ELIFTQ02 problem matrix directly:

- the hinge-row universe over **all 21,222 pivot columns** is 169,250;
- restricted to the **15,896 nonzero-support columns** it is 169,166;
- the set difference is exactly the 84 rows, hinge IDs 169166 through 169249;
- **0 of those 84 rows has any nonzero-witness toucher** — every column touching
  them is a zero-coefficient pivot, and the finalizer rejects serialized zeros, so
  each such coordinate is exactly zero in the witness.

So the lift built its row count over the full pivot set and the certificate's
count is over the nonzero support. The two numbers were never in conflict. **My
doubt 2 is closed for run7.**

One corroboration worth recording, because it comes from a completely different
artifact than anything I used: that audit's "raw hinge entries over support
columns" is **681,123,474**, which is exactly the `emitted_hinge_entries` value in
my own `verify11` report. A stream over the lift's problem matrix and my
certificate-side evaluation independently agree on that count.

**The F2 analogue is not covered.** The F2 lift report claims 146,176 union hinge
rows against 145,530 observed, a 646-row gap, and its shape is identical (15,904
pivot columns, 11,320 nonzero support, so 4,584 zero-coefficient pivots against
run7's 5,326). The same mechanism plainly explains it, but no equivalent streamed
audit has been run on the F2 problem matrix and no gap entry covers it. This does
not touch `@3`, whose `not_equivalent_to` already excludes "the unverified
11,320-term F2 certificate alone", but the 646 should not be quoted as reconciled.

## 5. Verdict

**holds.**

**capable_of_failure.** This review would have returned narrowed or refuted, not
holds, on any of: one byte of drift in the `statement` field, including the pinned
certificate SHA-256; any edit that broadened scope, removed a `no_claim` sentence,
or weakened `not_equivalent_to`; a new `depends_on` entry that was itself
unreviewed, refuted, or narrowed; a G-0016 resolution showing any of the 84 rows
had a nonzero-witness toucher, which would have reopened the residual-count doubt
and put the lift report's numbers in genuine conflict with the verifier's; or a
`C-0054` bump I could not bridge with a re-verification under the newer
toolchain. The first of these was checked by exact field comparison rather than
by reading, and the last was the reason for the Part III re-runs.

**Residual doubts on @3.**

1. I did not referee C-0059@1. `@3`'s soundness as a network-representability
   claim, as opposed to an identity claim, rests on a lemma whose only
   cross-lineage review is IndigoCarp's. I read the review records, not the proof.
2. Neither exact rational lift was re-run. No number in either
   `member_exact_lift_report.json` is supported by my work, and G-0016's
   resolution is IndigoCarp's audit, not mine.
3. The G-0027 universe remains read as data, not audited.
4. The F2 646-row analogue of G-0016 is unaudited (§4).
5. The four null-direction items named in the new second `no_claim` sentence are
   outside anything I have refereed.
6. The C-0054 dependency bump was not in the change description I was given
   (§2). Nothing else in the diff was undescribed, but a reviewer who had checked
   only the two described changes would have missed it.
7. Unchanged from V-0008 and already stated in the claim's own `no_claim`: not
   human-refereed in the journal sense, and not formalized in a proof assistant.

**No-claim line.** This review adjudicates the `@3` claim text and the carry-over
of my existing certificate findings. It performs no new verification of the
certificate, the lift, the universe, or the depth-2 lemma, and it asserts nothing
about n >= 12, minimality, or any lower bound.
