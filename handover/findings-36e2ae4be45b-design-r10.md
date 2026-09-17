# Opponent-model design 36e2ae4be45b — round 10 findings (fail; F1 substantive)

Delete this file, and `findings-36e2ae4be45b-design-r{8,9}.md`, in the landing
commit. Fix branch worker/142074837788 (checkout
`C:\Users\chase\.heater\worktrees\pokerbot\design` on the PC), tip 51fb5b7 as
reviewed. Recorded in the store as round 10 (b3d5f7a9c2e4). Lens default.
Lines at 51fb5b7. Merges cleanly into local main 0565d1a.

Sound and not to be re-checked: rounds 8 and 9's lists; round-9 F1's three
new checks pin what they name (six mutations exit 1, named); W1 (:1364 the
negation of the load rule), W2 (:315 — "Made" capitalised and the five
buckets kept are both right), W3 (:1046-1053 accurate against Tier 2
:1434-1441), W4 (hashes dropped; branch facts true); no engine-side flag
mechanism invented; the design cites CLAUDE.md by section only, and the
checker's table comparison exits 0 against main's CLAUDE.md; checker 683;
28 passed; the three new tests non-vacuous.

- F1 (substantive) tools/check_design_numbers.py:22-27 states the standard
  ("mutating any derived figure in the document, anywhere, makes this script
  exit 1") and three bare restatements in §5.2 escape it (each →80/300
  exits 0, "683 … all match"): :1553 "at that same 50 the Tier A
  confidence(vpip) ≥ 0.5 threshold is reached too" — a DERIVED figure
  (opportunities_at_gate at :304-306 from PRIOR_STRENGTH["vpip"] and
  CLASSIFY_CONF_GATE); :1555 "Below 50 hands both gates refuse"; :1558
  "from 200 on, neither of the two holds it back" — recorded nowhere until
  now (the first two are queue finding fcf61d67d726). Resolve: in
  check_restated_constants add `from (\d+) on, neither` as one more
  alternative to the existing WARMUP_HANDS every_occurrence (:1553-1557);
  add one every_occurrence against MIN_CLASSIFY_HANDS with alternatives
  `Below (\d+) hands\s+both gates refuse` and `at that same\s+(\d+) the Tier
  A` (both straddle a line break — match on whitespace); one mutation test
  each; figure count above 683; then close fcf61d67d726 as done
  (`bin/inbox.py` / mark the queue file's resolution).
- W1 (wording; durability) tools/check_design_numbers.py:1577-1584 the new
  `(\d+) hands against (\d+)` pattern has no anchoring word; anchor it, e.g.
  `clear at different\s+points — (\d+) hands against (\d+)`.
- Observation (not a finding): on a cp1252 console the checker crashes
  with a traceback (exit still 1) when a FAILING figure's name carries ⌈⌉;
  pre-existing; the Mac never sees it.

Every finding wording only: NO (F1).

Round-10 cost: 40 tool calls, 46+ mutations, about 15 minutes; no dollar
figure. Ten rounds on this change so far.
