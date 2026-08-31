# G-0126 deterministic continuation handoff

The G-0121 candidate is refuted, but its 348 exact master rows remain valid.
The next non-discretionary CEGIS batch is the 32 directions serialized in
`global_replay_v1.json`, bound by digest

```text
0cd2699dec0bc5ffd7cb81c1454aac79143ae4a37c571fcb707c85a55a5c459e
```

Each selected direction already has an exact nonzero residual for the
refuted candidate, with decimal-LF digest

```text
000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b
```

Those residuals certify rejection, but they are not yet the complete
`32 x 163,740` family price matrix needed to reopen the restricted master.
The highest-leverage continuation is therefore:

1. bind this receipt and price all 32 directions exactly for all 163,740
   records in frozen record order;
2. retain all old 348 rows and append the new zero-target rows, discarding a
   row only after an exact dependency certificate;
3. solve the resulting exact rational master over the complete frozen family;
4. if it returns a member, subject it to a fresh preregistered complete global
   replay; if it returns nonmembership, report only the bounded frozen-family
   obstruction and pivot atom families.

Do not interpret the large nonzero-direction count, the selected tuple
prefix, or another finite-row member as convergence.  Only exact global zero
changes the MAX11 identity claim; only statement-matched architecture replay
and independent review would then trigger Lean.
