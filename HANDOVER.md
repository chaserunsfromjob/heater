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
| Fix usage taper round 4 | `c79a35661f9c` | fixer 4 (round 4 failed on the debrief page only: two entries describe the wrong work, a repository and a branch name still reach the page, the repeat count reads lossy text; see `handover/findings-c79a35661f9c-taper-r4.md`; taper half sound for the third round) | dispatch review round 5; wording-only → confirming round → `bin/dispatch.py land`; at landing mark task 32cbdf129bdf done (the 95 STOP band and debrief are in this branch) |
| Review reconcile change round 5 | `059566b3e160` | review 5 (round-4 fixes at 0b9af3e on origin: runs split into consolidated and still-to-account-for, failed round named on left-behind and unknown lines; fixer flagged that `land()` records no commit state so its runs list as still-to-account-for; reviewer weighs it) | record; fail → fixer; wording-only → failure-mode lens, then land by merging from trunk with the gate |
| Review automatic handoff round 8 | `46e285e1bfd0` | review 8 (default + failure-mode; round-7 fixes at b0f9878 on origin: bounded hold, one session named once, unwritten note logged and its claim not counted; a stale round-7 reviewer worktree still holds the branch name, task 418b4396b9f7, so reviewers use `worktree add --detach`) | record; fail → fixer; wording-only → confirming round → merge from trunk, tell the operator to start `bin/stoker.sh` once |
| Fix exploitation survey round 4 | `76bbf2823a53` | fixer 4 (round 4 failed: 3 substantive, two of the over-claim class; see `handover/findings-76bbf2823a53-exploitation-r4.md`) | dispatch review round 5 |
| Fix engine survey round 2 | `7f09949cb56f` | fixer 2 | dispatch review round 3 |
| Fix bots survey round 5 | `14d64950c0bc` | fixer 5 (round 5 failed on the two sentences the round-4 fixer added on its own; see `handover/findings-14d64950c0bc-bots-r5.md`; brief forbids adding anything beyond the findings) | dispatch review round 6 |
| Fix solvers survey round 3 | `048795519f43` | fixer 3 (round 3 failed: 6 substantive, runtime evaluator nominated inside "settled", flop figures a composite of runs of different lengths; see `handover/findings-048795519f43-solvers-r3.md`) | dispatch review round 4 |

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
