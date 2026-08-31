# G-0117e addendum — mandatory fresh-Q result path

Registered after the v3 certificate preregistration and before the iteration-1
cache, modular scan, exact-Q decision, or certificate existed.  This addendum
closes a path-binding omission discovered while implementing the independent
consumers.

In addition to every field in
`ITERATION1_V3_CERTIFICATE_PREREGISTRATION.md`, a v3 certificate must contain

```text
source_cegis.result_path    workspace-relative path to the exact fresh-Q result
```

Both global replayers must resolve this path under the repository root, reject
absolute paths and `..`, require the file to exist, hash its actual bytes, and
require that hash to equal `source_cegis.sha256`.  They must parse that actual
result file and independently validate all duplicated paths, bindings, receipt
fields, selected sequences, selected basis columns, rational coefficients,
fresh denominator scale, integer coefficients, exact 313-row replay, and the
coefficient-plus-one hostile control.

A v3 certificate without `source_cegis.result_path`, or one whose named file is
missing, stale, outside the repository, or inconsistent with the certificate,
is inadmissible before normal-form aggregation.

This is a corrective extension, not a relaxation.  The original v3 document
and this addendum are both permanent certificate inputs and are independently
bound into the producer and consumers.  All original no-claim boundaries and
retirement conditions remain unchanged.
