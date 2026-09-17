# Exploitation-survey trunk touch-up 8a80689e7354 — round 1 findings (fail; F1-F2 substantive, small)

Delete this file, and `findings-pokerbot-trunk-touchup.md`, in the landing
commit. Branch worker/8a80689e7354, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\touchup` on the PC, cut from local
main 03622d6, tip 16d2c51 as reviewed. Recorded in the store as round 1
(e5a1c3f7b2d9). Lens default. Lines at 16d2c51. SINCE THE REVIEW the
licence change 114e5b3f5b1b has LANDED on local main (e67825b): LICENSE is
at the root, CLAUDE.md's Licence section is at :59-64, main is not yet
pushed. The fixer merges local main into this branch first and writes what
is true of that tree.

Sound and not to be re-checked: item 1 (both converter footers re-fetched
2026-09-17 01:00Z, exact; parenthetical sits beside the quotes; :155-157
untouched); item 2's definition of AFq against OPPONENT_MODEL_DESIGN.md
:258/:294 and the choice of Part 4; item 3's three claims match both
sister surveys; all twenty-two (e) marks checked against their licences,
fpdb-3 AGPL ~ right; the four reworded reasons right; §1.6 routes AGPL to
the operator (:421-423, :1152-1154); no privacy premise left; suite 25;
merge-tree with the licence branch clean.

- F1 (substantive) :407-411 "CLAUDE.md:45-49 records a position … on trunk
  still the private one, and under change 114e5b3f5b1b the public one…" —
  the Licence section is now :59-64 and trunk (local main) records the
  public GPL-3.0 position. Resolve: cite "CLAUDE.md's Licence section" by
  name, no line numbers, as RESOURCES_BOTS.md:756 does; state the public
  position in one voice (it answers the GPL-3.0 question by publishing this
  project's own source and says nothing about any other licence). The
  other CLAUDE.md references (:505, :607) cite by name and are fine.
- F2 (substantive) :1012 / :1018 IRC Poker Database: "Licence: none stated"
  yet (e) ✔ with no reason, while the four unlicensed CODE entries (1.7,
  2.1, 2.3, 2.9) are ~ with "unlicensed code cannot be copied into a
  published repository". Keep ✔; give it its reason on the rating line
  (read as data to compute statistics from, never copied into the
  repository); and in criterion (e) :134-147 split unlicensed code (cannot
  be copied in) from an unlicensed corpus (can be read and measured), as
  the solvers survey's wording leaves room for.
- Also, now that the licence has landed locally: the qualifier "(the
  repository is already public; the GPL-3.0 licence is change
  114e5b3f5b1b, not yet landed: as of 2026-09-17 LICENSE is not on main
  and GitHub reports no licence)" at :139-141 is no longer true of the tree
  this lands on. Resolve: "(LICENSE at the repository root; the repository
  is public at github.com/chaserunsfromjob/pokerbot)". Make no claim about
  what GitHub reports.
- W1 (wording) :134-141 the criterion's opening sentence runs ~70 words
  with a dash-aside, a parenthesis, a semicolon and a colon; split after
  "GPL-3.0" into short sentences like RESOURCES_BOTS.md's.
- W2 (wording) :1105 "AFq incl. all-ins" precedes the expansion at
  :1113-1116, and the spelling differs (AFq vs AFQ). Expand at or above
  :1105; use AFq for the statistic and AFQ_SPLIT for the threshold, as the
  design does.
- W3 (wording) :1113-1115 twenty-word subject before the verb; lead with
  the threshold.
- W4 (wording) :1411 "re-verified 2026-09-16" is local time; the survey and
  :139 use UTC (the re-check was 2026-09-17 00:09Z). One clock: UTC.
- W5 (wording) :140, :410 bare "change 114e5b3f5b1b"; gloss once ("the
  change that adds the licence file") or, now that it has landed, drop the
  id.
- W6 (wording) :144-147 "The two to watch" split by a thirty-word aside;
  "a trigger GPL-3.0 does not carry" attaches to the clause, not the
  licence. Number them or split.

Every finding wording only: NO (F1, F2).

Round-1 cost: 33 tool calls, about 12 minutes, three fetches; no dollar
figure.
