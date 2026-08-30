MATERIAL_INCREMENT

# G-0081 T1 hostile source-only verification

Pinned subject: commit `b8801227a04bab9b8dac44f364ee3cc119866368`, runner SHA-256 `dfd3c4f561536f2cd18b5d269be9b846aee1064ebbe38916bb200ca64e33c5ff`.

No preregistration was created, no `--run`/`--internal-run` was invoked, and no scientific rank or branch outcome was inspected.

## Material protocol break: preregistration precedence and the launcher boundary are not enforced

The README says execution requires a **separately committed** preregistration (`README.md:173-177`), but `validate_registration` only compares live bytes to a hash supplied by the same invocation and to fields self-declared in those bytes (`full_dictionary_schur.py:497-568`). It never verifies a pre-existing Git object/ref, trusted timestamp, signature, or other external commitment. The result later records only that same hash (`:1925-1935`). A local file can therefore be prepared uncommitted, used to compute and inspect caches/output, and committed only afterward if the result is favorable; the recorded bytes and hashes cannot distinguish that selective promotion from commit-before-computation custody. A content hash proves identity, not precedence.

There is a second path around the claimed launcher controls. `--internal-run` is an ordinary hidden CLI mode (`:2332-2345`). Its only authorization is equality between `--internal-token` and `G0081_INTERNAL_TOKEN` (`:2388-2396`), both of which a direct caller chooses. Such a caller reaches `internal_kernel` without `public_run`'s exclusive cache lock, new process group, or parent-enforced six-hour `communicate()` timeout (`:1980-2048`). The in-kernel deadline is not a whole-kernel kill boundary, so later Schur/RREF stages can escape the registered launcher timeout. This also permits scientific caches to be produced outside the advertised custody path.

These are protocol/custody failures, not a finding about either possible mathematical outcome.

## Required repair

- Bind every run/cache/result to an externally established preregistration anchor that demonstrably predates computation (for example, an already-published immutable commit/ref or signed timestamp receipt), and verify that anchor rather than a hash supplied only by the executing caller.
- Make every entry path capable of scientific computation enforce the same cache lock and absolute whole-kernel deadline. Do not treat a caller-controlled CLI/environment token comparison as a launcher capability.
- Bind the verified anchor identifier and enforced execution path into cache and result receipts.

## Controls that passed

- The authorized `--self-test` passed without evaluating the actual quotient/rank.
- Independent tiny fixtures passed for the block determinant identity, target-last member/separator pivots, and new-column nullspace recovery with a target pivot.
- The bound price artifact independently has 18,582 entries, exact/modular congruence, and the stated 630 zero / 17,952 nonzero census; the runner retains all columns.
- Source inspection found the target-local/global indices, modular-vs-integer Schur claims, raw-minor implication, separate pre-RREF/RREF caches, and partial-cache rejection internally consistent.

## Observation that would have yielded a negative verdict

I would have returned `NO_MATERIAL_INCREMENT` if the preregistration validator proved an externally anchored commitment existed before any scientific cache could be produced **and** direct child invocation could not bypass the lock and whole-kernel timeout. Under those conditions, the source-only tests and independent algebra fixtures exposed no mathematical or cache-indexing defect.
