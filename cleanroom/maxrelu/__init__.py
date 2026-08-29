"""Exact clean-room verifier for symmetrized MAX certificates.

This package is intentionally standard-library-only.  It exposes the strict input
boundary, the exact ordered-cone accumulator, and a two-arm control harness.  It
does not load or execute any registered subject at import time.
"""

from .controls import (
    ArmObservation,
    ControlReport,
    ParserControlResult,
    parse_for_control,
    run_two_arm_control,
)
from .model import (
    Certificate,
    CertificateFormatError,
    REGISTERED_MANIFEST_SHA256,
    REGISTERED_SPECS,
    SubjectSpec,
    Term,
    load_corpus,
    load_registered_corpus,
    parse_certificate_bytes,
    parse_registered_certificate_bytes,
)
from .verifier import (
    CanonicalHinge,
    Census,
    Residual,
    TermCensus,
    VerificationInputError,
    VerificationResult,
    canonicalize_hinge,
    ordered_cone_sign,
    side_linear_form,
    verify_certificate,
)

__all__ = [
    "ArmObservation",
    "CanonicalHinge",
    "Census",
    "Certificate",
    "CertificateFormatError",
    "ControlReport",
    "ParserControlResult",
    "REGISTERED_MANIFEST_SHA256",
    "REGISTERED_SPECS",
    "Residual",
    "SubjectSpec",
    "Term",
    "TermCensus",
    "VerificationInputError",
    "VerificationResult",
    "canonicalize_hinge",
    "load_corpus",
    "load_registered_corpus",
    "ordered_cone_sign",
    "parse_certificate_bytes",
    "parse_for_control",
    "parse_registered_certificate_bytes",
    "run_two_arm_control",
    "side_linear_form",
    "verify_certificate",
]
