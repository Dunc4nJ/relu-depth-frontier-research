# G-0016: run7 hinge-union reconciliation

- Reviewer/executor: IndigoCarp (`openai-gpt` lineage)
- Date: 2026-09-03
- Bottom line: **CONFIRMED**
- Scope: the named run7 ELIFTQ02 matrix and named finalized sparse witness only

## Result

The proposed reconciliation is exact on the inspected artifacts. The problem matrix has a hinge-row universe of **169,250/169,250** directions across all **21,222/21,222** pivot columns. Restricting the same streamed CSC incidences to the witness's **15,896/21,222** nonzero coefficient columns leaves **169,166/169,250** directions. Their set difference is **84/169,250** directions. Those are hinge IDs 169166 through 169249 (combined zero-based rows 190399 through 190482).

Across the 84-row difference, the second pass found **1,214/5,326** distinct touching source columns among the zero-coefficient pivots and **0/84** rows with any nonzero-witness toucher. Equivalently, every column touching any of the 84 directions is absent from the finalized sparse witness. The finalizer rejects serialized zero coefficients and emits every reconstructed nonzero coefficient, so each omitted pivot coordinate is exactly zero in this witness.

This confirms the hypothesis: `union_hinge_rows = 169250` was built over all pivot columns, while the upstream certificate's 169166 directions are the union over the nonzero witness support.

## Input custody

| Input | Bytes | SHA-256 |
|---|---:|---|
| `artifacts/math/n11-stageA-exact-lift/run3-sketch-minor/stageA_sketch_problem.eliftq02` | 12,873,100,556/12,873,100,556 | `2db8c4acff53cd300e9766d3fd01a704f97bf170149c2d25bdffcb905369e5e6` |
| `artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_exact_witness.json` | 4,650,964/4,650,964 | `14ff53ee831a6bc2f5f2aa3a45420376f6676e30f1ca1f90253d26a6f386a238` |

The witness's embedded problem custody independently names the same problem byte count and SHA-256. The one-thread audit emitted a transient 3,026,058-byte JSON result with SHA-256 `39dd1ba1894fccbb96c2ab7e7b047c73466ead148b209945aafbe6f15de7670a`; the exact per-row mapping from that output is retained below in compressed canonical form.

Format/code references inspected at starting workspace commit `35e6b731bfe0c90b4769501c04ccbe4fb0da37f9`:

- `tools/exactlift/lift_large_rs/src/problem.rs`: SHA-256 `4cca089c1af1aca9cecdde3f7c7b2291ba38ce76deff49b42cf58960fb9bb30e`.
- `tools/exactlift/lift_large_rs/src/sketch_member.rs`: SHA-256 `017470796a3b60689ae41969681fee6cd9e8f860d2aec648b83a4f0b537b1510`.
- `tools/exactlift/sketch_member_lift.py`: SHA-256 `e6627a1aa746a7e57dfb18583ab55330b46ab2cbc15a2b009b059fb8295c0a9a`.
- Executed audit source (included verbatim below): SHA-256 `0e9bac5a89d28f1525973fb20eee379709b2d2678c04e777b721aec76b2daf0d`.

## Method

The ELIFTQ02 header decoded to 190,483/190,483 rows, 21,222/21,222 columns, 21,222/21,222 selected rows, and 1,072,596,018/1,072,596,018 CSC entries. With `n=11`, hinge rows begin at combined row `21222 + 11 = 21233`; hence the hinge universe denominator is `190483 - 21233 = 169250`. The computed byte layout ended exactly at 12,873,100,556/12,873,100,556 bytes, and the CSC offsets were monotone from 0 through 1,072,596,018.

Pass 1 streamed each CSC column's row-index slice and parallel value slice. It rejected an out-of-range row or stored zero value, then marked a 169250-bit all-column set and a second set only when that column's source ID occurred in the sparse witness. It consumed 1,072,596,018/1,072,596,018 row/value pairs; stored zero values were 0/1,072,596,018. Pass 2 streamed the row-index segment again, intersected each column with the discovered 84-row difference, and recorded source IDs. No matrix-sized array or 12.9 GB file image was loaded; the largest persistent arrays were the 21,223 offsets and three hinge-universe bit/lookup arrays.

The witness parser checked schema and `n`, uniqueness of all 15,896/15,896 listed source IDs, exact rational parsing, and nonzero value for all 15,896/15,896 serialized coefficients. All 15,896/15,896 support IDs matched exactly one of the 21,222 problem source IDs; the latter were also unique 21,222/21,222.

## Counts

| Quantity | Observed | Denominator / interpretation |
|---|---:|---|
| Pivot columns processed | 21,222 | 21,222 |
| Witness nonzero support columns | 15,896 | 21,222 |
| Witness-zero pivot columns | 5,326 | 21,222 |
| Distinct all-column hinge rows | 169,250 | 169,250 |
| Distinct support-column hinge rows | 169,166 | 169,250 |
| All-minus-support hinge rows | 84 | 169,250 |
| Difference rows with a nonzero-witness toucher | 0 | 84 |
| Distinct zero-coefficient columns touching the difference | 1,214 | 5,326 |
| Raw hinge entries over all columns | 855,008,797 | 1,072,596,018 |
| Raw hinge entries over support columns | 681,123,474 | 1,072,596,018 |
| Raw entries incident to the 84-row difference | 96,478 | 855,008,797 |

The 84 rows have 625 through 1,214 touching zero-coefficient source columns apiece (minimum/maximum, each over the 5,326 zero-column denominator). Their 96,478/96,478 summed incidences equal the second pass's raw difference-entry count, so no repeated `(row,column)` incidence was hidden by per-row deduplication.

## Controls

- Known-answer positive: a 3-column/4-hinge synthetic fixture had all-column union 3/4, support union 2/4, difference 1/4, and the exact sole toucher `[200]`; the unchanged set-accumulation kernel recovered all four facts.
- Deliberate negative: adding source column 200 to the synthetic support changed the difference from 1/4 to 0/4. The audit would therefore not remain green under the support-classification defect most relevant to G-0016.
- Subject structural controls: valid magic 1/1; exact file-layout end 12,873,100,556/12,873,100,556 bytes; monotone offsets ending at 1,072,596,018/1,072,596,018; in-range row IDs 1,072,596,018/1,072,596,018; nonzero stored values 1,072,596,018/1,072,596,018; unique problem source IDs 21,222/21,222; witness support IDs found 15,896/15,896; difference rows recovered by pass 2 84/84; nonzero-witness touchers 0/96,478 incidences.

## Resource/timing record

The recorded audit invocation used 1/1 Python process and at most 1 thread (well below the 4-thread cap). Peak RSS was 55,728 KiB / 16,777,216 KiB permitted. Internal timings on the retained invocation were 12.180147632025182 seconds / one complete pass 1, 4.694508737884462 seconds / one complete pass 2, and 17.042873114347458 seconds / one complete program invocation. External `time -p` on that same invocation reported 17.45 wall seconds / one run, 13.02 user seconds / one run, and 4.20 system seconds / one run. The separate SHA-256 custody pass reported 56.11 wall seconds / one run, 50.35 user seconds / one run, and 2.25 system seconds / one run.

## Exact commands

```bash
ssh -p 29562 -o BatchMode=yes root@ssh5.vast.ai 'cd /workspace/relu && time -p sha256sum artifacts/math/n11-stageA-exact-lift/run3-sketch-minor/stageA_sketch_problem.eliftq02 artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_exact_witness.json'
scp -P 29562 -o BatchMode=yes artifacts/math/n11-hinge-union-84/audit_stream.py root@ssh5.vast.ai:/tmp/indigocarp-g0016-audit_stream.py
ssh -p 29562 -o BatchMode=yes root@ssh5.vast.ai 'sha256sum /tmp/indigocarp-g0016-audit_stream.py && cd /workspace/relu && time -p python3 /tmp/indigocarp-g0016-audit_stream.py --problem artifacts/math/n11-stageA-exact-lift/run3-sketch-minor/stageA_sketch_problem.eliftq02 --witness artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_exact_witness.json > /tmp/indigocarp-g0016-audit.json && sha256sum /tmp/indigocarp-g0016-audit.json && stat -c "%s bytes" /tmp/indigocarp-g0016-audit.json'
```

The remote image lacked `/usr/bin/time`; POSIX shell `time -p` supplied wall/user/system time, while the program recorded Linux `ru_maxrss` itself.

## Exact 84-row toucher mapping

The following blob is the complete mapping requested, not a sample. Its decoded canonical JSON is an array of 84/84 objects with keys `hinge_id_zero_based`, `combined_row_zero_based`, and the full sorted `touching_source_columns` array. Canonical uncompressed bytes: 683,076/683,076; SHA-256 `6e36e0b2ee0c43f8b069d29e22a1f18e4c5c0b0dc4e228a8907df450904ac237`. Zlib level-9 bytes: 14,576/14,576; SHA-256 `eaae40d9b7365245697016b588917897819e64311bb9888b375c863940a8adcf`. Base64 characters: 19,436/19,436.

```text
eNrtnduO88qRZu/nMXztC/GQB/arNBob0/bGjIFpb8BuY4Bp9LuPxE8qK7VTqSSZyZPWVeKvEqkqRpKqP9aKiH/9rz/86bf/+Pe/
/PXXP//yt9/+7y//79e//fbLv//Pv//65z/8SzNcumH44x/+91/++r9+/eUvfw6/aYfG2j/+4T9/+8efbi/45e+//eNvf/r1lz/9
9n/+8R9//fsf/uVfXXPpB/fHcfFahutyPWmjpdXSaem1GC1Wi9Pitejw/qJFZ+l1ll5n6XWWXmfpdZZeZ+l1ll5nMTqL0VmMzmJ0
FqOzGJ3F6Dij46yOszrO6jir46yOs3pbq7e1Os7pOKfjnI5zOsDpjZwOcHo/p+O8jvM6zus4r/fzOtyPhzeX8YCmuWhptLRaOi29
Fh3QOC1eiw5vdXirw1sd3urwVoe3Ory1WnR4q8M7Ha4QNwpxo6A2imajaDaKZqNoNopmo2g2imajaDaKZqNoNopYo4g1ilFj7t/T
OyhijSLWKFSNQtUoVI1C1Vgdrog1VscpYo0i1ihijSLWOB2uwDUKXON0uALXKHCNAtcocI0i1txD5XWA14/rdZzXcYOOG3TcoLcd
dPigtx10lkFnGXSWQWfRPdZeLlrGw1sFrlXgWgWubZ0Wr0XHKX6t4tcqfq1u0VZhbHVvtopmqzC2ClyrULW61Vrdaq0i1io4rYLT
KjhG19roWhtda6NrbXStja610bU2utZG19roWhtdZKO7w+haG90dRpfc6JIbXXKjS250yY0ustFFNrrIRhfZ6CIbXWSji2wvnRan
5f7F8WRWN57VjWd141ndcVZ3ldXtZBUV296/Z7XonIqKVVSsomIVFauoWEXF6sFpFRyr4FhFxermsrq5rGJkdXNZhcrqrrJ6RloF
zipwVs9Iq/hZxc8qcFbPQauby+rmsrq5rG4uq5vL6jlodXNZBdwq4FaxtYqtVWytnoNWIbYKsdXtZBVpq0hbRdoq0laRtoq0VaSt
Im0VaaubyyrgVgG3CrhVwK1uIKcbyF0aLb0Wo8VqcVq8Fh2nx6/TLnDaBU67wOnx67QZXKOz6Cns9BR2ego7PYWd9ovTU9hp2zjt
F6f94rRfnPaL035x2i9OO8RphzjtEKcd4rQnnPaE02Zw2gVOu8Dp2eoUd2fuX9Q7KPxO4XcKv1PAnSLtFGKne9rpnna6p53i7hR3
p7g7xd25++F6IwXcKeBOkXYKsVOInULsFGKnEDs9P50i7RRppxA73dNO97TTPe0Ud6+4e8Xd60b3Cr9X+L3C7xV+r7h7Bdwr4F4B
9wq4V8C9Au4VcK+AewXcK+BekfaKtFekvaLpdfd73f1esfWKrVdQvT5avW57rxB7fYp6hdjrfveKtFekvW50r89Ur7+CvALuFWKv
EHvd4d7ev6cfXpH2irRXpL0i7RVpr0h7xdYrtl73tL+FuL3+kXfR0mrptPRajBarZRiXQd8b9L1B37sF9bb429JfLlpaLVaLvteM
Z+nbRovRope0Tote2eqVnU7W6YBO5+w6Lb0WnaXTWTqdpdNZOp2l1+G9Du/1yl6v7PXKXq80ej+jA4wOMHo/o/czOtzoAKsDrA6w
OsDqAKsDrH5AqzeyOk5Xvlccel35Xte69/rJvA7Qle8HHTDogEFvNOg4BcBcOi29FqPFavFaxpOZptHSatFxjY5rdECjcypipr1o
0XGtjmt1XKvjFE2jMBqF0SiMRqEyvQ7o7//SAQqHUTiMwmEUDqNwGIXDKBxG4TAKhzE6i8JhFA6jAIx/4twWHe50uLt/T4c7vbvT
2zqdRVExiorR/WAUHKOoGEXFKCpGUTGKitHdYXUHWEXFKipWAbDNRUujRS9RAMY/XG6L1eK0eC06XFfe6upa3R1Wd4DV1h//Drkt
+p4uq9Xlsbo8VtfF6rpYd/+ifginH0KXx+rXtLr77XD/on4y3fbjZ3h7cbr7x8/w29Jq6bQYLV6LDtCVcLoSTlfC6Zd2+qWdfmmn
Pei0B532oNOVcNqDTnvQaQ86PS5cf1/0Sm0+p53ltKWctpQz9+9ZLTqL0Q+hDeZ0BZ2uktNVcv6+6ADtEKdr5hVGrx/X68f1+nG9
flzf3l/itIxv5BVUr9/B65HndR95PfK8nnVev5/XL+Z153jdMl6/kddv5PUbef1GXr+R12/ktSe81Uv0sPJ6WHndR16/9P2zw+tD
w+sm8fqlvW4Lf//ddVt43RZeDyuvbeO1bby2zaA9MWjrD7pYgy7WoAsy6KNg0AUZdEEGXZBBF2TQHTDougy6EQZ9Bgy6PIO5LzpA
12XQE3rQ7z7odx/0uw+6SQbdHYMuwaC4D+Pd0VzGfX1dhnEZN/R1abXoJeOvcl30SnNf9L0xKs2Y87gtOovV4eNHSDMmNK6L01mc
DnA6wOl7Y1SaMVtxW3Rqr1d6vWTQSwadZdAPMeiVg145RqVpxg+N66J/jTdlM6Ywrst4GzZjtuK2tFr0Ev1+Y9rguozbphn/Imuv
j/JGSzsu41Uy+iAy+kAx+gi5LlaLG5cx7kZPU6Pnp9ED0Iz/Zbst+uL9leOdY8b/bF2X8fczelgZPXuMHiVGjxKjZ4hxOovr9Mox
Rkb3+/Xj4b70WnQWndrrV/H6VbxO7fWT6WY2Xj+Z7mmje9qMfzlel/G5ZLx+3PFPv+vi9BKnw73+pXf349Pm+l/mi5bxJcO4ia7/
ZdYXx41itFuv/4FutOgl+uGH8Ra1lzHS18WNi7svXsswLl7LeBdb7Zfr51czLq3+Nd5/dkwQXRerL4730fXzy2nRv7xeMtyX8bhW
796OF/K69Fr0vVZLpy92euV46a7/mbda9K/xIX5ddIDevdXv0Hp9UT98P36uWP2NafU3ptVflVZ/CFr9eXf9L/r4tmMytbVOL9Gz
3OpZbvUQt+Pf89fF6ovjfXtdxvdT4K4fhrezODvehm78r+x1GZ9ZTh89Th821/9W9Vpu3/N6ovgx7Xpb9MXxYeXH5GY7jOHvLpfb
p+91ue2e29Jr8eNyC3+nh851ue3r26Iv3s7SNWN2smvGHNJ1uV3Brhn/iu3a9ha423L/1+0l/XD7o627/sVxO9yOKYzrMp7Tj4+L
638ixpdcP4D6f/vvP6YT37f/OSQS347EN4lvNzX/beulwfsK2XBXPSneBrnxfpsUefOcKVfCp7301fPmPpY+74Isuosl0y9BTl3H
KfxVM+yXIon2Zla+3ShiVhGziphVxH5y8UriKkX3JjN/+Zigb+7Z90uQrm/Xytr77OR9PzOHr7PocW+1baweFz/5fT8zzW8/Z/t1
Fm0+q823GQJoPpMAnUVb0d7RTxwPKMusrbgvWNBPZQbtR3SgJ5jTbnXarU679RUr6CzarXHIoG3qtE2d9qfT/pwPIFwFDnGJ4Ygu
oBJmGZzo6zEKH6CKS0li0cTARf/ML7TrvHad167z2nVT2IZbhDi0z35IRxMDHjqLdp3XU9Fr8z1giDbfGyaiw7UHvR6HXltxPi/R
WbQj39OT29LOhCiCL0qLdUqLzSAryv0rqfrDWVyAW3SA8sq9kqo7YTA6XEm5XiRgMZgxAZ9xMzGNDlcu8AXaKA/aKyXYK2/eKzPY
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
qloU6aYQ8y9SvRWK2xg2ZWN02BjYGNgY2BjYGNgY2BjYGNgY2BjYGNgY2BjYGNgY2BjYGNgY2BjYGNgY2BjYGNgY2BjYGJvbGGgY
aBhoGGgYaBhoGNkaRgn/YpJ44VLiRY94gXiBeHF68QLjAuNifeMC1QLVAtUC1QLVAtUiW7WIOhbnsyrQKdAppugUZTyKtQUKzAnM
icOZE2d3JTIkiR4tAi3i7FpE3IeIihAYEKc1IF7Uh9B5QHaYLjvMtRxSegNeA14DXsPhvIZNhYalJsNWCsMyd+EuLUywFSKawpp+
gk/5CQY/AT8BP4HGEGgKaAo0hsBWwFbAVsBWwFagMQSNITAZaAxBYwj0BvQGGkPQGAIDAgOCxhBoETSG2M6VYD7HUoECcwJzAnOC
jhAM5lhrMMeQ8i8s/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+xea9KiZrGPgXNLBA
w0DDQMM4koZx0Ikc15MmjAuHcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGBcbGRcYFqgWpxONUCxwLHAseCKR+ZUz6wKr5s
2Ac6xa50CjwKPAo8CjyKfc4D2VigWHssiNnDdJDrjZRwJTyuBK4ErgSuBK4ErgSuBK4ErgSuBK4ErgSuBK4ErgSuBN0pUCZQJlAm
UCZQJlAmUCZQJmhEgTmBOYE5gTmBOYE5cWZzok2ZEwPmBOYE5gTmBOYE5gTmBOYE5gTmBOYE5gTmBOYE5gTmBF0mUCZQJlAmUCZQ
JlAm5ioTjPCg2QTKBLM7MCcwJzAnmN3xzbM7jupRdAmP4nq58CjwKPAo8CjwKPAo8CjwKPAo8CjwKPAo8CjwKPAo8CjoQIFO8WU6
xWk9CgSKrxYo6psTX6VM6HldtdkErkS+K0F7iZquRCFJYrIdYYr0ldhIi0j5EKEIgeyA7IDsgOywnexwtxwa9yw7jNZBIeehvV3y
2zIUMCDGx/ZEEaJPiRANIgQiBCIEIgQiBCIEIgQiBCIEIgQiBCIEIgQiBCIEIgQiBCIEIgQiBCIEIgQiBCIEIgQiBCIEIgQiBCIE
IgQixIFECJMSIVpECEQIRAhECEQIRAhECEQIRAhECEQIRAhECEQIRAhECCZrYEAwWYPJGvgQTNZgsgaTNZiswWQNJmswWQPHAscC
xwLH4nsma9iUR9HhUeBR4FHgUeBR4FHgUeBR4FHgUeBR4FHgUeBR4FHgUdBQAp0CnQKdAp0CnQKdYqFOgUfxlR7Fl/ScOLZOgUeB
R4FHgUdRx6M4uEDxneaES5kTPeYE5gTmBOYE5gTmBOYE5gTmBOYE5gTmBOYE5gTmBOYEHShQJlAmUCZQJlAmUCZQJlAmaD2BK4Er
gSuBK4ErgStxLlfCp1wJgyuBK4ErgSuBK4ErgSuBK4ErgSuBK4ErgSuBK4ErgStBlwmUCZSJScrEBXMCcwJzAnPiugyM8MCjoPUE
kzywKrAqsCqwKpjkkXIsGldctWj9sLZxMaSMC4txgXGBcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGB
cYFxgXGxnXExWbUwGBehcYFqgWqBaoFqsWvVYpQdihkXfTnxYnzAT/Mvrjss4V84/Av8C/yL0/sXiBeIF+uLFxgXGBcYFxgXGBcY
F9nGRVS1OJ9cgVWBVTHFqiijUzDlY7pAgTnxMCdOq0ycXZLIsCN6fAh8iNCH+M6hHTgP3zKtI7Qc0BseDSVWHszxMBloGoHJgMlw
OJPh0DM4vmX4xrZTN663eMJB8DgIOAg4CPSAQEVARaAHBEYCRgJGAkYCRgI9IOgBga1ADwh6QKAw0PyB5g80f0B2QHag6wMGBF0f
dq1F1O/6gCuBK4ErQdcHuj7stevD2nM2rs+EhGMx4FjgWOBY4FjgWOBY4FjgWOBY4FjgWOBY4FjgWOBY4FjgWDBnA9UC1QLVAtWC
ORsYFxgXGBfLjYu5qkW7W+NibdUCxwLHAscCxwLHYn+TNbr3xsUN1mJcYFxgXNQwLlAtUC1mqBZlHIsWq6KoVYFOcQqdYqpH8SJQ
LFQmcCVeXIm1JYk92RGhFmH3YEBkqA/7dR6ilgN6Q3294cVrOJ3QsJXJsENpIWorHKUVRFRMyDcS1h5cEVoHGbpBmxAMomZBoA1U
EQXcMieg3xH+7yLA/wxQPw7ud0jsu01xvNs7gB92i9X9Mma+DSyvgscDIL4eAh+W0e4afLt/T7RDhj0BXqeodffMqe+AGux8VOwM
b67Om78eNOcQ5vloOWDKSZj8niK/4OPS3LhPceMGbgw3hhvDjeHGcGO4MdwYbgw3hhvDjeHGcGO4MdwYbgw3hhvDjeHGcGO4MdwY
bgw3hhvDjeHGZ+fGJsWNW7gx3BhuTId38DEd3mHKdHgHLdPhnQ7vdHinwzsd3unwTod3OrzT4Z0O73R4p8M7Hd7p8E6Hdzq80+Gd
Du90eEeZoMM7Hd7p8E6H998bFzZlXHQYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXGBcYFxgXe2w6gGqBaoFqgWpxEtUCxwLH
Asfi1I5Ft0y12KFjYbZRLSzGBcYFxgXGBcbFW+OihGoxybFwKceix7HAscCxOL1jgVyBXLG+XIFVgVWBVYFVgVWBVZFtVUR1ivMJ
FJgTmBNTzIkyysTargSSxJkkidPaEWf3ITJEiB71AfXhtOpD3HmIyg5YDqe1HF70htBrQGiYLjTMNRnC8Re4C7gLuAtHdRc2lRaW
2gpbaQrL/IS7mDDBSIioCGs6CD7lIBgcBBwEHAT6PKAioCLQ5wEjASMBIwEjASOBPg/0ecBWoM8DfR6YrEG7B9o90O4B54HJGnR9
wIeg68N2ksQOJ2t0xxIoMCcwJzAn6PrAnI215mwMKf/C4l/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf4F/gX+Bf
4F/gX+Bf4F/gX2zepGKyhoF/QQMLNAw0DDSMI2kYB526cb1/E8aFw7jAuMC4wLjAuMC4wLjAuMC4wLjAuMC4wLjAuMC4wLjYyLhA
tUC1OJxqgWOBY4Fj8d2OxYTxHlgVXzblA51iVzoFHgUeBR4FHsU+54FsLFCsPRbE7GE6yPUtEq6Ex5XAlcCVwJXAlcCVwJXAlcCV
wJXAlcCVwJXAlcCVwJWgOwXKBMoEygTKBMoEygTKBMoEjSgwJzAnMCcwJzAnMCfObE60KXNiwJzAnMCcwJzAnMCcwJzAnMCcwJzA
nMCcwJzAnMCcwJygywTKBMoEygTKBMoEysRcZYIRHjSbQJlgdgfmBOYE5gSzO755dsdRPYou4VFc44JHgUeBR4FHgUeBR4FHgUeB
R4FHgUeBR4FHgUeBR4FHQQcKdIov0ylO61EgUHy1QFHfnPgqZULP66rNJnAl8l0J2kvUdCUKSRKT7QhTpK/ERlpEyocIRQhkB2QH
ZAdkh+1kh7vl0Lhn2WG0Dgo5D+3tkt+WoYABMT62J4oQfUqEaBAhECEQIRAhECEQIRAhECEQIRAhECEQIRAhECEQIRAhECEQIRAh
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
LEjOhFkZpWNy8jBjAiY75fJv/+P/A0kNcIo=
```

Decoder/check:

```python
import base64, hashlib, json, zlib
# Paste the whitespace-joined blob above into BLOB.
compressed = base64.b64decode("".join(BLOB.split()))
assert hashlib.sha256(compressed).hexdigest() == "eaae40d9b7365245697016b588917897819e64311bb9888b375c863940a8adcf"
raw = zlib.decompress(compressed)
assert len(raw) == 683076
assert hashlib.sha256(raw).hexdigest() == "6e36e0b2ee0c43f8b069d29e22a1f18e4c5c0b0dc4e228a8907df450904ac237"
mapping = json.loads(raw)
assert len(mapping) == 84
```

Per-row count and toucher-list digest below provide a readable index. Each count denominator is the 5,326 zero-coefficient pivot columns. Each digest hashes that row's sorted touching source IDs as concatenated little-endian unsigned 64-bit integers.

| Hinge ID (0-based) | Combined row (0-based) | Touchers / 5,326 | Toucher-list SHA-256 |
|---:|---:|---:|---|
| 169166 | 190399 | 827 / 5,326 | `01f178deddd1b552d07f56ac63e24926c8421897f3da7eb97016ef4220ae5958` |
| 169167 | 190400 | 1,127 / 5,326 | `426fda50dafe50f232e6f49b558080ea80fe8027305a63a6154236bf15b48b36` |
| 169168 | 190401 | 1,185 / 5,326 | `e76f427b87d2041122729bc360991d70684cdddcdc78ac826850907d1bca25a0` |
| 169169 | 190402 | 1,181 / 5,326 | `2d05a2afc953452e9e06692604ec6919aaf6128f16a4e8edf49731139d672e56` |
| 169170 | 190403 | 1,091 / 5,326 | `d9f0da21ca67a43685d95b1e8d48bff81d9872a424a86a7bcb4830cb73baaf82` |
| 169171 | 190404 | 1,168 / 5,326 | `668057cb0dc34912bd2bd085334b47131bf0f8a19e2f2678c92d12e3df8d5561` |
| 169172 | 190405 | 1,214 / 5,326 | `43cd604305733da4a2c6b534e9bd1a4139cb6f9f0bde5ff1f669fb6f247eee22` |
| 169173 | 190406 | 1,211 / 5,326 | `3f9e233bd528dfbde0371b7d3bdf778b68becbf27c7724e39b6e6e7df2af90dd` |
| 169174 | 190407 | 1,179 / 5,326 | `0ab1f9748393aa7891d8a669365275cd092f76e415e9219a1dcefd03c6064871` |
| 169175 | 190408 | 1,212 / 5,326 | `c5a118fd112ce4b7ec1cbdff2ade1d5b9820d7d405cb7b9bc2a49fd87315a773` |
| 169176 | 190409 | 1,210 / 5,326 | `4ce4eaa1cf7e7c7e180458b70ff060e3c9cd683e2e8c36d7da822c90f60b0a0a` |
| 169177 | 190410 | 1,189 / 5,326 | `6024badc4841842da0f832695dd9144b3ac6c175b5953de7716c21a60cbeb880` |
| 169178 | 190411 | 1,198 / 5,326 | `3c5bf837d1fcbb704d50757ddb3a792e35e6efee96c735b99c7fbceaf77e343b` |
| 169179 | 190412 | 1,187 / 5,326 | `14db15c566f4fc576ff28f7dafb18a596658969c02ec2ae70132b705efb55d5d` |
| 169180 | 190413 | 1,097 / 5,326 | `0cb214bd28b880884af0b8133a61ae5dd90252742946b262b137c8ac207c4c2c` |
| 169181 | 190414 | 1,151 / 5,326 | `af96e2efd8d7225f0b95aca8a398372b3c43e5ec3b6f59bbf910809d7ba9d875` |
| 169182 | 190415 | 1,214 / 5,326 | `43cd604305733da4a2c6b534e9bd1a4139cb6f9f0bde5ff1f669fb6f247eee22` |
| 169183 | 190416 | 1,211 / 5,326 | `3fc67f001bd9858fee2a7ee22263a809595144de09eb7225cf14ecfefced90e8` |
| 169184 | 190417 | 1,180 / 5,326 | `6c5ebfcd5e4513c5ea03e6ac5d9b6338c91aa49e397cff73ffbb9580c2a75c17` |
| 169185 | 190418 | 1,212 / 5,326 | `c5a118fd112ce4b7ec1cbdff2ade1d5b9820d7d405cb7b9bc2a49fd87315a773` |
| 169186 | 190419 | 1,210 / 5,326 | `4ce4eaa1cf7e7c7e180458b70ff060e3c9cd683e2e8c36d7da822c90f60b0a0a` |
| 169187 | 190420 | 1,200 / 5,326 | `3f8030519becf89c37cdb89cf203f0b21e25106d6210669133c1feeb204320a4` |
| 169188 | 190421 | 1,202 / 5,326 | `6c519db15fde136f5b5967199238f0dc6ec2674e3a6c088f8ab9310aa1d22392` |
| 169189 | 190422 | 1,204 / 5,326 | `a2d9ef6816ed089a5037df82cf5822cee4cbb25ba0479daa36852676e59725e4` |
| 169190 | 190423 | 1,195 / 5,326 | `b1d12187fa5117337549f2f1802d981b858d91e3eff9ba1713e652b1d6a8c73e` |
| 169191 | 190424 | 1,195 / 5,326 | `b1d12187fa5117337549f2f1802d981b858d91e3eff9ba1713e652b1d6a8c73e` |
| 169192 | 190425 | 1,204 / 5,326 | `a2d9ef6816ed089a5037df82cf5822cee4cbb25ba0479daa36852676e59725e4` |
| 169193 | 190426 | 1,202 / 5,326 | `6c519db15fde136f5b5967199238f0dc6ec2674e3a6c088f8ab9310aa1d22392` |
| 169194 | 190427 | 1,200 / 5,326 | `3f8030519becf89c37cdb89cf203f0b21e25106d6210669133c1feeb204320a4` |
| 169195 | 190428 | 1,210 / 5,326 | `4ce4eaa1cf7e7c7e180458b70ff060e3c9cd683e2e8c36d7da822c90f60b0a0a` |
| 169196 | 190429 | 1,212 / 5,326 | `c5a118fd112ce4b7ec1cbdff2ade1d5b9820d7d405cb7b9bc2a49fd87315a773` |
| 169197 | 190430 | 1,176 / 5,326 | `b6fb809676cf8326d5e1326b6ea782b16d12ba6995e535e165af1086a07e99ee` |
| 169198 | 190431 | 1,208 / 5,326 | `f3ce5fa233aa8c74b78cdd698649d669577904ef8d5f34e37005c65a02411107` |
| 169199 | 190432 | 1,210 / 5,326 | `e92b68d261beb4421a040fbcc0364b8d243c5b66270fd2a30272835a72b50919` |
| 169200 | 190433 | 1,092 / 5,326 | `8e5f789c5d9976c3ffe9a65fd92f0720935a5ab4da6e2d69963f460772ca34b6` |
| 169201 | 190434 | 1,092 / 5,326 | `8e5f789c5d9976c3ffe9a65fd92f0720935a5ab4da6e2d69963f460772ca34b6` |
| 169202 | 190435 | 1,210 / 5,326 | `e92b68d261beb4421a040fbcc0364b8d243c5b66270fd2a30272835a72b50919` |
| 169203 | 190436 | 1,208 / 5,326 | `f3ce5fa233aa8c74b78cdd698649d669577904ef8d5f34e37005c65a02411107` |
| 169204 | 190437 | 1,176 / 5,326 | `b6fb809676cf8326d5e1326b6ea782b16d12ba6995e535e165af1086a07e99ee` |
| 169205 | 190438 | 1,212 / 5,326 | `c5a118fd112ce4b7ec1cbdff2ade1d5b9820d7d405cb7b9bc2a49fd87315a773` |
| 169206 | 190439 | 1,210 / 5,326 | `4ce4eaa1cf7e7c7e180458b70ff060e3c9cd683e2e8c36d7da822c90f60b0a0a` |
| 169207 | 190440 | 1,200 / 5,326 | `3f8030519becf89c37cdb89cf203f0b21e25106d6210669133c1feeb204320a4` |
| 169208 | 190441 | 1,202 / 5,326 | `6c519db15fde136f5b5967199238f0dc6ec2674e3a6c088f8ab9310aa1d22392` |
| 169209 | 190442 | 1,204 / 5,326 | `a2d9ef6816ed089a5037df82cf5822cee4cbb25ba0479daa36852676e59725e4` |
| 169210 | 190443 | 1,195 / 5,326 | `b1d12187fa5117337549f2f1802d981b858d91e3eff9ba1713e652b1d6a8c73e` |
| 169211 | 190444 | 1,195 / 5,326 | `b1d12187fa5117337549f2f1802d981b858d91e3eff9ba1713e652b1d6a8c73e` |
| 169212 | 190445 | 1,204 / 5,326 | `a2d9ef6816ed089a5037df82cf5822cee4cbb25ba0479daa36852676e59725e4` |
| 169213 | 190446 | 1,202 / 5,326 | `6c519db15fde136f5b5967199238f0dc6ec2674e3a6c088f8ab9310aa1d22392` |
| 169214 | 190447 | 1,200 / 5,326 | `3f8030519becf89c37cdb89cf203f0b21e25106d6210669133c1feeb204320a4` |
| 169215 | 190448 | 1,180 / 5,326 | `6c5ebfcd5e4513c5ea03e6ac5d9b6338c91aa49e397cff73ffbb9580c2a75c17` |
| 169216 | 190449 | 1,097 / 5,326 | `0cb214bd28b880884af0b8133a61ae5dd90252742946b262b137c8ac207c4c2c` |
| 169217 | 190450 | 1,187 / 5,326 | `14db15c566f4fc576ff28f7dafb18a596658969c02ec2ae70132b705efb55d5d` |
| 169218 | 190451 | 1,198 / 5,326 | `3c5bf837d1fcbb704d50757ddb3a792e35e6efee96c735b99c7fbceaf77e343b` |
| 169219 | 190452 | 1,189 / 5,326 | `6024badc4841842da0f832695dd9144b3ac6c175b5953de7716c21a60cbeb880` |
| 169220 | 190453 | 1,179 / 5,326 | `0ab1f9748393aa7891d8a669365275cd092f76e415e9219a1dcefd03c6064871` |
| 169221 | 190454 | 1,091 / 5,326 | `d9f0da21ca67a43685d95b1e8d48bff81d9872a424a86a7bcb4830cb73baaf82` |
| 169222 | 190455 | 857 / 5,326 | `e78303bafefab19b72ac61fbf27a2b591b52acf135f3228ab75611152f1b02ae` |
| 169223 | 190456 | 1,119 / 5,326 | `ec4c3e0a3e87bde5fa9c044e361cd2abb2d9b3125c1d98512ad87872f6febba9` |
| 169224 | 190457 | 1,112 / 5,326 | `abd71d715f38f534d25da66ba66e003c623794f7598ee4f139650e9e2a70ae6d` |
| 169225 | 190458 | 1,047 / 5,326 | `ee7607c458c4f7b21b6413a98d1eee0f7b2de6c9ae31a8cb97678ca16e89d644` |
| 169226 | 190459 | 1,160 / 5,326 | `d6e33691b31cf7afe6719f472047e5e768fd5cc66985aa5ebd179839bac754a4` |
| 169227 | 190460 | 1,184 / 5,326 | `bc1daf21e7c95d6e85d5f62efe15f7d3d2b24fba0eb91d5ab7d28668279b3b8c` |
| 169228 | 190461 | 1,179 / 5,326 | `ce42dd19637ff7949a55b833725caf9a1aaf609a3838662651555835ce538fbe` |
| 169229 | 190462 | 1,171 / 5,326 | `4518f5f4178a8a479d07db89ac60efb97aba2ba06472f99c936a8a0edb095e11` |
| 169230 | 190463 | 1,181 / 5,326 | `d9fe070c34ec7cbfe32ef9a52b26b8d57dd124328fbcc428286f0b5aa4b4aa99` |
| 169231 | 190464 | 1,139 / 5,326 | `69bdc13b8eb3812033a5ecaaeb2586bdeaf979da77a33468fe85fbe36e793970` |
| 169232 | 190465 | 1,158 / 5,326 | `848e06cdce9aa1ced69dfac1b67bdadb14ac351dd29004f655147cd36fa3ac2a` |
| 169233 | 190466 | 1,197 / 5,326 | `7e568b02bfd7ce76b97d782cbec9db1f443c772aac8516a0e650a0715210359b` |
| 169234 | 190467 | 1,201 / 5,326 | `f08316982251adbec287a15cb4ad80ee07cc859b7deba103e3c3d9ecedf3bcaa` |
| 169235 | 190468 | 1,195 / 5,326 | `56096abf955918db59beb40d4580b040c352f1c7f9bc7f2871b7c5a8882ec250` |
| 169236 | 190469 | 1,169 / 5,326 | `8fc6b484e4c7f889127ac3485eb4746c495e603ea534455348b6a035be459665` |
| 169237 | 190470 | 1,097 / 5,326 | `0cb214bd28b880884af0b8133a61ae5dd90252742946b262b137c8ac207c4c2c` |
| 169238 | 190471 | 1,187 / 5,326 | `14db15c566f4fc576ff28f7dafb18a596658969c02ec2ae70132b705efb55d5d` |
| 169239 | 190472 | 1,198 / 5,326 | `3c5bf837d1fcbb704d50757ddb3a792e35e6efee96c735b99c7fbceaf77e343b` |
| 169240 | 190473 | 1,189 / 5,326 | `6024badc4841842da0f832695dd9144b3ac6c175b5953de7716c21a60cbeb880` |
| 169241 | 190474 | 1,179 / 5,326 | `0ab1f9748393aa7891d8a669365275cd092f76e415e9219a1dcefd03c6064871` |
| 169242 | 190475 | 1,091 / 5,326 | `d9f0da21ca67a43685d95b1e8d48bff81d9872a424a86a7bcb4830cb73baaf82` |
| 169243 | 190476 | 748 / 5,326 | `aee28b8b894e2d96a99e1a671d774b701cfec6c68e6df090bc766bf68aa19346` |
| 169244 | 190477 | 973 / 5,326 | `b2c4ff777a98bb82ac1a1b6c7a7a82d7440020a554ac5497c9034676b4a72ea2` |
| 169245 | 190478 | 989 / 5,326 | `a27de91c2210fcce5e0cbf99cc7f228dd2e5c70b48458aca2d01b1a0634a60cd` |
| 169246 | 190479 | 1,059 / 5,326 | `38cfa5ccd610561ba2487172baeb08e149a47c606066cd87f6aa3831eef3af30` |
| 169247 | 190480 | 1,077 / 5,326 | `7e43d65c616b034216010f0a2b57f7e1f28ba439f31a2bbc7b9f6810a0f24495` |
| 169248 | 190481 | 1,002 / 5,326 | `231080d139cbc60b8b00dfb062eb90f68264771d81b2712f5adf3bd01b3d94e7` |
| 169249 | 190482 | 625 / 5,326 | `25ed5d44c9901fa7a342a734431e12fb192217cb6d39a7d0606ed2f183882048` |

<details>
<summary>Executed audit source (verbatim)</summary>

```python
#!/usr/bin/env python3
"""Bounded streaming incidence audit for G-0016 (temporary execution source)."""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import struct
import time
from fractions import Fraction
from pathlib import Path

import numpy as np


EXPECTED_SCHEMA = "max11-exactlift-witness-v1"
EXPECTED_MAGIC = b"ELIFTQ02"
EXPECTED_N = 11


def accumulate(
    all_seen: np.ndarray,
    support_seen: np.ndarray,
    hinge_ids: np.ndarray,
    is_support: bool,
) -> None:
    all_seen[hinge_ids] = True
    if is_support:
        support_seen[hinge_ids] = True


def self_test() -> dict[str, str]:
    # Known answer: support columns 100 and 300 touch {0,2}; zero column 200
    # adds hinge 1, so all-support is exactly {1}, touched only by column 200.
    columns = {
        100: np.array([0, 2], dtype=np.uint32),
        200: np.array([1, 2, 2], dtype=np.uint32),
        300: np.array([2], dtype=np.uint32),
    }
    all_seen = np.zeros(4, dtype=np.bool_)
    support_seen = np.zeros(4, dtype=np.bool_)
    support = {100, 300}
    for source, hinges in columns.items():
        accumulate(all_seen, support_seen, hinges, source in support)
    difference = np.flatnonzero(all_seen & ~support_seen).tolist()
    touching = {
        hinge: [source for source, hinges in columns.items() if hinge in hinges]
        for hinge in difference
    }
    assert np.flatnonzero(all_seen).tolist() == [0, 1, 2]
    assert np.flatnonzero(support_seen).tolist() == [0, 2]
    assert difference == [1]
    assert touching == {1: [200]}

    # Deliberately defective support: marking column 200 nonzero must destroy
    # the one-row difference. A result invariant to this mutation is broken.
    bad_support_seen = np.zeros(4, dtype=np.bool_)
    for source, hinges in columns.items():
        if source in {100, 200, 300}:
            bad_support_seen[hinges] = True
    assert np.flatnonzero(all_seen & ~bad_support_seen).tolist() == []
    return {
        "known_answer_positive": "PASS: all=3/4, support=2/4, difference=1/4, toucher=[200]",
        "support_mutation_negative": "PASS: adding source 200 to support changed difference 1/4 -> 0/4",
    }


def read_header(path: Path) -> tuple[dict[str, int | str], np.ndarray, dict[str, int]]:
    with path.open("rb", buffering=16 << 20) as stream:
        magic = stream.read(8)
        if magic != EXPECTED_MAGIC:
            raise ValueError(f"magic {magic!r} != {EXPECTED_MAGIC!r}")
        rows, columns, selected = struct.unpack("<III", stream.read(12))
        (nnz,) = struct.unpack("<Q", stream.read(8))
        offsets = np.fromfile(stream, dtype="<u8", count=columns + 1)
    if len(offsets) != columns + 1:
        raise ValueError("short CSC offsets")
    if offsets[0] != 0 or offsets[-1] != nnz or np.any(offsets[1:] < offsets[:-1]):
        raise ValueError("invalid CSC offsets")

    row_start = 28 + 8 * (columns + 1)
    value_start = row_start + 4 * nnz
    selected_start = value_start + 8 * nnz
    rhs_start = selected_start + 4 * columns
    source_start = rhs_start + 8 * rows
    expected_bytes = source_start + 8 * columns
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(f"file bytes {actual_bytes} != layout bytes {expected_bytes}")
    if selected != columns:
        raise ValueError(f"selected rows {selected} != columns {columns}")
    return (
        {
            "magic": magic.decode("ascii"),
            "rows": rows,
            "columns": columns,
            "selected_rows": selected,
            "nnz": nnz,
            "bytes": actual_bytes,
        },
        offsets,
        {
            "row_start": row_start,
            "value_start": value_start,
            "selected_start": selected_start,
            "rhs_start": rhs_start,
            "source_start": source_start,
        },
    )


def parse_witness(path: Path) -> tuple[dict, dict[int, Fraction]]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if document.get("schema") != EXPECTED_SCHEMA or int(document.get("n", -1)) != EXPECTED_N:
        raise ValueError("wrong witness schema or n")
    coefficients: dict[int, Fraction] = {}
    for entry in document["coefficients"]:
        source = int(entry["column"])
        if source in coefficients:
            raise ValueError(f"repeated witness source column {source}")
        coefficient = Fraction(entry["coefficient"])
        if coefficient == 0 or coefficient.denominator <= 0:
            raise ValueError(f"noncanonical/zero sparse coefficient at {source}")
        coefficients[source] = coefficient
    return document, coefficients


def read_source_indices(
    path: Path, source_start: int, columns: int
) -> np.ndarray:
    with path.open("rb", buffering=16 << 20) as stream:
        stream.seek(source_start)
        source_indices = np.fromfile(stream, dtype="<u8", count=columns)
    if len(source_indices) != columns:
        raise ValueError("short source-index array")
    if len(np.unique(source_indices)) != columns:
        raise ValueError("repeated source index in ELIFTQ02")
    return source_indices


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", required=True, type=Path)
    parser.add_argument("--witness", required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    controls = self_test()
    witness, coefficients = parse_witness(args.witness)
    header, offsets, layout = read_header(args.problem)
    rows = int(header["rows"])
    columns = int(header["columns"])
    nnz = int(header["nnz"])
    source_indices = read_source_indices(args.problem, layout["source_start"], columns)
    source_to_position = {int(source): position for position, source in enumerate(source_indices)}
    unknown_support = sorted(set(coefficients) - set(source_to_position))
    if unknown_support:
        raise ValueError(f"witness has {len(unknown_support)} non-pivot source IDs")
    support_position = np.array(
        [int(source) in coefficients for source in source_indices], dtype=np.bool_
    )
    if int(support_position.sum()) != len(coefficients):
        raise ValueError("witness support/pivot intersection count mismatch")

    n = int(witness["n"])
    hinge_base = columns + n
    hinge_universe = rows - hinge_base
    if hinge_universe <= 0:
        raise ValueError("empty hinge universe")
    all_seen = np.zeros(hinge_universe, dtype=np.bool_)
    support_seen = np.zeros(hinge_universe, dtype=np.bool_)
    raw_hinge_entries_all = 0
    raw_hinge_entries_support = 0
    stored_zero_values = 0
    pass1_started = time.monotonic()
    with args.problem.open("rb", buffering=16 << 20) as row_stream, args.problem.open(
        "rb", buffering=16 << 20
    ) as value_stream:
        row_stream.seek(layout["row_start"])
        value_stream.seek(layout["value_start"])
        for column in range(columns):
            count = int(offsets[column + 1] - offsets[column])
            row_ids = np.fromfile(row_stream, dtype="<u4", count=count)
            values = np.fromfile(value_stream, dtype="<i8", count=count)
            if len(row_ids) != count or len(values) != count:
                raise ValueError(f"short CSC column {column}")
            if count and int(row_ids.max()) >= rows:
                raise ValueError(f"row outside universe in column {column}")
            stored_zero_values += int(np.count_nonzero(values == 0))
            is_hinge = row_ids >= hinge_base
            hinge_ids = row_ids[is_hinge] - hinge_base
            raw_hinge_entries_all += len(hinge_ids)
            if support_position[column]:
                raw_hinge_entries_support += len(hinge_ids)
            accumulate(all_seen, support_seen, hinge_ids, bool(support_position[column]))
        if row_stream.tell() != layout["value_start"]:
            raise ValueError("row-index pass ended at wrong byte")
        if value_stream.tell() != layout["selected_start"]:
            raise ValueError("value pass ended at wrong byte")
    if stored_zero_values:
        raise ValueError(f"ELIFTQ02 stores {stored_zero_values} zero CSC values")
    pass1_seconds = time.monotonic() - pass1_started

    difference = np.flatnonzero(all_seen & ~support_seen).astype(np.int64)
    difference_lookup = np.full(hinge_universe, -1, dtype=np.int32)
    difference_lookup[difference] = np.arange(len(difference), dtype=np.int32)
    touching_positions: list[list[int]] = [[] for _ in difference]
    raw_difference_entries = 0
    pass2_started = time.monotonic()
    with args.problem.open("rb", buffering=16 << 20) as row_stream:
        row_stream.seek(layout["row_start"])
        for column in range(columns):
            count = int(offsets[column + 1] - offsets[column])
            row_ids = np.fromfile(row_stream, dtype="<u4", count=count)
            if len(row_ids) != count:
                raise ValueError(f"short second-pass CSC column {column}")
            is_hinge = row_ids >= hinge_base
            hinge_ids = row_ids[is_hinge] - hinge_base
            slots = difference_lookup[hinge_ids]
            slots = slots[slots >= 0]
            raw_difference_entries += len(slots)
            for slot in np.unique(slots):
                touching_positions[int(slot)].append(column)
    pass2_seconds = time.monotonic() - pass2_started

    difference_rows = []
    support_touchers = 0
    touching_source_union: set[int] = set()
    for slot, hinge_id in enumerate(difference.tolist()):
        positions = touching_positions[slot]
        if not positions:
            raise ValueError(f"difference hinge {hinge_id} has no touching column")
        sources = [int(source_indices[position]) for position in positions]
        present = [source for source in sources if source in coefficients]
        support_touchers += len(present)
        touching_source_union.update(sources)
        difference_rows.append(
            {
                "hinge_id_zero_based": hinge_id,
                "combined_row_zero_based": hinge_base + hinge_id,
                "touching_pivot_positions_zero_based": positions,
                "touching_source_columns": sources,
                "touching_columns_numerator": len(sources),
                "touching_columns_denominator": columns,
                "witness_nonzero_touching_columns_numerator": len(present),
                "witness_nonzero_touching_columns_denominator": len(sources),
            }
        )
    if support_touchers:
        raise ValueError(f"difference rows have {support_touchers} support-column touchers")

    all_count = int(all_seen.sum())
    support_count = int(support_seen.sum())
    observed = {
        "all_column_hinge_union_numerator": all_count,
        "all_column_hinge_union_denominator": hinge_universe,
        "support_column_hinge_union_numerator": support_count,
        "support_column_hinge_union_denominator": hinge_universe,
        "difference_hinge_rows_numerator": len(difference),
        "difference_hinge_rows_denominator": hinge_universe,
        "pivot_columns_numerator": columns,
        "pivot_columns_denominator": columns,
        "witness_support_columns_numerator": len(coefficients),
        "witness_support_columns_denominator": columns,
        "zero_coefficient_pivot_columns_numerator": columns - len(coefficients),
        "zero_coefficient_pivot_columns_denominator": columns,
        "difference_touching_source_columns_numerator": len(touching_source_union),
        "difference_touching_source_columns_denominator": columns - len(coefficients),
        "support_touching_difference_rows_numerator": support_touchers,
        "support_touching_difference_rows_denominator": len(difference),
        "raw_hinge_entries_all_numerator": raw_hinge_entries_all,
        "raw_hinge_entries_all_denominator": nnz,
        "raw_hinge_entries_support_numerator": raw_hinge_entries_support,
        "raw_hinge_entries_support_denominator": nnz,
        "raw_difference_entries_numerator": raw_difference_entries,
        "raw_difference_entries_denominator": raw_hinge_entries_all,
    }
    expected_hinge_union = int(
        witness["exact_verification"]["union_hinge_rows_denominator"]
    )
    verdict = (
        "CONFIRMED"
        if all_count == expected_hinge_union
        and support_count == 169166
        and len(difference) == 84
        and support_touchers == 0
        else "REFUTED"
    )
    output = {
        "schema": "max11-g0016-hinge-union-audit-v1",
        "verdict": verdict,
        "controls": controls,
        "problem_header": header,
        "layout": layout,
        "witness_problem_custody": witness["problem_custody"],
        "observed": observed,
        "difference_rows": difference_rows,
        "timing_seconds": {
            "pass1_rows_and_values": pass1_seconds,
            "pass2_rows": pass2_seconds,
            "total": time.monotonic() - started,
        },
        "threads_maximum": 1,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "no_claim": (
            "This audit only reconciles the named run7 problem-row union with the "
            "named sparse witness support. It does not reverify the rational identity, "
            "the upstream translation, the realization lemma, or MAX_11 itself."
        ),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
```

</details>

## Workspace rail

`./skill-runtime verify-quick` was run after writing this artifact and exited 1 with 22 pre-existing/campaign-ledger immutability findings (SE-10 entries in canonical ledger files outside this task). I did not edit those prohibited ledger paths and do not report the workspace rail as green. The audit-specific mapping/hash checks above passed independently.

## Conclusion and no-claim

**G-0016 data verdict: CONFIRMED.** The 84-row discrepancy is exactly the set of hinge directions introduced only by pivot columns whose run7 witness coefficient is zero; there are no nonzero-support exceptions (0/84 rows, 0/96,478 incidences). This supplies the requested reconciliation for the orchestrator/referee to discharge G-0016.

**No-claim:** This audit only reconciles the named run7 problem-row union with the named sparse witness support. It did not reverify the rational identity, the upstream translation, the depth-2 realization lemma, or `MAX_11` itself. It also did not reconstruct the original hinge direction vectors from the ELIFTQ02 row IDs; the exact audited object here is CSC row incidence keyed by the builder-assigned hinge IDs.

