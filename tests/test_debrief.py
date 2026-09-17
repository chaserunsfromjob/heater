#!/usr/bin/env python3
"""Tests for the five-hour debrief.

The debrief is the one thing in the fleet written to be read by someone who does
not program, so the tests check the two things that would fail that reader: an
account that leaves out what an agent was sent to do or how its check went, and
an empty window that says nothing at all rather than saying it was empty.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import debrief  # noqa: E402
import dispatch  # noqa: E402
import jsonstore  # noqa: E402
import queue  # noqa: E402
import store  # noqa: E402
import worktrees  # noqa: E402


class DebriefCase(unittest.TestCase):
    ENV = ("HEATER_DISPATCHES_DIR", "HEATER_REVIEWS_DIR", "HEATER_SUITES_DIR",
           "HEATER_LEASES_DIR", "HEATER_QUEUE_DIR", "HEATER_ROLE")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.previous = {k: os.environ.get(k) for k in self.ENV}
        for key in self.ENV[:-1]:
            os.environ[key] = str(Path(self.tmp.name) / key.lower())
        os.environ.pop("HEATER_ROLE", None)

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def stamp(self, minutes_ago: float) -> str:
        return (datetime.now(timezone.utc)
                - timedelta(minutes=minutes_ago)).isoformat(timespec="microseconds")

    def job(self, task: str, *, minutes_ago: float = 60, agent: str = "worker",
            outcome: str | None = None, closed_minutes_ago: float | None = None,
            note: str = "", done_when: str = "") -> dict:
        record = {
            "id": jsonstore.new_id(), "created": self.stamp(minutes_ago), "task": task,
            "project": "heater", "done_when": done_when, "task_id": "", "agent": agent,
            "repo": "", "workdir": "", "lease_id": "", "branch": "", "run_id": "",
            "part": "",
            "closed_at": self.stamp(closed_minutes_ago) if outcome else None,
            "outcome": outcome, "note": note,
        }
        jsonstore.write(dispatch.dispatches_dir(), record)
        return record

    def check(self, change: str, *, round_number: int = 1, verdict: str = "fail",
              findings: int = 0, cost: float | None = None,
              minutes_ago: float = 30) -> dict:
        record = {
            "id": jsonstore.new_id(), "created": self.stamp(minutes_ago),
            "change": change, "project": "heater", "round": round_number,
            "lens": "default", "verdict": verdict, "findings": findings,
            "wording_only": False, "files": 1, "insertions": 1, "deletions": 0,
            "cost_usd": cost, "duration_s": None, "note": "",
        }
        jsonstore.write(store.reviews_dir(), record)
        return record

    def workspace(self, *, released: bool = False, minutes_ago: float = 60,
                  released_minutes_ago: float = 1) -> dict:
        record = {"id": jsonstore.new_id(), "created": self.stamp(minutes_ago),
                  "project": "heater", "repo": "", "branch": "b", "dispatch_id": "",
                  "base_sha": "", "base_branch": "main", "path": "",
                  "released_at": self.stamp(released_minutes_ago) if released else None,
                  "released_how": "landed" if released else ""}
        jsonstore.write(worktrees.leases_dir(), record)
        return record


class TestAFullWindow(DebriefCase):
    def test_it_names_both_jobs_and_how_the_check_went(self):
        """The fixture the finding asked for: two jobs, one round of checking."""
        first = self.job("Vendor the poker solver so it builds without the network",
                         minutes_ago=200, outcome="landed", closed_minutes_ago=90,
                         note="merged into main")  # "vendor" is said as "bring"
        self.job("Build the usage taper against the plan's two windows", minutes_ago=90)
        self.check(first["id"], round_number=1, verdict="fail", findings=3, cost=0.42)

        text = debrief.write(hours=5)

        self.assertIn("Bring the poker solver", text)
        self.assertIn("Build the usage taper", text)
        self.assertIn("Checked over once", text)
        self.assertIn("3 things", text)
        self.assertIn("the work is now part of the project", text)
        self.assertIn("Still running", text)
        self.assertIn("$0.42", text)

    def test_a_passing_check_is_said_as_passing(self):
        record = self.job("Write the handover")
        self.check(record["id"], round_number=1, verdict="fail", findings=2)
        self.check(record["id"], round_number=2, verdict="pass")
        text = debrief.write(hours=5)
        self.assertIn("Checked over twice", text)
        self.assertIn("the last check passed it", text)

    def test_a_second_check_is_said_as_twice_not_as_a_figure(self):
        """"2 times" is a log line. A person says twice."""
        record = self.job("Write the handover")
        self.check(record["id"], round_number=1, verdict="fail", findings=2)
        self.check(record["id"], round_number=2, verdict="fail", findings=1)
        text = debrief.write(hours=5)
        self.assertIn("Checked over twice", text)
        self.assertNotIn("2 times", text)

    def test_a_third_check_is_counted_in_figures(self):
        record = self.job("Write the handover")
        for number in (1, 2, 3):
            self.check(record["id"], round_number=number, verdict="fail", findings=1)
        self.assertIn("Checked over 3 times", debrief.write(hours=5))

    def test_a_job_still_out_from_before_the_window_is_still_named(self):
        """It is about to be stopped, so leaving it out would hide the stop."""
        self.job("Sweep the long-running research", minutes_ago=600)
        self.assertIn("Sweep the long-running research", debrief.write(hours=5))

    def test_work_finished_before_the_window_is_left_out(self):
        self.job("Something from yesterday", minutes_ago=2000,
                 outcome="landed", closed_minutes_ago=1900)
        self.assertNotIn("Something from yesterday", debrief.write(hours=5))

    def test_notes_and_workspaces_are_counted(self):
        self.job("Anything at all")
        queue.add("escalation", "a decision is needed")
        self.workspace()
        self.workspace(released=True)
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("One note was left for you", text)
        self.assertIn("a decision an agent needs from you", text)
        self.assertIn("One separate working copy of a project is still set aside", text)
        self.assertIn("one other was handed back", text)
        self.assertNotIn("(s)", text, "a person does not read 'note(s)'")

    def test_one_minute_is_not_said_as_one_minutes(self):
        self.job("Just started", minutes_ago=1.2)
        self.job("Started an hour and a minute back", minutes_ago=61)
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Sent out 1 minute ago", text)
        self.assertIn("Sent out 1 hour 1 minute ago", text)
        self.assertNotIn("1 minutes", text)

    def test_a_finding_is_not_counted_as_a_note_left_for_the_operator(self):
        """29 of 31 were findings for the stoker. They are a different thing."""
        self.job("Anything at all")
        queue.add("finding", "something an agent noticed")
        judged = queue.add("finding", "something already judged")
        judged["resolution"] = {"action": "dismissed", "reason": "already known"}
        queue.write(judged)
        queue.add("report", "an account for the operator")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("2 things were noticed in passing by an agent and written "
                      "down for the stoker to judge", text)
        self.assertIn("one has been judged and one is still waiting", text)
        self.assertIn("One note was left for you in this window", text)
        self.assertIn("an account an agent wrote for you", text)
        self.assertNotIn("3 notes were left for you", text)
        self.assertNotIn("something an agent noticed in passing and wrote down.",
                         text, "a finding is not one of the notes written for you")

    def test_a_job_that_began_before_the_window_was_not_sent_out_in_it(self):
        """The count said 19 went out where 5 did; the rest were already running."""
        self.job("Older work, still running", minutes_ago=600)
        self.job("Newer work", minutes_ago=10)
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("2 agents were working in this window, one of them sent out "
                      "inside it and one already running when it began", text)
        self.assertNotIn("2 jobs went out", text)

    def test_the_same_brief_sent_out_twice_is_named_as_one_piece_of_work(self):
        """Four of nineteen live entries were a brief dispatched a second time."""
        for _ in range(2):
            self.job("Survey the engines", minutes_ago=30)
        self.job("Something else", minutes_ago=20)
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("One of the jobs below was the same brief sent out a second "
                      "time, so this window covers 2 separate pieces of work, "
                      "not 3", text)
        self.assertNotIn("of the entries below", text,
                         "the reader counting entries that read alike finds more")

    def test_two_briefs_that_only_differ_in_machinery_read_as_one_repeat(self):
        """The live pair differed only in which checkout the second was sent to."""
        self.job("Resolve the merge conflict in pokerbot.", minutes_ago=40)
        self.job("Resolve the merge conflict in pokerbot, working IN THE EXISTING "
                 "checkout /Users/someone/.heater/worktrees/pokerbot/4c952047cdd3.",
                 minutes_ago=30)
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("One of the jobs below was the same brief sent out a "
                      "second time", text)

    def test_a_brief_full_of_machinery_is_said_in_plain_words(self):
        """One fixture with all three: an absolute path, a branch name, a file name."""
        self.job("Resolve the merge conflict between worker/36e2ae4be45b and main, "
                 "working in the checkout at "
                 "/Users/someone/.heater/worktrees/pokerbot/4c952047cdd3, keeping "
                 "both sides of CLAUDE.md and running bin/gate.sh afterwards.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertNotIn("worker/36e2ae4be45b", text)
        self.assertNotIn("/Users/someone", text)
        self.assertNotIn("CLAUDE.md", text)
        self.assertNotIn("bin/gate.sh", text)
        self.assertNotIn("4c952047cdd3", text)
        self.assertIn("Resolve the merge conflict", text)

    def test_a_bare_record_number_in_a_brief_is_not_shown(self):
        self.job("Close out dispatch 059566b3e160 and report what it cost.")
        self.assertNotIn("059566b3e160", debrief.write(hours=5))

    def test_a_brief_that_opens_by_saying_what_it_is_not_still_says_what_it_was(self):
        """Six live entries read only "Research task, not code", three identically."""
        self.job("Research task, not code. Survey open-source poker engines that "
                 "deal every table size from two to nine players.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Survey open-source poker engines", text)
        self.assertNotIn("Research task, not code", text)

    def test_a_meta_clause_that_names_a_file_is_still_stepped_over(self):
        """The live entry that got through: the clause carries a file name in it."""
        self.job("This is research and design-writing, not poker-decision code "
                 "(that stays banned per this repo's CLAUDE.md). Survey how a bot "
                 "reads its opponents.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Survey how a bot reads its opponents", text)
        self.assertNotIn("design-writing", text)

    def test_a_file_name_that_owns_the_next_word_reads_as_the_project(self):
        self.job("Raise tools/worktrees.py's limit on working copies from 3 to 6.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Raise the project's limit on working copies from 3 to 6", text)

    def test_a_brief_written_in_code_shapes_carries_none_of_them(self):
        """Every shape the live page leaked: a class, a call, a command, a
        constant, a folder inside a project and a repository somebody owns."""
        self.job("Stub TestStopHook so context.state(None) is not read live, run "
                 "`bin/gate.sh`, raise MAX_SLOTS, and vendor "
                 "github.com/fedden/poker_ai under vendor/poker_ai/.",
                 done_when="the suite passes on this machine")
        text = " ".join(debrief.write(hours=5).split())
        for shape in ("TestStopHook", "context.state(", "`", "MAX_SLOTS",
                      "vendor/poker_ai/", "github.com/fedden/poker_ai"):
            self.assertNotIn(shape, text, f"{shape} is machinery")
        self.assertIn("Done when the suite passes on this machine", text)

    def test_an_aside_that_is_all_machinery_is_dropped_not_translated(self):
        """"(already on branch a separate copy of the work)" says nothing."""
        self.job("Resolve the merge conflict between worker/36e2ae4be45b and main "
                 "(already on branch worker/36e2ae4be45b; do not create another).")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Resolve the merge conflict between a separate copy of the "
                      "work and the shared copy.", text)
        self.assertNotIn("already on branch", text)

    def test_a_clause_that_only_says_where_to_work_is_dropped(self):
        self.job("Resolve the merge conflict in pokerbot, working IN THE EXISTING "
                 "checkout /Users/someone/.heater/worktrees/pokerbot/4c952047cdd3.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Resolve the merge conflict in pokerbot.", text)
        self.assertNotIn("a folder on this machine", text)

    def test_the_background_a_brief_opens_with_is_not_taken_for_the_work(self):
        """Dispatch 984aa6810a05, word for word out of the store.

        Two of eighteen live entries said what the operator had confirmed or
        what the project did not have yet. The order is the fourth sentence,
        and the page has to keep reading to reach it.
        """
        self.job("Research and design-writing, not code. The operator has confirmed "
                 "firm requirements: the bot must handle every table size from 2 to "
                 "9 players and use true no-limit bet sizing (continuous raise "
                 "amounts, not fixed increments). Our existing "
                 "OPPONENT_MODEL_DESIGN.md (do not edit it -- it's mid-review on a "
                 "different in-progress task; read it for context only) was written "
                 "mostly assuming a fixed-ish table size. Research and write a NEW "
                 "file, TABLE_SIZE_AND_SIZING_NOTES.md, covering: how player "
                 "statistics and exploitative adjustments should change with table "
                 "size.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Research and write a new file", text)
        self.assertIn("how player statistics and exploitative adjustments should "
                      "change with table size", text)
        self.assertNotIn("The operator has confirmed", text)
        self.assertNotIn("Our existing", text)

    def test_a_list_keeps_both_its_items_or_shows_neither(self):
        """Dispatch 7f09949cb56f, word for word out of the store.

        The page promised a list after a colon and then showed one item of it,
        because the second ran past the length the account cuts at.
        """
        self.job("Research task, not code. Survey real open-source poker "
                 "engines/bots (beyond fedden/poker_ai, which we already know "
                 "defaults to a 20-card short deck and fixed-limit betting) that "
                 "natively support: (a) standard 52-card no-limit hold'em with real "
                 "continuous bet sizing (not fixed raise amounts), and (b) a "
                 "VARIABLE number of players per hand from 2 up to 9 (heads-up "
                 "through full-ring), not a hardcoded table size.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("a variable number of players per hand from 2 up to 9", text,
                      "half a list after a colon is worse than no list")
        self.assertIn("standard 52-card no-limit hold'em", text)

    def test_the_brief_of_the_job_that_raised_the_limit_says_what_was_wanted(self):
        """Dispatch ca03e4463c49, word for word out of the store.

        The page said "Done when a file in the project passes" -- a swap and a
        verb, which is nothing -- and before that it said an agent had been
        spent on a comment. What the operator wanted is in the brief's second
        sentence, in the operator's own words.
        """
        self.job("Raise tools/worktrees.py's MAX_SLOTS constant from 3 to 6. The "
                 "operator wants more concurrent workers per project (was hitting "
                 "the cap running research/coding/testing streams in parallel on "
                 "the pokerbot project) and considers 3 an arbitrary default "
                 "rather than a load-bearing limit -- confirm that's true by "
                 "reading the surrounding code and existing tests before changing "
                 "it (check tests/test_worktrees.py and anywhere else MAX_SLOTS is "
                 "referenced or relied on for a specific value). Update the "
                 "constant's comment if it references the old number. Do not "
                 "change any other behavior.",
                 done_when="bin/gate.sh passes; MAX_SLOTS is 6; no test hard-codes "
                           "an assumption that breaks at the new value (if one "
                           "does, fix that test's assumption, not the feature)")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("The operator wants more concurrent workers per project and "
                      "considers 3 an arbitrary default rather than a load-bearing "
                      "limit", text)
        self.assertNotIn("Update the constant's comment", text)
        self.assertNotIn("a file in the project passes", text)
        self.assertNotIn("MAX_SLOTS", text)

    def test_the_brief_of_the_job_that_stubbed_the_tests_says_so_honestly(self):
        """Dispatch 3ea2c1c2c6b7, word for word out of the store.

        Every sentence of it is either the diagnosis or machinery, and what
        finishing looks like is four unexplained fleet words in a row, so the
        honest line is the only true thing the page can say about it.
        """
        self.job("tests/test_queue_and_stop.py's TestStopHook and TestStopFailsOpen "
                 "read live session/repo state instead of stubbing it: "
                 "context.state(None) reads the actual current context-usage "
                 "reading. Confirmed: the module passes 20/20 in a clean worktree "
                 "and fails 7/20 in the main checkout right now, with "
                 "byte-identical code. This makes bin/gate.sh an unreliable "
                 "landing signal. Fix by making these tests stub/monkeypatch "
                 "context.state, handover.in_flight, and handover.problems to "
                 "fixed, deterministic values for each test case.",
                 done_when="bin/gate.sh passes with the same result regardless of "
                           "whether it's run from a clean worktree or from a dirty "
                           "checkout with a different context-usage reading; "
                           "tests/test_queue_and_stop.py no longer reads live "
                           "session/repo state for its assertions")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("written for another agent and does not translate", text)
        for leak in ("Confirmed", "20/20", "worktree", "dirty checkout",
                     "monkeypatch", "context-usage", "unreliable landing signal"):
            self.assertNotIn(leak, text, f"{leak} means nothing to the reader")

    def test_a_project_name_a_repository_and_a_branch_are_all_said_plainly(self):
        """Three shapes the live page still leaked, in one fixture."""
        self.job("Vendor the solver into this repo wherever poker_ai is being "
                 "kept, and resolve the conflict between worker/36e2ae4be45b "
                 "and main.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertNotIn("poker_ai", text)
        self.assertNotIn("this repo", text)
        self.assertNotIn("and main", text)
        self.assertIn("into this project", text)
        self.assertIn("and the shared copy", text)

    def test_two_different_jobs_that_read_alike_are_not_counted_as_one(self):
        """The page is lossy on purpose, so the count comes off the records."""
        self.job("Survey the engines and pick one, checking TestAlpha.",
                 minutes_ago=40)
        self.job("Survey the engines and pick one, checking TestBeta.",
                 minutes_ago=30)
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Survey the engines and pick one.", text)
        self.assertNotIn("already listed above", text)

    def test_a_brief_that_is_all_machinery_says_so_honestly(self):
        """No sentence survives and nothing says what done looks like."""
        self.job("TestStopHook calls context.state(None) and reads MAX_SLOTS.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("written for another agent and does not translate", text)
        self.assertNotIn("TestStopHook", text)

    def test_a_long_sentence_is_never_cut_off_mid_clause(self):
        self.job("Survey the field of open-source poker engines that deal every "
                 "table size from two to nine players, weigh each one against the "
                 "two hard requirements the operator named, and end with a single "
                 "recommendation a later worker could act on without asking.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Survey the field of open-source poker engines that deal "
                      "every table size from two to nine players, weigh each one "
                      "against the two hard requirements the operator named.", text)
        self.assertNotIn("...", text)
        self.assertNotIn("end with a single recommendation", text)

    def test_a_cut_sentence_does_not_end_on_a_clause_that_cannot_stand_alone(self):
        """"...: when a session has written, committed and pushed." is a fragment."""
        self.job("Make the handover fully automatic: when a session has written, "
                 "committed and pushed it, the same `bin/stoker.sh` command must "
                 "end that session and open a fresh one.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Make the handover fully automatic.", text)
        self.assertNotIn("when a session has written", text)

    def test_a_cut_sentence_does_not_end_on_a_pointer_to_the_list_it_lost(self):
        """"...and a Pluribus-style blueprint; for each." points at nothing.

        The sentence promised a thing about each item and was cut before it
        said what, so the promise is all the reader is left holding.
        """
        self.job("Cover at least: vanilla CFR and Deep CFR; for each: what "
                 "OpenSpiel already ships, and the abstraction it needs.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Cover at least: vanilla cfr and Deep cfr.", text)
        self.assertNotIn("for each", text)

    def test_a_cut_sentence_does_not_end_on_what_each_item_comes_with(self):
        """"...the stages to build, in order, each with: what it is." trails off."""
        self.job("Write the stages to build, in order, each with: what it is, "
                 "which document settles it, and what TestDone looks like.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Write the stages to build, in order.", text)
        self.assertNotIn("each with", text)

    def test_two_briefs_that_open_alike_do_not_read_alike(self):
        self.job("Research and design-writing, not code. Survey how a bot beats "
                 "human opponents.")
        self.job("Research and design-writing, not code. Work out how to test "
                 "whether the bot is any good.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Survey how a bot beats human opponents", text)
        self.assertIn("Work out how to test whether the bot is any good", text)

    def test_a_brief_that_says_only_what_it_is_not_falls_back_to_what_done_means(self):
        self.job("Research task, not code.",
                 done_when="a survey of four real engines is written down")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("a survey of four real engines is written down", text)

    def test_a_general_purpose_agent_is_said_by_what_it_was_there_to_do(self):
        self.job("Write up the ready-made bots we could adopt", agent="general-purpose")
        self.assertIn("to look something up and write up what it found",
                      " ".join(debrief.write(hours=5).split()))

    def test_an_agent_kind_the_account_does_not_know_still_gets_a_purpose(self):
        self.job("Anything at all", agent="cartographer")
        self.assertIn("to carry out a piece of work",
                      " ".join(debrief.write(hours=5).split()))

    def test_a_workspace_opened_before_the_window_and_handed_back_inside_it_counts(self):
        """The store said ten handed back where the account said seven."""
        self.job("Anything at all")
        self.workspace(minutes_ago=600, released=True, released_minutes_ago=10)
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("one other was handed back", text)

    def test_a_workspace_handed_back_before_the_window_is_left_out(self):
        self.job("Anything at all")
        self.workspace(minutes_ago=3000, released=True, released_minutes_ago=2000)
        self.assertNotIn("handed back", debrief.write(hours=5))

    def test_a_word_from_version_control_is_explained_before_it_is_named(self):
        """Plain words first, the term last: the reader has never used either."""
        self.job("Anything at all", outcome="pushed", closed_minutes_ago=5)
        self.workspace()
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("saved on its own copy of the project", text)
        self.assertLess(text.index("its own copy of the project"), text.index("merging"))
        self.assertLess(text.index("set aside for these agents"), text.index("checkout"))

    def test_it_says_when_no_cost_was_recorded(self):
        record = self.job("Anything at all")
        self.check(record["id"])
        self.assertIn("No check recorded what it cost", debrief.write(hours=5))

    def test_it_leaves_out_identifiers_and_branch_names(self):
        """A record number and a branch name mean nothing to the reader, and the
        closing note is where both of them live."""
        record = self.job("Vendor the poker solver", outcome="landed",
                          closed_minutes_ago=10,
                          note="merged worker/aebf85e3a420 into main")
        self.check(record["id"])
        text = debrief.write(hours=5)
        self.assertNotIn(record["id"], text)
        self.assertNotIn("worker/aebf85e3a420", text)
        self.assertIn("the work is now part of the project", text)

    def test_a_task_written_with_an_abbreviation_is_not_cut_in_half(self):
        """The abbreviation must not end the sentence; the folder must not survive."""
        self.job("Vendor the solver into this repo (e.g. under vendor/) so it "
                 "builds without the network. The rest does not matter.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Bring the solver into this project so it builds without "
                      "the network.", text)
        self.assertNotIn("vendor/", text)
        self.assertNotIn("The rest does not matter", text)


class TestARecordThatCannotBeRead(DebriefCase):
    """A store file that will not parse is dropped in silence when it is read.

    The page opens by saying every line of it is read back from what the agents
    wrote down, so a record the reader never sees must be counted and owned up
    to: a live page said eleven further rounds of checking where the store held
    thirteen, because two review records had a stray backslash in them.
    """

    def corrupt(self, directory, name="20260917T040000.000000+0000-badf00dbadf0.json"):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text('{"id": "badf00dbadf0", "note": "a \\ b"}\n',
                                      encoding="utf-8")

    def test_one_unreadable_record_is_counted_and_said(self):
        record = self.job("Write the handover")
        self.check(record["id"])
        self.corrupt(store.reviews_dir())
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("One record could not be read and is not counted below.", text)

    def test_unreadable_records_across_the_stores_are_counted_together(self):
        self.job("Write the handover")
        self.corrupt(store.reviews_dir())
        self.corrupt(queue.queue_dir())
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("2 records could not be read and are not counted below.", text)

    def test_a_window_whose_records_all_read_back_says_nothing_about_it(self):
        record = self.job("Write the handover")
        self.check(record["id"])
        self.assertNotIn("could not be read", debrief.write(hours=5))

    def test_an_empty_window_still_owns_up_to_what_it_could_not_read(self):
        """The one page that shows no records at all is the one that must say so."""
        self.corrupt(dispatch.dispatches_dir())
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("One record could not be read", text)
        self.assertIn("Nothing happened in the last 5 hours", text)


class TestMachineryTheSwapsUsedToMiss(DebriefCase):
    """Shapes that reached the live page whole, each from the brief that leaked it."""

    def test_a_dot_leading_name_and_a_tool_name_stay_off_the_page(self):
        """Dispatch 3b3236e88284, word for word out of the store."""
        self.job("Add bin/gate.sh to pokerbot: one command that stands up or "
                 "reuses .venv from requirements-research.txt, runs pytest over "
                 "tests/, and runs the three tools/check_*_numbers.py checkers; "
                 "exit 0 only when all pass",
                 done_when="bash bin/gate.sh exits 0 on the branch and prints a "
                           "one-line verdict; it exits non-zero on a deliberately "
                           "failing test; README.md names it; branch pushed with a "
                           "draft PR")
        text = " ".join(debrief.write(hours=5).split())
        for leak in (".venv", "pytest", "requirements-research", "tools/check"):
            self.assertNotIn(leak, text, f"{leak} means nothing to the reader")

    def test_an_abbreviation_is_still_safe_from_the_dot_rule(self):
        """"e.g." must not be read as a name beginning with a dot."""
        self.job("Survey the engines, e.g. the ones that deal nine players.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Survey the engines, e.g. the ones that deal nine players.", text)

    def test_a_branch_name_a_short_commit_and_a_bare_call_stay_off_the_page(self):
        """Dispatch ec057301faac, word for word out of the store."""
        self.job("Fresh reviewer, read-only: judge the classmate's branch "
                 "codex/tonight (ten commits, tip ca8339e, no pull request) "
                 "against the REWRITTEN forefront rule, and report what must "
                 "change before it can be merged.")
        text = " ".join(debrief.write(hours=5).split())
        for leak in ("codex/tonight", "ca8339e", "read-only", "pull request"):
            self.assertNotIn(leak, text, f"{leak} means nothing to the reader")
        self.assertIn("judge the classmate's separate copy of the work against the "
                      "rewritten forefront rule", text)

    def test_a_call_written_bare_and_a_true_are_machinery(self):
        """Dispatch ecc208e2d0d6, word for word out of the store."""
        self.job("Fix three landing defects in tools/dispatch.py: reconcile lands "
                 "on one wording-only pass instead of two consecutive "
                 "(f16c56933d8a); reviewed() returns True if ANY round passed "
                 "rather than the latest (dc8e3ac0bd7f); reconcile treats a live "
                 "worker's empty branch as landed and discards it (f0b91b86f69f)")
        text = " ".join(debrief.write(hours=5).split())
        self.assertNotIn("reviewed()", text)
        self.assertNotIn("returns True", text)
        self.assertIn("Fix three landing defects in a file in the project: "
                      "reconcile lands on one wording-only pass instead of two "
                      "consecutive.", text)


class TestARenderingThatSaysNothingOfItsOwn(DebriefCase):
    def test_a_line_left_pointing_at_a_sentence_the_reader_never_saw_is_dropped(self):
        """Dispatch 3b2131f2f81c, word for word out of the store.

        The whole of a live entry was "Sweep every such passage.", where the
        passages were named in a sentence the account had already passed over.
        """
        self.job("Mechanical sweep, no design calls. The forefront rule in "
                 "CLAUDE.md was rewritten and landed on main (2d411f3): an AI "
                 "assistant may write the decision code; no model call in the "
                 "live decision path; no stored model output as decision content; "
                 "rules and hand evaluation from the engine. Some documents still "
                 "assert the OLD rule (a 'carve-out' the operator had to grant "
                 "before our code could choose an action) or cite CLAUDE.md by "
                 "line number, and the line numbers have moved. Sweep every such "
                 "passage: run `grep -nE 'carve-out|CLAUDE\\.md:[0-9]+' *.md "
                 "README.md tests tools` and fix each hit so it states the new "
                 "rule and cites CLAUDE.md by section name, never by line. Known "
                 "hits: RESOURCES_SOLVERS.md :137-138, :145, :150. In "
                 "TABLE_SIZE_AND_SIZING_NOTES.md's Sources, move the "
                 "pseudo-harmonic formula, Ganzfried-Sandholm 2013 and Pluribus's "
                 "abstraction from memory-cited to retrieved (verified on branch "
                 "worker/5a58d580c339, ACTION_TRANSLATION.md).")
        text = " ".join(debrief.write(hours=5).split())
        self.assertNotIn("Sweep every such passage", text)
        self.assertIn("move the pseudo-harmonic formula", text)

    def test_two_jobs_whose_only_name_was_swapped_away_do_not_read_alike(self):
        """Dispatches baed4c5203a7 and f541eb44075b, word for word out of the store.

        Both rendered as "Write one new file a file in the project at the
        pokerbot root.": every word of it was the frame of the order, and the
        one word that said which job it was -- the file's name -- is the word
        the swap took out.
        """
        self.job("Research with measurement, not product code. Write ONE new file "
                 "DECISION_LAYER_BLUEPRINT.md at the pokerbot root: the options "
                 "for a PRE-COMPUTED strategy (a 'blueprint') on top of OpenSpiel "
                 "universal_poker for 2-9 player no-limit hold'em. Cover at least: "
                 "vanilla CFR, external-sampling MCCFR, and a Pluribus-style "
                 "abstracted blueprint.", minutes_ago=50)
        self.job("Research with measurement, not product code. Write ONE new file "
                 "DECISION_LAYER_SEARCH.md at the pokerbot root: the options for "
                 "choosing an action IN REAL TIME at the table on top of OpenSpiel "
                 "universal_poker for 2-9 player no-limit hold'em. Cover at least: "
                 "equity-versus-pot-odds rules with Monte Carlo equity, and "
                 "depth-limited search with a blueprint at the leaves.",
                 minutes_ago=40)
        text = " ".join(debrief.write(hours=5).split())
        self.assertNotIn("Write one new file a file in the project at the "
                         "pokerbot root.", text)
        self.assertIn("vanilla cfr", text)
        self.assertIn("equity-versus-pot-odds rules", text)
        lines = [l for l in text.split(" Sent out ") if "Cover at least" in l]
        self.assertEqual(len(lines), 2, "both entries must say what their job was")
        self.assertNotEqual(lines[0], lines[1], "two different jobs, two lines")

    def test_a_file_named_where_it_goes_still_reads_as_one_file(self):
        """The swap put a second file beside the word file: "one new file a file"."""
        self.job("Write ONE new file LLM_POKER_FAILURE_MODES.md at the pokerbot "
                 "root: a short note on what makes large language models bad at "
                 "playing poker.")
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("Write one new file at the pokerbot root: a short note on "
                      "what makes large language models bad at playing poker.", text)
        self.assertNotIn("file a file", text)


class TestNotesLeftForTheOperator(DebriefCase):
    def test_one_note_passed_on_is_said_of_one_note(self):
        """"One note was left for you ... and all of them have been passed on"."""
        self.job("Write the handover")
        item = queue.add("report", "the five-hour account", urgency="high")
        queue.mark_delivered([item])
        text = " ".join(debrief.write(hours=5).split())
        self.assertIn("One note was left for you in this window, and it has been "
                      "passed on to you.", text)
        self.assertNotIn("all of them have been passed on", text)


class TestAnEmptyWindow(DebriefCase):
    def test_it_says_so_plainly(self):
        text = debrief.write(hours=5)
        self.assertIn("Nothing happened in the last 5 hours", text)
        self.assertIn("no agent was sent out", text)

    def test_older_work_does_not_make_the_window_look_busy(self):
        self.job("Yesterday's job", minutes_ago=3000, outcome="landed",
                 closed_minutes_ago=2900)
        self.assertIn("Nothing happened", debrief.write(hours=5))


class TestFilingIt(DebriefCase):
    def test_the_queue_flag_files_it_as_a_report(self):
        self.job("Write the handover")
        item = debrief.file_it(debrief.write(hours=5))
        waiting = queue.pending()
        self.assertEqual([i["id"] for i in waiting], [item["id"]])
        self.assertEqual(waiting[0]["kind"], "report")
        self.assertIn("Write the handover", waiting[0]["summary"])


class TestTheEntryPoint(DebriefCase):
    def run_it(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "bin" / "debrief.py"), *args],
                              capture_output=True, text=True, timeout=60,
                              env={**os.environ})

    def test_it_runs_and_prints_the_account(self):
        self.job("Anything at all")
        done = self.run_it("--hours", "5")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("What the agents did in the last 5 hours", done.stdout)

    def test_it_does_not_file_anything_without_the_flag(self):
        self.job("Anything at all")
        self.run_it("--hours", "5")
        self.assertEqual(queue.pending(), [])

    def test_the_flag_files_it(self):
        self.job("Anything at all")
        done = self.run_it("--hours", "5", "--queue")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(queue.pending()), 1)

    def test_a_window_of_no_hours_is_refused(self):
        self.assertEqual(self.run_it("--hours", "0").returncode, 2)


if __name__ == "__main__":
    unittest.main()
