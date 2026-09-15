# Handover

<!-- handover-commit: 36bd007 -->

Written at `36bd007` on `main`. Verify with
`bin/handover.py`. A snapshot, not a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and the commit messages for why
each change looks the way it does. **None of that is repeated here.** What
follows is only what you cannot look up.

---

## Start here

**All seven steps plus handover are landed, pushed, and green: 289 tests,
`bin/gate.sh` passes.** Nothing is half-finished. No pull request is open and the
operator has not asked for one.

**The next action is not building. It is the first real run.** Nothing here has
ever run unattended: every piece is unit-tested and no stoker session has
dispatched a real worker. The likely failures are in the seams, not the units —
whether `HEATER_ROLE` actually reaches a dispatched agent's session, and whether
the Stop hook's wake behaves the way the unit tests assume. Do not build more
until one dispatch has gone out and come back.

**Two things only the operator can do**, both still outstanding: delete the stale
`claude/artifact-system-continuation-ko9236` branch on GitHub, and run
`bin/deploy.py` on a real machine. Until the second one happens none of this is
live for them.

**Branches.** `main` is canonical and is now GitHub's default. The stale
`claude/artifact-system-continuation-ko9236` still exists on GitHub pointing at
an old commit: **deleting it from this environment is blocked**, not flaky. Both
`git push --delete` and the colon refspec return HTTP 403 from the sandbox proxy,
which the proxy's own README calls a policy denial to report rather than route
around, and no delete-branch tool exists in the GitHub API set here. The operator
deletes it from GitHub's branches page. Do not burn a session retrying.

**The operator has not yet run `bin/deploy.py` on a real machine.** Nothing in
this system is actually live for them until they do.

## The operator

This is the single most important thing in this file.

**They are not a programmer and have little computing background.** An
explanation they cannot follow is a failed deliverable, exactly like a failing
test. This is recorded as opinion 9 and as the rules under "Talking to the
operator", so the standard is enforceable rather than a matter of tone.

The chosen style: plain words carry the explanation, and the technical term is
named last, after the plain version already stands on its own.

**The mistake to avoid.** Early on they were asked to choose between
architectural options using vocabulary they had never been given. They answered
"i dont understand" three times in a row. That was a failure of the question,
not of the person. Never present a choice between unexplained options — explain,
recommend, then ask.

They want context cleared often and deliberately. That is why the handover
procedure was built before the review loop.

## Do not try to read the source artifact

The design derives from reference notes the operator pasted into the session,
titled "Everythingdev Field Guide". The artifact at
`https://claude.ai/artifact/94SNUmhCsGxeAEEe6WcKGT` is **not readable** by a
Claude session: it is shared with the operator rather than owned by them, and
every read path fails with "served to you as a public (non-member) reader".
Artifact read, a targeted extraction prompt, and WebFetch were all tried.

Ask the operator to paste anything you need from it. Everything already borrowed
lives in `OPINIONS.md` and `rules/`.

## Decisions whose alternatives left no trace

Each of these looks arbitrary in the code and is not. Re-deriving them costs a
session; reversing them costs more.

**Near-duplicate detection uses character matching, not token overlap.** Token
overlap was written first, then measured against the real rule files: a plural
variant scored 0.82 while the closest genuinely different pair scored 0.33 — too
thin a margin. Character matching scored the same pairs 0.99 and 0.60. The 0.85
threshold sits in that gap. Token overlap looks simpler and is wrong.

**Deploy drift is deliberately not in the gate.** Whether a given machine is
symlinked is a property of that machine, not of a change, so gating on it would
fail every run on a machine that has not deployed. The link table is checked by
tests instead.

**`settings.json` is merged, `CLAUDE.md` is symlinked.** The asymmetry is
deliberate: symlinking settings would wipe whatever else the operator has
configured there. The merge replaces only groups whose commands point into this
repo.

**The guard warns rather than denies on unrouted git writes.** Opinion 2 calls an
unrouted repo write a defect, which argues for a denial. The stoker does not
exist until step 6, so denying now would lock the operator out of their own
repository. The README marks step 6 as where this flips.

**Queue items are tracked in git.** Chosen for diff-readability over
conflict-avoidance, with eyes open. `queue/README.md` records the intended
response if conflicts become routine: move to per-machine directories synced by
the SessionEnd hook, and specifically *not* adopt a database.

**Judge-only is enforced by the guard, not by the reviewer's tool list.** The
obvious implementation is to leave `Write` and `Edit` out of the agent's `tools`
allowlist, and that is done — but it is not sufficient, because a reviewer must
run the suite to prove a change works, which needs Bash, and Bash can write
anything. So the guard denies writes whenever `HEATER_ROLE=reviewer`. Tests pin
both directions: commits, staging, `sed -i`, file removal and redirection into a
file are denied, while running the suite, running the gate, grepping, `2>&1` and
`>/dev/null` stay open. Widening that allow-list carelessly reopens the hole.

**`ENFORCE_STOKER_ROUTING` in the guard is deliberately `False`.** It is not a
forgotten debug flag. Nothing can set the dispatch marker until step 6, so the
warning would fire on every hand-written commit forever and train the operator
to ignore warnings. **Step 6 flips it to `True`.** Both states are tested.

**A review round cannot be recorded as a pass while substantive findings are
outstanding.** The store raises rather than accepting it, because the loop lands
on a pass and a pass carrying real findings would land them too. Wording-only
findings are the deliberate exception.

**Deploy discovers agents and skills rather than listing them**, and links each
one individually. Linking the whole `~/.claude/agents` directory would displace
anything else the operator keeps there.

**Findings live in the queue store, not in a directory of their own.** The
obvious build is a parallel `inbox/findings/`, and it was rejected: one finding
would then have two records that can disagree. `inbox/` holds only the task
list. `tools/inbox.py` is the lifecycle over queue items of kind `finding`.

**Only dismissed findings answer the refile question.** An open finding is still
waiting to be judged and a promoted one is live work, so matching a new finding
against either would suppress something real. Tests pin all three cases.

**The task cap deletes, and a test asserts no file is left behind.** The
tempting failure is to move a dropped task somewhere quieter and call that
deleted. Opinion 5 means deleted.

**`ENFORCE_STOKER_ROUTING` is now `True`.** Step 6 flipped it, as planned. It
stays a warning rather than a denial: the operator works by hand in the fleet
repository itself, and denying that would cost more than it protects.

**All logic lives in `tools/`, and `bin/` holds only entry points.** This is not
tidiness. `bin/dispatch.py` and `tools/dispatch.py` shared a name, and whichever
directory came first on the import path won — `bearings` imported the CLI shim
instead of the module and failed with a missing attribute. Never put importable
logic in `bin/`.

**Every worker leases its own checkout, the first one included.** An earlier
version gave the first worker the project's own checkout and only leased from
the second onwards. The operator pushed back twice here and was right both
times. The project's checkout is the consolidation target and must never also be
a workspace: when it is both, every clash between the merge target and the edits
in it becomes a decision somebody has to make, which is the input opinion 1 says
to eliminate. Do not re-optimise this back.

**`reconcile` derives what to do from git, never from a flag.** A sweep that
dies halfway must be repeatable, and a flag written before a crash is a lie
afterwards. `worktrees.landed` asks git whether the commits are reachable from
the trunk, and that answer is correct whatever happened last time. A test pins
idempotence by comparing the trunk commit before and after a second sweep.

**Loose work is committed, not refused over.** The sweep autosaves anything
uncommitted onto the worker's own branch before doing anything else. Refusing
would be safe for the data and useless for the operator, who then has to
intervene; committing is safe and needs nobody.

**A conflict from the trunk having moved is resolved automatically; a real one
is not.** The sweep merges the trunk into the worker's branch and retries, which
handles the common case. A genuine conflict keeps the branch, the checkout and
the slot and reports `needs_fix`, for a fixer to be dispatched. It never
discards the losing side.

**A dirty trunk holds everything, on purpose.** It is the one case not resolved
automatically, because the uncommitted work there is the operator's and mixing
it into a merge is not a call to make for them. Nothing is lost by waiting. In
normal running the trunk is clean, because opinion 2 says changes go through the
stoker.

**A slot holding work that exists nowhere else is never destroyed, by any
route.** Close, release, reclaim and land all refuse, and close records the
reason on the dispatch rather than swallowing it. `--force` exists for a human
who has looked.

**`work_at_risk` checks three separate ways of being safe: merged, pushed, or
never started.** The earlier version asked only "was it pushed to a remote",
which meant work merged into trunk still counted as at risk and its slot could
never be freed — the normal end of a dispatch would have jammed the pool. Do not
collapse these back into one question.

**Nothing is deleted until its commits are provably in the trunk.** `finish`
raises rather than clean up an unlanded branch, and a test calls it on unlanded
work so the invariant is proven rather than merely intended. Every cleanup path
goes through it.

**`dispatch.land` is the single-dispatch version of the sweep and is deliberately
not separable.** Merge back, delete the branch, remove the checkout, free the slot,
close the dispatch. A merge that leaves the checkout behind and a checkout
deleted before its merge are both ways to lose work. It refuses and changes
nothing on: no recorded review pass, uncommitted work, a failing gate, a dirty
or wrong-branch main checkout, or a conflict — and a conflicting merge is
aborted, never left half-applied.

**Landing reads the review store rather than trusting the report.** An
unrecorded round did not happen, so the stoker must run
`bin/store.py review --change <dispatch-id>` for each round or nothing will ever
land.

**`unpushed()` measures against the lease's recorded `base_sha`, never against
"has any commits".** The first implementation asked whether the branch had any
commits when no remote was configured. That is true of every fresh checkout the
instant it is created, because it inherits the base history — so every slot
would have been permanently un-releasable and the pool would have jammed after
three dispatches. It passed a manual demo and failed the tests. Do not
"simplify" this check.

**`SessionEnd` records what is unsynced rather than committing it.** It shares a
1.5 second budget with every other SessionEnd hook and cannot block termination,
so a push cut off halfway could not even be reported. The write belongs to a
session that can supervise it.

## A tension already resolved — do not re-litigate

Opinion 1 says the system must stop needing the operator and must never ask the
same question twice. Opinion 9 says to check whether an explanation landed. Read
carelessly these contradict.

The resolution is written into opinion 9: opinion 1 governs work the system does
while the operator is away and must not wake them to decide; opinion 9 governs
the conversation when they are present and asking. Leave it settled.

## Traps

- `OPINIONS.md` is deliberately not linted. It carries dates and prose by
  design; the linter targets `rules/` and `roles/` only. `roles/` does not exist
  yet and its absence is handled.
- **`bin/deploy.py` has never been run against a real machine.** Every session so
  far has been an ephemeral container where deploying accomplishes nothing. It is
  tested against temporary directories only. Treat the first real run as unproven.
- Two ordering bugs were caught by tests rather than by reading: the urgency rank
  was reversed twice, so `normal` sorted above `high`, and second-precision
  timestamps lost arrival order within the same second. Both are pinned by tests
  now. Ordering in this repo is worth testing rather than eyeballing.
- The guard denies by pattern, so it will miss spellings nobody has thought of.
  That is the accepted design: it denies only what it is certain about, and the
  rule covers the rest. Do not widen it into blocking on suspicion.
- Hook scripts must stay executable. A test asserts this, because a registered
  hook that cannot run fails silently.
- `bin/store.py`'s subcommands use `dest="action"`, not `dest="command"`. The
  `suite` subcommand takes a `--command` flag, and sharing the name made argparse
  overwrite the subcommand itself, so recording a suite run silently ran the
  query instead. It failed without erroring, which is the dangerous kind.
- `tools/jsonstore.py` is shared by the queue and both stores. A change to its
  atomic write or its skip-corrupt behaviour touches all three.
- `tests/test_worktrees.py` runs against a real git repository in a temporary
  directory, not a mock, and is the slowest file in the suite by far. That is
  deliberate: the failures that matter there are git's behaviour, and a mock
  would have agreed with the bug described above.
- `tools/textmatch.py` is shared by the rule linter and the findings inbox, at
  two different thresholds: 0.85 for rules, 0.75 for findings. The lower one is
  deliberate, because findings are free text written in a hurry and the same
  observation arrives worded differently far more often than a rule does.
  Changing the shared `ratio` moves both.

## Conventions worth knowing before you write anything

- Every rule file is linted: one imperative bullet, under fifty words, at most
  two sentences, no dates or prior-practice prose, and no restatement anywhere in
  the tree. A prose edit can fail the suite. That is intended.
- Commit messages carry the reason for a change. Rules never do.
- This session runs in Claude Code on the web, so `/voice` and any real deploy
  are unavailable here. Both work on the operator's own machine.
