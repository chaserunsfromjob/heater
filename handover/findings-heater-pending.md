# Fleet-repository changes still in the review loop

Delete each section in that change's landing commit.

## Automatic handoff 46e285e1bfd0

Branch worker/46e285e1bfd0 at 530927b (origin); scratch worktree
`/private/tmp/claude-501/-Users-chasethompson-heater/60db9bfd-fa3a-4035-aa37-91a8741fa698/scratchpad/review-46e285e1bfd0`
(if gone: `git worktree prune`, re-add from origin). Round-5 findings A-E are
all applied with failing-first tests (483 tests, gate 0): per-supervisor
child records, orphan = child alive AND owner dead, a queue item plus a
bearings section "A session left running", no asserted cause, README ps
sentence, fleet queue file removed. Round 6 FAILED (all round-5 fixes hold;
round-6 fixer RUNNING at the handover, then dispatch round 7):
- F1 tools/stoker.py:638-661 _terminate returns -SIGKILL whether or not the
  child died; watch treats it as a clean ending; a second session opens
  silently; record_child (:888) overwrites the old entry under the same
  "<pid> <start>" key so the un-ended session is never named. Resolve:
  _terminate reports whether the child exited; on "no", announce through the
  same three channels announce_orphan uses (screen, log, one queue item) and
  keep the un-ended session in the record under a key the next record_child
  does not overwrite; behavioural test on that path, no pragma no cover.
- F2 tools/stoker.py:425-452, :494-507 read-modify-write with no lock and
  truncate-in-place: entry lost 20/20 in simultaneous launches; duplicate
  queue items; a partial write leaves a truncated record read as empty.
  Resolve: one critical section (O_EXCL lock file or fcntl.flock) covering
  record_child and mark_orphan_reported; write to a temp file in the same
  directory then os.replace; a two-process barrier test.
- F3 tools/bearings.py:66-67 "pid" unexplained; say "program number" first.
- F4 tools/stoker.py:54-59, :518 the fleet-queue import cannot fail (the
  stdlib queue answers instead); fix the comment and drop the dead branch, or
  say file_orphan_note's except is what tolerates a wrong module.
After a wording-only round: one confirming round, then merge from trunk yourself with
`bin/gate.sh` (dispatch record already CLOSED, reconcile will not land it),
resolve the OPINIONS.md conflict with the taper branch by keeping both 12 and
13, and tell the operator to start `bin/stoker.sh` once.

## Reconcile stale-pass fix 059566b3e160

Branch at fde4b46 (origin), no worktree (reviewers and fixers make their own
in the scratchpad). Rounds 1-2 proved the highest-round rule; round-2 fixes
(456 tests, gate 0) add commits_reached_trunk so the loud "landed WITHOUT a
passing review" fires only when commits reached the trunk, sentence-shaped
refusals and notes, unreadable rounds quoted and described as unreadable,
every needs-a-fixer line in "<branch>: <why>" shape, awaiting dispatches
named, SKILL.md restated. Round-3 review was RUNNING at the handover. Land it
as soon as a round is wording-only (merge from trunk with the gate; dispatch
record CLOSED). Until it lands, check `store/reviews` for a stale pass on
every open dispatch before each reconcile (none today).

## Usage taper c79a35661f9c

Branch at 7e652cc (origin), checkout `.heater/worktrees/heater/03a2b608f262`,
merged with main at 4f5622c, 494 tests, gate 0. Round 2 passed the taper
half under every probe and failed the debrief's prose; round-2 fixes: plain
word substitutions for paths/branches/files/ids, meta-clause skipping, lease
window fix, agent-kind fallback, `bin/queue.py show <id>`, stop bullet names
`bin/dispatch.py close <id> --outcome abandoned`. Round-3 review was RUNNING
at the handover; its brief flags two entries whose substituted prose may
mislead ("checkout a folder on this machine … on branch a separate copy of
the work"). After a wording-only round: one confirming round, then land with
`bin/dispatch.py land c79a35661f9c --gate "bash bin/gate.sh"`. Dismissed by
the stoker: F6 (no UnicodeDecodeError guard). Open observation: 40 review
rounds carry no cost figure; `bin/store.py review --cost-usd` exists and
nothing fills it.
