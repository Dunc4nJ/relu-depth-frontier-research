# G-0113 frozen lower-arity execution

Frozen after the self-test and before the first outcome-producing invocation.

```text
repository_HEAD        5b11554f7b5902abbae5d0dde1c5b8b30532be01
python                 3.13.7
preregistration_sha256 0ae8cff9f62fc2a4074d338d2a352388cb638b7d065be9766c6fbfb0b556301e
runner_sha256          b92ef70ab9187c4989c80cf7b948324ec65a9ef8deff9cf3e5dfdff022a106ea
command                /usr/bin/time -p .venv/bin/python -u -B artifacts/math/G-0113/double_star_search.py --lower --output artifacts/math/G-0113/lower_potency_v1.json
```

The command must use the displayed unused output path.  A failure or resource
stop is retained; the source, family, ordering, or target is not repaired and
silently rerun under this receipt.
