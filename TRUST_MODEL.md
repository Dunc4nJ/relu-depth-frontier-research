# TRUST MODEL — relu-depth-frontier-research

Installed and runnable does not mean trusted. These are provisional scopes pending the named controls; none of the tools below may promote a mathematical claim merely because it returned success.

| Component | Trusted for | NOT trusted for | Basis / control required |
|---|---|---|---|
| Git 2.51.0 | revision identity and change history | truth, authorship independence, or completeness | repository integrity plus clean-status checks |
| SHA-256 (`sha256sum`) | binding retained bytes to a manifest | source authenticity or mathematical correctness | two-path manifest regeneration |
| curl 8.14.1 | retrieving bytes from an explicitly recorded HTTPS URL | proving the server is the intended author | primary URL plus source card and hash |
| Poppler 25.03.0 | extracting searchable text and PDF metadata | preserving equations/layout perfectly | PDF magic, `pdfinfo`, nonempty extraction, locator spot-check |
| Python 3.13.7 | orchestration and deterministic file processing | exact theoremhood or floating conclusions | known-answer suite; math delegated to exact libraries |
| SymPy / FLINT | exact rational and integer arithmetic within exercised operations | completeness of a search or statement match | planted arithmetic/identity controls and independent path |
| Z3 5.1.0 | exact SMT answers on bound formulas after encoding audit | correctness of an unaudited encoding; unrestricted neural-network impossibility | known SAT/UNSAT pair plus cvc5 cross-check |
| cvc5 1.3.4 | independent exact SMT path on bound formulas | unrestricted impossibility or independence by mere vendor difference | known SAT/UNSAT pair plus Z3 cross-check |
| HiGHS 1.15.1 | floating-point discovery, candidate support selection, performance estimates | exact feasibility, infeasibility, or certificate validity | known LP controls; every promoted candidate rechecked exactly |
| Lean 4.33.1 kernel | checking elaborated terms under the recorded axioms/imports | target statement match, import trust, or informal-to-formal translation | trust scan plus independent statement audit |
| Mathlib v4.33.1 | definitions and proved lemmas at pinned commit | automatic match to this campaign's network conventions | exact import manifest and statement audit |
| Upstream certificate verifier | candidate checking only after clean-room reproduction | universal coverage, MAX11, or independence | pinned source hash, max5–10 controls, deliberate corruptions |
| Model recall | nothing | citations, novelty, proofs, or frontier status | always capped at narrative floor |

Absent at bootstrap: Sage, GAP, Coq, Maxima, R, and Julia. Their absence is a declared capability boundary, not a negative result. A route may add one only with a pinned install and a control that can fail.

Cross-family review is `NONE` at bootstrap. All Codex/GPT-5 agents are one lineage and count at most as same-family T1 checks; T2+ promotion requires a human referee or another explicitly allowed family.
