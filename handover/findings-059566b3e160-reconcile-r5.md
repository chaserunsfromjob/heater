# Reconcile stale-pass fix 059566b3e160 — round 5 findings (fail; S1, S2 substantive)

Delete this file, and the r3 and r4 files beside it, in the landing commit.
Branch worker/059566b3e160 at 0b9af3e on origin, no worktree slot (make one
in the scratchpad, remove it after). Core verified again on the reviewer's
own probes (original bug, all tie-breaks, unreadable round, door guard,
per-dispatch alarm lines, cross-sweep persistence); merge clean, revert
restores main; 51 of the new tests fail on main's code. Both fails are in
the run-level summary round 4 added. The round-5 fixer was dispatched with
these and with the stoker's decision on S2.

Lines in tools/dispatch.py unless named.

- S1 :245-246 and :276-277 (land) close the dispatch without writing the
  `consolidated` field; :525 (finished_runs) requires REACHED or NO_COMMITS
  for every member; skills/dispatch/SKILL.md:69, :88, :109-112. A run whose
  members were all landed by `bin/dispatch.py land` (the documented route,
  step 4 at :109) stores `[None, None]` and prints "runs finished, with work
  still to account for" on every later sweep, forever, since reconcile
  walks only live dispatches. `close --outcome landed` does the same.
  SKILL.md:88 says "reached the trunk or never existed" then patches it with
  "or never recorded", contradicting itself. Resolve: land() records the
  state it proved (REACHED after a successful merge, or what
  commits_reached_trunk answers on the no-lease and nothing-to-merge
  branches) on the dispatch before closing, with a behavioural test that a
  run landed entirely through land() reads "runs fully consolidated";
  SKILL.md states what a by-hand `close --outcome landed` does to the run
  line.
- S2 :376-397 (record_landing writes the answer once) and :504-529
  (finished_runs reads only the stored field); SKILL.md:88 states no
  clearing path. A member released with work unmerged is correctly reported
  left behind; the operator then merges that branch by hand and records a
  passing round, and every later sweep still says "work still to account
  for" with states ['reached', 'left behind']. Same for UNKNOWN from an
  unreadable base_sha (:349-350) even where worktrees.landed() has just
  proved the commits are in the trunk (:435-442). Snapshot-versus-re-ask is
  a design decision the change settled silently. Stoker's decision: re-ask.
  finished_runs re-asks git for any member whose recorded state is not
  REACHED or NO_COMMITS (the lease still holds tip_sha and base_sha after
  close), writes the new answer back if it changed, and the line clears
  once the work is in the trunk; a test that a hand-merged branch clears
  the line. Record in SKILL.md:88 that the answer is re-asked at every
  sweep until it reads reached or no commits. This matches rules/global.md
  Evidence: a number comes from a live query, not a stored impression.

Observations, not findings: :414 sets trunk="the trunk" as a literal for a
no-lease dispatch (renders fine); a released-with-work dispatch is still
outcome landed (:417), pre-existing vocabulary covered by task 68b249e08219;
a second sweep dies on close_dispatch's uncaught ValueError for an
already-closed record, filed and promoted as task fad0e0aba254.
