# Licence / GitHub-rules / engine-decision change 114e5b3f5b1b — round 1 findings (fail; F1-F4 substantive)

Delete this file in the landing commit. Branch worker/114e5b3f5b1b, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\rules` on the PC, tip 27154d9 as
reviewed (c8b5cb1 + 27154d9). Recorded in the store as round 1
(9f4b2c7a1e63). Lens default. Line numbers at 27154d9.

Sound and not to be re-checked: LICENSE is byte-identical to gnu.org's
gpl-3.0.txt (sha256 3972dc97…6986, fetched 2026-09-17 00:22Z); GPL-3.0 is
the right choice (vendor/poker_ai/LICENSE is GPL-3 with a §7 indemnification
addition — keep it beside the engine, never deduplicate it against the root
copy); no other licence file or header in the tree; criterion (e) true under
the new premise and all twenty `e` marks checked (3.8 DecisionHoldem ✓→~ is
right; the unlicensed 3.7/3.16 ~ marks right to leave); the forefront rule's
text untouched, the added bullet records the carve-out as open and not
granted; stage 1 superseded with no plan invented; the GitHub section's seven
bullets each trace to the operator's or the classmate's words; no decision
made that the operator did not make; suite 25 passed; check_design_numbers
680 figures match.

- F1 (substantive) RESOURCES_BOTS.md:1011-1013 "Recommending a blueprint
  would also set aside the opening of CLAUDE.md, which names fedden/poker_ai
  as the engine this project is built on, and its Plan, whose stage 1 is
  moving that engine to the 52-card game." Both halves now false on this
  branch (CLAUDE.md:7-11, :38). It is an argument the reconciliation would
  inherit. Resolve: restate what CLAUDE.md now says (OpenSpiel
  universal_poker is the road; stage 1 superseded) and say whether the
  blueprint objection still stands on its own.
- F2 (substantive) REFERENCE_NOTES.md:66-67 "Why a copy and not a
  submodule: stage 1 of the plan in CLAUDE.md is to move this engine off
  the 20-card deck, which means editing its source." Stage 1 is
  superseded. Resolve: rest the reason on what survives (upstream archived,
  a copy is one clone and one review) without stage 1.
- F3 (substantive) CLAUDE.md:63 "the vendored engine's terms bind anything
  published alongside it" overstates GPL-3.0: §5 says an aggregate of
  separate works is not covered; what is bound is work built on or combined
  with the covered code. Resolve: say that.
- F4 (substantive) CLAUDE.md:38 "Superseded. This stage was the 52-card
  conversion of fedden/poker_ai; …" — history in a rule file
  (rules/global.md:91, :10). Resolve: "Superseded by the reconciliation the
  four surveys feed; the engine road is OpenSpiel universal_poker."
- W1 (wording) RESOURCES_BOTS.md:118 the ✓ column "free and
  GPL-3.0-compatible" and the ~ column "copyleft with a condition attached"
  both describe plain GPL-3.0. Resolve: ~ column "copyleft with a condition
  beyond publishing source, such as the network clause".
- W2 (wording) RESOURCES_BOTS.md:127 AGPL not written out on first use:
  "the GNU Affero General Public License, or AGPL".
- W3 (wording) CLAUDE.md:34 "carve-out" used before it is explained; say
  "the exception to this rule is not granted".
- W4 (wording) CLAUDE.md:11 "never for play" is firmer than any source;
  drop the clause, keep "the reference for table-state capture".
- W5 (wording) CLAUDE.md:53 "Cut the task's branch from origin/main"
  restates rules/global.md:14; keep only the new part: push the branch
  before doing the work.
- W6 (wording) README.md:11-12 the 52-card conversion reads as live work;
  mark it as the road not taken ("and why converting it to a normal 52-card
  deck was ruled out").

Every finding wording only: NO.

Round-1 cost: 33 tool calls, about 20 minutes, one fetch; no dollar figure.
