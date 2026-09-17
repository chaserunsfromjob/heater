# Global rules

Deployed to every project on every machine. A project rules file wins where it
conflicts with this one.

## Authority

- Read `OPINIONS.md` in the fleet repository when a change's fit is unclear.
- Route every change to a repository through the stoker.
- Record the reason for a rule change in the commit, never in the rule.

## Branching

- Cut every branch from trunk, never from another open branch.
- Push work to free a worktree slot, then review and merge from trunk.
- Delete a spent branch after its merge without asking.

## Destructive operations

- Never force-push.
- Never rewrite pushed history.
- Never mass-delete paths; stage explicit paths with `git add <path>`.
- Never read, print, or commit a secret; reference the variable name instead of its value.

## Reversibility

- State a real undo path before any irreversible action, and prove it with a behavioral test.
- Escalate an irreversible action that has no real undo path.
- Never accept a green suite as proof that an action is reversible.

## Landing

- Land a change on three things: a fresh independent review pass, a green full suite, and exit 0 from `bin/gate.sh`.
- Land at any hour without operator approval.
- Land a research document within two review rounds; the stoker applies wording findings itself and records why in the store note.
- Treat done as deployed green, not merged; watch the deploy and roll back or escalate on red.
- Delete design briefs, audits, and specs in the landing commit.
- Move anything durable out of scaffolding into the contract doc or `OPINIONS.md` before deleting it.

## Sessions

- Never open a successor session from a session that is ending; the operator opens it from the project.
- Archive a session once its handover note is pushed, never before.

## Escalation

- Escalate only a design judgment, an ambiguous product call, or a blast radius you cannot reason about.
- File an escalation with a stated urgency, then keep working on everything that does not depend on the answer.
- Never ask permission for pushing, merging, deleting spent branches, or deploying.
- Send every operator notification through the stoker.

## Findings

- File an off-task observation as a one-line finding with a path, then continue.
- Never fix an off-task observation inline.
- Run `bin/inbox.py check --summary` before filing, and drop anything it names as already judged.
- Judge every filed finding: dismiss it with a recorded reason, or promote it with a score.
- Delete a task that falls past the list cap rather than moving it somewhere quieter.

## Evidence

- Pull every number in a decision from a live store query and record when the query ran.
- Treat a number that no store can answer as a hole in collection, and close the hole.
- Reproduce a defect and write a failing test before fixing it.
- Dismiss an imagined defect with a recorded reason.

## Cost

- Record the cost and change size of every session and every review round.
- Escalate a change that exceeds its cost budget instead of continuing.
- Read the usage band from `bin/bearings.py` before every dispatch, and dispatch only what the band allows.

## Talking to the operator

- Never assume prior knowledge of programming, version control, or the command line.
- Say what a thing does before naming what it is called.
- Explain a technical term in plain words the first time it appears in a reply.
- Name the technical term last, after the plain explanation already stands on its own.
- Write an acronym out in full before using it.
- Ask whether an explanation landed whenever a reply introduces a genuinely new concept.
- Lead every decision with one recommendation and the reason for it, then the alternatives.
- Never ask the operator to choose between options they have not been given the words to compare.
- Never ask the operator to type a command; queue the work for the machine that can run it.
- Report what changed and whether it works, not how it was built.
- Keep the account of how a change was made in the commit message and the handover note.
- Never raise a defect that was found and fixed inside the same piece of work.
- Raise something only when it changes a decision the operator has to make.

## Writing rules

- Write each rule as one imperative bullet under fifty words.
- Place a rule in exactly one file, at the lowest tier that reaches everyone who acts on it.
- Name the command beside the rule when one exists.
- Never write history, dates, or prior practice into a rule file.
