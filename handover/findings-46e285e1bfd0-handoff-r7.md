# Automatic handoff 46e285e1bfd0 — round 7 findings (fail; F1-F3 behavioural)

Delete this file in the landing commit. Branch worker/46e285e1bfd0 at 029057a
on origin, no worktree slot (make one in the scratchpad, remove it after).
Main has moved to 6c61aa9 since the branch was cut; merge-tree is clean and a
revert of the merge restores main byte for byte. Every round-6 fix reproduced
as fixed. All three fails are in code round 6 added. The round-7 fixer was
dispatched with these.

Lines in tools/stoker.py unless named.

- F1 :457 (`fcntl.flock(handle, fcntl.LOCK_EX)`), critical section :490-494,
  call site :1001. record_child takes the hold and then, inside it, prunes
  through child_alive → process_alive → process_start, which runs a `ps`
  subprocess (timeout 5) per kept entry: 4 `ps` calls measured under the
  hold. The comment at :487-489 ("Both start times are read before the hold
  is taken") is true only of the two values in `entry`, not of the pruning.
  The hold has no deadline and no LOCK_NB fallback: with one holder SIGSTOPped
  mid-hold, record_child had not returned after 8 s. _run_sessions spawns the
  child at :991, calls record_child at :1001 and reaches watch only at :1010,
  so a blocked supervisor has a live claude session nobody polls the marker
  for; SIGTERM runs _forward_stop but the flock resumes and the supervisor
  never exits. Resolve: non-blocking acquire in a retry loop against a short
  deadline, then proceed unlocked and log that it did (hold_records' own
  docstring :448-450 already states that policy: "a lost entry beats no
  session at all"); decide liveness outside the critical section; correct
  the comment.
- F2 :540-558 (keep_unended), :577-578 (orphan_sessions), operator-visible at
  tools/bearings.py:66-69. record_child already wrote the child under the
  supervisor's key "<owner pid> <owner start>"; keep_unended adds a second
  entry with the same pid/start under "<owner pid> <owner start> left <child
  pid>". Once that supervisor is gone both entries match, and one session is
  reported twice on screen and in bearings.left_running() (reproduced from
  the real code path: 2 orphans, 2 identical bearings lines, 1 queue item).
  Resolve: unique per session, not per record: collapse entries sharing
  pid + start in orphan_sessions, or have keep_unended drop the own-key entry
  for that pid as it writes the `left` entry.
- F3 :512-516 (write_child_records' except OSError), :458-460 (hold_records'
  except OSError), :581-602 (claim_orphan_report). With the state directory
  unwritable, record_child writes nothing, takes no hold, emits nothing: no
  stderr, zero log events, while the log dir was writable. claim_orphan_report
  returns True after a write that silently did nothing, so the claim is never
  persisted: three launches filed three queue items for one session, the
  duplicate-wake defect round 6 closed, reappearing under the one condition
  the swallow tolerates. Resolve: write_child_records reports whether the
  replace landed; claim_orphan_report returns False when it did not; log one
  event (same shape as stoker_stale_marker) when the hold cannot be taken or
  the note cannot be written.
- F4 (wording) :632-639 orphan_message, reached from :741-744 on the
  un-ended path, says "the program that was watching it is not running any
  more"; on that path the supervisor is running and about to open the next
  session. One wording true of both paths: nothing is watching it now, no
  claim about why.
- F5 (wording) :993 failed-launch message is "could not start Claude: [Errno
  2] No such file or directory: 'claude'", exit 127. Plain sentence that the
  claude program could not be started on this machine, one action, the
  system's words last if kept.
- F6 (wording) :632-639 as filed by file_orphan_note :605-618: the queue item
  says "run `kill <pid>`" with no caveat that the number is only good while
  the session still runs; point at bin/bearings.py as what confirms it.
- F7 (wording) README.md:125 names ~/.heater/handover-complete and
  ~/.heater/stoker-session but not ~/.heater/stoker-session.lock (created
  :139, :434-435, :456, never removed). One clause: a small companion file
  that keeps two copies of bin/stoker.sh from writing the note at once, never
  anything to tidy.
