#!/usr/bin/env python3
"""Cross-check source-card statements against retained local artifacts.

This certifies provenance, byte identity, and statement-to-page traceability.  It
does not certify a paper's proof or promote any mathematical claim.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LITERATURE = ROOT / "literature"
CARDS = LITERATURE / "source-cards"
HEX64 = r"[0-9a-f]{64}"


class AuditFailure(RuntimeError):
    pass


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def match_one(pattern: str, text: str, label: str) -> re.Match[str]:
    found = re.search(pattern, text, flags=re.MULTILINE)
    require(found is not None, f"missing or malformed {label}")
    return found


def within(base: Path, relative: str) -> Path:
    candidate = (base / relative).resolve()
    require(candidate.is_relative_to(base.resolve()), f"path escapes corpus: {relative}")
    require(candidate.is_file(), f"missing retained artifact: {relative}")
    return candidate


def compact_variants(value: str) -> set[str]:
    base = unicodedata.normalize("NFKC", value).replace("\u00ad", "")
    variants = {
        re.sub(r"\s+", "", base),
        re.sub(r"\s+", "", re.sub(r"-\s*\n\s*", "", base)),
        re.sub(r"\s+", "", re.sub(r"-\s*\n\s*", "-", base)),
    }
    return {item.casefold() for item in variants}


def excerpt_on_page(pdf: Path, page: int, excerpt: str) -> bool:
    result = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), pdf.as_posix(), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    page_variants = compact_variants(result.stdout)
    excerpt_variants = compact_variants(excerpt)
    return any(needle in haystack for needle in excerpt_variants for haystack in page_variants)


def pdf_pages(pdf: Path) -> int:
    result = subprocess.run(
        ["pdfinfo", pdf.as_posix()], check=True, capture_output=True, text=True
    )
    found = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, flags=re.MULTILINE)
    require(found is not None, f"pdfinfo returned no page count: {pdf}")
    return int(found.group(1))


def audit_reference(card: Path) -> None:
    text = card.read_text(encoding="utf-8")
    ref_id = card.stem
    require(text.startswith(f"# {ref_id} — "), "heading ID does not match filename")
    require("- Retrieved: 2026-08-29 UTC" in text, "missing frozen retrieval date")
    require("- Cousin boundary:" in text, "missing cousin boundary")
    require("- Certification:" in text, "missing certification tier")

    if ref_id == "REF-0004":
        crossref = within(
            LITERATURE, "metadata/wang-sun-2005.crossref.json"
        )
        semantic = within(LITERATURE, "metadata/wang-sun-2005.s2.json")
        expected_crossref = match_one(
            rf"^- Crossref SHA-256: ({HEX64})$", text, "Crossref hash"
        ).group(1)
        expected_semantic = match_one(
            rf"^- Semantic Scholar SHA-256: ({HEX64})$", text, "Semantic Scholar hash"
        ).group(1)
        require(digest(crossref) == expected_crossref, "Crossref card hash mismatch")
        require(digest(semantic) == expected_semantic, "Semantic Scholar card hash mismatch")
        record = json.loads(crossref.read_text(encoding="utf-8"))["message"]
        require(record.get("DOI", "").casefold() == "10.1109/tit.2005.859246", "wrong DOI")
        title = " ".join(record.get("title", []))
        require("Generalization of Hinging Hyperplanes" in title, "title excerpt absent")
        require("L0 only" in text, "metadata-only record must remain L0")
        return

    local = match_one(
        r"^- Local: ([^;]+\.pdf); ([^;]+\.txt); ([^;]+\.atom\.xml)$",
        text,
        "local artifact tuple",
    )
    pdf = within(LITERATURE, local.group(1))
    extracted = within(LITERATURE, local.group(2))
    atom = within(LITERATURE, local.group(3))
    require(pdf.read_bytes()[:5] == b"%PDF-", "retained PDF has invalid magic")

    arxiv_id = pdf.stem
    require(
        f"https://arxiv.org/abs/{arxiv_id}" in text,
        "primary arXiv identifier does not match retained PDF",
    )
    version = int(match_one(r"\(v(\d+)(?:[,\)])", text, "arXiv version").group(1))
    atom_root = ET.parse(atom).getroot()
    namespace = {"atom": "http://www.w3.org/2005/Atom"}
    entry_id = atom_root.findtext("atom:entry/atom:id", namespaces=namespace)
    require(
        entry_id == f"http://arxiv.org/abs/{arxiv_id}v{version}",
        "card version does not match retained Atom entry",
    )

    doi = re.search(r"^- Primary: .+; DOI ([^\s]+)$", text, flags=re.MULTILINE)
    if doi is not None:
        registry = match_one(
            rf"^- DOI registry: ([^;]+\.crossref\.json); Crossref SHA-256: ({HEX64})$",
            text,
            "DOI registry identity",
        )
        registry_path = within(LITERATURE, registry.group(1))
        require(digest(registry_path) == registry.group(2), "DOI-registry card hash mismatch")
        record = json.loads(registry_path.read_text(encoding="utf-8"))["message"]
        require(record.get("DOI", "").casefold() == doi.group(1).casefold(), "DOI registry mismatch")

    declared = match_one(
        rf"^- PDF: (\d+) pages, (\d+) bytes, SHA-256 ({HEX64})$",
        text,
        "PDF identity",
    )
    declared_pages = int(declared.group(1))
    declared_bytes = int(declared.group(2))
    require(pdf_pages(pdf) == declared_pages, "PDF page-count mismatch")
    require(pdf.stat().st_size == declared_bytes, "PDF byte-count mismatch")
    require(digest(pdf) == declared.group(3), "PDF card hash mismatch")

    expected_text = match_one(
        rf"^- Text SHA-256: ({HEX64})$", text, "text hash"
    ).group(1)
    require(digest(extracted) == expected_text, "extracted-text card hash mismatch")
    require(extracted.stat().st_size > 0, "extracted text is empty")

    locator = match_one(
        r"^- Locator: .+PDF physical page (\d+)(?: \(paper page \d+\))?$",
        text,
        "PDF physical-page locator",
    )
    page = int(locator.group(1))
    require(1 <= page <= declared_pages, "locator page outside retained PDF")
    excerpt = match_one(
        r"^- Short excerpt: “([^”]+)”", text, "short excerpt"
    ).group(1)
    require(
        excerpt_on_page(pdf, page, excerpt),
        f"short excerpt not traceable to declared PDF page {page}",
    )
    additional_locator = re.search(
        r"^- Additional locator: .+PDF physical page (\d+)$",
        text,
        flags=re.MULTILINE,
    )
    additional_excerpt = re.search(
        r"^- Additional short excerpt: “([^”]+)”",
        text,
        flags=re.MULTILINE,
    )
    require(
        (additional_locator is None) == (additional_excerpt is None),
        "additional locator and excerpt must occur together",
    )
    if additional_locator is not None and additional_excerpt is not None:
        additional_page = int(additional_locator.group(1))
        require(1 <= additional_page <= declared_pages, "additional locator page outside PDF")
        require(
            excerpt_on_page(pdf, additional_page, additional_excerpt.group(1)),
            f"additional excerpt not traceable to declared PDF page {additional_page}",
        )


def audit_source_card() -> None:
    card = CARDS / "SRC-0001.md"
    text = card.read_text(encoding="utf-8")
    require(text.startswith("# SRC-0001 — "), "malformed source archive card")
    archive_rel = match_one(
        r"^- Retained archive: (.+\.tar\.gz)$", text, "source archive"
    ).group(1)
    archive = within(LITERATURE, archive_rel)
    expected_archive = match_one(
        rf"^- Archive SHA-256: ({HEX64})$", text, "archive hash"
    ).group(1)
    require(digest(archive) == expected_archive, "source archive hash mismatch")
    manifest_rel = match_one(
        r"^- Extracted tree manifest: (.+SOURCE_MANIFEST\.sha256)$",
        text,
        "source manifest",
    ).group(1)
    manifest = within(LITERATURE, manifest_rel)
    expected_manifest = match_one(
        rf"^- Tree-manifest SHA-256: ({HEX64})$", text, "tree-manifest hash"
    ).group(1)
    require(digest(manifest) == expected_manifest, "tree-manifest card hash mismatch")
    require("provenance/bytes only" in text, "missing source-code epistemic boundary")


def audit_import_card() -> None:
    card = CARDS / "IMP-0001.md"
    text = card.read_text(encoding="utf-8")
    require(text.startswith("# IMP-0001 — "), "malformed import card")
    manifest_rel = match_one(
        r"^- Import manifest: (.+IMPORT_MANIFEST\.sha256)$",
        text,
        "import manifest",
    ).group(1)
    manifest = within(ROOT, manifest_rel)
    expected_manifest = match_one(
        rf"^- Manifest SHA-256: ({HEX64})$", text, "import-manifest hash"
    ).group(1)
    require(digest(manifest) == expected_manifest, "import-manifest card hash mismatch")
    for name, expected in re.findall(rf"^  - (.+?) — ({HEX64})$", text, flags=re.MULTILINE):
        imported = within(ROOT, f"imports/target-selection-2026-08-27/{name}")
        require(digest(imported) == expected, f"import hash mismatch: {name}")
    require("No-claim:" in text and "quarantined" in text, "missing import quarantine")


def main() -> int:
    cards = sorted(CARDS.glob("REF-*.md"))
    expected = [f"REF-{number:04d}" for number in range(1, 14)]
    require([card.stem for card in cards] == expected, "REF card sequence is not exactly 0001..0013")
    failures: list[str] = []
    for card in cards:
        try:
            audit_reference(card)
            print(f"{card.stem}: PASS")
        except (AuditFailure, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            failures.append(f"{card.stem}: {exc}")
            print(f"{card.stem}: FAIL — {exc}")
    for label, check in (("SRC-0001", audit_source_card), ("IMP-0001", audit_import_card)):
        try:
            check()
            print(f"{label}: PASS")
        except (AuditFailure, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
            failures.append(f"{label}: {exc}")
            print(f"{label}: FAIL — {exc}")
    print("epistemic-boundary: traceability certified; mathematical correctness not inferred")
    if failures:
        print(f"source-card-audit: FAIL ({len(failures)} finding(s))", file=sys.stderr)
        return 1
    print(f"source-card-audit: PASS ({len(cards) + 2} cards)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditFailure as exc:
        print(f"source-card-audit: FAIL — {exc}", file=sys.stderr)
        raise SystemExit(1)
