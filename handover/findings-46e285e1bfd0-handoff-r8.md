# Automatic handoff 46e285e1bfd0 — round 8 findings (fail; text only, R8-1 substantive as unrecorded)

Delete this file, and `findings-46e285e1bfd0-handoff-r7.md`, in the landing
commit. Branch worker/46e285e1bfd0 at b0f9878 on origin. A stale round-7
reviewer worktree still holds the branch name (task 418b4396b9f7), so
fixers and reviewers use `git worktree add --detach … b0f9878` and push with
`git push origin HEAD:worker/46e285e1bfd0`, then move the local ref with
`git update-ref refs/heads/worker/46e285e1bfd0 <new> <old>` (a guarded
fast-forward). All three round-7 behavioural fixes reproduced from the real
code path; merge clean against main, revert restores main. Every resolution
below is a text change; no behaviour changes. The round-8 fixer was
dispatched with these.

- R8-1 (substantive: unrecorded design decision) tools/stoker.py:674
  (`return write_child_records(records)` in claim_orphan_report) against
  README.md:130-133. With the state directory readable but unwritable, the
  "session left running" warning is filed in the queue zero times (screen,
  log `stoker_records_unwritten`, and bin/bearings.py still say it).
  README:130-133 states without qualification that it is also filed in the
  queue. Stoker's decision: the code stays (once per launch is unreachable
  when nothing on disk can de-duplicate; every-time is the duplicate-wake
  defect round 6 closed; two of three channels survive). Resolve: one
  clause in README beside the existing `ps` degraded-path paragraph
  (:141-145), same register: when the stoker's notes folder cannot be
  written, a session left running is still said on screen and still
  reported by bin/bearings.py, but is not filed in the queue, and the log
  records why. No code change.
- R8-2 (wording, false statement to the operator) tools/stoker.py:715
  (orphan_message), reached from :1032 (_stopped_by_interrupt) and :1090
  (the `if _stopping:` branch). "A fresh session is being opened, so two of
  them will be working this folder at once" is true on the handover (:926)
  and startup-orphan (:1059) paths and false on the two stop paths, where
  the supervisor is exiting. Same class as round 7's F4, same sentence.
  Resolve: one sentence true of all four paths (nothing is watching it, and
  a session working this folder unwatched is trouble whether or not another
  opens), or pass the caller's situation into the message.
- R8-3 (wording) README.md:134-137 and the docstring at tools/stoker.py:656.
  The new README clause says the lock file "keeps two copies of
  bin/stoker.sh from writing the record at the same moment and erasing each
  other's entry"; with HOLD_WAIT = 2.0 (:147) that is conditional: past two
  seconds a supervisor writes unheld and can erase another's entry (the
  reviewer made it happen). The docstring "Only one call can be told it
  took it" holds only while the hold is held. Resolve: a qualifier in both:
  the wait has a couple of seconds in it, past that the note is written
  anyway and the log says so, a lost entry being better than a stalled
  handoff.
- R8-4 (wording) README.md:125-127 "one entry per bin/stoker.sh" is false
  once keep_unended (:597-613) writes a second entry under "… left <child
  pid>" for a session that would not end; orphan_sessions collapses them
  for display only. Drop or qualify the phrase.
