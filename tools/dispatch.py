#!/usr/bin/env python3
"""Dispatch records: what the stoker sent out, and whether it came back.

The stoker never builds. It sends a worker a brief and waits for a report. This
records both ends, so "what is running" and "what did we send out this week" are
queries rather than something the stoker has to hold in its head across a wake.

A brief is composed here rather than written freehand, so every worker arrives
wrapped in the same standing instructions.

    bin/dispatch.py open --task "..." --project api
    bin/dispatch.py list
    bin/dispatch.py close <id> --outcome pushed --note "branch fix-auth"
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonstore
import store
import worktrees
# Re-exported, not re-implemented: worktrees answers the same question on the
# route reclaim takes, and it cannot import this module back.
from heartbeats import STALE_MINUTES, beats, someone_working_in  # noqa: F401

OUTCOMES = ("landed", "pushed", "escalated", "failed", "abandoned")
REPO = jsonstore.REPO

# Review ends when this many consecutive rounds pass finding only wording, which
# is `skills/adversarial-review/SKILL.md`'s rule and not a number picked here.
# One wording-only pass is the second-to-last step of the loop, not its end.
ROUNDS_TO_END_REVIEW = 2

# How long a branch with no commits on it is left alone. A checkout that has
# produced nothing is a worker that has not finished its first commit far more
# often than it is a worker that is gone, and the two look identical to git.
EMPTY_BRANCH_STALE_HOURS = 24

def dispatches_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_DISPATCHES_DIR", "store/dispatches")


def worker_wrapper() -> str:
    path = REPO / "roles" / "worker.md"
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def compose_brief(record: dict[str, Any]) -> str:
    """The task, wrapped in the standing instructions every worker gets."""
    header = [f"# Brief {record['id']}"]
    if record.get("project"):
        header.append(f"Project: {record['project']}")
    if record.get("task_id"):
        header.append(f"Task: {record['task_id']}")
    if record.get("workdir"):
        header.append(f"Work in: {record['workdir']}")
    if record.get("branch"):
        header.append(f"On branch: {record['branch']} (already checked out for you)")
    parts = ["\n".join(header), "## Your task", record["task"]]
    if record.get("done_when"):
        parts += ["## Done when", record["done_when"]]
    wrapper = worker_wrapper()
    if wrapper:
        parts.append(wrapper)
    parts.append(f"Close this dispatch by reporting; the stoker runs "
                 f"`bin/dispatch.py close {record['id']}`.")
    return "\n\n".join(parts)


def needs_its_own_checkout(project: str) -> bool:
    """Always, whenever there is a repository to lease from.

    Every worker gets its own checkout, including the first. The project's own
    checkout is the consolidation target, not a workspace: sharing it with a
    worker means the thing being merged into is the thing being edited, and
    every conflict between the two becomes a decision somebody has to make.
    """
    del project
    return True


def open_dispatch(task: str, *, project: str = "", done_when: str = "",
                  task_id: str = "", agent: str = "worker",
                  repo: str = "", run_id: str = "", part: str = "") -> dict[str, Any]:
    if not task.strip():
        raise ValueError("a dispatch needs a task")
    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(), "task": task.strip(),
        "project": project, "done_when": done_when.strip(), "task_id": task_id,
        "agent": agent, "repo": repo, "workdir": repo, "lease_id": "", "branch": "",
        "run_id": run_id, "part": part,
        "closed_at": None, "outcome": None, "note": "",
    }

    if repo and needs_its_own_checkout(project or Path(repo).name):
        held = worktrees.lease(Path(repo), project or Path(repo).name,
                               f"worker/{record['id']}", dispatch_id=record["id"])
        record.update(lease_id=held["id"], workdir=held["path"], branch=held["branch"])

    jsonstore.write(dispatches_dir(), record)
    return record


def close_dispatch(dispatch_id: str, outcome: str, note: str = "") -> dict[str, Any]:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    record = next((d for d in jsonstore.load(dispatches_dir()) if d["id"] == dispatch_id), None)
    if record is None:
        raise ValueError(f"no dispatch with id {dispatch_id!r}")
    if record.get("closed_at"):
        raise ValueError(f"{dispatch_id} was already closed as {record['outcome']}")
    record.update(closed_at=jsonstore.now(), outcome=outcome, note=note.strip())
    jsonstore.write(dispatches_dir(), record)

    # Giving the slot back is part of closing, not a separate chore somebody
    # remembers. Release refuses while the branch still holds unpushed work.
    if record.get("lease_id"):
        try:
            worktrees.release(record["lease_id"], f"dispatch {outcome}")
        except (RuntimeError, ValueError) as error:
            record["note"] = (record["note"] + f" [slot held: {error}]").strip()
            jsonstore.write(dispatches_dir(), record)
    return record


class NotReadyToLand(RuntimeError):
    """A landing condition is unmet. Never a reason to merge anyway."""


def rounds_for(change: str) -> list[dict[str, Any]]:
    """Every recorded round for this change, oldest first.

    Ordered by round number and then by when it was recorded, so two rounds both
    called "round 6" settle on the one that arrived last rather than on whichever
    the filesystem happened to list first.
    """
    return sorted((r for r in jsonstore.load(store.reviews_dir())
                   if r.get("change") == change),
                  key=lambda r: (r.get("round", 0), r.get("created", "")))


def settled(round_record: dict[str, Any]) -> bool:
    """True when this round is a pass with nothing substantive left outstanding.

    `bin/store.py review` already refuses to record a pass with substantive
    findings. This refuses to act on one anyway: the store is a directory of
    files, and a file can arrive by some route other than that command.
    """
    if round_record.get("verdict") != "pass":
        return False
    return not round_record.get("findings") or bool(round_record.get("wording_only"))


def reviewed(change: str) -> bool:
    """True when the review loop has ended for this change.

    The latest round decides, never the best one on record: a pass from round 4
    says nothing about a change that rounds 5, 6 and 7 failed. And one pass is
    not the end of the loop — review ends on two consecutive rounds that find
    only wording, so the last two rounds must both be settled passes.
    """
    rounds = rounds_for(change)
    if len(rounds) < ROUNDS_TO_END_REVIEW:
        return False
    return all(settled(r) for r in rounds[-ROUNDS_TO_END_REVIEW:])


def review_note(change: str) -> str:
    """Which rounds a landing rests on, for the note it leaves behind.

    A landing that does not say what it landed on cannot be checked afterwards,
    which is how a stale round-4 pass went unnoticed for a day.
    """
    rounds = rounds_for(change)[-ROUNDS_TO_END_REVIEW:]
    if not rounds:
        return "no review round recorded"
    return "landed on " + ", ".join(f"round {r.get('round', '?')}" for r in rounds)


def review_state(change: str) -> str:
    """Where the review loop has got to, for a refusal that has to explain itself."""
    rounds = rounds_for(change)
    if not rounds:
        return "no round recorded"
    last = rounds[-1]
    findings = f" with {last['findings']} finding(s)" if last.get("findings") else ""
    return (f"{len(rounds)} round(s) recorded, the latest is round "
            f"{last.get('round', '?')}: {last.get('verdict')}{findings}")


def override_note(reason: str) -> str:
    """What a landing that skipped review rests on, in the note it leaves behind.

    `OPINIONS.md` 13 allows the skip on condition the note records why, so the
    reason is part of the phrase rather than something beside it. A skip with
    nothing said is still recorded, and says that nothing was said: refusing it
    would only push the override somewhere that leaves no note at all.
    """
    said = reason.strip()
    phrase = "review skipped by the stoker's explicit override"
    return f"{phrase}: {said}" if said else f"{phrase} (no reason given)"


def land(dispatch_id: str, *, gate: str = "", change: str = "",
         skip_review: bool = False, reason: str = "") -> dict[str, Any]:
    """Merge a worker's branch back, then give its slot up.

    The whole cycle in one step, because a merge that leaves the checkout behind
    and a checkout deleted before its merge are both ways to lose work.

    The heartbeat guard the sweep applies is deliberately left off here: the
    caller named this one dispatch rather than sweeping whatever it found, and
    land refuses outright on uncommitted changes, so a worker mid-task is
    stopped by the refusal rather than by being read as silent.
    """
    record = next((d for d in jsonstore.load(dispatches_dir()) if d["id"] == dispatch_id), None)
    if record is None:
        raise ValueError(f"no dispatch with id {dispatch_id!r}")
    if record.get("closed_at"):
        raise NotReadyToLand(f"{dispatch_id} is already closed as {record['outcome']}")

    named = change or dispatch_id
    # What the landing rests on, written into the record either way: an override
    # that leaves no trace reads exactly like a change that was reviewed.
    approval = override_note(reason)
    if not skip_review:
        if not reviewed(named):
            raise NotReadyToLand(
                f"review has not ended for {named} ({review_state(named)}); it ends on "
                f"{ROUNDS_TO_END_REVIEW} consecutive rounds passing with wording-only "
                "findings, each recorded with `bin/store.py review`")
        approval = review_note(named)

    lease = None
    if record.get("lease_id"):
        lease = next((l for l in jsonstore.load(worktrees.leases_dir())
                      if l["id"] == record["lease_id"]), None)

    if lease is None:
        # The worker used the project's own checkout, so there is nothing to
        # merge from and nothing to clean up.
        return close_dispatch(dispatch_id, "landed",
                              f"worked in the project checkout; {approval}")

    path, repo = Path(lease["path"]), Path(lease["repo"])
    branch, trunk = lease["branch"], lease.get("base_branch") or "main"

    code, dirty = worktrees.git(path, "status", "--porcelain")
    if code == 0 and dirty.strip():
        raise NotReadyToLand(f"{branch} has uncommitted changes; the worker is not finished")

    if gate:
        done = subprocess.run(gate, shell=True, cwd=path, capture_output=True, text=True, timeout=1800)
        if done.returncode != 0:
            raise NotReadyToLand(f"the gate failed in {path}:\n{(done.stdout + done.stderr)[-2000:]}")

    code, on = worktrees.git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or on.strip() != trunk:
        raise NotReadyToLand(f"{repo} is on {on.strip() or '?'}, not {trunk}; merge from trunk")
    code, dirty = worktrees.git(repo, "status", "--porcelain")
    if code == 0 and dirty.strip():
        raise NotReadyToLand(f"{repo} has uncommitted changes; merging would mix them in")

    code, output = worktrees.git(repo, "merge", "--no-ff", branch,
                                 "-m", f"Land {branch}: {record['task'][:60]}")
    if code != 0:
        # Never leave a half-finished merge behind for someone to discover.
        worktrees.git(repo, "merge", "--abort")
        raise NotReadyToLand(f"merge of {branch} into {trunk} failed and was aborted:\n{output}")

    worktrees.release(lease["id"], "landed")
    worktrees.git(repo, "branch", "-d", branch)
    return close_dispatch(dispatch_id, "landed", f"merged {branch} into {trunk}; {approval}")


def start_run(task: str, *, repo: str, project: str = "", workers: int = 2,
              done_when: str = "", task_id: str = "",
              parts: list[str] | None = None) -> list[dict[str, Any]]:
    """Put several workers on one task, each in its own checkout.

    They share a run id so the sweep can consolidate them together and tell when
    the task as a whole is finished.
    """
    if workers < 1:
        raise ValueError("a run needs at least one worker")
    if parts and len(parts) != workers:
        raise ValueError(f"{len(parts)} part(s) given for {workers} worker(s)")

    run_id = jsonstore.new_id()
    return [
        open_dispatch(task, project=project, done_when=done_when, task_id=task_id,
                      repo=repo, run_id=run_id, part=(parts[n] if parts else f"{n + 1} of {workers}"))
        for n in range(workers)
    ]


def merge_into_trunk(repo: Path, path: Path, branch: str, trunk: str,
                     subject: str) -> tuple[bool, str]:
    """Merge a worker's branch into the trunk, resolving what can be resolved.

    A conflict is not a dead end. The usual cause is that the trunk moved while
    the worker was out, so the trunk is merged into the worker's branch first,
    where a conflict is the worker's own to fix, and the trunk merge is retried.
    Both merges abort rather than leaving anything half applied.
    """
    code, output = worktrees.git(repo, "merge", "--no-ff", branch, "-m", subject)
    if code == 0:
        return True, "merged"
    worktrees.git(repo, "merge", "--abort")

    code, output = worktrees.git(path, "merge", "--no-edit", trunk)
    if code != 0:
        worktrees.git(path, "merge", "--abort")
        return False, f"conflicts with {trunk} that the worker must resolve"

    code, output = worktrees.git(repo, "merge", "--no-ff", branch, "-m", subject)
    if code == 0:
        return True, f"merged after catching up with {trunk}"
    worktrees.git(repo, "merge", "--abort")
    return False, f"merge failed even after catching up: {output[-400:]}"


def reconcile(*, run_id: str = "", project: str = "", require_review: bool = True,
              gate: str = "", reason: str = "") -> dict[str, Any]:
    """Consolidate every finished worker into the trunk, then clean up after it.

    Safe to run at any time and safe to run again: what to do is worked out from
    git, not from a flag, so a sweep interrupted halfway is simply repeated.

    Nothing is deleted until its commits are reachable from the trunk. Work is
    never refused for being loose; it is committed on its own branch first.
    """
    report: dict[str, Any] = {"at": jsonstore.now(), "landed": [], "held": [],
                              "awaiting_review": [], "needs_fix": [], "runs_finished": []}
    leases = {l["id"]: l for l in jsonstore.load(worktrees.leases_dir())}

    candidates = [d for d in live()
                  if (not run_id or d.get("run_id") == run_id)
                  and (not project or d.get("project") == project)]

    checked: dict[str, str] = {}
    for record in candidates:
        lease = leases.get(record.get("lease_id", ""))
        if lease is None or lease.get("released_at"):
            close_dispatch(record["id"], "landed", "no checkout to consolidate")
            report["landed"].append(record["id"])
            continue

        repo, path = Path(lease["repo"]), Path(lease["path"])
        trunk = lease.get("base_branch") or "main"
        branch = lease["branch"]

        # The trunk must be clean and checked out before anything merges into it.
        if str(repo) not in checked:
            checked[str(repo)] = trunk_state(repo, trunk)
        if (blocked := checked[str(repo)]):
            report["held"].append({"dispatch": record["id"], "why": blocked})
            continue

        # Asked before autosave, not only before the routes that delete a
        # checkout: committing a file the worker is still writing puts a commit
        # the worker did not make in the middle of the change it is making.
        # One route takes a live checkout anyway — a dispatch whose review has
        # ended is cleaned up with a session still in it, which `README` says
        # out loud — so that route still autosaves, because there the loose
        # files go with the checkout if nobody commits them. Every other route
        # leaves the checkout standing, so its loose work is left alone too.
        # The later guards stay: they read the heartbeat again nearer the moment
        # a checkout is removed, with git and the gate run in between.
        working = still_in_use(path, f"{branch} is checked out")
        if working and not (require_review and reviewed(record["id"])):
            report["held"].append({"dispatch": record["id"], "branch": branch,
                                   "why": working})
            continue

        # Loose work becomes a commit first, so a branch still standing on the
        # commit it was cut from is one nobody worked, not one nobody saved.
        worktrees.autosave(lease)

        if (state := empty_branch(lease, trunk)):
            # Work that has not started, which `merge-base` cannot tell from
            # work that already landed. Answering "landed" here once released
            # three running workers' slots and deleted their checkouts.
            if (why := held_in_flight(record, lease, state)):
                report["held"].append({"dispatch": record["id"], "branch": branch, "why": why})
                continue
            finish(record, lease, branch, repo, trunk,
                   f"{branch} {state}, and nothing has run in the checkout for over "
                   f"{EMPTY_BRANCH_STALE_HOURS}h")
            report["landed"].append(record["id"])
            continue

        if worktrees.landed(lease, trunk):
            # A previous sweep merged it and stopped before cleaning up — or a
            # worker that has not committed yet caught its empty branch up with
            # a trunk that moved (`git pull`, `git merge main`). Both leave a
            # branch the trunk contains, standing past the commit it was cut
            # from, so git cannot tell them apart and the heartbeat has to:
            # deleting the second one takes the slot from a worker mid-task.
            if (why := still_in_use(path, f"{branch} is already in {trunk}")):
                report["held"].append({"dispatch": record["id"], "branch": branch,
                                       "why": why})
                continue
            finish(record, lease, branch, repo, trunk, "already in the trunk")
            report["landed"].append(record["id"])
            continue

        if require_review and not reviewed(record["id"]):
            report["awaiting_review"].append(record["id"])
            continue

        if not require_review:
            # The third route that removes a checkout, and the one the review
            # requirement used to stand in for: with `--skip-review` nothing
            # else here asks whether the worker has finished, so a first commit
            # from a session still making tool calls would be merged and its
            # slot taken mid-task. The reviewed path stays exempt on purpose —
            # a recorded review pass says the work itself is finished, while an
            # override says something about the reviewer, not about the worker.
            if (why := still_in_use(path, f"{branch} has commits {trunk} does not")):
                report["held"].append({"dispatch": record["id"], "branch": branch,
                                       "why": why})
                continue

        if gate:
            done = subprocess.run(gate, shell=True, cwd=path, capture_output=True,
                                  text=True, timeout=1800)
            if done.returncode != 0:
                report["needs_fix"].append({"dispatch": record["id"], "branch": branch,
                                            "why": "the gate does not pass in this checkout"})
                continue

        ok, why = merge_into_trunk(repo, path, branch, trunk,
                                   f"Land {branch}: {record['task'][:60]}")
        if not ok:
            report["needs_fix"].append({"dispatch": record["id"], "branch": branch, "why": why})
            continue

        approval = review_note(record["id"]) if require_review else override_note(reason)
        finish(record, lease, branch, repo, trunk, f"{why}; {approval}")
        report["landed"].append(record["id"])

    report["runs_finished"] = finished_runs()
    return report


# Why a branch carries nothing the trunk lacks. Both read as a clause after the
# branch name, because both are said back in a held report and in a closing note.
NEVER_COMMITTED = "has no commits of its own yet"
BASE_UNRECORDED = ("has no commits the trunk lacks and no record of the commit "
                   "it was cut from")


def empty_branch(lease: dict[str, Any], trunk: str) -> str:
    """Why this branch has nothing to land, or "" when it has work to land.

    Two opposite branches carry no commit the trunk lacks: one nobody has
    committed on, and one whose commits the trunk has already taken. Counting
    commits alone says the same "0" for both, so merged work was held as a
    worker still out, and a day later closed as work nobody ever did.

    The commit the slot was cut from tells them apart: a branch that never
    started still stands on it, while a merged branch has moved past it. An old
    lease that never recorded one is held rather than guessed at, which is the
    refusal `worktrees.work_at_risk` already makes for the same reason.

    Asked of git in the checkout itself, and only while the checkout is there: a
    slot whose folder has gone has nothing left to protect.
    """
    path = Path(lease.get("path", ""))
    if not path.exists():
        return ""
    code, output = worktrees.git(path, "rev-list", "--count", f"{trunk}..HEAD")
    if code != 0 or output.strip() != "0":
        return ""
    base = str(lease.get("base_sha", "")).strip()
    code, head = worktrees.git(path, "rev-parse", "HEAD")
    if code != 0 or not base:
        return BASE_UNRECORDED
    return NEVER_COMMITTED if head.strip() == base else ""


def held_in_flight(record: dict[str, Any], lease: dict[str, Any], state: str) -> str:
    """Why an empty checkout must be kept, or "" when nobody is left to keep it for.

    Two things have to be true before an empty slot is taken back, because
    either alone is wrong often enough to cost a day's work: the dispatch is
    older than anything a worker plausibly runs for, and the checkout has gone
    silent. Silence is read from the same heartbeats bearings calls dead, so a
    worker that is quiet in one place is not busy in the other.

    `state` is `empty_branch`'s answer, said back as given so the hold never
    claims more about the branch than git showed.
    """
    branch = lease.get("branch", "this branch")
    age = age_minutes(record)
    if age is None or age < EMPTY_BRANCH_STALE_HOURS * 60:
        return f"{branch} {state}; the worker is still out"
    return still_in_use(Path(lease.get("path", "")), f"{branch} {state}")


def still_in_use(path: Path, state: str) -> str:
    """Why this checkout may not be removed yet, or "" when nobody is in it.

    One sentence for every route that would delete a checkout, so a worker that
    is alive is said to be alive the same way wherever the sweep notices it.
    `state` is what git showed, said back as given.
    """
    if someone_working_in(path):
        return f"{state}, but its checkout made a tool call within {STALE_MINUTES}m"
    return ""


def trunk_state(repo: Path, trunk: str) -> str:
    """Empty when the trunk is ready to be merged into, otherwise why it is not."""
    code, on = worktrees.git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0:
        return f"cannot read {repo}"
    if on.strip() != trunk:
        return f"{repo} is on {on.strip()}, not {trunk}"
    code, dirty = worktrees.git(repo, "status", "--porcelain")
    if code == 0 and dirty.strip():
        return f"{repo} has uncommitted changes; consolidating would mix them in"
    return ""


def finish(record: dict[str, Any], lease: dict[str, Any], branch: str,
           repo: Path, trunk: str, why: str) -> None:
    """Clean up one worker, and only once its work is provably in the trunk."""
    if not worktrees.landed(lease, trunk):
        raise RuntimeError(f"refusing to clean up {branch}: its commits are not in {trunk}")
    worktrees.release(lease["id"], "consolidated")
    worktrees.git(repo, "branch", "-d", branch)
    close_dispatch(record["id"], "landed", why)


def finished_runs() -> list[str]:
    """Runs whose every worker has landed, so nothing of theirs is left anywhere."""
    everything = jsonstore.load(dispatches_dir())
    runs: dict[str, list[dict[str, Any]]] = {}
    for record in everything:
        if record.get("run_id"):
            runs.setdefault(record["run_id"], []).append(record)
    return [run for run, members in runs.items()
            if all(m.get("outcome") == "landed" for m in members)]


def live() -> list[dict[str, Any]]:
    """Dispatches still out, oldest first: the oldest is the one most likely stuck."""
    return sorted((d for d in jsonstore.load(dispatches_dir()) if not d.get("closed_at")),
                  key=lambda d: d.get("created", ""))


def age_minutes(record: dict[str, Any]) -> float | None:
    try:
        started = datetime.fromisoformat(record["created"])
    except (ValueError, KeyError):
        return None
    return (datetime.now(timezone.utc) - started).total_seconds() / 60


def render_reconcile(result: dict[str, Any]) -> str:
    lines = [f"reconcile as of {result['at']}",
             f"  landed           {len(result['landed'])}",
             f"  awaiting review  {len(result['awaiting_review'])}",
             f"  needs a fixer    {len(result['needs_fix'])}",
             f"  held             {len(result['held'])}"]
    for entry in result["needs_fix"]:
        lines.append(f"    {entry['branch']}: {entry['why']}")
    for entry in result["held"]:
        lines.append(f"    {entry['dispatch']}: {entry['why']}")
    if result["runs_finished"]:
        lines.append(f"  runs fully consolidated: {', '.join(result['runs_finished'])}")
    return "\n".join(lines)


def render(records: list[dict[str, Any]]) -> str:
    if not records:
        return "dispatches: none out"
    lines = [f"{len(records)} dispatch(es) still out:"]
    for record in records:
        age = age_minutes(record)
        stamp = f"{age:.0f}m" if age is not None else "?"
        where = f" {record['project']}" if record.get("project") else ""
        lines.append(f"  {record['id']}  {stamp:>6} ago{where}  {record['task'][:70]}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)

    start = sub.add_parser("open", help="record a dispatch and print the brief to hand the worker")
    start.add_argument("--task", required=True)
    start.add_argument("--project", default="")
    start.add_argument("--done-when", default="")
    start.add_argument("--task-id", default="", help="the inbox task this serves, if any")
    start.add_argument("--agent", default="worker")
    start.add_argument("--repo", default="", help="the project checkout; a slot is leased automatically if one is needed")

    group = sub.add_parser("run", help="put several workers on one task, each in its own checkout")
    group.add_argument("--task", required=True)
    group.add_argument("--repo", required=True)
    group.add_argument("--project", default="")
    group.add_argument("--workers", type=int, default=2)
    group.add_argument("--done-when", default="")
    group.add_argument("--part", action="append", dest="parts", default=None,
                       help="what this worker does; repeat once per worker")

    sweep = sub.add_parser("reconcile", help="consolidate finished workers into the trunk and clean up")
    sweep.add_argument("--run-id", default="")
    sweep.add_argument("--project", default="")
    sweep.add_argument("--gate", default="", help="command that must exit 0 in each checkout")
    sweep.add_argument("--skip-review", action="store_true")
    sweep.add_argument("--reason", default="",
                       help="why review was skipped; only used with --skip-review")

    sub.add_parser("list", help="dispatches still out")

    finish = sub.add_parser("land", help="merge the worker's branch back, then free its slot")
    finish.add_argument("dispatch_id")
    finish.add_argument("--gate", default="", help="command that must exit 0 in the worker's checkout")
    finish.add_argument("--change", default="", help="the change name in the review store; defaults to the dispatch id")
    finish.add_argument("--skip-review", action="store_true",
                        help="land without a recorded review pass; for a human who has looked")
    finish.add_argument("--reason", default="",
                        help="why review was skipped; only used with --skip-review")

    end = sub.add_parser("close", help="record that a worker reported")
    end.add_argument("dispatch_id")
    end.add_argument("--outcome", choices=OUTCOMES, required=True)
    end.add_argument("--note", default="")

    args = parser.parse_args(argv[1:])

    if args.action == "open":
        record = open_dispatch(args.task, project=args.project, done_when=args.done_when,
                               task_id=args.task_id, agent=args.agent, repo=args.repo)
        print(f"# dispatch {record['id']} recorded; hand the brief below to the {record['agent']} agent\n")
        print(compose_brief(record))
    elif args.action == "run":
        records = start_run(args.task, repo=args.repo, project=args.project,
                            workers=args.workers, done_when=args.done_when, parts=args.parts)
        print(f"# run {records[0]['run_id']}: {len(records)} worker(s) on one task\n")
        for record in records:
            print(f"# --- brief for worker {record['part']} ---\n")
            print(compose_brief(record))
            print()
    elif args.action == "reconcile":
        result = reconcile(run_id=args.run_id, project=args.project,
                           require_review=not args.skip_review, gate=args.gate,
                           reason=args.reason)
        print(render_reconcile(result))
        return 1 if (result["held"] or result["needs_fix"]) else 0
    elif args.action == "list":
        print(render(live()))
    elif args.action == "land":
        try:
            record = land(args.dispatch_id, gate=args.gate, change=args.change,
                          skip_review=args.skip_review, reason=args.reason)
        except (NotReadyToLand, ValueError) as error:
            print(f"dispatch: {error}", file=sys.stderr)
            return 1
        print(f"landed {record['id']}: {record['note']}")
    else:
        record = close_dispatch(args.dispatch_id, args.outcome, args.note)
        print(f"closed {record['id']} as {record['outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
