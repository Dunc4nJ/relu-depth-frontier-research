"""Strict JSON boundary and immutable exact certificate model."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


class CertificateFormatError(ValueError):
    """The input does not exactly satisfy its declared subject contract."""


_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_RATIONAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")
_SUBJECT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


@dataclass(frozen=True)
class SubjectSpec:
    """The complete shape/hash contract for one accepted JSON subject."""

    subject_id: str
    filename: str
    n: int
    k: int
    term_count: int
    byte_sha256: str | None = None
    normalized_sha256: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("n", "k", "term_count"):
            value = getattr(self, field_name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field_name} must be a positive genuine integer")
        if (
            type(self.subject_id) is not str
            or _SUBJECT_ID_RE.fullmatch(self.subject_id) is None
        ):
            raise ValueError("subject_id has an invalid shape")
        if (
            type(self.filename) is not str
            or not self.filename
            or Path(self.filename).name != self.filename
        ):
            raise ValueError("filename must be one plain path component")
        for field_name in ("byte_sha256", "normalized_sha256"):
            value = getattr(self, field_name)
            if value is not None and (
                type(value) is not str or _SHA256_RE.fullmatch(value) is None
            ):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")


Pair = tuple[int, int]
Side = tuple[Pair, ...]


@dataclass(frozen=True)
class Term:
    coefficient: Fraction
    left: Side
    right: Side


@dataclass(frozen=True)
class Certificate:
    subject_id: str
    n: int
    k: int
    term_count: int
    terms: tuple[Term, ...]
    raw_sha256: str
    normalized_sha256: str


# Frozen input identities from handoff/CLEAN_ROOM_PREREGISTRATION.md.  Merely
# importing this module performs no filesystem access.
REGISTERED_SPECS: tuple[SubjectSpec, ...] = (
    SubjectSpec(
        "MAX5-k2",
        "certificate_5_2.json",
        5,
        2,
        3,
        "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
        "757d8f0dc23729a54059044a464ea2795486b20f3b2de2465f4cd5647691846f",
    ),
    SubjectSpec(
        "MAX6-k2",
        "certificate_6_2.json",
        6,
        2,
        4,
        "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
        "b5e5ca7eb0e69a88d988285e847da6816b7eda07aff5664fef2b3b527e14daaa",
    ),
    SubjectSpec(
        "MAX7-k3",
        "certificate_7_3.json",
        7,
        3,
        57,
        "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
        "bc2ec7ed82d98f24d1480a72d0899e2c8d4c7075fb3a167616c860d815931448",
    ),
    SubjectSpec(
        "MAX8-k3",
        "certificate_8_3.json",
        8,
        3,
        69,
        "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
        "5db584c920faf7298ef4e069d073e418f26fd6ef1c30ac62260e3f72b9af9961",
    ),
    SubjectSpec(
        "MAX9-k4",
        "certificate_9_4.json",
        9,
        4,
        337,
        "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
        "1741b37cc316f704897d541f70a118642d07a6ca3af41c71fe929a6d2ab5f423",
    ),
    SubjectSpec(
        "MAX10-k4",
        "certificate_10_4.json",
        10,
        4,
        402,
        "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
        "354f9fab7bdf02b71ad55bbfcdbb8fb962bb479376d4b8fa2762711721c29473",
    ),
)
REGISTERED_MANIFEST_SHA256 = (
    "70851ae4fdd20ddc53a87b7817effd8efb983d721e518bcf6ef8c5a9edf848f2"
)
_REGISTERED_BY_FILENAME = {spec.filename: spec for spec in REGISTERED_SPECS}


def _reject_float(token: str) -> Any:
    raise CertificateFormatError(f"floating JSON number is forbidden: {token!r}")


def _reject_constant(token: str) -> Any:
    raise CertificateFormatError(f"non-finite JSON number is forbidden: {token!r}")


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CertificateFormatError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_json(raw: bytes) -> Any:
    if type(raw) is not bytes:
        raise TypeError("certificate input must be bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CertificateFormatError("certificate is not valid UTF-8") from exc
    try:
        return json.loads(
            text,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except CertificateFormatError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise CertificateFormatError(f"malformed JSON: {exc}") from exc


def _require_exact_keys(value: Any, expected: set[str], location: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise CertificateFormatError(f"{location} must be a JSON object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise CertificateFormatError(
            f"{location} keys mismatch: missing={missing}, unknown={unknown}"
        )
    return value


def _require_genuine_int(value: Any, location: str) -> int:
    if type(value) is not int:
        raise CertificateFormatError(f"{location} must be a genuine JSON integer")
    return value


def _parse_coefficient(value: Any, location: str) -> Fraction:
    if type(value) is not str or _RATIONAL_RE.fullmatch(value) is None:
        raise CertificateFormatError(
            f"{location} must be a canonical integer or numerator/denominator string"
        )
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise CertificateFormatError(f"{location} is not a rational number") from exc
    if result == 0:
        raise CertificateFormatError(f"{location} must be nonzero")
    return result


def _parse_endpoint(value: Any, n: int, location: str) -> Pair:
    if type(value) is not list or len(value) != 2:
        raise CertificateFormatError(f"{location} must be a two-integer JSON array")
    a = _require_genuine_int(value[0], f"{location}[0]")
    b = _require_genuine_int(value[1], f"{location}[1]")
    if not (1 <= a <= b <= n):
        raise CertificateFormatError(
            f"{location} must satisfy 1 <= a <= b <= n (got {a}, {b}, n={n})"
        )
    return (a, b)


def _parse_side(value: Any, n: int, k: int, location: str) -> Side:
    if type(value) is not list:
        raise CertificateFormatError(f"{location} must be a JSON array")
    if len(value) != k:
        raise CertificateFormatError(
            f"{location} has length {len(value)}; contract requires k={k}"
        )
    return tuple(
        _parse_endpoint(endpoint, n, f"{location}[{index}]")
        for index, endpoint in enumerate(value)
    )


def normalized_json_bytes(value: Any) -> bytes:
    """Return the documented deterministic JSON normalization used for hashes."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def parse_certificate_bytes(raw: bytes, spec: SubjectSpec) -> Certificate:
    """Parse only a subject explicitly admitted by ``spec``.

    No inference from filenames, n, or term contents widens the contract.  Hashes
    are checked when supplied, so registered inputs are byte- and content-pinned.
    """

    raw_digest = hashlib.sha256(raw).hexdigest()
    if spec.byte_sha256 is not None and raw_digest != spec.byte_sha256:
        raise CertificateFormatError(
            f"byte SHA-256 mismatch for {spec.subject_id}: {raw_digest}"
        )

    value = _load_json(raw)
    root = _require_exact_keys(value, {"n", "terms"}, "root")
    n = _require_genuine_int(root["n"], "root.n")
    if n != spec.n:
        raise CertificateFormatError(f"root.n={n}; contract requires n={spec.n}")
    terms_value = root["terms"]
    if type(terms_value) is not list:
        raise CertificateFormatError("root.terms must be a JSON array")
    if len(terms_value) != spec.term_count:
        raise CertificateFormatError(
            f"root.terms has length {len(terms_value)}; "
            f"contract requires {spec.term_count}"
        )

    terms: list[Term] = []
    for term_index, term_value in enumerate(terms_value):
        location = f"root.terms[{term_index}]"
        term_object = _require_exact_keys(
            term_value, {"coefficient", "pair"}, location
        )
        coefficient = _parse_coefficient(
            term_object["coefficient"], f"{location}.coefficient"
        )
        pair = term_object["pair"]
        if type(pair) is not list or len(pair) != 2:
            raise CertificateFormatError(
                f"{location}.pair must contain exactly two sides"
            )
        left = _parse_side(pair[0], n, spec.k, f"{location}.pair[0]")
        right = _parse_side(pair[1], n, spec.k, f"{location}.pair[1]")
        if len(left) != len(right):
            # Redundant after the k checks, retained as an explicit schema invariant.
            raise CertificateFormatError(f"{location} sides have mismatched lengths")
        terms.append(Term(coefficient, left, right))

    normalized_digest = hashlib.sha256(normalized_json_bytes(value)).hexdigest()
    if (
        spec.normalized_sha256 is not None
        and normalized_digest != spec.normalized_sha256
    ):
        raise CertificateFormatError(
            f"normalized JSON SHA-256 mismatch for {spec.subject_id}: "
            f"{normalized_digest}"
        )
    return Certificate(
        subject_id=spec.subject_id,
        n=n,
        k=spec.k,
        term_count=spec.term_count,
        terms=tuple(terms),
        raw_sha256=raw_digest,
        normalized_sha256=normalized_digest,
    )


def parse_registered_certificate_bytes(raw: bytes, filename: str) -> Certificate:
    """Parse one of the six frozen subjects by its exact registered filename."""

    try:
        spec = _REGISTERED_BY_FILENAME[filename]
    except KeyError as exc:
        raise CertificateFormatError(f"unregistered certificate filename: {filename!r}") from exc
    return parse_certificate_bytes(raw, spec)


def load_corpus(directory: str | Path, specs: Iterable[SubjectSpec]) -> tuple[Certificate, ...]:
    """Load an exact closed set of files, refusing missing or extra entries."""

    root = Path(directory)
    specs_tuple = tuple(specs)
    expected = {spec.filename for spec in specs_tuple}
    if len(expected) != len(specs_tuple):
        raise ValueError("corpus contract contains duplicate filenames")
    if not root.is_dir():
        raise CertificateFormatError(f"corpus path is not a directory: {root}")
    entries = tuple(root.iterdir())
    actual = {entry.name for entry in entries}
    if actual != expected:
        raise CertificateFormatError(
            f"corpus file set mismatch: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    for entry in entries:
        if entry.is_symlink() or not entry.is_file():
            raise CertificateFormatError(f"corpus entry must be a regular file: {entry.name}")
    return tuple(
        parse_certificate_bytes((root / spec.filename).read_bytes(), spec)
        for spec in specs_tuple
    )


def load_registered_corpus(
    certificate_directory: str | Path, manifest_path: str | Path
) -> tuple[Certificate, ...]:
    """Load the frozen six-file corpus after checking its separate manifest bytes.

    Stage A deliberately does not call this entry point.  It exists for a later,
    lead-authorized stage after the implementation hash is frozen.
    """

    manifest = Path(manifest_path)
    if manifest.is_symlink() or not manifest.is_file():
        raise CertificateFormatError("registered manifest must be a regular file")
    manifest_digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if manifest_digest != REGISTERED_MANIFEST_SHA256:
        raise CertificateFormatError(
            f"registered manifest SHA-256 mismatch: {manifest_digest}"
        )
    return load_corpus(certificate_directory, REGISTERED_SPECS)
