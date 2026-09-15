# Fleet-repository changes with findings still open

Delete each section in that change's landing commit.

## Automatic handoff 46e285e1bfd0 — round 5 (fail: A, B behavioural; C, D wording)

Branch worker/46e285e1bfd0 (origin), scratch worktree
`/private/tmp/claude-501/-Users-chasethompson-heater/60db9bfd-fa3a-4035-aa37-91a8741fa698/scratchpad/review-46e285e1bfd0`
(if gone: `git worktree prune`, re-add from origin). Round-5 fixer was stopped
at the usage limit having done NONE of A-E; its commit 14d9a31 (pushed) only
adds HEATER_STATE_DIR to tests/test_stoker.py:34-37's StoreCase.ENV. Suite not
run on it. For E: the branch carries queue/…-6e2302faa051.json (a finding that
bearings shows no stoker launch/restart/exit events, already on the task list
as 2206a361b159), so just drop the file from the branch.

- A tools/stoker.py:437-449 orphan_session ignores owner_pid (written at :419),
  so with two supervisors in one folder the second reports the first's live
  session as orphaned and tells the operator to `kill` it; the single record
  slot (:423) also erases the first supervisor's session. Fix: orphan = child
  alive AND recording supervisor (owner pid + start, via process_alive) dead;
  one record entry per supervisor; prune dead children. Tests: live second
  supervisor is silent; killed supervisor's orphan still reported after another
  launch; existing two-supervisor test (tests/test_stoker.py:691) still passes.
- B tools/stoker.py:779 the warning only reaches stderr, which claude
  overwrites; file a queue item (urgency high) and add a bearings section "A
  session left running"; test the item survives the launch.
- C README.md:125-130, docstring :440-444, orphan_message :452-459 assert
  "was killed outright"; state only what is known.
- D README handover section: one sentence that the handoff needs the machine
  to report when a program started (ps); when it cannot, the session says so
  and the operator opens the next one.
- E Landing prep: `git diff --stat main...HEAD -- queue inbox store` showed one
  file +12 on the branch; restore fleet record paths from main before merging.
- Reviewer verified: revert of all five commits applies clean, 408 tests on
  the reverted tree. Round 4's four fixes all reproduced true.

## Reconcile stale-pass fix 059566b3e160 — round 1 (fail: F1 code, F2 docs)

ALL FIVE FINDINGS ARE APPLIED at 2752f36 on origin (the subject says "WIP"
because it was dictated at the stop; the body records the truth: 442 tests
green, style clean; bin/gate.sh not re-run on that exact commit). It also
hardened reviewed(): an unreadable round number never counts as a pass. Next:
a fresh round-2 default-lens review, then land it (this fix is what stops
reconcile landing on a stale pass again).

- F1 tools/dispatch.py:328-330 a change whose latest round FAILED lands in
  awaiting_review with no round named; split it into the needs-a-fixer bucket
  (or a "rejected" bucket) with dispatch, round, review id, verdict, and a
  render line; test distinguishes rejected from never-reviewed.
- F2 skills/dispatch/SKILL.md:82, :95, :108 still describe the any-pass rule.
- F3 round_order sorts a missing/text/float round to 0 (fails open): reject
  non-int in store.record_review AND order unusable rounds last.
- F4 exact tie (same round, same created) resolved to the pass: add verdict to
  the sort key so fail outranks pass.
- F6 render "landed WITHOUT a passing review" loudly; say once what landed means.
- Verified: reviewed() now False for pass-then-fail on a fixture, True on main.

## Usage taper c79a35661f9c — round 2 review was stopped before it began

Branch at 1a3a8eb (origin), checkout `.heater/worktrees/heater/03a2b608f262`,
merged with main at 4f5622c, suite 477 green, gate exit 0. Needs a fresh
round-2 default-lens review; the brief is reconstructable from the round-1
findings in the store note plus the fixer's commit message. Dismissed by the
stoker: F6 (no UnicodeDecodeError guard; a non-text usage.json makes wakes
no-op until the status line rewrites it, which it does on the next render).
