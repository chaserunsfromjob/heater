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
| `OPINIONS.md` | The operator's positions on direction. Dated. Only the operator edits it. Every other file answers to it. |
| `rules/global.md` | Rules deployed to every project on every machine. |
| `rules/project.template.md` | Starting point for a per-project rules file, which wins where it conflicts with the global one. |

A rule is one imperative bullet under fifty words, stated in exactly one place.
`tools/style_lint.py` enforces that, and the gate runs it.

## Commands

```sh
bin/gate.sh              # the landing gate: style + suite. Exit 0 or it does not land.
bin/deploy.py            # symlink this machine's ~/.claude files into this repo
bin/deploy.py --check    # report drift without changing anything
tools/style_lint.py      # check rule files on their own
python3 -m unittest discover -s tests
```

Deploy uses symlinks so a machine cannot drift between pulls. Anything already
sitting at a target path is moved to `<name>.pre-heater`, never deleted.

## Build order

Each step is useful on its own. Do not build step seven to make step one feel
complete.

- [x] **1. Opinions and global rules**, written in the strict style, with the
      style linter and the gate that runs it.
- [ ] **2. The PreToolUse guard and the Stop hook**, both failing open.
- [ ] **3. One adversarial-review skill**, with a judge-only reviewer agent and a
      fixer agent.
- [ ] **4. A review-rounds store** the skill writes to, and one query over it.
- [ ] **5. The findings inbox**, with dismiss and promote.
- [ ] **6. The stoker**: its role file, its SessionStart loader, its dispatch command.
- [ ] **7. The worktree pool**, once one worker at a time is no longer enough.

## Credit

The design follows a set of principles the operator was given as reference
notes. The principles are borrowed; the files, commands, and names here are not.
