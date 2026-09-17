# Table-size notes 984aa6810a05 — round 6 findings (fail; F1 substantive, small)

Delete this file, and `findings-984aa6810a05-tablesize-r{4,5}.md`, in the
landing commit. Branch worker/984aa6810a05, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\tablesize` on the PC, tip d43bab9
as reviewed; trunk NOT merged in (confirmed). Recorded in the store as
round 6 (a4c6e8f1b3d5). Lens default. Lines at d43bab9.

Sound and not to be re-checked: rounds 4 and 5's lists; all five round-5
substantive findings resolved as asked — F1 reproduced on this machine
(old checker crashes by default, new one names the figure under both
encodings, for ≤ and −), F2 naming right (only the added "landed on trunk"
clause is wrong), F3 stated in the document matching the script docstring,
F4 paragraph accurate against worker/114e5b3f5b1b's CLAUDE.md and heater
fb353c6 with the three substitutions made, F5 pinned from `full` with a
real drift test and a delete-proof anchor; all four round-5 wording
findings resolved; 142 links / 55 targets / 0 broken verified; twelve
figures hand-traced with exact fractions, all match; the OpenSpiel
paragraph settles nothing; Q4's closing sentence (:1205-1206) and :825 /
:155 / :1120 "wait on the engine choice" read fine and need nothing;
checker 233 match; 35 passed with PYTHONIOENCODING unset and with cp1252.
Accepted limit, not a finding: on a legacy cp1252 console ≤ and − render
as mojibake; the figure name and numbers stay readable.

- F1 (substantive; a claim no store supports) :128-131 "…and
  RESOURCES_EXPLOITATION.md, which landed on the trunk branch on
  2026-09-17". On origin/main only RESOURCES_BOTS.md exists;
  ENGINE_ALTERNATIVES.md and RESOURCES_SOLVERS.md are on their branches;
  RESOURCES_EXPLOITATION.md is on LOCAL main (03622d6), not pushed.
  Resolve: delete the clause and let the four names stand (:974-979 and
  :1217-1219 already say correctly which are in progress); or state it per
  document, checked with `git ls-tree --name-only origin/main` at the time
  of writing. :526-529 and :1081-1083 name the four without asserting
  where they are — no change.
- W1 (wording) :143-146 "nothing below is rewritten on the strength of it
  and no recommendation changes" — :526-529 and :1079-1083 WERE rewritten
  on its strength in the same commit. Drop the first half, keep "no
  recommendation changes"; or "the two places below that name it do so as
  the same recorded decision, and no recommendation changes".
- W2 (wording) :140-142 three names with no plain words first: OpenSpiel's
  `universal_poker` (a published collection of ready-made game
  implementations, of which universal_poker is the configurable poker
  one); `fedden/poker_ai` is the same engine the document calls plain
  `poker_ai` from :80 and "the vendored poker_ai" at :1216 — say so;
  `dickreuter/Poker` same notation (its job is glossed).
- W3 (wording) :1079-1083 the closing clause "as the reconciliation … is
  made against it" does not parse; split into two sentences.
- W4 (wording) abbreviations never written out: EP/MP/LP/SB/BB (:348, R3
  heading :885, :889-890); wsd (:314); VPIP used in the §1.2 heading :182
  before its expansion :187; AF used :379 before its gloss :384; "A/B"
  :989 unglossed (a side-by-side comparison of two versions).
- W5 (wording) :184-189 the VPIP gloss splits a five-line sentence; make
  the expansion its own sentence. Five of the six new glosses name the
  abbreviation first, explain second (AF :384, pp :439, DBR :503, DBBR
  :567, bb/100 :990) — flip to plain words first where cheap.
- W6 (wording) :144-146 cites "branch worker/114e5b3f5b1b" as where the
  decision is written; that branch is not on origin either. Say the branch
  is unpushed and name heater commit fb353c6 as the durable record, or give
  the date and that the operator recorded it.

Every finding wording only: NO (F1 only).

Round-6 cost: 47 tool calls, about 40 minutes, no fetches; no dollar
figure. Six rounds on this change so far.
