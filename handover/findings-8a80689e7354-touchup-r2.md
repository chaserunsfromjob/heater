# Exploitation-survey trunk touch-up 8a80689e7354 — round 2 findings (fail; F1-F2 substantive)

Delete this file, `findings-8a80689e7354-touchup-r1.md` and
`findings-pokerbot-trunk-touchup.md` in the landing commit. Branch
worker/8a80689e7354, checkout `C:\Users\chase\.heater\worktrees\pokerbot\touchup`
on the PC, tip 066421e as reviewed (on a merge of local main 51fd3fe; current
main 0565d1a merges clean). Recorded in the store as round 2 (c4e6a8b2d5f1).
Lens default. Lines at 066421e.

Sound and not to be re-checked: round 1's list; round-1 F1 (the fpdb-3
passage cites CLAUDE.md's Licence section by name; paraphrase faithful to
main :59-64); the landed-licence text (:137-140) true of the tree and of
GitHub, no claim about GitHub's licence field; the code/corpus split
consistent with RESOURCES_SOLVERS.md :181-183 and RESOURCES_BOTS.md, and it
touches exactly one rating (§3.2; §3.3's ~ rests on price and ToS, §3.4/§3.5
unrated); all twenty (e) verdicts right; AF matches the design :261; the
spelling convention AFq / AFQ_SPLIT followed; both footers re-fetched exact
(2026-09-17 01:15Z); :1422's "2026-09-17 00:09Z" right; AGPL still routed to
the operator; suite 25; checker 680.

- F1 (substantive) :1103-1104, consequences at :1122-1126. "Two ways of
  measuring aggression appear in the table" — the table names three: AF,
  AFq, and AGG% (fpdb-3 row :1112, bets+raises ÷ (bets+raises+calls)). The
  next paragraph then justifies AFQ_SPLIT = 0.50 with "every aggressive
  type has AGG% ≥ 35" — AGG% excludes folds from the denominator, AFq
  includes them, so AGG% always reads higher; not like for like. Resolve:
  name all three at :1103-1107 (AGG%'s formula is already in the table),
  say AGG% and AFq differ only in whether folds are counted so AGG% reads
  higher; at :1122-1124 drop AGG% from the AFQ_SPLIT justification or call
  it a near-neighbour, not the same statistic. No table number changes.
- F2 (substantive; unrecorded decision) :148-153, instantiated at
  :1023-1026. The new rule states as project fact that an unlicensed corpus
  "is read as data … and never copied into the repository" and concludes it
  is not marked down — settling a licence position no project file records
  (CLAUDE.md's Licence section is silent on third-party data and routes
  licence moves to the operator), about material that carries a copyright
  notice with no grant (§3.2 :1017-1018, already downloaded in full :1004).
  The same document routes AGPL to the operator at :430-432. The rule as
  drawn also reaches §3.3's bought histories (:1069-1072 says every site's
  terms ban importing hands you did not play). Resolve (preferred): rate
  §3.2 ✔ on a stated condition (read and measured, nothing redistributed),
  say this survey does not conclude the copyright notice imposes nothing,
  and route that question to the operator beside the AGPL one, mirroring
  :430-432; narrow the criterion's rule so it does not reach corpora
  acquired against a room's terms. (Alternative: record the position in
  CLAUDE.md's Licence section first, then cite it by name — a separate
  change this would wait on.)
- W1 (wording) :414 "the public one" is a leftover of the removed
  private/public hedge; "the position criterion (e) above is rated against".
- W2 (wording) :1105-1106 AFq gloss "out of all the chances they had to
  act" is wider than the design's formula :294 (checks are not in the
  denominator); "out of the times they bet, raised, called or folded".
- W3 (wording) :1124-1126 restates both definitions; cut to "AFQ_SPLIT is a
  threshold on AFq, not on the AF of the table."
- W4 (wording) :148-150 "raises a different question depending on what the
  resource is" names neither side; "marked down for it" — "it" points past
  a clause. "What a missing licence costs depends on whether the resource
  is code or data"; "marked down for the missing licence".
- W5 (wording) :667 §2.3 "(e) ~." with no reason while §1.7, §2.1, §2.9
  carry "(no licence)"; add it.

Follow-up filed separately (NOT this change; a new branch from main):
RESOURCES_SOLVERS.md on main :40-42 and :174-176 still say the GPL-3.0
licence "is change 114e5b3f5b1b, not yet landed: as of 2026-09-17 LICENSE
is not on main and GitHub reports no licence" — false since e67825b landed
and was pushed.

Every finding wording only: NO (F1, F2).

Round-2 cost: 27 tool calls, about 14 minutes, two fetches; no dollar
figure. Two rounds on this change so far.
