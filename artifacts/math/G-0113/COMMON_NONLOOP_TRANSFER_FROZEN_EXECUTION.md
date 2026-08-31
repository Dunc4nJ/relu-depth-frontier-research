# G-0113c common-nonloop transfer frozen execution

Frozen before the verifier's first execution.

- protocol SHA-256:
  `5d6dea7e1d4f0375f377578c15dee87201c338cbc1cfe6e132c0012bcc66bdc3`
- verifier SHA-256:
  `9a6321db302cf9478b88e2eccb0c4e38d1006fcf1851b0949c4ead23a88cce16`
- signed-W map SHA-256:
  `57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48`

Invocation from the repository root:

```bash
source scripts/activate-toolchain.sh
/usr/bin/time -v python artifacts/math/G-0113/verify_common_nonloop_transfer.py \
  --output artifacts/math/G-0113/common_nonloop_transfer_verification_v1.json
```
