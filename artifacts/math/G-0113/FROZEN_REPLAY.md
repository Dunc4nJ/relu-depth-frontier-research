# G-0113 frozen method-disjoint replay

Frozen before executing the brute-force `7!`-order verifier.

```text
producer_result_sha256 d67f102624dfa494b76fd2c5ad7602c91c2ab5786fee68d34cdfb37c04aaf665
verifier_sha256        354c18f4f61a6e4738acca7a4f769f2b0ee59e3805731340ae26b4d19385a757
command                /usr/bin/time -p .venv/bin/python -u -B artifacts/math/G-0113/verify_lower_potency.py --output artifacts/math/G-0113/lower_potency_replay_v1.json
```

The verifier is confirmatory same-agent replay.  Its implementation route is
different (literal permutation enumeration instead of the producer's subset
dynamic program), but it does not satisfy the campaign's T2 independence bar.

## Retained first invocation and v2 freeze

The displayed v1 invocation exited nonzero after 7.46 seconds before writing
an output.  It had reconstructed the matrices but compared a JSON list label
to an in-memory tuple label at separator row zero.  No rank or separator
comparison was accepted.  The only v2 change normalizes verifier labels to
JSON lists before equality checking.

```text
v1_failure              RuntimeError: separator label drift at row 0
v1_output_created       no
v2_verifier_sha256      6e1b05f99be1b0849a2284554882f297a57336c40873f0a4fd35d6e75a1ed677
v2_command              /usr/bin/time -p .venv/bin/python -u -B artifacts/math/G-0113/verify_lower_potency.py --output artifacts/math/G-0113/lower_potency_replay_v1.json
```
