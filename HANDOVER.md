# Handover

<!-- handover-commit: 928b983 -->

Written at `928b983` on `main`. Verify with
`bin/handover.py`. A snapshot, not a log — rewrite it, do not append.

Read `README.md` for what is built and what is next, `OPINIONS.md` for the
operator's positions, `rules/` for the rules, and the commit messages for why
each change looks the way it does. **None of that is repeated here.** What
follows is only what you cannot look up.

---

## Start here

**Everything built is landed, pushed, and green: 379 tests, `bin/gate.sh`
passes.** Nothing is half-finished.

**The next action is still the first real run, and it has still never
happened.** No stoker session has dispatched a real worker. Every piece is unit
tested and the seams between them are not: whether `HEATER_ROLE` reaches a
dispatched agent, and whether the Stop hook's wake behaves the way the unit
tests assume. Do not build more until one dispatch has gone out and come back.
The operator has agreed to the drift finding in the queue as the first job,
with them watching.

**The stoker is now live on the operator's own Mac**, started with
`bin/stoker.sh`, under Remote Control, and confirmed: it identified itself as
the stoker without being told and found the waiting work on its own. That is
the first time any of this has run outside a container.

**Both of the old operator-only items are closed.** The stale
`claude/artifact-system-continuation-ko9236` branch is deleted, and
`bin/deploy.py` has been run on their machine.

**Machines need a re-deploy.** The `PreToolUse` matcher changed to reach
`create_session`, so every machine deployed before that reports
`hook registration out of date` until `bin/deploy.py` runs again. This is
expected, not a fault.

## The operator

This is the single most important thing in this file.

**They are not a programmer and have little computing background.** An
explanation they cannot follow is a failed deliverable, exactly like a failing
test. This is recorded as opinion 9 and as the rules under "Talking to the
operator", so the standard is enforceable rather than a matter of tone.

The chosen style: plain words carry the explanation, and the technical term is
named last, after the plain version already stands on its own.

**The second mistake to avoid.** Opinion 10 exists because they were handed an
implementation walkthrough and a bug report for something already fixed. Report
what changed and whether it works. The account of how it was made goes in the
commit message, which is where this sentence is aimed.

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

**Remote Control settles cloud-versus-terminal, and the question is closed.** A
whole session went into the premise that the operator had to choose: a cloud
session cannot reach their disk, a terminal session is not in the app. Remote
Control is neither — the session runs on their machine with their filesystem and
their fleet install, and the app is a window onto it. `bin/stoker.sh` asks for
it. Do not re-open this as a trade-off; it is not one.

**Opening the repository is what makes a session the stoker, not a marker.**
Requiring `HEATER_ROLE=stoker` failed in the worst available way: the session
opened, looked ordinary, and silently was not the stoker, so the Stop hook never
handed it the queue. An explicit marker still wins, which is what keeps the
reviewer's write ban intact. `is_dispatched()` deliberately still reads the
marker alone — letting the fleet-repo default satisfy it would quietly retire
the unrouted-write warning.

**`in_fleet_repo` takes the most authoritative source outright**, not any match:
payload `cwd`, then `CLAUDE_PROJECT_DIR`, then the process directory. The first
draft accepted any of them and the suite caught it, because the tests run inside
the repository, so every session looked like it was in the repository too.

**The arming mark is 30%, not 25%, because the measurement ignored the floor.**
A session is near 10% before the operator has said anything — system prompt,
tool definitions, `CLAUDE.md`. The mark is against total usage, so that floor is
a toll paid before any working room is counted, and 25% left about fifteen
points rather than twenty-five. The test pins the reasoning against the floor
rather than the digits.

**A session must never open its own successor, and the guard denies it.** This
is why this repository's sessions went missing from the project list: a session
created from inside another arrives with no checkout, so it is filed under no
project and the operator cannot find it. It also opens by re-cloning, which is
work they watch instead of the work they asked for. It cannot be fixed
afterwards — the workspace is settled when the container starts. A note in the
handover skill was not enough, because the skill is read when invoked and this
fires whether or not anyone invoked it.

**The denial is narrow by tool name.** `get`, `list`, `archive` and retitle are
untouched. A test asserts the registered matcher actually matches the tool,
because a denial the matcher never routes to the guard is decoration.

**Handover ends by archiving the session.** Its notes are written and pushed, so
everything it knew is in the repository; leaving it open invites the operator
back into a conversation that has said goodbye, and invites two sessions editing
the same files. After the push, never before.

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

**Handover has two marks, and the difference between them is the whole design.**
25% arms it: hand over at the next clean boundary, say once what is in flight,
then wait. 45% forces it: park what is in flight and go. One mark could not
express this, and the reason matters — handing over costs a re-orientation, but
being cut off mid-task costs the work twice, and that second cost is invisible
because redone work looks like ordinary work.

**Mid-task is detected, not judged.** Uncommitted changes, unpushed commits, or a
worker still out. At a boundary all three are clear, which is exactly when a
fresh session can pick up from the repository alone. Do not replace this with a
model deciding whether it feels finished.

**While armed and mid-task the hook must fall through, not return a stop
decision.** Returning one swallows the turn and the queue stops reaching the
stoker for the whole armed period. Armed means finish what you are doing, not
stop working. A test pins it.

**25% came from measurement, not taste.** The dominant cost term is that every
tool call re-sends the whole conversation — this session averaged 5.3 requests
per turn — so the bill grows with context far faster than the message count
suggests. Cost per turn falls about a third from 55% to 25% and the curve
flattens below that while disruption keeps growing. Re-orientation cost is the
thing that moves the optimum: a tight HANDOVER.md and a small CLAUDE.md are what
make a low mark affordable, so they are coupled, not independent.

**Context is read from the transcript, not the status line.** Every hook gets a
`transcript_path`, and the last usage record in it carries the token counts the
API reported. That works in a web session, where no status line runs at all —
which is exactly how this sat silent at 53% of the window for a whole evening.
The status line is now only a fallback, useful because it knows the exact window
size. Verified live: 53.4% from the transcript against 528,816 reported by the
session record.

**The settings file is committed at `.claude/settings.json`, so a fresh clone
arrives switched on.** It is generated by `bin/deploy.py --write-project-settings`
from the same table the installer uses, never edited by hand, and a test fails if
the committed copy drifts or an absolute path leaks in. That is what makes a
cloud container work, since there is no installer to run in one.

**The operator has now run the install on their own machine** and reported it
succeeded. That is the first real deploy outside a container.

**The system is deployed on this container.** `bin/deploy.py` has been run for
real for the first time: nine targets linked, hooks and status line registered.
It has still never run on the operator's own machine.

**The old status-line note, kept because the failure mode is worth knowing.** Hooks are never told how full the context window is — only the
status line is. So `hooks/statusline.py` records it to `~/.heater/context.json`
and `hooks/stop.py` reads it. If the status line is not deployed, or the operator
has their own, automatic handover silently never fires. Deploy reports that as
drift rather than taking their status line over. Do not "tidy" the status line
out of the hooks directory.

**Nothing can clear the conversation.** Hook output cannot send input into a
session, confirmed in the docs, so the final `/clear` is always a keystroke the
operator makes. Everything before it — noticing, writing, committing, pushing,
verifying — is automatic. Do not promise the operator otherwise.

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
