# Certificates for $\max_n$

This repository contains certificates used to show that $\max_n$ for $n \le 10$ can be represented by a network with two hidden layers, together with a small verifier.

The certificates are JSON files in `certificates/`. A certificate expresses $\max(x_1, ..., x_n)$ as a rational linear combination of symmetrized terms of the form

```math
\max\left(\sum_{(a,b) \in \text{left}} \max(x_a, x_b),
    \sum_{(a,b) \in \text{right}} \max(x_a, x_b)\right).
```

The verifier uses exact rational arithmetic and checks that the certificate equals $x_n$ on the sorted cone $x_1 \le \dots \le x_n$. On this cone, $\max(x_1, ..., x_n) = x_n$; by symmetry, this proves the identity everywhere.

## Verification

Use Python 3.10 or newer and install `tqdm`:

```shell
python -m pip install tqdm
python verify_certificate.py certificates/certificate_5_2.json
```

A successful verification prints `OK`. To check every certificate:

```sh
for certificate in certificates/*.json; do
    python verify_certificate.py "$certificate" || exit 1
done
```

The verifier deliberately favors a short, transparent implementation over performance. It enumerates permutations, so the larger certificates can take several hours to verify.
