# Licence / GitHub-rules / engine-decision change 114e5b3f5b1b — round 2 findings (fail; F1 substantive)

Delete this file, and `findings-114e5b3f5b1b-rules-r1.md`, in the landing
commit. Branch worker/114e5b3f5b1b, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\rules` on the PC, tip 33c5325 as
reviewed (c8b5cb1, 27154d9, 33c5325). Recorded in the store as round 2
(b7e0d3a4c9f1). Lens default. Line numbers at 33c5325.

Sound and not to be re-checked: round 1's list, plus all ten round-1 fixes
applied as asked — F1's replacement paragraph in RESOURCES_BOTS.md:1007-1013
faithful and decides nothing (the paragraph opens "this survey does not
choose the strategy road, and must not"); F2 rests on reasons already in
REFERENCE_NOTES.md:49-51; F3's GPL wording matches LICENSE:235-243 in both
directions; no history anywhere in CLAUDE.md; every GitHub and Licence
bullet a single imperative under fifty words tracing to a source; no fleet
rule duplicated; the forefront-rule section byte-identical to origin/main
but for the one added bullet at :34; LICENSE sha256 unchanged; suite 25
passed; design checker 680 match. REFERENCE_NOTES.md:503-504 and :554 still
speak of the 52-card move as pending; untouched by this change and inside a
reference record — not raised.

- F1 (substantive; reviewer.md's irreversible-path item) README.md:6-9 and
  CLAUDE.md:63. CLAUDE.md:63 routes "any move to close the repository, or
  to a different licence" to the operator, but nothing tells the operator
  that the grant already made cannot be pulled back: LICENSE:155-157 — "All
  rights granted under this License are granted for the term of copyright
  on the Program, and are irrevocable provided the stated conditions are
  met." The repository is already public, so everyone who has taken a copy
  keeps the GPL-3.0 rights permanently; closing or relicensing only changes
  what people get from then on. Resolve: one plain sentence in README.md's
  licence paragraph saying exactly that. CLAUDE.md:63 stays as it is.
- W1 (wording) RESOURCES_BOTS.md:1012-1013 "Neither says anything about
  whether the strategy is trained in advance…" — the Plan's stage 3
  (CLAUDE.md:42) does mention a trained model as a refinement. Resolve:
  "Neither the opening nor stage 1 speaks to whether…", or add the
  half-clause that stage 3's optional trained model is a refinement, not
  the strategy road.
- W2 (wording) CLAUDE.md:61 GPL-3.0 never written out in this file; at first
  use: "the GNU General Public License version 3 — GPL-3.0 — whose full
  text is `LICENSE` at the root".
- W3 (wording) CLAUDE.md:38-39 stage 1 names "the reconciliation the four
  surveys feed" without saying what that is, and three of the four surveys
  are not in this repository. Resolve: "1. Superseded; the engine road is
  OpenSpiel `universal_poker`. What replaces this stage is settled by the
  reconciliation of the four survey documents, which is still to come." Do
  not name the absent files.
- W4 (wording) CLAUDE.md:42 stage 3 "on top of stages 1-2" builds on a
  superseded stage; "on top of stage 2" or "on top of the engine and the
  opponent modelling".

Every finding wording only: NO (F1). If F1 alone is resolved, the rest are
wording.

Round-2 cost: 22 tool calls, about 15 minutes, no fetch; no dollar figure.
Two rounds on this change so far.
