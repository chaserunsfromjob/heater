#!/usr/bin/env python3
"""The review-round and suite-run stores, and the one query over them.

Two things are written as they happen: every review round, and every suite run.
A decision, report, or brief carrying a number pulls it from here at the moment
of writing and says when the query ran. A number typed into a file is stale the
next day.

    bin/store.py review --change auth-fix --round 1 --lens default --verdict fail ...
    bin/store.py suite --command "bin/gate.sh" --passed --duration 12.4
    bin/store.py query --days 7
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import jsonstore
import reviewloop

LENSES = ("default", "failure-mode", "environment")
VERDICTS = ("pass", "fail")


def reviews_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_REVIEWS_DIR", "store/reviews")


def suites_dir() -> Path:
    return jsonstore.resolve_dir("HEATER_SUITES_DIR", "store/suites")


def record_review(change: str, round_number: int, lens: str, verdict: str, *,
                  findings: int = 0, wording_only: bool = False, document_only: bool = False,
                  files: int = 0,
                  insertions: int = 0, deletions: int = 0, cost_usd: float | None = None,
                  duration_s: float | None = None, project: str = "", note: str = "") -> dict[str, Any]:
    if lens not in LENSES:
        raise ValueError(f"lens must be one of {LENSES}, got {lens!r}")
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}, got {verdict!r}")
    if round_number < 1:
        raise ValueError("round numbering starts at 1")
    if not change.strip():
        raise ValueError("every round belongs to a named change")
    if verdict == "pass" and findings and not wording_only:
        raise ValueError("a round cannot pass with substantive findings outstanding")

    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(), "change": change.strip(),
        "project": project, "round": round_number, "lens": lens, "verdict": verdict,
        "findings": findings, "wording_only": wording_only,
        "document_only": bool(document_only), "files": files,
        "insertions": insertions, "deletions": deletions, "cost_usd": cost_usd,
        "duration_s": duration_s, "note": note,
    }
    jsonstore.write(reviews_dir(), record)
    return record


def record_suite(command: str, passed: bool, *, duration_s: float | None = None,
                 tests: int | None = None, failures: int | None = None,
                 project: str = "") -> dict[str, Any]:
    if not command.strip():
        raise ValueError("a suite run records the command that produced it")
    record = {
        "id": jsonstore.new_id(), "created": jsonstore.now(), "command": command.strip(),
        "passed": bool(passed), "duration_s": duration_s, "tests": tests,
        "failures": failures, "project": project,
    }
    jsonstore.write(suites_dir(), record)
    return record


def cutoff(days: int | None) -> str:
    """The oldest timestamp a window of this many days takes, or "" for all time."""
    if days is None:
        return ""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def within(records: list[dict[str, Any]], days: int | None, project: str) -> list[dict[str, Any]]:
    kept = records
    if project:
        kept = [r for r in kept if r.get("project") == project]
    if not (oldest := cutoff(days)):
        return kept
    return [r for r in kept if r.get("created", "") >= oldest]


def changes_landed(days: int | None, project: str) -> list[str]:
    """Changes whose review loop ended, and ended inside this window.

    Asked of each change's whole history, never of the rounds the window kept.
    A review runs for as long as it takes: round 1 can be a month old while the
    round that ended it arrived this morning. Window the rounds first and that
    change loses its opening round, its remaining rounds are not the end of a
    loop, and the week's report says nothing landed while `dispatch` lands it.

    The window still decides which changes are counted; it is applied to the
    round that ended the review, which is when the change actually landed.
    """
    everything = jsonstore.load(reviews_dir())
    if project:
        everything = [r for r in everything if r.get("project") == project]

    per_change: dict[str, list[dict[str, Any]]] = {}
    for record in everything:
        per_change.setdefault(record["change"], []).append(record)

    oldest = cutoff(days)
    landed = []
    for change, rounds in per_change.items():
        history = reviewloop.ordered(rounds)
        # How many passes this change takes, from what its own rounds recorded.
        # Without it a document that ended on one round is never counted here
        # while `dispatch` has already landed it, and "how many rounds do
        # documents take" has nothing to read.
        needed = reviewloop.needed_from_rounds(history)
        if reviewloop.ended(history, needed) and history[-1].get("created", "") >= oldest:
            landed.append(change)
    return landed


def query(days: int | None = None, project: str = "") -> dict[str, Any]:
    """Aggregate both stores. Always stamped, because a number without a time is a claim."""
    rounds = within(jsonstore.load(reviews_dir()), days, project)
    suites = within(jsonstore.load(suites_dir()), days, project)

    per_change: dict[str, list[dict[str, Any]]] = {}
    for record in rounds:
        per_change.setdefault(record["change"], []).append(record)

    counts = [len(v) for v in per_change.values()]
    costs = [r["cost_usd"] for r in rounds if isinstance(r.get("cost_usd"), (int, float))]
    # Landed means the review loop ended, which is the judgement `dispatch` lands
    # on, asked of the same module. Counting a change landed because some round
    # of it once passed is the stale-pass reading: rounds 5, 6 and 7 can fail
    # after a round-4 pass, and the sweep will rightly refuse to land any of it
    # while this figure says eleven changes went out. Asked of the full history
    # rather than of `rounds`, which the window has already cut down.
    landed = changes_landed(days, project)
    first_time = [c for c, rs in per_change.items()
                  if len(rs) == 1 and rs[0]["verdict"] == "pass"]

    return {
        "as_of": jsonstore.now(),
        "window_days": days,
        "project": project or None,
        "reviews": {
            "rounds": len(rounds),
            "changes": len(per_change),
            "changes_landed": len(landed),
            "rounds_per_change_mean": round(statistics.mean(counts), 2) if counts else None,
            "rounds_per_change_median": statistics.median(counts) if counts else None,
            "rounds_per_change_max": max(counts) if counts else None,
            "passed_first_round": len(first_time),
            "failed_rounds": sum(1 for r in rounds if r["verdict"] == "fail"),
            "wording_only_rounds": sum(1 for r in rounds if r.get("wording_only")),
            "document_only_rounds": sum(1 for r in rounds if r.get("document_only")),
            "cost_usd_total": round(sum(costs), 4) if costs else None,
            "cost_usd_per_change": round(sum(costs) / len(per_change), 4) if costs and per_change else None,
            "rounds_missing_cost": sum(1 for r in rounds if not isinstance(r.get("cost_usd"), (int, float))),
            "lines_changed": sum(r.get("insertions", 0) + r.get("deletions", 0) for r in rounds),
        },
        "suites": {
            "runs": len(suites),
            "passed": sum(1 for s in suites if s["passed"]),
            "failed": sum(1 for s in suites if not s["passed"]),
        },
    }


def render(result: dict[str, Any]) -> str:
    reviews, suites = result["reviews"], result["suites"]
    window = f"last {result['window_days']} day(s)" if result["window_days"] else "all time"
    lines = [
        f"as of {result['as_of']}  ({window}"
        + (f", project {result['project']}" if result["project"] else "") + ")",
        "",
        f"  review rounds          {reviews['rounds']}",
        f"  changes reviewed       {reviews['changes']}  ({reviews['changes_landed']} landed)",
        f"  rounds per change      mean {reviews['rounds_per_change_mean']}, "
        f"median {reviews['rounds_per_change_median']}, worst {reviews['rounds_per_change_max']}",
        f"  passed first round     {reviews['passed_first_round']}",
        f"  failed rounds          {reviews['failed_rounds']}",
        f"  wording-only rounds    {reviews['wording_only_rounds']}",
        f"  document-only rounds   {reviews['document_only_rounds']}",
        f"  lines changed          {reviews['lines_changed']}",
        f"  cost                   {reviews['cost_usd_total']} total, "
        f"{reviews['cost_usd_per_change']} per change",
        f"  suite runs             {suites['runs']}  ({suites['failed']} failed)",
    ]
    if reviews["rounds_missing_cost"]:
        lines += ["", f"  {reviews['rounds_missing_cost']} round(s) recorded no cost. "
                      "That is a hole in collection, not a rounding error."]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # dest is "action", not "command": the suite subcommand takes a --command
    # flag, and sharing the name silently overwrote the subcommand itself.
    sub = parser.add_subparsers(dest="action", required=True)

    review = sub.add_parser("review", help="record one review round")
    review.add_argument("--change", required=True)
    review.add_argument("--round", type=int, required=True)
    review.add_argument("--lens", choices=LENSES, required=True)
    review.add_argument("--verdict", choices=VERDICTS, required=True)
    review.add_argument("--findings", type=int, default=0)
    review.add_argument("--wording-only", action="store_true")
    review.add_argument("--document-only", action="store_true",
                        help="every path this change touched is prose, so it ends on one "
                             "such round; the query's landed count reads this")
    review.add_argument("--files", type=int, default=0)
    review.add_argument("--insertions", type=int, default=0)
    review.add_argument("--deletions", type=int, default=0)
    review.add_argument("--cost-usd", type=float)
    review.add_argument("--duration", type=float)
    review.add_argument("--project", default="")
    review.add_argument("--note", default="")

    suite = sub.add_parser("suite", help="record one suite run")
    suite.add_argument("--command", required=True)
    suite.add_argument("--passed", action="store_true")
    suite.add_argument("--duration", type=float)
    suite.add_argument("--tests", type=int)
    suite.add_argument("--failures", type=int)
    suite.add_argument("--project", default="")

    q = sub.add_parser("query", help="aggregate both stores, stamped with when it ran")
    q.add_argument("--days", type=int)
    q.add_argument("--project", default="")
    q.add_argument("--json", action="store_true")

    args = parser.parse_args(argv[1:])

    if args.action == "review":
        record = record_review(
            args.change, args.round, args.lens, args.verdict, findings=args.findings,
            wording_only=args.wording_only, document_only=args.document_only,
            files=args.files, insertions=args.insertions,
            deletions=args.deletions, cost_usd=args.cost_usd, duration_s=args.duration,
            project=args.project, note=args.note)
        print(f"recorded round {record['round']} of {record['change']}: {record['verdict']} ({record['id']})")
        return 0

    if args.action == "suite":
        record = record_suite(args.command, args.passed, duration_s=args.duration,
                              tests=args.tests, failures=args.failures, project=args.project)
        print(f"recorded suite run {record['id']}: {'passed' if record['passed'] else 'failed'}")
        return 0

    result = query(args.days, args.project)
    print(json.dumps(result, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
