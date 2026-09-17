# Table-size notes 984aa6810a05 — round 8 findings (fail; F1-F2 substantive, prose facts only)

Delete this file, and `findings-984aa6810a05-tablesize-r{4,5,6,7}.md`, in the
landing commit. Branch worker/984aa6810a05, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\tablesize` on the PC, tip 663c717
as reviewed; trunk NOT merged in (confirmed; keep it so — read main's files
with `git show main:<file>` for facts). Recorded in the store as round 8
(d7f1b3c5e8a2). Lens default. Lines at 663c717. EIGHT rounds: the operator's
cap applies — fixer 8 applies these, round 9 records any wording as
observations and lands on its pass.

Sound and not to be re-checked: rounds 4-7's lists; round-7 F1 fixed (the
gloss now matches the design's §2.2 AF / §4.2 afq / §4.4 AFQ_SPLIT); W1-W7
applied (W4 correction confirmed: the R3 heading has no links); links
142/55/0; no CLAUDE.md line citations; the eight REFERENCE_NOTES.md line
citations (:8-11, :12-15, :16-19, :485-497, :499-503, :523-542) verified by
content on main; the two design citations at :988/:991 pinned to a named
revision; §4.5 on main names ENGINE_ALTERNATIVES.md and not
RESOURCES_SOLVERS.md (R6 stands); main's CLAUDE.md still says "3 or more"
(Q5 stands); merge-tree clean against 0565d1a; checker 233; 35 passed;
nothing settled.

- F1 (substantive; stale facts about trunk) :151-157, :138-139, and :1002,
  :1243-1244, :1464-1469, :14-15. "CLAUDE.md on branch worker/114e5b3f5b1b,
  which has not been pushed … Nothing about it has reached this project's
  trunk branch" and "not a fact about the repository" — false since
  e67825b landed on main (2026-09-16 18:06 -0700) and was pushed; main's
  CLAUDE.md:7 opens "The engine road is OpenSpiel's universal_poker".
  Resolve: say the decision is on trunk in CLAUDE.md (landed e67825b), with
  the dated record in heater (fb353c6); the paragraph's conclusions do not
  change. Same pass: :1002 and :1243-1244 "both in progress" — the solvers
  survey is on trunk (0565d1a); only ENGINE_ALTERNATIVES.md is in progress
  (still absent from trunk — confirm). :1464-1469 the design is on trunk;
  only this document's landing is outstanding before the two checkers can
  be merged. :14-15 "mid-review on a separate task" — the design landed;
  the pinning to revision 5aa40b8 stays, the reason given changes.
- F2 (substantive) :395 "OPPONENT_MODEL_DESIGN.md §4.2 calls that ratio the
  aggression factor" — §2.2 does (AF = (bets + raises) / calls and the
  AF > 1 threshold); §4.2 is the stat table and mentions AF once, pointing
  to §2.2. :407 and :1187 already say §2.2. Resolve: §4.2 → §2.2 at :395
  only; the other §4.2 references (:358, :804, :809, :829, :909, :922,
  :1043, :1069) are the stat table and right.
- W1 (wording) :321-323 "every stat whose opportunity definition involves
  position — pfr, limp, open_raise, three_bet, fold_to_steal": by the
  design's definitions pfr's and three_bet's opportunities do not mention
  position. The list is right; the criterion is wrong. State it as the
  section's own argument does: stats whose rate depends on the seat and is
  therefore a mixture over seats.
- W2 (wording) :394 "The threshold quoted below" — the quotation carries
  two; "The aggression half of the threshold quoted below".
- W3 (wording) :397-399 the description of the rate hangs off the threshold
  and never names the design's stat; "AFQ_SPLIT is the cut-off on a
  different rate — the design's afq, aggression frequency: bets or raises
  over all voluntary actions, folds included — which descends from AF but
  is not it."
- W4 (wording; cosmetic) :504 (33 chars) and :1420 (19 chars) short
  mid-paragraph lines; re-flow. Leave the lines forced by the 95-character
  §1.2 anchor.

Every finding wording only: NO (F1, F2 — prose facts; no figure, link,
checker or recommendation moves).

Round-8 cost: 40 tool calls, about 30 minutes, no fetches; no dollar
figure. Eight rounds on this change so far.
