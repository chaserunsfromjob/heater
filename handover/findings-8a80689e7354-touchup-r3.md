# Exploitation-survey trunk touch-up 8a80689e7354 — round 3 findings (pass; wording only)

Delete this file, `findings-8a80689e7354-touchup-r{1,2}.md` and
`findings-pokerbot-trunk-touchup.md` in the landing commit. Branch
worker/8a80689e7354, checkout `C:\Users\chase\.heater\worktrees\pokerbot\touchup`
on the PC, tip cb8d797 as reviewed; merges clean into main f8dc012. Recorded
in the store as round 3 (f9d3b5a7c2e4). Lens default. FIRST wording-only
round; fixer applies W1-W6, then confirming round 4; wording-only → land.

Sound and not to be re-checked: rounds 1-2's lists; round-2 F1 (AF, AFq,
AGG% exact against the design and the table; AGG% a near neighbour at
:1138); F2 (criterion (e) :147-159 conditional, narrowed, routed; §3.2
:1029-1036 mirrors §1.6's AGPL wording at :435-438; §3.3 keeps its own
ToS note); all eighteen (e) marks; W1-W5 landed; the design byte-identical
on branch and main; suite 25; checker 680.

- W1 :1119-1121 vs :1138-1139 AGG% is "the same statistic as AFq except…"
  and twenty lines later "not the same statistic". One voice: at :1119-1120
  "counted the same way as AFq but over a smaller set of actions, so it is
  a different number"; and "never lower, and higher for anyone who folds"
  is exact where "read higher" is not.
- W2 :1114-1115 "Three ways of measuring aggression appear in the table" —
  the column also carries PFR bands, a VPIP/PFR ratio and per-street
  deviation scores. "Three closely-named measures of aggression appear in
  the table and are easy to confuse."
- W3 :1135-1139 the direction of the AGG%/AFq difference is unstated: an
  AGG% floor of 35 is an AFq floor below 0.35, so 0.50 is the more
  demanding line, not an outlier; and the floor comes from fpdb-3's row
  only, not "every scheme". One clause.
- W4 :152-154 and :1030-1032 "nothing of it is copied … or passed on, so
  that nothing of it would be published" — the tail repeats; drop it in
  both. Use :151's "published for anyone to fetch" at :155 too.
- W5 :1032-1034 the copyright notice is quoted in full twice in §3.2; "The
  page carries a copyright notice (above) with no grant of any kind."
- W6 :1208-1209 shortlist item 9 reads "free" alone; add "no licence
  stated; its ✔ is conditional and the copyright question is with the
  operator (§3.2)".

Every finding wording only: YES.

Round-3 cost: 23 tool calls, about 11 minutes, no fetch; no dollar figure.
Three rounds on this change so far.
