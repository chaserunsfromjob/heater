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
| (none running) usage taper | `c79a35661f9c` | round 5 failed on the debrief page only (5 substantive, 6 wording; see `handover/findings-c79a35661f9c-taper-r5.md`); taper half sound four rounds running. Fixer 5 waits for a slot behind the research | when a slot is free after the research: fixer 5 from that file, then review 6; wording-only → confirming round → `bin/dispatch.py land`; at landing mark task 32cbdf129bdf done |
| Fix evaluation strategy round 3 | `45e49ce81e40` | fixer 3 (round 3 failed 2026-09-15 21:22Z: gated on a 52-card conversion trunk says is out, summary carries the abolished four-seat grid, a weights arithmetic error, the sha-gating rule stated five ways; findings recovered from the reviewer transcript into `handover/findings-45e49ce81e40-evaluation-r3.md`) | dispatch review round 4 |
| Review table-size notes round 4 | `984aa6810a05` | review 4 (round-3 fixes at 9c4a168; cross-references judged against trunk's OPPONENT_MODEL_DESIGN.md at 5aa40b8 and REFERENCE_NOTES.md's seven-seat ceiling) | record; fail → fixer; wording-only → confirming round |
| (none running) reconcile change | `059566b3e160` | fixer 5 done at 79d66c1 on origin (`land` records where the commits went via `close_landed`; `consolidated_now` re-asks git at every sweep; SKILL.md rows; 475 tests, gate 0). Review 6 waits for a slot behind the research (operator's instruction 2026-09-15 late: wrap the research inside this usage window) | when a slot is free after the research: review round 6 at 79d66c1; wording-only → failure-mode lens, then land by merging from trunk with the gate. Note for that reviewer: the two-round landing rule is still not coded (task f16c56933d8a) |
| (none running) automatic handoff | `46e285e1bfd0` | fixer 8 done at 1c55d7f on origin (all four text findings applied, 497 tests, gate 0); one in-change finding dismissed and carried: the `end_session` docstring at tools/stoker.py:827-828 still promises a fresh session, false on the two exit paths. Review 9 waits for a slot: the operator's order puts research ahead of the handoff, and the operator has asked to wrap the research inside this usage window | when a slot is free after the research: review round 9 (default + failure-mode) at 1c55d7f, carrying the docstring finding; wording-only → confirming round → merge from trunk, tell the operator to start `bin/stoker.sh` once |
| Review opponent-model design round 8 | `36e2ae4be45b` | review 8 against trunk pokerbot main (design landed at 659c6b7 on a stale pass; round-7 fixes at 72eff27, then 5f7a1a8; rounds 5-7 notes were never stored) | record; wording-only → done, delete the design section from `handover/findings-pokerbot-pending.md`; substantive → tell the operator the cost, no round 9 unasked |
| Review exploitation survey round 6 | `76bbf2823a53` | review 6 (round-5 fixes at 9dea35e: DriveHUD re-read with a browser user-agent, key clause for partly-evidenced ~, four wording; fixer flagged the converter-price caveat at about :152 for the reviewer) | record; fail → fixer; wording-only → confirming round; never run reconcile while its pass is recorded and it is unlanded |
| Fix engine survey round 2 | `7f09949cb56f` | fixer 2 | dispatch review round 3 |
| Confirming review bots survey round 7 | `14d64950c0bc` | round 6 PASSED wording-only; then reconcile LANDED it early on pokerbot main at ea013b5 (see the trap below) with fixer 6's autosave, which carries the fixed bonusbots tagline; round-6 F2 (PokerScreenBot quote, about :682-683) still open. Confirming round 7 running against trunk, told to record F2 as known | wording-only → one fixer on a fresh branch from trunk applies F2 plus any new wording, lands via `bin/dispatch.py land`, deletes `handover/findings-14d64950c0bc-bots-r{4,5}.md`; substantive → fixer on a fresh branch, then round 8. Undo path if ever needed: `git -C /Users/chasethompson/pokerbot revert -m 1 ea013b5` |
| Fix solvers survey round 4 | `048795519f43` | fixer 4 (round 4 failed: 7 substantive, evidence base all held; "buy preflop ranges" under "settled", MonkerSolver scripting wording, one summary row, one unpublished load, an unsourced play-out count, Deepsolver pricing, an Appendix contradiction; see `handover/findings-048795519f43-solvers-r4.md`) | dispatch review round 5 |

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
  `reviewed()` accepts any pass ever recorded. Fix on `worker/059566b3e160`.
  It bit again at 02:52Z: the bots survey was recorded as a wording-only
  pass (round 6) and the very next reconcile merged it (ea013b5) with the
  fixer still in the checkout, before the confirming round. Even the fixed
  tool lands on one pass; the two-round rule is not coded (task at score
  75). **Never run reconcile while any open dispatch has a pass recorded.**
  Record a pass, dispatch the confirming round, and reconcile only after
  the change is landed by hand with `bin/dispatch.py land`.
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
- With seven agents out the one-minute load reaches 11 and the harness
  watchdog kills agents as "stalled: no progress for 600s"; their edits
  survive on disk. SendMessage to the same agent id resumes it; tell it to
  commit what is on disk first. One stalled twice in a row before resuming.
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
