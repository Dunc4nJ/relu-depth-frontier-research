# G-0051/G-0052 corrected mass-four preflight audit

## Verdict

**HARD PASS for the frozen preflight geometry; no rank verdict.**

The clean-room program imports none of the G-0047, G-0051, or G-0052
producer code. It reconstructs rows from disjoint signed supports, scans the
raw G-0038 orbit stream, and reconstructs columns with a separately written
base-five subset-state dynamic program. All 1,465 full-core mass-four column
fingerprints, support counts, and absolute hinge weights match G-0052.

This verdict verifies the corrected finite subject and makes S0 rank work
auditable. It does **not** compute the S0 rank, find a rational circuit, or
prove a mass-four or unrestricted MAX11 theorem.

## Independently recovered facts

| Quantity | Clean-room result |
|---|---:|
| primitive degree-four rows | 99,858 |
| degree-four universe SHA-256 | `500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2` |
| embedded degree-three rows | 10,065 |
| new rows beyond degree three | 89,793 |
| mass-four proper/full columns | 132,728 / 1,465 |
| literal columns through mass four | 137,503 |
| span-equivalent reduced columns | 134,684 |
| S0 total nonzeros | 12,331,131 |
| S0 exact nonzero-row union | 42,457 |
| S0 union SHA-256 | `43000a1a6ead56da88ce26dd4a6e862e5de522ee23fda6dcfcf8573b0214bfb0` |
| S0 min / median-low / max support | 714 / 8,155 / 21,854 |

The strongest hostile control is not cosmetic: **33,692 of the 42,457 S0
union rows are absent from the degree-three universe**. A 10,065-row S0
calculation would therefore omit most row types that actually occur.

The dense byte arithmetic also matches exactly. In particular, the lossless
S0 union restriction is `42,457 x 1,465`, or 497,596,040 bytes as `int64`
and 248,798,020 bytes for one `uint32` prime matrix. The literal complete
`99,858 x 137,503` `int64` matrix is 109,846,196,592 bytes.

## Rank-criterion review

For a selected column set, let `H` be its hinge matrix and `lambda` its
eleventh-difference row. Over any field,

```text
exists c: Hc = 0 and lambda*c != 0
iff lambda is not in rowspace(H)
iff rank([H; lambda]) = rank(H) + 1.
```

Thus a positive on a subset extends globally by assigning zero to omitted
columns, while a negative on a subset says nothing about omitted columns.
Full column rank modulo one prime certifies full column rank over `Q`, because
it exposes an integer minor nonzero modulo that prime. Neither modular rank
gain nor modular no-gain alone determines the rational rank difference; the
audit includes explicit must-fail examples in both directions.

## Controls prepared for G-0054

The forthcoming rank result is acceptable only with an extracted object:

- full column rank: frozen pivot-row list / square minor at each claimed
  prime, independently reconstructed and checked nonzero;
- nonzero-`lambda` circuit: explicit coefficients replaying to zero on all
  99,858 rows with `lambda*c != 0`;
- an intermediate exact rank: both a lower-bound minor and an independent
  upper-bound certificate.

A solver status, two agreeing rank integers, a sketch, or reuse of only the
10,065 degree-three rows is insufficient.

## Artifact bindings

- verifier SHA-256:
  `76c67f4499228fd07b3cdea782bf6fe7b351fe333948062484aa8285c9cdc616`
- report SHA-256:
  `0af7666d1c3d1e3259c6ecd5b67d500e29ac75e83ed0e17d3f2493638c2d1aa9`
- report canonical-payload SHA-256:
  `fb8799780a9a81850f824f405f3ed09aebccb9db68e5084f08400c45e59c79bd`
- subject G-0052 report SHA-256:
  `23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37`

Replay:

```bash
python -B artifacts/cleanroom/G-0051-mass4-preflight-audit/independent_mass4_preflight_audit.py --self-test
python -B artifacts/cleanroom/G-0051-mass4-preflight-audit/independent_mass4_preflight_audit.py \
  --workers 8 --output artifacts/cleanroom/G-0051-mass4-preflight-audit/replay.json
```

## Anti-ceremony and honesty record

Creation gate: the consumer is the research lead deciding whether G-0054 can
be trusted; the gate is promotion of the S0 rank result; the observed defect
is the earlier use of an incomplete 10,065-row universe; this audit retires
from active maintenance when G-0054 is adjudicated. Verdict: legitimate,
minimal gate.

Real-work audit: one executable enabler and one bounded audit report were
created. The enabler was exercised on all 1,465 columns. No MAX11 solution
was shipped; the value is preventing an invalid rank calculation from being
accepted. No plan item was closed or laundered.

Honesty inventory: no test was weakened or skipped; no mock, regenerated
golden, suppression, bypass, hidden failure, silenced evidentiary stderr, or
post-selected denominator was used. The small matrices and edge mutant are
identified as controls, not promoted as subject evidence. The full replay
ran 1,465/1,465 columns and the report explicitly withholds every rank and
unrestricted claim. Concurrent root test additions in commit `4b92520` were
outside this audit's authorship and are not evidence for this verdict. This
fresh subagent identity has no older sessions to mine. Strongest replayable
evidence: the verifier re-derives every S0 hinge fingerprint from the frozen
raw stream and fails closed on any mismatch. Disposition: clean within this
bounded review; nothing to correct or conceal.
