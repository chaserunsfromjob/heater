# Opponent-model design 36e2ae4be45b — round 9 findings (fail; F1 substantive)

Delete this file, and `findings-36e2ae4be45b-design-r8.md`, in the landing
commit. The design is on main; the round-8 fix is on branch
worker/142074837788 (checkout `C:\Users\chase\.heater\worktrees\pokerbot\design`
on the PC, cut from local main 03622d6), tip c0fa920 as reviewed. Recorded in
the store as round 9 (b9c1d4e6f2a8). Lens default. Lines at c0fa920.

Sound and not to be re-checked: round 8's list; S1 arithmetic
(MIN_CLASSIFY_HANDS 50 with s = 50 → confidence exactly 0.5 at 50;
WARMUP_HANDS 200; below 50 both refuse, 50-199 warm-up binds, 200+ neither)
agreed at :1350-1352, :1378-1386, :1554-1557 and the Tier 0 example
:1232-1238; S2 applied at :1009-1013, :1528, :1532, :1582-1588, remaining
"fire" uses mean "is set", §4.6 table still descriptive, no mechanism
invented, "Choosing an action" quoted from the right column; W1 and W2
quotations verbatim (AISTATS09.pdf §5.2 "Curve confidence functions";
opponentModeling.aamas11.pdf), both fetched 2026-09-17 00:59Z; W3 naming;
W4 facts true today; checker 680 exit 0, 25 passed, checker names a
drifted figure without crashing (the ± prints as a replacement character
on cp1252 — cosmetic).

- F1 (substantive) tools/check_design_numbers.py, unchanged by the fix,
  does not pin the fix's own figures at OPPONENT_MODEL_DESIGN.md:1350-1352,
  :1383-1386, :1549-1557: mutating "from 50 to 199"→198, "clears at
  200"→300 (twice), "between 50 and 199"→149, "200 hands against 50"→300 all
  leave "680 figures … all match", exit 0. Round 8 recorded a mutation sweep
  with no escape; the fix broke that property. Resolve: add checks pinning
  the three boundary statements against MIN_CLASSIFY_HANDS and WARMUP_HANDS
  (the "50 to 199" spans as MIN_CLASSIFY_HANDS to WARMUP_HANDS − 1; bare
  "clears at 200" and "200 hands against 50" as WARMUP_HANDS and
  MIN_CLASSIFY_HANDS), using every_occurrence/prose; the figure count must
  rise above 680; add a mutation test in tests/test_design_numbers.py.
- W1 (wording) :1363 Tier 1 table "The bot loads it when…" column says
  S_BASE loads when "any opponent is UNKNOWN, or the table is mixed" —
  omits warm-up. Resolve: "any opponent has not passed warm-up or is
  UNKNOWN, or the table is mixed".
- W2 (wording) :315 glosses open_raise as "PFR split five ways by seat
  bucket"; §4.2 :679 defines open_raise as first-in with no prior raiser,
  a different denominator from pfr :312. Resolve: "made the first raise
  preflop, first-in with no prior raiser; split five ways by seat bucket".
  (:854-858 already reconciles Tier A/B.)
- W3 (wording) :1046-1048 "The first tier at which a flag could reach play
  is Tier 2" — Tier 2 (:1434-1440) consumes per-public-history action
  frequencies, not flags. Resolve: Tier 2 is the first tier at which the
  engine receives a per-opponent model at all, so the earliest point a
  flag's underlying rates reach play; no flag-specific consumer is
  specified even there.
- W4 (wording) :1290-1291 names the engine branch's heads 6720c8a (local)
  and 52bd81d (origin); they go stale. Keep the branch name and "has not
  landed"; drop the hashes or mark them as at the time of writing.

Every finding wording only: NO (F1).

Round-9 cost: 27 tool calls, about 11 minutes, two PDF fetches; no dollar
figure. Nine rounds on this change so far.
