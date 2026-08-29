# G-0059 clean-room joint-329 audit

This audit independently replays the frozen producer artifact in commit
`0d2d1a4`. It confirms the bounded modular conclusion:

```text
prime       joint residual / augmented rank    block-only residual / augmented rank
1,000,003   323 / 323                           322 / 322
1,000,033   323 / 323                           322 / 322
```

Thus the ordered joint family—sequence 92,489 followed by the 328 proper
mass-four atoms induced by the public MAX10 certificate—has no augmented
quotient gain over either frozen finite field.

## What was independently checked

- Recomputed the producer's scientific hash after recursively stripping its
  runtime fields; deliberate timing/memory mutations leave the digest fixed.
- Parsed all 402 MAX10 certificate terms, performed multiset cancellation,
  retained exactly 328 mass-four terms, and independently matched their typed
  incidence classes to the hash-bound G-0038 stream using canonical
  certificates plus NetworkX VF2.
- Recovered the exact certificate-term candidate order and matched the
  producer's complete 328-entry manifest byte-for-byte.
- Regenerated the 1,358 baseline columns and 329 joint candidate columns on the
  complete 99,858-row universe. The integer baseline, union, lambda row,
  candidate matrix, combined union, and ordered sparse stream hashes match.
- At each prime, verified a nonzero 1,288-by-1,288 pivot minor and replayed all
  70 normalized kernel vectors. The minor supplies rank at least 1,288; the 70
  independent free-coordinate-normalized kernel vectors supply rank at most
  1,288.
- Replayed `B^T w = lambda_C` and the sparse dual on all 1,358 baseline
  columns, checked `B A = h_R` for all 329 candidates, rebuilt every Schur
  residual and delta, and matched every per-column hash.
- Recomputed both full-prefix joint ranks directly at both primes. The
  328-only calculation is retained only as a subordinate diagnostic.
- Exercised a regression control where two singleton families each have no
  gain but their joint family does, guarding against the omission found during
  the pre-run adversarial review.

## Immutable bindings

```text
producer commit
  0d2d1a4
producer script
  dd743b702a99541e835b52bbdf5ec4c50c9650344bdf2ea0d4f81d22a7678ecd
producer report
  72ade3d6c9c507d6843f161419dc92b7b1273a299a7eff7c9def6a7d3e0ddb37
producer deterministic scientific payload
  9f5d1dfde5a8ccaa4e0e02d98a588e41025c1a973211a7829f14af9ab74c5d6b
independent_joint329_audit.py
  584bdbf1b1d7de637bd97acbfdaa8baa41157eca950baaaf73f2b7775851ceb2
independent_joint329_audit_v1.json.gz
  c4971bf6e2543f5646dcbde5e2deb1e88567edb57610d403484e054a63fd0537
audit canonical payload
  936499b3f3b15c8e72e7ee4706e89aa97ec5052dbd0f651920df8b97a4ef19c9
```

## Reproduce

```bash
.venv/bin/python -B artifacts/cleanroom/G-0059/independent_joint329_audit.py --self-test
.venv/bin/python -B artifacts/cleanroom/G-0059/independent_joint329_audit.py --workers 8
```

The executable refuses to overwrite an existing report. Remove or rename a
prior replay output deliberately before reproducing.

## Claim boundary

This is a two-prime modular no-gain certificate for one frozen 1,358-column
baseline and one ordered 329-column family. It does not establish the rank over
the rationals, cover all 132,728 proper mass-four atoms, or settle unrestricted
MAX11. The audit reuses the hash-bound G-0057 primitive-normal-form semantic
generator; it independently reconstructs the order, matrices, modular
certificates, Schur algebra, and ranks, but is not a second implementation of
that semantic kernel.
