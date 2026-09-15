# Handover

<!-- handover-commit: 9242a44 -->

Written at `9242a44` on `main`. Verify with `bin/handover.py`. A snapshot, not
a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and commit messages for why.
**None of that is repeated here.** What follows is only what you cannot look
up.

---

## Why this handover exists

The operator is closing the laptop mid-flight. Every agent below dies with the
sleep (their network calls fail on wake). Their **on-disk work survives** in
the worktrees; the job on reopening is to re-dispatch each unfinished round
from what is on disk, not from scratch. Run `bin/bearings.py`, then
`bin/dispatch.py list`, then check each worktree's `git status` and
`git log -3` before dispatching anything.

## Operator positions stated this session, not yet in any rule file

All recorded verbatim as ranked tasks (`bin/inbox.py tasks`: 96243ce4163a,
f2f8237946ac, 4fd636640f0a, 65bba741bf40) — dispatch them as ONE brief once
`36e2ae4be45b` lands, since all touch `pokerbot/CLAUDE.md`:

- Mandate: "just do whatever you think is best ... beating real players by a
  lot, 2-9 players, exploitative play. i dont care how you do it."
- No multi-day computing; a playable bot in hours on one laptop.
- Private, never distributed (so GPL and paid tools are fine).
- Plays mostly 6-handed, then 8/9 "treated the same".
- Fleet-level: opinion 12 (handoff needs nothing from the operator) is on
  branch `worker/46e285e1bfd0`, not yet on main.

## State of every change (all pokerbot unless noted; pokerbot has no remote)

| Change | Branch / checkout | Where it is |
| --- | --- | --- |
| Vendoring `aebf85e3a420` | `0f748212fb4c` | Round 4 review (default + environment) was running. Rounds 1-3 recorded fail (r3 had only two small leftovers, fixed in 3ba7e8c). If r4 is wording-only → land it. |
| Opponent-model design `36e2ae4be45b` | `4c952047cdd3` | Round-6 fixer was running: applying 6 findings AND writing `tools/check_design_numbers.py` + `tests/test_design_numbers.py` so every derived number is machine-checked. Six rounds so far, each finding new arithmetic drift — if round 7 fails on substance, **escalate the cost to the operator** rather than spin round 8. |
| Engine alternatives `7f09949cb56f` | `92e2a2c459ef` | Round-1 fixer was running: commit the research bot under `research/engine_alternatives/`, state betting mode per speed row, drop or bound the +3.87 bb/hand figure (it was noise: ±25 at n=300), scope the "no offline training" claim, and reframe the forefront-rule carve-out as a decision for the reconciliation step. |
| Table-size notes `984aa6810a05` | `8b0b4064141f` | Round-2 review was running (fix ace10ce applied 11 findings). |
| Evaluation strategy `45e49ce81e40` | `9fd7bd8ad257` | Round-1 fixer was running with the stoker's decisions on Q1/Q3/Q4 and the operator's answer to Q2 (6-max first, 8/9 one band). |
| Bots research `14d64950c0bc` | `b1f72dd635fa` | Committed 60c6835; round-1 review was running (verification-heavy: NoRegrets is the lead candidate). |
| Solvers research `048795519f43` | `85f4140c6fae` | Worker was running; check for a commit. |
| Exploitation research `76bbf2823a53` | `41a874aea055` | Worker was running; check for a commit. |
| Automatic handoff (heater) `46e285e1bfd0` | scratchpad worktree at `/private/tmp/claude-501/-Users-chasethompson-heater/60db9bfd-fa3a-4035-aa37-91a8741fa698/scratchpad/review-46e285e1bfd0`; branch on origin | Round-2 fixer was running (6 findings, the big one: Ctrl-C during the 2 s grace crashed the supervisor). Dispatch is already CLOSED (closing released its lease — a mistake to avoid: close only after landing), so `reconcile` will not land it; merge from trunk yourself after a wording-only round. The scratchpad worktree may be gone after a reboot: `git worktree prune`, then re-add from `origin/worker/46e285e1bfd0`. |

## The decision waiting at the end of the research

Two documents disagree on how the bot gets its poker judgment:
ENGINE_ALTERNATIVES.md says compute each decision at play time with OpenSpiel
(needs a recorded carve-out to pokerbot's forefront rule, because a rollout
chooser is action-choosing code we wrote); RESOURCES_BOTS.md says adopt
NoRegrets (2–6 player Pluribus-style, its own code chooses, claims a
blueprint in ~1 h on 16 cores — unverified on a Mac). Neither has passed
review. **Do not pick by instinct**: once engine, bots, solvers and
exploitation have all landed, dispatch one worker to reconcile them into a
plan with measured numbers (a half-day NoRegrets spike on this Mac is the
obvious first measurement), and record the forefront-rule decision in
pokerbot/CLAUDE.md as part of that.

## Traps

- `bin/dispatch.py close --outcome pushed` releases the lease and deletes
  the worktree. For pokerbot branches that is fine (the branch stays in the
  local repo) but findings a worker filed from inside a heater worktree are
  lost with it (task d67cffad749a). Close pokerbot research dispatches only
  via `reconcile`/`land` after review.
- `bin/store.py review` refuses `--verdict pass` when findings are
  substantive; record such rounds as fail.
- Reviewers judging TABLE_SIZE_AND_SIZING_NOTES.md must read the CURRENT
  companion design doc in `4c952047cdd3`; round 1 judged a stale copy.
- Workers of type `worker`/`fixer`/`reviewer` have no WebFetch; `curl` and
  `git clone` work. Use `general-purpose` for web research.
- `caffeinate -dims` is running to stop idle sleep; lid-close still sleeps.

## Nothing is blocked on the operator

They know the research is the focus and that the engine decision is coming.
