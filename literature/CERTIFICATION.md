# Literature and material certification protocol

“Certified” in this workspace is deliberately narrow.

## Levels

| Level | Meaning | Does not mean |
|---|---|---|
| L0 identity | title/authors/date/identifier resolved at a primary registry | paper retrieved or theorem checked |
| L1 bytes | retained artifact has source URL, retrieval date, size, and SHA-256 | source server/authors are infallible |
| L2 extraction | PDF magic/metadata/page count and nonempty text extraction checked | equations/layout were extracted perfectly |
| L3 statement trace | source card gives an exact locator, short excerpt, relevance, and cousin boundary | proof is correct |
| L4 reconstructed | campaign independently reconstructs the cited argument/certificate | independent referee agreement |
| L5 verified | independent replay/referee/formalization obligations pass | priority/novelty forever |

The bootstrap corpus is certified through L3 unless a source card says otherwise. No paper is L4/L5 merely because it is published, cited, recent, or bundled here.

## Admission procedure

1. Prefer the author/publisher/arXiv/DOI primary endpoint.
2. Retain the exact PDF or registry response and its retrieval metadata.
3. Verify PDF magic, page count, parseability, nonempty extraction, and SHA-256.
4. Create one REF-numbered source card with a locator and excerpt shorter than 25 words.
5. Record what claim the passage can support and the nearest invalid cousin inference.
6. Add all retained bytes to MANIFEST.sha256; regenerate and diff before each release.
7. If only closed metadata is available, retain registry metadata and label the missing full text.
8. A new version is a new artifact/hash; never overwrite a version silently.

## Source-code material

The max-relu-certificates repository is retained both as the GitHub archive for commit 2343f1213302e3431344595423e69e3395537020 and as an extracted tree. Its presence is provenance evidence only. The verifier and certificates are not native evidence until clean-room controls and independent replay pass.

## Imported material

Files under imports/ have source paths and hashes but are quarantined. They may suggest a route; they cannot support a native claim until re-authored and checked through the ledger.

## Known limitations

- REF-0004 (Wang–Sun 2005) is closed access in the queried registries. Crossref and Semantic Scholar metadata are retained; technical use is triangulated through retrieved later papers until lawful full text is supplied.
- arXiv certifies a deposited version, not peer-review status.
- pdftotext emitted font-mismatch warnings for two PDFs; text is nonempty and statement locators are manually spot-checked, but equations should be read against the PDF.
- Novelty coverage is bounded to the dated corpora in NOVELTY_SEARCH_LOG.md.

