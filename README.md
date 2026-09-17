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
| `hooks/statusline.py` | The status line. Records the exact context window size and the plan's usage windows, neither of which the transcript carries. |
| `tools/usage.py` | How much of the plan is spent, and how much that still allows the stoker to start. |
| `tools/fleetrepo.py` | Which checkout is the fleet repository: the main worktree, worked out from git, so a leased checkout reads and writes the fleet's own queue and stores. `HEATER_REPO` overrides it; a `HEATER_*_DIR` setting still wins over both. |
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
bin/stoker.sh            # open the stoker on this machine, reachable from the Claude app
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
                         # it also pushes any branch that lives on this machine only,
                         # on every machine and including `main`; HEATER_AUTOPUSH=0 turns
                         # that off, HEATER_AUTOPUSH_DEADLINE bounds how long it may take
bin/debrief.py --hours 5 # what the agents did, in plain English. add --queue to send it
bin/dispatch.py open --task "..." --done-when "..."   # record a dispatch, print the brief
bin/dispatch.py run --task "..." --repo <path> --workers 2   # several workers, one task
bin/dispatch.py reconcile --gate "..."   # consolidate everything finished, then clean up
bin/dispatch.py land <id> --gate "..."   # the same, for one dispatch
bin/dispatch.py list / close <id> --outcome failed
bin/worktrees.py list / reclaim    # checkouts leased to workers, created on demand
bin/handover.py          # is this session safe to clear? exit 0 means yes
                         # handover arms itself at 30% context and is forced at 45%;
                         # HEATER_HANDOVER_AT and HEATER_HANDOVER_CEILING move them
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

## Tapering as the plan's limits approach

A Claude.ai subscription meters two clocks. One covers the last five hours and
refills several times a day. The other covers the last seven days, and when it
runs out everything stops until it resets. The seven-day one is the one that
hurts, so it is the one the fleet steers by.

Claude Code tells the status line how full both clocks are, and tells nothing
else. `hooks/statusline.py` writes that reading to `~/.heater/usage.json` on
every render that carries the figures. A render without them — an API key rather
than a subscription, or a first render before any reply has come back — leaves
the previous reading exactly as it was rather than erasing it, so what is known
is never overwritten with nothing:

```json
{"five_hour": {"used_percentage": 18.0, "resets_at": 1789560000},
 "seven_day": {"used_percentage": 42.0, "resets_at": 1789824000},
 "recorded_at": "2026-09-15T21:30:00+00:00"}
```

`resets_at` is a moment in time written the way computers write it — the number
of seconds since the start of 1970. `bin/bearings.py` prints it as a date, and
prints how many days of the week are left, so nobody has to read the number.

From those two percentages `bin/bearings.py` works out how much the fleet may
start right now, and prints it as one word. That word is called a **band**.
`tools/usage.py` holds the four of them and the percentages that trigger each.
The word appears at the top of every `bin/bearings.py` run, and at the top of
every wake message once it is anything other than `OPEN`. Bearings exits 1 — its
way of saying "something needs your attention" — when the word is `NOTHING_NEW`,
or when no reading exists at all. An old reading is printed with its age and a
warning to treat it as a guess, but it is not by itself something to act on:
every reading goes stale overnight and the next session's first reply refreshes
it, so raising the flag for age alone would mean an alarm every morning.

`NOTHING_NEW` is a full stop, not a slow-down. Once either clock crosses the
percentage `tools/usage.py` holds for that band — the band `bin/bearings.py`
prints, so the figure never has to be quoted from memory — every agent
still running is stopped, and `bin/debrief.py --hours 5 --queue` writes the
operator one plain account of what the five hours bought — what each agent was
sent to do, what came back, what the checks found, what is unfinished, and what
it cost where a round recorded a cost — and puts it in the queue. Where no round
recorded one, the account says so rather than implying the window was free.
Where a brief cannot be put into plain words, the account says that outright
rather than guessing at the job. Run it without `--queue` to read it first.

The reading only exists on a Pro or Max subscription, and only once an
interactive session has had a reply back from the model. With an API key, or
before the first reply, there is no reading and bearings says so instead of
guessing.

To move a threshold, set the matching environment variable to a percentage. The
name is the band, then the window:

| Variable | Moves |
| --- | --- |
| `HEATER_TAPER_NOTHING_NEW_SEVEN_DAY` | The `NOTHING_NEW` band's weekly percentage |
| `HEATER_TAPER_NOTHING_NEW_FIVE_HOUR` | The `NOTHING_NEW` band's five-hour percentage |
| `HEATER_TAPER_REVIEWS_ONLY_SEVEN_DAY` | The `REVIEWS_AND_LANDINGS_ONLY` band's weekly percentage |
| `HEATER_TAPER_REVIEWS_ONLY_FIVE_HOUR` | The `REVIEWS_AND_LANDINGS_ONLY` band's five-hour percentage |
| `HEATER_TAPER_TOP_OF_LIST_SEVEN_DAY` | The `TOP_OF_LIST_ONLY` band's weekly percentage |
| `HEATER_TAPER_TOP_OF_LIST_FIVE_HOUR` | The `TOP_OF_LIST_ONLY` band's five-hour percentage |
| `HEATER_TAPER_TOP_OF_LIST_AGENTS` | How many agents `TOP_OF_LIST_ONLY` leaves out at once — a count, not a percentage |

What each band allows is written once, in `tools/usage.py`, and printed by
`bin/bearings.py`. Anything that is not a number is ignored, and the built-in
figure is used.

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
      plus a suite-run store beside it. A round records the change it belongs
      to, its number, the lens, the verdict, how many findings it raised,
      whether those were wording only (`--wording-only`), whether every path
      the change touched was a document (`--document-only`), the change size,
      and the cost. The query counts a change landed by the same rule
      `bin/dispatch.py land` lands it on, and `--document-only` is how it
      knows which rule applied: by the time a week is counted the branch is
      merged and there is no diff left to read.
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
      deleted until its commits are provably in the trunk. Before removing a
      checkout the sweep asks three things: a branch with nothing committed
      goes only when its dispatch is over a day old (`EMPTY_BRANCH_STALE_HOURS`)
      and the checkout has been silent for half an hour
      (`heartbeats.STALE_MINUTES`); a branch the trunk already contains goes
      only after that half hour of silence; a branch with commits to merge goes
      once its review has ended, or, under `--skip-review`, after the half hour
      of silence. A review has ended after one round that finds only wording
      when every path the branch changed is a document — `.md`, `.txt`, or
      under `handover/` or `research/results/` — and after two consecutive such
      rounds for anything else. A checkout whose review has ended is cleaned
      up on the next sweep even if a session is still working in it, so do not
      keep one open expecting it to survive. That same half hour holds back the
      two things the sweep does short of removing a checkout: committing what a
      worker left loose, and `bin/worktrees.py reclaim` taking a slot back once
      its lease is four hours old (`worktrees.STALE_MINUTES` is the age of the
      lease, not the silence).

## Credit

The design follows a set of principles the operator was given as reference
notes. The principles are borrowed; the files, commands, and names here are not.
