# heater

The fleet repository. Canonical home of the rules, roles, hooks, skills, and
stores that govern every project on every machine.

One orchestrator — the **stoker** — runs as a long-lived Claude Code session. It
never builds anything itself. It dispatches workers into leased git worktrees,
reads their reports, judges what they found, and takes the merge.

The whole thing is built to run with the operator away. Everything else follows
from that.

## Where to start reading

| File | What it is |
| --- | --- |
| `CLAUDE.md` | Project memory. Says that a session opened here is the stoker, and points at everything else. |
| `OPINIONS.md` | The operator's positions on direction. Dated. Only the operator edits it. Every other file answers to it. |
| `rules/global.md` | Rules deployed to every project on every machine. |
| `rules/project.template.md` | Starting point for a per-project rules file, which wins where it conflicts with the global one. |
| `hooks/pre_tool_use.py` | The guard. Denies the destructive spellings it is certain about, warns on the rest, never blocks ordinary work. |
| `hooks/stop.py` | The one channel to the stoker. Wakes it with the queue at a turn boundary. |
| `hooks/session_start.py` | Loads the right role's rules from an environment marker, and reports machine drift. |
| `hooks/post_tool_use.py` | A heartbeat, so a watcher can tell a quiet worker from a dead one. |
| `hooks/session_end.py` | Records how a session ended and what fleet state it left unsynced. |
| `hooks/statusline.py` | The status line. Records the exact context window size, which the transcript does not carry. |
| `hooks/pre_compact.py` | Backstop. Marks a session whose memory was summarised before a handover. |
| `roles/stoker.md` | The stoker's own rules. Loaded for any session opened in this repository, and by `HEATER_ROLE=stoker` anywhere else. |
| `roles/worker.md` | Standing instructions wrapped around every dispatched brief. |
| `queue/` | Notes waiting for the stoker, one JSON file each. |
| `agents/reviewer.md` | The judge. No write tools, and the guard enforces it through Bash too. |
| `agents/fixer.md` | Applies findings. Never passes its own work. |
| `agents/worker.md` | Carries out one dispatched brief, pushes a branch, reports. |
| `skills/adversarial-review/SKILL.md` | The per-change gate: lens routing, the round loop, when review ends. |
| `store/` | Every review round and every suite run, as written. |
| `inbox/` | The ranked task list, and the lifecycle over filed findings. |
| `HANDOVER.md` | What the next session cannot look up for itself. Rewritten, never appended to. |
| `skills/handover/SKILL.md` | The procedure for ending a session safely. |

A rule is one imperative bullet under fifty words, stated in exactly one place.
`tools/style_lint.py` enforces that, and the gate runs it.

## Commands

```sh
bin/stoker.sh            # run the stoker on this machine, reachable from the Claude app.
                         # Stays running: ends a session that has handed over and
                         # opens the next one itself. /exit or Ctrl-C stops it.
bin/gate.sh              # the landing gate: style + suite. Exit 0 or it does not land.
bin/deploy.py            # link ~/.claude files and register the hooks on this machine
bin/deploy.py --check    # report drift without changing anything
bin/queue.py add --kind escalation --summary "..."   # file a note for the stoker
bin/queue.py list        # what the stoker will be woken with
bin/store.py review --change X --round 1 --lens default --verdict fail   # record a round
bin/store.py query --days 7    # is review eating the week? stamped with when it ran
bin/inbox.py check --summary "..."   # already judged? exit 1 means do not file
bin/inbox.py list / dismiss <id> --reason / promote <id> --score 70 / tasks
bin/bearings.py          # where everything stands, in one read. exit 1 means something waits
bin/dispatch.py open --task "..." --done-when "..."   # record a dispatch, print the brief
bin/dispatch.py run --task "..." --repo <path> --workers 2   # several workers, one task
bin/dispatch.py reconcile --gate "..."   # consolidate everything finished, then clean up
bin/dispatch.py land <id> --gate "..."   # the same, for one dispatch
bin/dispatch.py list / close <id> --outcome failed
bin/worktrees.py list / reclaim    # checkouts leased to workers, created on demand
bin/handover.py          # is this session safe to end? exit 0 means yes
                         # handover arms itself at 30% context and is forced at 45%;
                         # HEATER_HANDOVER_AT and HEATER_HANDOVER_CEILING move them.
                         # Once it reads ok, the Stop hook marks the session done and
                         # bin/stoker.sh replaces it. The operator types nothing.
tools/style_lint.py      # check rule files on their own
python3 -m unittest discover -s tests
```

All logic lives in `tools/`; `bin/` holds only entry points. Nothing in `bin/` is
imported, because a module there sharing a name with one in `tools/` shadows it
on the import path.

Deploy uses symlinks so a machine cannot drift between pulls. Anything already
sitting at a target path is moved to `<name>.pre-heater`, never deleted.
`settings.json` is merged rather than linked, so hook registration never wipes
whatever else the operator has configured there.

Every hook fails open. A hook that raises, gets malformed input, or cannot reach
the queue exits 0 and changes nothing, because a guard that blocks every tool
call is a fleet halt.

## Build order

Each step is useful on its own. Do not build step seven to make step one feel
complete.

- [x] **1. Opinions and global rules**, written in the strict style, with the
      style linter and the gate that runs it.
- [x] **2. The PreToolUse guard and the Stop hook**, both failing open, with the
      fleet queue they read and write.
- [x] **Handover** (moved up from step 6): `skills/handover/SKILL.md` and the
      check that proves a session is safe to end. Brought forward because the
      operator clears context often, and clearing is only safe once the reasons
      are written down.
- [x] **3. One adversarial-review skill**, with a judge-only reviewer agent and a
      fixer agent. Judge-only is enforced by the guard, not by the tool list,
      because Bash is a write tool and a reviewer needs it to run tests.
- [x] **4. A review-rounds store** the skill writes to, and one query over it,
      plus a suite-run store beside it.
- [x] **5. The findings inbox**, with dismiss and promote. Findings live in the
      queue store rather than a second directory, so one finding has one record.
      The dismissal reason is what `check` uses to refuse a refile.
- [x] **6. The stoker**: its role file, the SessionStart loader that reads
      `HEATER_ROLE`, dispatch records with composed briefs, the heartbeat, and
      `bearings`. This is the step that switched routing enforcement on.
- [x] **7. Worktree slots**, leased on demand rather than provisioned. The first
      worker on a project uses its checkout; a second one while the first is out
      gets its own, automatically, first one included. Limited by the room left
      on the disk rather than by a headcount.
      `reconcile` sweeps finished workers into the trunk and clears up behind
      them, deriving what to do from git so it is safe to repeat. Nothing is
      deleted until its commits are provably in the trunk.

## Credit

The design follows a set of principles the operator was given as reference
notes. The principles are borrowed; the files, commands, and names here are not.
