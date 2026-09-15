# Handover

<!-- handover-commit: f909772 -->

Written at `f909772` on `main`. Verify with `bin/handover.py`. A snapshot,
not a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and commit messages for why.
**None of that is repeated here.** What follows is only what you cannot look
up.

---

## Why this session ended

The operator reported 97% of the five-hour usage window and said, verbatim:
"by the time we get to 95% usage in the 5 hour period i want to stop running
agents and just get a full debrief of what they have accomplished over the 5
hours in plain english". Every agent was stopped; nothing is running. The
debrief was given in the terminal and filed in the queue as a report. The
fleet still has no live usage number (the taper change is unlanded), so the
next session must ask the operator where the windows stand before dispatching
anything, and start small.

## Every open finding is under `handover/`

`handover/findings-*.md` hold the review findings each pending fixer needs.
They existed only in this session's conversation. Delete each file in its
change's landing commit. The state table below points into them.

## State of every change

| Change | Where it is | Next action |
| --- | --- | --- |
| Usage taper `c79a35661f9c` (heater) | 1a3a8eb on origin, merged with main, 477 tests, gate 0. 95% five-hour stop, `bin/debrief.py`, opinion 13 with four quotes. | Fresh round-2 review (default lens), then an environment-lens round is worth one pass (the reading depends on a real status line), then land. **Land this first**: it closes the collection hole. |
| Reconcile stale-pass fix `059566b3e160` (heater) | 2752f36 on origin, all round-1 findings applied, 442 tests green. Dispatch record CLOSED (pushed). | Fresh round-2 review, then merge from trunk yourself with `bin/gate.sh`. Until it lands, **run reconcile only after checking no open dispatch has a stale pass** (none does today). |
| Automatic handoff `46e285e1bfd0` (heater) | 14d9a31 on origin; round 5 FAILED (A, B behavioural); fixer did nothing before the stop. Dispatch record CLOSED. | Dispatch a round-5 fixer from `handover/findings-heater-pending.md`. After a wording-only round, merge from trunk with the gate; tell the operator to start `bin/stoker.sh` once. Conflicts with the taper branch on OPINIONS.md (12 and 13): keep both. |
| Opponent-model design `36e2ae4be45b` (pokerbot) | LANDED on pokerbot main at 659c6b7 by reconcile on a stale pass, without round 8. | Round-8 review against trunk. Wording-only: done. Substantive: escalate cost, no round 9 unasked. |
| Engine survey `7f09949cb56f` | Round 2 FAILED (4 substantive); fixer stopped mid-way, autosave 59022d1. | Fixer from `handover/findings-7f09949cb56f-engine-r2.md`, with its measurement rule. |
| Exploitation survey `76bbf2823a53` | Round 2 FAILED (9 substantive); fixer stopped at F5/F7, autosave e864c17. | Fixer from `handover/findings-76bbf2823a53-exploitation-r2.md`. |
| Bots survey `14d64950c0bc` | Round-2 fixes at 903c15e; round-3 review stopped mid-way. | Re-dispatch round 3 (see `findings-pokerbot-pending.md`). |
| Solvers survey `048795519f43` | Round-1 fixes at de64884; round-2 review stopped before it began. | Re-dispatch round 2. |
| Evaluation `45e49ce81e40` | Round 3 FAILED; findings only in the previous session's reviewer transcript (path in `findings-pokerbot-pending.md`). | Lower priority. |
| Table-size notes `984aa6810a05` | Round-3 fixes at 9c4a168. | Round-4 review. |

Priority the operator set: the four surveys → the reconciliation (the engine
decision) → the design → the handoff → evaluation → table-size. Land the
taper and the reconcile fix first anyway: they are small and they make the
rest safe.

## Traps found this session

- `bin/dispatch.py reconcile` landed the design on an hours-old pass because
  `reviewed()` accepts any pass ever recorded. The fix is on
  `worker/059566b3e160`; until it lands, check `store/reviews` for a stale
  pass on every open dispatch before each reconcile.
- Reconcile's autosave commits a live worker's half-edited tree. Judged
  intentional (two findings dismissed with the reason): review the branch tip
  against main, never commit by commit.
- Benchmarks on this laptop are noise while several agents run: the engine
  round-2 reviewer measured under a load average of 22 on 10 cores. Any brief
  with timings must carry the measurement rule in the engine findings file.
- Reviewers that run `hooks/stop.py` against a branch worktree dirty its
  copy of `queue/`; the taper fixer restored one such file. Tell fixers to
  check `git status` first.
- A closed dispatch releases its worktree slot; a later fixer must make its
  own worktree from origin (the reconcile fixer did, in its scratchpad).
- pokerbot has no remote and no `bin/gate.sh`; "push" means nothing there and
  the suite is `tests/ground_truth` in a venv from its requirements file.

## This machine

MacBook, Apple M4, 16 GB, no Homebrew, no tmux. A Rust toolchain now exists
only in the solvers fixer's scratch dir (RUSTUP_HOME/CARGO_HOME), nothing in
$HOME. Workers of type `worker`/`fixer`/`reviewer` have no WebFetch; curl and
gh work. Lid-close stalls every subagent; on wake, SendMessage each one "the
machine slept; continue from disk".

## Cost

This session: ~$86 (`~/.heater/context.json`), 26% context, 15 agents
dispatched, 8 review rounds recorded. 40 rounds in the last day carry no cost
figure; that hole is still open.
