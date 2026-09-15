# Handover

<!-- handover-commit: 4cb65b6 -->

Written at `4cb65b6` on `main`. Verify with `bin/handover.py`. A snapshot,
not a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and commit messages for why.
**None of that is repeated here.** What follows is only what you cannot look
up.

---

## First: the operator's taper policy, stated today and not yet in any rule

"as we get closer to both running out of 5 hour usage and weekly usage, i
want to implement running less agents and using less usage more and more as
we approach the limit ... cut agents that are working on things that are not
as important, and prioritize more important tasks at your discretion."

The fleet records NO 5-hour/weekly utilization — that is task (score 65, top
of `bin/inbox.py tasks`). Until it is closed, taper by judgement and say so.
Priority order the operator has set, highest first: the four research
surveys → the reconciliation (the engine decision) → the opponent-model
design → the automatic handoff → evaluation → table-size notes. This session
cost about $207 (`~/.heater/context.json`, `cost_usd`), with up to 10 agents
at once; the operator did not object but has now asked for restraint as
limits approach.

## Other operator positions stated today, recorded only as ranked tasks

Dispatch tasks 96243ce4163a, f2f8237946ac, 4fd636640f0a, 65bba741bf40 as ONE
brief once `36e2ae4be45b` lands (all touch `pokerbot/CLAUDE.md`): the
mandate ("beating real players by a lot, 2-9 players, exploitative play. i
dont care how you do it"), no multi-day computing, private and never
distributed, and "mostly 6 player tables, followed by 8 or 9 player tables
which can honestly be treated the same". Opinion 12 (handoff needs nothing
from the operator) is on branch `worker/46e285e1bfd0`, not yet on main.

## This machine

MacBook, Apple M4, 16 GB RAM, no Homebrew, no tmux, no Rust toolchain. pip
egress is sometimes blocked for subagents; curl and git clone work. Workers
of type `worker`/`fixer`/`reviewer` have no WebFetch; use `general-purpose`
for web research. `caffeinate -dims` runs to stop idle sleep; lid-close still
sleeps, and every subagent stalls when it does — on wake, `SendMessage` each
stalled agent by name with "the machine slept; continue from disk" and they
resume with their memory intact (proven today, nine of nine).

## Landed today

pokerbot `aebf85e3a420` (vendoring + REFERENCE_NOTES + licence/compute/
combinatorics bullets in CLAUDE.md) landed at pokerbot `3dc6fd9` after six
rounds. Every other pokerbot branch is now BEHIND main and will need a merge;
`36e2ae4be45b` will conflict on CLAUDE.md (both changed it).

## State of every change (pokerbot has no remote; branches live locally)

| Change | Checkout | Where it is when this was written |
| --- | --- | --- |
| Opponent-model design `36e2ae4be45b` | `4c952047cdd3` | Round-7 fixer running (narrow: one arithmetic sentence, the seat priority in §4.5, ~15 figures the checker missed). Seven rounds; `tools/check_design_numbers.py` checks 554 figures and is the source of truth. If round 8 is wording-only, land (after a CLAUDE.md merge fix). If it fails on substance, escalate the cost — do not run round 9. |
| Engine alternatives `7f09949cb56f` | `92e2a2c459ef` | Round-1 fixer running (commit the research bot, per-mode speeds, drop/bound the noise "+3.87", scope the "no offline training" claim, route the forefront carve-out to the reconciliation). |
| Table-size notes `984aa6810a05` | `8b0b4064141f` | Round-3 fixer running (the band-boundary rationale was false; 4.5× was the wrong ratio). Cross-refs pinned to companion commit 5aa40b8 — reviewers must judge against that, not the moving working tree. |
| Evaluation strategy `45e49ce81e40` | `9fd7bd8ad257` | Round-3 review running. Nightly acceptance = 5 seats (6,8,9,2 + one rotating), 20 cells, ~4.9 h; every seat gates on a four-night window. The 10 h / 1 h bounds are the stoker's design choices, labelled so. |
| Bots research `14d64950c0bc` | `b1f72dd635fa` | Round-2 review running. Headline: NoRegrets needs 36–50 GB RAM (out on 16 GB); no surveyed bot covers 7–9 seats with true no-limit; value is in pieces (Slumbot benchmark, OpenHoldem's per-name stat design, ppl-interpreter). |
| Solvers research `048795519f43` | `85f4140c6fae` | Round-1 fixer running (Rust timings unreproducible here; OMPEval capped at 6 players; MonkerSolver mis-listed; recommendation must not settle engine choice). |
| Exploitation research `76bbf2823a53` | `41a874aea055` | Round-1 fixer running (fpdb-3 modules don't import standalone and DerivedStats carries a second evaluator; add villain, NE_RL, pokerchase-hud). phh-dataset (21.6M hands, 2–10 seats, stable player codes, CC BY) verified real and is the BASELINE source. |
| Automatic handoff (heater) `46e285e1bfd0` | scratchpad worktree `/private/tmp/claude-501/-Users-chasethompson-heater/60db9bfd-fa3a-4035-aa37-91a8741fa698/scratchpad/review-46e285e1bfd0`; branch on origin | Round-3 fixer running (marker ownership by supervisor pid+start time so stale markers are reclaimed; marker checked before child-exit; O_EXCL create; crash-vs-operator-stop distinction). Dispatch record already CLOSED — `reconcile` will not land it; after a wording-only round, merge from trunk yourself with `bin/gate.sh`. If the scratchpad worktree is gone: `git worktree prune` then re-add from `origin/worker/46e285e1bfd0`. |

Every dispatch above except the handoff is still OPEN in `bin/dispatch.py
list`; land them only through `bin/dispatch.py land <id> --gate "<pytest
commands>"` (pokerbot has no gate script — task 5283f76b00b9) so the lease and
branch are cleaned up. Closing a dispatch by hand releases the worktree.

## The decision at the end of the research

Four surveys disagree on where the bot's poker judgment comes from:
ENGINE_ALTERNATIVES says compute each decision at play time with OpenSpiel
(needs a recorded carve-out to the forefront rule: a rollout chooser is
action-choosing code we wrote); RESOURCES_BOTS found nothing that fits 16 GB
and all five criteria; RESOURCES_SOLVERS found fast heads-up solvers and
equity tools but nothing multiway at decision speed; RESOURCES_EXPLOITATION
found the opponent-statistics side is well covered (fpdb-3 counting logic,
phh-dataset, pokeragent's DBBR). **Once all four have passed review, dispatch
ONE worker to reconcile them into a plan with measured numbers and record the
forefront-rule decision in pokerbot/CLAUDE.md.** Do not pick by instinct, and
do not let any survey settle it by assertion — three of the four tried.

## Traps

- `bin/store.py review` refuses `--verdict pass` when any finding is
  substantive; record such rounds as fail.
- A fixer that finds a defect inside its own change must fix it, not file
  it — three did today; a one-line SendMessage sends them back.
- Reviewers of documents that cite a companion under revision judge a stale
  copy unless told which commit to read.
- The design document's rounds 1–6 each found new arithmetic drift; the
  checker ended that class. Any new numeric design document should ship
  with the same kind of checker from its first round.

## Nothing is blocked on the operator

They know the research is the focus, the engine decision is coming, and that
this session is handing over.
