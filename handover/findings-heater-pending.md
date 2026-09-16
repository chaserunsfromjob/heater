# Fleet-repository changes still in the review loop

Delete each section in that change's landing commit.

## Automatic handoff 46e285e1bfd0

Branch worker/46e285e1bfd0 at 530927b (origin); scratch worktree
`/private/tmp/claude-501/-Users-chasethompson-heater/60db9bfd-fa3a-4035-aa37-91a8741fa698/scratchpad/review-46e285e1bfd0`
(if gone: `git worktree prune`, re-add from origin). Round-5 findings A-E are
all applied with failing-first tests (483 tests, gate 0): per-supervisor
child records, orphan = child alive AND owner dead, a queue item plus a
bearings section "A session left running", no asserted cause, README ps
sentence, fleet queue file removed. Round-6 review (default + failure-mode)
was RUNNING at the handover. Its brief asked it to decide whether an
unkillable child under a live supervisor still needs a message. After a
wording-only round: one confirming round, then merge from trunk yourself with
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
