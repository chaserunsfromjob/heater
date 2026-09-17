# Read-only assessment of the classmate's branch `codex/tonight` (2026-09-17)

Written on the PC session from a read-only assessor's report. Branch at
ca8339e, ten commits by Rohit Vakkalagadda (OpenAI Codex), forked from
trunk 3fbd279, pushed 2026-09-16, NO pull request. Nothing was written to
the branch. Delete this file once the operator has ruled and the ruling is
recorded in OPINIONS.md or pokerbot/CLAUDE.md.

## What it builds

A laboratory for testing poker strategies against each other on 52-card
no-limit hold'em at 2-9 seats (dealing, refereeing by PokerKit, exact
replay logs, a per-player fold-rate scorecard, a frozen benchmark with a
pre-declared pass mark), plus a first set of simple strategies (equity vs
pot odds; position; opponent-range guess; per-opponent fold-rate memory
with forgetting; turn/river rollout search). By its own notes
(research/BACKLOG.md:13-20, research/PROGRESS.md:11) no strategy variant
has passed the benchmark. What is solid: a real betting-rules bug (when a
player regains the right to re-raise after a short all-in) found and fixed
in OpenSpiel, PokerKit and NoRegrets, with TDA-rulebook fixtures.

Size: ~83,000 lines, of which 90.5% is generated result JSON (one file is
38,808 lines). The program is ~5,000 lines of Python.

## The forefront rule — the finding that needs the operator

Hand evaluation and rules: delegated to engines (pokerbot/equity.py:9-26
reads winners off OpenSpiel; engine.py:238-341 referees via PokerKit;
treys test-only). Sound.

Action choice: written on the branch in every policy — baseline_v1.py:16-29,
policies.py:62-87, card_controls.py:36-70 (hand-picked thresholds, 12%
bluff rate), range_policy.py:30-59, river_search.py:118-147,
turn_search.py:71-98. Opponent ranges assigned by a hand-written formula
(ranges.py:61-83, :113). Live opponents' fold rates averaged to shift a
raise threshold (policies.py:73-79) — the rule's own named example.

The branch resolves this by REPLACING CLAUDE.md (52 lines removed, 45
added): the forefront rule and its table, the plan, the compute budget and
the licence section are deleted. The new text (lines 7-25) is headed
"Scope authorized by the operator, September 16, 2026" and says "The
former ban on AI-authored strategy code is superseded" and "Remove the
former hours-on-one-laptop ceiling", and calls the design document and the
surveys "historical inputs". The old rule is moved to
research/LEGACY_GUIDANCE.md as "an archival test fixture", and
tools/check_design_numbers.py:284-286 is repointed at that copy so the
design-number check still passes. AGENTS.md (64 lines, Codex instructions)
repeats both reversals at :15-19 and at :63-64 disclaims merge authority.

heater's record says the opposite: commit fb353c6 (operator decision,
2026-09-16) "the action-chooser carve-out stays open"; worker/114e5b3f5b1b
(PC, 2026-09-17) records it as open and not granted. ONLY THE OPERATOR can
say whether the authorisation the branch cites exists.

## Other divergences

- Engine: the operator chose OpenSpiel as the road; the branch refereed on
  OpenSpiel, hit the short-all-in bug (research/PROGRESS.md:28-31), and
  moved refereeing to PokerKit, keeping OpenSpiel as hand-strength sampler.
  Reasoned and evidenced, but it changes a decision just made.
- Baseline: neither the 2009 archive nor observe-first; hard-coded starting
  assumptions (responses.py:21-22: fold 35%, raise 20%).
- OPPONENT_MODEL_DESIGN.md gets a banner calling it historical; the branch
  implements essentially none of it.
- research/patches/ carries patches against dickreuter/Poker (GPL-3.0) with
  a full licence copy; no code copied. Pull this thread before vendoring.

## Does it run

Not on the PC: pokerbot/runner.py:9 `import resource` and benchmark.py:3
`import fcntl` are Mac/Linux-only; the Windows OpenSpiel wheel lacks
`universal_poker` (7 failures "Unknown game 'universal_poker'"). Of the
files that load, 52 passed. The branch claims 177 passing on the Mac
(research/PROGRESS.md:44); unverified here. Needs a Mac.

## Options put to the operator (assessor's, not a decision)

A. Ask for a draft pull request and a description before reading further
   (the rule already on the books; cheapest).
B. Rule on the CLAUDE.md question first, in isolation: the repeal is
   separable (commit 2f0daf5 plus the CLAUDE.md part of 306bdf1); the other
   nine commits are the building.
C. Split: take the engine-side rules-bug work (pokerkit_rules.py,
   REOPENING_REPAIR.md, TDA fixtures, probes), leave the strategy modules
   for after the ruling, move result JSON out of the tree.
