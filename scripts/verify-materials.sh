#!/usr/bin/env bash
set -euo pipefail

campaign_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
literature_root="$campaign_root/literature"
scratch_dir="$(mktemp -d)"
regenerated="$scratch_dir/MANIFEST.sha256"

(
  cd "$literature_root"
  find . -type f ! -name MANIFEST.sha256 -print0 |
    sort -z |
    xargs -0 sha256sum
) > "$regenerated"
cmp "$literature_root/MANIFEST.sha256" "$regenerated"

(
  cd "$literature_root"
  sha256sum -c MANIFEST.sha256 >/dev/null
)
(
  cd "$campaign_root/imports/target-selection-2026-08-27"
  sha256sum -c IMPORT_MANIFEST.sha256 >/dev/null
)
(
  cd "$literature_root/repos/max-relu-certificates"
  sha256sum -c SOURCE_MANIFEST.sha256 >/dev/null
)

pdf_count=0
for pdf in "$literature_root"/papers/*.pdf; do
  [[ "$(head -c 5 "$pdf")" == "%PDF-" ]]
  pages="$(pdfinfo "$pdf" | awk -F: '/^Pages/{gsub(/ /,"",$2); print $2}')"
  [[ "$pages" =~ ^[1-9][0-9]*$ ]]
  text_file="${pdf%.pdf}.txt"
  [[ -s "$text_file" ]]
  pdf_count=$((pdf_count + 1))
done
[[ "$pdf_count" -eq 12 ]]

ref_count="$(find "$literature_root/source-cards" -maxdepth 1 -type f -name 'REF-*.md' | wc -l)"
[[ "$ref_count" -eq 13 ]]
jq -e '.message.DOI == "10.1109/tit.2005.859246"' \
  "$literature_root/metadata/wang-sun-2005.crossref.json" >/dev/null
jq -e '.openAccessPdf.status == "CLOSED"' \
  "$literature_root/metadata/wang-sun-2005.s2.json" >/dev/null
tar -tzf "$literature_root/source-archives/max-relu-certificates-2343f1213302e3431344595423e69e3395537020.tar.gz" >/dev/null
[[ ! -e "$literature_root/repos/max-relu-certificates/.git" ]]
python3 "$campaign_root/scripts/audit-source-cards.py"

printf 'materials-manifest: PASS (%s entries)\n' "$(wc -l < "$literature_root/MANIFEST.sha256")"
printf 'pdf-integrity-and-extraction: PASS (%s PDFs)\n' "$pdf_count"
printf 'source-card-census: PASS (%s REF cards plus source/import cards)\n' "$ref_count"
printf 'source-archive-and-quarantine-manifests: PASS\n'
printf 'epistemic-boundary: provenance certified; mathematical correctness not inferred\n'
