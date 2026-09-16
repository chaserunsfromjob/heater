# Opponent-model design 36e2ae4be45b — round 8 findings (fail; S1-S2 substantive)

Delete this file when the design is declared done. The design is already on
pokerbot main (landed by reconcile at 659c6b7 on a stale round-4 pass; round-7
fixes at 72eff27 and 5f7a1a8). Round 8 was reviewed against trunk
`/Users/chasethompson/pokerbot/OPPONENT_MODEL_DESIGN.md` plus
`tools/check_design_numbers.py` and `tests/test_design_numbers.py`. Recorded in
the store as round 8 (eaed53858431). No round 9 or fixer runs until the
operator answers the escalation queued 2026-09-16. Lines are at trunk as
reviewed; re-locate by content.

Sound and not to be re-checked: the checker (680 figures, exit 0), 25 tests,
all six primary citations verbatim, about thirty figures recomputed by hand,
a 300-token mutation sweep (no derived figure escaped), a CLAUDE.md drift test
(the §1 reproduction is checked against the real file), the forefront
boundary (nothing tells our code to combine live opponents' rates, assign a
range, or choose an action), the heater task quote at :1285.

- S1 (substantive) :1505-1507 says the table reads `S_BASE` until every live
  opponent has passed warm-up "because §4.5 already refuses a
  counter-strategy while any live opponent is `UNKNOWN`". It does not:
  `UNKNOWN` clears at `MIN_CLASSIFY_HANDS = 50` (with s = 50, confidence ≥
  0.5 is the same point, :977-978) while `WARMUP_HANDS = 200`, so for 50-199
  stored hands the two rules disagree; §4.5's load rule at :1345-1347 never
  mentions warm-up, and the heads-up case at :1317-1318 loads "once they are
  classified", i.e. at 50. The Tier 0 example at :1210-1212 treats warm-up as
  a separate gate. Resolve: make warm-up an explicit conjunct of the §4.5 load
  rule and of the heads-up case; replace the "because §4.5 already refuses"
  clause with a statement of which gate binds when they differ. Do not
  resolve by lowering `WARMUP_HANDS` to 50 without saying why (:1509-1515
  argues 200 against DBBR's T = 1000).
- S2 (substantive) :1022-1103 (and :603, :625, :1008, :1487, :1491,
  :1528-1530). `classify.py` emits `Bucket` + `ExploitFlags`; seven flags are
  fully specified with confidence gates, margins and margin-vs-interval
  proofs; :1008 says flags "reach for money", :1487 "no exploit fires below
  its threshold", :1491 tracks bb/100 per flag and disables non-earning
  exploits, :1528-1530 says a flag "must go stale and switch off". Nothing
  consumes them: `select.py` takes buckets + table context (:626), Tier 1's
  load rule reads bucket labels only (:1328-1347), Tier 2 is per-opponent
  DBBR, Tier 3 is out of scope. The only description of a flag's effect on
  play, the table at :1425-1437, sits under :1410-1415 "descriptive, not
  prescriptive ... No coding task should implement this table as rules." The
  obvious mechanism (adjust the bot's action when a flag is set) is
  "Choosing an action" at CLAUDE.md:23, the engine's side. Resolve: either
  say plainly that flags are report-only diagnostics until Tier 2 and
  re-scope :1008, :1487, :1491, :1528-1530 to match, or name the engine-side
  mechanism a flag feeds (a second archetype axis, a per-flag solve, a
  strategy-selection input), which tier builds it, and which side of
  CLAUDE.md:20-31 it sits on. The first is the conservative reading and
  needs no new engine mechanism.
- W1 (wording) :1700-1704 and :514-516 call "1-Curve = s-Curve at s = 1" this
  document's inference. Johanson & Bowling 2009 §5.2 states it: "The s-Curve
  function returns Pmax × (nI/(s + nI)) for any constant s; in this
  experiment, we used s = 1." State it as the paper's own, cite §5.2, drop
  the "check the primary text" caveat.
- W2 (wording) :538-540 the `N_prior` quote ends at "...observed the
  opponent's action 5 times"; the source continues "at the given public
  history set". Restore the clause or mark the elision.
- W3 (wording) :315 `open_raise_by_seat` split four ways (early/middle/late/
  blinds) vs the §4.2 table at :676 `open_raise` with EP/MP/LP/SB/BB and
  :853-855 "split five ways by seat bucket". :667-669 says implement §4.2
  literally. Make §2.3 use the §4.2 name and the five-way split. The stale
  name escapes the checker, which validates names against §4.2.
- W4 (wording) :1260 makes Tier 1 conditional on `ENGINE_ALTERNATIVES.md`,
  which is not on trunk (only on unlanded worker/7f09949cb56f). Say it has
  not landed and where it is, or drop the reference until it lands.

Round-8 cost: reviewer 24 tool calls, about 12 minutes at load 3.7-5.3,
137,782 tokens; no dollar figure (the cost hole is still open).
