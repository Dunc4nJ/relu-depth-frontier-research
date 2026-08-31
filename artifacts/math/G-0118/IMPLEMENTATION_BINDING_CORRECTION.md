# G-0118 implementation-binding correction

The first invocation of `prefix_exact_cegis.py` stopped before loading a
matrix or computing a scientific result because its imported G-0117 helper
changed concurrently from SHA-256 `e4cc1d56...` to `ee422e6e...`.  The change
adds the preregistered v3 result-path binding; it does not alter the exact
linear-algebra functions imported by G-0118.

This correction binds the stabilized helper from commit `5f1f14e`:

```text
ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281  fresh_q_cegis_exact.py
```

No G-0118 output file existed, no rank or membership decision was observed,
and the frozen family, prefix hash, rows, target, algorithm, and stopping rule
remain unchanged.  The failed preflight is retained as an aborted provenance
trial rather than silently erased.

