# T2 review of ledger deviation X-0005

- **Reviewer lineage:** Claude, Opus 5 (1M context). Same referee as V-0008 on
  C-0002@2 and `REVIEW_C-0002v3.md` on C-0002@3.
- **Review date:** 2026-09-03.
- **Target:** exactly `X-0005` in `ledger/deviations.toml`, recorded in commit
  `3741e9d4d7386093d3b024ff8b9ea3815f9132c0`.
- **Repository HEAD at review:** `4888126` plus this file.

**Verdict: holds.** The deviation is faithfully described and its corrections are
legitimate.

## 1. Object and hashes

X-0005 occupies lines 60-68 of `ledger/deviations.toml` at HEAD, `[[deviation]]`
through `created = …` inclusive.

| object | SHA-256 |
| --- | --- |
| X-0005 TOML block (9 lines) | `17b961f1e3c4d3e3749c4afef7f575d2a96199b55940c27a839d2f0b5a4aeda1` |
| `reason` field value, 2,493 chars, the text carrying all 22 findings | `833cd96c1543ccfe764a320129ebbbc85c5dad274969753179aa37e18b700242` |

Fields: `planned` "in-place edits of immutable records during the n=11
recording", `substitute` retain corrected content and disclose, `affects`
`["C-0002@3"]`, `status` `"open"`, `author_path` `ledger-auditor/goldmeadow`.

The 22 findings name **19 distinct records**; EXP-0044, EXP-0045 and V-0008 each
appear twice, once against their introduction and once against an intermediate
edit.

## 2. Method

Two passes, both mechanical rather than by reading.

**Structural pass, all 19 records.** For each record I reconstructed its full
field map at the introducing commit named in the deviation and at HEAD, then
listed every field whose value differs. This tests the deviation's per-record
field lists exhaustively rather than sampling them.

**Completeness pass.** For each of the three introducing commits named in the
deviation (`6ef091f1953b`, `6f3cea5cbd0c`, `7cf9d50deb61`) I snapshotted **every**
record in all six ledger files at that commit and at HEAD and reported every
record whose content changed. A record edited in place but omitted from X-0005
would appear here. 194, 184 and 128 records were examined respectively.

**Content pass, 8 of 19 records**, adjudicated against the artifacts they cite.
The brief required at least 6 including V-0008, V-0009, E-0034 and EXP-0048; I
added X-0001, G-0015, EXP-0044 and V-0013, choosing the two most-edited records
(G-0015 with four edit commits, EXP-0044 with two) as the stress cases.

## 3. Structural result: the field lists are exact

Every one of the 19 records changed **exactly** the fields the deviation names,
no more and no fewer, and **no record changed a standing, disposition or class
field**. Checked against a blocklist including `verdict`, `status`, `result`,
`role`, `tier`, `disposition`, `class`, `standing`, `outcome`, `prereg`, `claim`,
`claims`, `target`, `capable_of_failure`, `falsifier`, `basis` and `reviewer`.

| record | fields X-0005 names | fields observed |
| --- | --- | --- |
| X-0001 | reason | reason |
| E-0034 | detection_floor | detection_floor |
| E-0037 | domain_checked, repro | domain_checked, repro |
| E-0044 | detection_floor | detection_floor |
| E-0048 | domain_checked | domain_checked |
| EXP-0036 | result_summary | result_summary |
| EXP-0039 | design | design |
| EXP-0044 | evidence, result_summary | evidence, result_summary |
| EXP-0045 | evidence, result_summary | evidence, result_summary |
| EXP-0047 | design, result_summary | design, result_summary |
| EXP-0048 | result_summary | result_summary |
| EXP-0050 | result_summary | result_summary |
| G-0015 | obligation | obligation |
| V-0008 | residual_doubts, transcript_sha256 | residual_doubts, transcript_sha256 |
| V-0009 | model_family | model_family |
| V-0010 | model_family | model_family |
| V-0011 | model_family | model_family |
| V-0012 | model_family | model_family |
| V-0013 | model_family | model_family |

Every field edited is descriptive: a reason, a detection floor, a domain note, a
repro line, a design, a result summary, an evidence list, an obligation text, a
residual-doubts paragraph, a transcript hash, a model-family attestation. None is
a verdict or a disposition.

## 4. Completeness result, including one thing X-0005 does not mention

The completeness pass found **no unlisted content edit** to any evidence,
experiment, review, deviation or claim record.

It did find six records not named in X-0005, all in `gaps.toml`, all changing only
`status`:

| gap | before | after | obligation text |
| --- | --- | --- | --- |
| G-0002 | open | discharged (`discharged_by` set) | unchanged |
| G-0005 | open | superseded | unchanged |
| G-0006 | open | superseded | unchanged |
| G-0008 | open | superseded | unchanged |
| G-0012 | open | superseded | unchanged |
| G-0014 | open | superseded | unchanged |

I judge these **outside the deviation's scope and correctly omitted**. A gap's
`status` is its lifecycle field: the ledger moves gaps open to discharged or
superseded as normal workflow, as with G-0016 and G-0017 during this same
recording, and the deviation-gating mechanism that freezes C-0002@3 depends on
that field being live. All six transitions are forward, none reverses, and no
obligation text moved with them. The distinction X-0005 draws is coherent, and
G-0015 is the proof of it: G-0015's *obligation* text was edited and **is** listed
as finding 15, while its `status` is untouched and still `open`.

I record the six explicitly so no later reader concludes they were hidden. If the
campaign's immutability rule is meant to cover gap `status` as well, then X-0005
is incomplete by exactly these six and by nothing else.

## 5. Content result: eight records adjudicated against their artifacts

Every correction moves the text **toward** the artifact. Several move it against
the campaign's own interest, which I take as evidence of good faith.

**V-0008 (findings 16, 17) — my own review record, so I can adjudicate it
directly.** `residual_doubts` went from 269 characters of generic caveat
("model-family and fresh-context facts are local attestations…") to 870
characters naming the actual doubts I reported: the lift not re-run, the G-0027
universe read as data, depth-2 realization being a separate step, the lattice tool
untracked and changed mid-review **with both exact hashes** `4e812678…` and
`e8175f87…`, n=9 and n=10 cross-checked only by verify11, and "two executions of
one verify11 binary count once". That is my finding list, and the original text
was not. The generic attestation caveat is retained as the closing clause, so
nothing was dropped. `transcript_sha256` was corrected twice and now reads
`ee800ef0…`; I hashed `reviews/referee/V-0008.transcript.toml` and it **matches
exactly**. Both edits are corrections toward the artifact, and the residual-doubts
edit strictly enlarges the caveat set.

**V-0009 (finding 18) and V-0010 to V-0012 (19-21).** `model_family` corrected
`openai-gpt` to `anthropic-claude`. All four are `reviewer =
orchestrator/amberbluff`, tier T0, and AmberBluff is attributed as Claude lineage
in `artifacts/math/t2-review/depth2-lemma-gpt/RESULT.md`. So the original label was
a systematic mislabel and the correction is right. Note the direction: it
*reduces* the apparent lineage diversity of the review set. A self-serving edit
would have gone the other way.

**V-0013 (finding 22).** `model_family` refined `anthropic-claude` to
`anthropic-claude-opus`, matching `reviewer = referee/opus-depth2-lemma`.

**E-0034 (finding 02).** `detection_floor` gained a sentence recording that the
T2 referee did not re-run the lift, supports none of the lift report's numbers,
and that the 169,250 versus 169,166 hinge-row gap of 84 "remains an open
question". That is an accurate transcription of my V-0008 caveat and it
**tightens** the floor rather than loosening it. It is now chronologically stale,
since G-0016 has resolved the 84 rows, but stale is not wrong.

**EXP-0048 (finding 13).** `result_summary` corrected "6,144/754,018 columns" to
"6,144/754,017 universe records", adding that the synthetic 5L would be appended
after those records to make 754,018 total for a completed arm. I verified this
against the artifact independently during the certificate review: the G-0027
universe has exactly 754,017 records and the synthetic 5L column is index 754,017.
The corrected number is right and the original was off by one.

**X-0001 (finding 01).** `reason` gained a carrier-bookkeeping paragraph stating
that 5E is universe record 0, that `--include-five-l` appends 5L at index 754017,
that the full-universe pass processed all 754,017 records, and that "the T2
referee confirmed that neither carrier is used by the 15,896-term certificate".
That last is my finding and it is correct: witness columns run 525143 to 708196,
excluding both 0 and 754017. `status` remains `reviewed` and `affects` is
unchanged.

**EXP-0044 (findings 08, 09).** `result_summary` went from a vague statement that
"only the campaign handoff and bead-330 multiplicity instruction preserve this
attempt" to a specific one naming
`artifacts/math/n11-stageA-exact-lift/run5-sketch-big-long/solve.stderr.log` with
SHA-256 `08215b99…`, noting the trace ends after Dixon iteration 100 of 20,000 and
that `solve.stdout.json` exists but is empty. I checked all three: **the hash
matches, the stdout file is 0 bytes, and the last stderr line is
`BIG_DIXON_STEP iteration=100/20000`.** `evidence` went from absent to
`["E-0050"]`. The verdict clause is unchanged in substance: it contributed no
mathematical result before and contributes none now.

**G-0015 (finding 15), the most-edited record at four edit commits.**
`obligation` was rewritten from a stale STAR-quarantine description to the current
state, recording what G-0181 through G-0187 closed. The decisive question is
whether the obligation was weakened. It was not: `status` is still `open`, the
text still says "The other 475 global kernel dimensions … still lack either
explicit lifts or a general loop-straightening theorem; the full target-specific
STAR quarantine remains unproved." Progress was recorded; nothing was discharged
by prose.

## 6. Verdict

**holds.** The deviation faithfully describes what was edited: its per-record
field lists are exact for all 19 records, no standing, disposition or class field
was touched anywhere, no unlisted content edit exists in any of the six ledger
files across all three introducing commits, and every one of the eight records I
adjudicated moves toward the artifact it cites, with three of them verified
against a hash or a count I computed myself.

**capable_of_failure.** This review would have returned refuted, not holds, on any
of: a record whose observed changed-field set differed from the deviation's list,
in either direction; any change to a verdict, status, tier, role, basis,
capable_of_failure or other standing field on a named record; any in-place content
edit to a record not listed in X-0005, which the completeness pass was built
specifically to surface and which it did surface for the six gap-status
transitions I then had to adjudicate; any edit moving text away from its cited
artifact, which would have shown as `08215b99…` not matching the stderr log, 0
bytes not being empty, iteration 100/20000 not being the last line, 754,017 not
matching the universe record count, `ee800ef0…` not matching the transcript file,
or `anthropic-claude` contradicting the reviewer identity; a weakened control,
meaning a loosened detection floor, a deleted residual doubt, or an obligation
narrowed or closed by prose while its status stayed open; or a gap status moving
backwards. Each of these was tested, not assumed.

## 7. Residual doubts

1. **Eleven of nineteen records were checked structurally but not adjudicated for
   content direction:** E-0037, E-0044, E-0048, EXP-0036, EXP-0039, EXP-0045,
   EXP-0047, EXP-0050, V-0010, V-0011, V-0012. For those I confirmed only that the
   changed-field set matches the deviation and touches no standing field. The brief
   asked for at least six; I did eight; the remaining eleven rest on the structural
   pass alone.
2. **The completeness pass compares introduction to HEAD.** An edit made and then
   reverted before HEAD would be invisible to it. The deviation's own per-commit
   attributions are the only evidence for intermediate states, and I verified those
   intermediate hops only for V-0008, where I confirmed both the `9255a1fe37c1` and
   `c9b88b2b06f2` transcript values.
3. **The six gap-status transitions are excluded on my judgment** that gap
   `status` is a lifecycle field rather than immutable content (§4). If the
   campaign's rule says otherwise, X-0005 is incomplete by six.
4. **E-0034's corrected text is now stale**, describing the 84-row hinge gap as an
   open question after G-0016 resolved it. Harmless, but it will mislead a reader
   who reads E-0034 without reading G-0016.
5. **I did not verify X-0005's own standing assertion**, that the corrections left
   the `c1553de7cfbe` baseline standing of C-0002@3 at INDEPENDENTLY_REPLAYED. That
   is a computation over the ledger I did not reproduce.
6. **I checked record content, not file structure.** Reordering, comment changes,
   or whitespace edits outside record bodies would not appear in my snapshots.
7. **I am not a neutral party to two of these findings.** X-0001 and V-0008 cite
   my own review, and E-0034 transcribes my caveat. I judged them correct because
   they match what I actually reported, which is the strongest available check on
   those three, but a reader should know the reviewer and the cited referee are
   the same agent.

**No-claim line.** This review adjudicates whether X-0005 faithfully describes the
in-place edits and whether those edits are legitimate corrections. It does not
re-adjudicate C-0002@3, does not verify the certificate or any lift, and does not
assert that in-place editing of immutable records was the right process choice,
only that what was done is accurately disclosed and did not alter any standing.
