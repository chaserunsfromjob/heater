# Reconcile stale-pass fix 059566b3e160 — round 4 findings (fail; S1, S2 substantive)

Delete this file, and `findings-059566b3e160-reconcile-r3.md`, in the
landing commit. Branch worker/059566b3e160 at f1a4543 on origin, no worktree
slot (make one in the scratchpad, remove it after). Main has moved to
2399f35; merge-tree is clean. The highest-round rule held on nine probes
including the original bug; every git-cannot-answer path renders "could not
check"; the two skill rows the round-3 fixer added are accurate. The fails
are two summary lines that contradict the new per-dispatch alarm. The
round-4 fixer was dispatched with these.

Lines in tools/dispatch.py.

- S1 :489-497 (finished_runs, docstring "Runs whose every worker has landed,
  so nothing of theirs is left anywhere") and :568-569 (rendered line).
  finished_runs keys on outcome == "landed", and LEFT_BEHIND and UNKNOWN
  still close as landed, so a sweep prints "<id> closed with commits left on
  worker/<id> that never reached main" and two lines later "runs fully
  consolidated: <run>". Same with "could not be checked". Resolve: a run is
  fully consolidated only when every member landed as REACHED or NO_COMMITS;
  otherwise leave it off the list or name it "runs finished, with work still
  to account for". Fix the docstring, and add the rule to the table in
  skills/dispatch/SKILL.md so it is recorded, not just coded.
- S2 :543-556 (render chain) with the comment at :539-542 making the choice
  deliberate. The chain tests `consolidated` first, so "landed WITHOUT a
  passing review" fires only when the state is REACHED. A dispatch closed as
  landed whose latest round FAILED prints only its commit state when that
  state is UNKNOWN or LEFT_BEHIND: a no-lease dispatch with round 1 fail
  prints "closed; could not check whether its commits reached the trunk" and
  nothing about the failed round; a pre-change lease with no tip_sha, branch
  deleted, round 1 fail, the same. These are exactly round 3's two cases.
  Resolve: when entry["verdict"] is not pass, append the round to the
  LEFT_BEHIND and UNKNOWN lines too ("…; and it has no passing review: review
  round 1 <id> (fail)"), and record in skills/dispatch/SKILL.md which line
  carries the review alarm in each state.
- W1 (wording) :192-194 resting_on sets why = "rejected at …" with no test
  on the verdict, so every landed report entry carries verdict 'pass' beside
  why 'rejected at review round 2 … (pass)'. Renders nowhere today, but it is
  a false sentence in the structure reconcile() returns and contradicts the
  docstring at :178-181. Derive why from the verdict: "rejected at" for a
  fail, "passed at" for a pass.
- W2 (wording) :536 "awaiting review  0  (nobody has reviewed these yet)"
  glosses a zero, the shape round 3's F6 removed from the landed line; when
  non-zero it repeats the per-entry line at :560-562 word for word. Attach
  the gloss only when non-zero, or drop it.

Observations, not findings (already on the task list or consistency notes):
reconcile still exits 0 for LEFT_BEHIND/UNKNOWN (task 68b249e08219); the
change's rendering makes that better, not worse. reviewed() reads only
`verdict`, so a hand-written pass with substantive findings would land;
store.record_review's door guard covers the normal path.
