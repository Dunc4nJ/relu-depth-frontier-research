# G-0113e frozen exact-Q postprocessor

Frozen during the corrected all-record scan, before the DISJOINT boundary and
before any target-membership decision was observed.

```text
07f20ee167483aedc0c06f40650fd3edc671ef7fc5cf1e1050b1ad388ba3ec48  exact_panel_postprocess.py
94d50a6b4defa5ce9e5502009b624d26c915ab49c4be8b4064c95b755640f44a  PANEL_EXACT_POSTPROCESS_PREREGISTRATION.md
8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f  src/main.rs
```

Python syntax compilation passed.  Planted exact controls passed for a rational
member, rejection of its first-nonzero-coefficient `+1` mutant, and a rational
nonmember with a primitive target-separating left-null vector.  The
postprocessor deterministically binds and rehashes all retained vectors,
rejects disagreement at either modular boundary, and follows the branch policy
frozen in the preregistration.

Potentially unbounded separator entries and their target pairing are serialized
as decimal strings, so a later verifier cannot silently truncate them to a
machine integer.

It must not run until both corrected scan outputs exist.  Its own output is a
finite-panel result: a member advances to global CEGIS, while a retained-span
separator advances to a fresh exact all-column replay.
