# Handover

<!-- handover-commit: 8fe7217 -->

Written at `8fe7217` on `main`. Verify with `bin/handover.py`. A snapshot,
not a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and commit messages for why.
**None of that is repeated here.** What follows is only what you cannot look
up.

---

## First: seven agents are running (the table is current as of the stamp) and will report to you

The operator cleared the context with agents still out (the limits had just
reset; the operator said "lets continue with the agents and the work", then
"lets wipe the context"). A cleared context keeps its subagents: their
reports arrive in the new context as messages headed "Subagent hand-back".
Act on each as it lands; do not re-dispatch a round that is already out.

| Agent name (as its report will show) | Change | Round out | On its report |
| --- | --- | --- | --- |
| Fix usage taper round 3 | `c79a35661f9c` | fixer 3 (round 3 failed on the debrief prose and a bearings crash; see `handover/findings-c79a35661f9c-taper-r3.md`) | dispatch review round 4; wording-only → confirming round → `bin/dispatch.py land` |
| Fix reconcile change round 3 | `059566b3e160` | fixer 3 (round 3 failed on the alarm gate's could-not-check case; see `handover/findings-059566b3e160-reconcile-r3.md`) | dispatch review round 4; wording-only → land by merging from trunk with the gate |
| Review automatic handoff round 7 | `46e285e1bfd0` | review 7 (default + failure-mode; round-6 fixes at 029057a: un-ended child announced, locked record, atomic write) | record; wording-only → confirming round → merge from trunk, tell the operator to start `bin/stoker.sh` once |
| Fix exploitation survey round 3 | `76bbf2823a53` | fixer 3 (round 3 failed: 4 substantive; see `handover/findings-76bbf2823a53-exploitation-r3.md`) | dispatch review round 4 |
| Fix engine survey round 2 | `7f09949cb56f` | fixer 2 | dispatch review round 3 |
| Review bots survey round 4 | `14d64950c0bc` | review 4 (round-3 fixes at fd21a22) | record; fail → fixer; wording-only → confirming round |
| Fix solvers survey round 2 | `048795519f43` | fixer 2 | dispatch review round 3 |

Every review round so far is recorded in the store. Record each new one
with `bin/store.py review` the moment it returns (a pass with any
substantive finding is recorded as fail). The store notes carry each round's
findings in one line; the full findings live in the fixer briefs, which are
gone with the context, so if a fixer's report never arrives, brief the next
one from the store note plus a fresh read of the reviewer's transcript under
`~/.claude/projects/-Users-chasethompson-heater/9aadbb23-…/subagents/`.

## Every open finding is under `handover/`

`handover/findings-*.md`: one per pending fixer input, plus the two
"pending" files that give the next action for every change. Delete each in
its change's landing commit.

## Priorities and the taper

Operator's order: the four surveys → the reconciliation (the engine
decision) → the design → the handoff → evaluation → table-size. Land the
taper and the reconcile fix first anyway: small, and they make the rest
safe. The fleet still has no live usage number until the taper lands; ask
the operator where the windows stand if in doubt, and hold at about seven
agents. The design document's round 8 has been waiting for a slot all day;
take it when one frees.

## Traps found this session

- `bin/dispatch.py reconcile` landed the design on an hours-old pass because
  `reviewed()` accepts any pass ever recorded. Fix on `worker/059566b3e160`;
  until it lands, check `store/reviews` for a stale pass on every open
  dispatch before each reconcile (none today).
- Reconcile's autosave commits a live worker's half-edited tree. Judged
  intentional twice: review the branch tip against main, never commit by
  commit. Reconcile reports the taper branch "held" whenever the fleet repo
  has uncommitted files; commit the store first.
- Benchmarks are noise while several agents run (load average 22 on 10
  cores once). Every brief with timings carries a measurement rule: check
  `uptime`, wait below 4.0, record the load beside each figure.
- Reviewers that run `hooks/stop.py` against a branch worktree dirty its
  copy of `queue/`; tell fixers to check `git status` first.
- A closed dispatch releases its worktree slot; reviewers and fixers of the
  reconcile fix make their own worktree in the scratchpad and remove it.
- Fixers sometimes file a defect inside their own change instead of fixing
  it; a one-line SendMessage sends them back.
- Two fixers substituted "Claude Opus 5" for the attribution line the brief
  gave; harmless, do not chase it.
- pokerbot has no remote and no `bin/gate.sh`; "push" means nothing there;
  the suite is `tests/ground_truth` in a venv from its requirements file.

## This machine

MacBook, Apple M4, 16 GB, no Homebrew, no tmux. A Rust toolchain and built
solvers exist only in fixers' scratch dirs under
`/private/tmp/claude-501/-Users-chasethompson-heater/` (RUSTUP_HOME and
CARGO_HOME set there), nothing in $HOME. Workers of type
`worker`/`fixer`/`reviewer` have no WebFetch; curl and gh work. Lid-close
stalls every subagent; on wake, SendMessage each one "the machine slept;
continue from disk". A zip of both projects and the fleet state sits on the
Desktop (`pokerbot-and-fleet-2026-09-15.zip`); pokerbot still has no online
backup, and giving it a private GitHub remote is worth a dispatch.

## Cost

This session: about $160 (`~/.heater/context.json`), 38% context, 26 agents
dispatched, 17 review rounds recorded. 40+ rounds carry no cost figure;
that hole is still open.
