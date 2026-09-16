# Reconcile stale-pass fix 059566b3e160 — round 3 findings (fail; F1, F2 behavioural)

Delete this file in the landing commit. Branch at fde4b46 (origin), no
worktree (make one in the scratchpad, remove it after). The core
highest-round rule is unbreakable on every probe and merges clean with main;
the failures are in the new alarm gate. Round-3 fixer dispatched at the handover.

- F1 tools/dispatch.py:313-329 (+ :371, rendered :502-508) commits_reached_trunk
  returns False for every failure to answer (missing base_sha, deleted branch,
  non-git path, no lease), so "closed with nothing to consolidate" prints and
  the alarm is silent where unreviewed commits ARE in the trunk: a sweep
  resumed after finish() deleted the branch but before close_dispatch; a
  dispatch with no lease whose worker committed straight to the trunk.
  Resolve: three states (reached / no commits of its own / could not
  determine), render the third as "could not check whether its commits
  reached <trunk>"; record the branch tip sha on the lease when the slot is
  released or merged and compare that sha with merge-base --is-ancestor
  instead of the branch name; the no-lease case says so rather than asserts.
- F2 :322-329, :489-492, :504 a lease force-released with unmerged commits
  (worktrees.reclaim does this when a checkout dir vanishes) is closed
  landed, counted under "all cleaned up after", rendered "nothing to
  consolidate", while the branch still holds the work. rev-list count is
  non-zero and is-ancestor fails: render that state as its own line naming
  the branch; stop asserting "all cleaned up after" when a branch was left;
  tests/test_worktrees.py:717-728 asserts the present wording.
- F3 :151, :157, :160-161 docstrings say "last recorded"; say highest-numbered,
  later record breaks a tie.
- F4 :126 sort-key comment reads as "usable rounds sort last"; name what sorts last.
- F5 :187 a record with no round key renders "review round None …"; say "a
  review round with no round number recorded".
- F6 :489-494 the gloss prints "landed 0 (0 merged …; all cleaned up after)";
  print it only when landed is non-zero.
- F7 :511 vs :514 awaiting line prints dispatch id and branch as two codes;
  say "dispatch …, branch …" and use one shape for awaiting and needs-fixer.
- F8 skills/dispatch/SKILL.md:95-99 add one sentence each for the two
  tie-breakers: exact tie resolves to the fail; a non-whole-number round never
  counts as a pass and blocks landing.
- Observation: commit 2752f36 is titled "WIP … suite not proven" though green;
  the stoker's call whether to leave it.
