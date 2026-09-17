# Licence / GitHub-rules / engine-decision change 114e5b3f5b1b — round 4 findings (fail; F1-F2 substantive, no wording)

Delete this file, and `findings-114e5b3f5b1b-rules-r{1,2,3}.md`, in the
landing commit. Branch worker/114e5b3f5b1b, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\rules` on the PC, tip 732a7f4 as
reviewed. Recorded in the store as round 4 (e3b7f9a2c514). Lens default.
Round 3 was wording-only; this confirming round found two substantive
line-citation defects, so the sequence restarts: fixer 4, then round 5, and
a wording-only round 5 needs a confirming round 6.

Sound and not to be re-checked: rounds 1-3's lists; round-3 W1/W2 applied;
forefront section byte-identical to origin/main but for the added bullet;
LICENSE sha unchanged; every new CLAUDE.md bullet imperative, 10-36 words;
no history; suite 25 passed; design checker 680; `git merge-tree` against
local main 03622d6 clean.

- F1 (substantive) REFERENCE_NOTES.md:306 and :346. This change adds two
  lines to CLAUDE.md's opening paragraph, so every rule bullet moved down
  two. :306 "CLAUDE.md:17 treats treys as an external evaluator" → the treys
  bullet is now CLAUDE.md:19. :346 "allowed by CLAUDE.md:16, the
  forefront-rule bullet that puts card combinatorics on our side" → now
  CLAUDE.md:18. Resolve: 17→19 at :306, 16→18 at :346; re-check against the
  final tree at landing.
- F2 (substantive) RESOURCES_BOTS.md:767-768 "REFERENCE_NOTES.md:414 for
  18.4 days, :427 for 146.5 GiB" — this change adds one net line to
  REFERENCE_NOTES.md above those; now :415 and :428. Resolve: 414→415,
  427→428.
- Observation, fix in the same pass: REFERENCE_NOTES.md:408 cites
  "CLAUDE.md:29" for the compute-budget rule; it was already wrong on
  origin/main (bullet at :43) and is now :47.
- Observation, owed to change 8a80689e7354 (the exploitation touch-up, on a
  branch from local main): RESOURCES_EXPLOITATION.md:134-138 still defines
  criterion (e) as private use, and :396-415 and :500-502 cite
  "CLAUDE.md:45-49" (the old Licence section, now :59-64). Land the touch-up
  AFTER this change and re-point those citations there.

Every finding wording only: NO.

Round-4 cost: 19 tool calls, about 15 minutes, no fetch; no dollar figure.
Four rounds on this change so far.
