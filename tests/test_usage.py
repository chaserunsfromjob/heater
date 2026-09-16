#!/usr/bin/env python3
"""Tests for the usage taper.

Two halves, like the handover: the status line is the only thing told how much
of the plan is spent, and everything downstream acts on what it wrote. So the
tests pin the bridge at both ends, then every threshold edge in between.

Every band edge is tested at the boundary and one step under it, because an
off-by-one here either halts the fleet a day early or lets it run into the wall.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "hooks"))

import bearings  # noqa: E402
import stop as stop_hook  # noqa: E402
import usage  # noqa: E402

TAPER_VARS = tuple(f"{prefix}_{window}"
                   for *_, prefix in usage.THRESHOLDS
                   for window in ("SEVEN_DAY", "FIVE_HOUR"))


class UsageCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        managed = ("HEATER_STATE_DIR",) + TAPER_VARS
        self.previous = {k: os.environ.get(k) for k in managed}
        os.environ["HEATER_STATE_DIR"] = self.tmp.name
        for key in TAPER_VARS:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def at(self, seven=None, five=None, age_hours=0.0, resets_in_days=None):
        """Write a reading straight to the snapshot, as the status line would."""
        recorded = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        reading = {"recorded_at": recorded.isoformat(timespec="seconds"),
                   "five_hour": None, "seven_day": None}
        if five is not None:
            reading["five_hour"] = {"used_percentage": five, "resets_at": None}
        if seven is not None:
            resets = None
            if resets_in_days is not None:
                resets = (datetime.now(timezone.utc)
                          + timedelta(days=resets_in_days)).timestamp()
            reading["seven_day"] = {"used_percentage": seven, "resets_at": resets}
        usage.write(reading)
        return reading


class TestBandEdges(UsageCase):
    """The weekly window is the one that stops everything, so it leads."""

    def test_nothing_recorded_is_open(self):
        self.assertEqual(usage.band(), usage.OPEN,
                         "a missing reading must not halt the fleet")

    def test_an_empty_file_is_open(self):
        usage.snapshot_path().write_text("not json\n", encoding="utf-8")
        self.assertEqual(usage.band(), usage.OPEN)

    def test_low_on_both_is_open(self):
        self.at(seven=10, five=20)
        self.assertEqual(usage.band(), usage.OPEN)

    def test_weekly_edges(self):
        for percentage, expected in ((74.9, usage.OPEN),
                                     (75.0, usage.TOP_OF_LIST_ONLY),
                                     (84.9, usage.TOP_OF_LIST_ONLY),
                                     (85.0, usage.REVIEWS_AND_LANDINGS_ONLY),
                                     (94.9, usage.REVIEWS_AND_LANDINGS_ONLY),
                                     (95.0, usage.NOTHING_NEW),
                                     (100.0, usage.NOTHING_NEW)):
            self.at(seven=percentage, five=0)
            self.assertEqual(usage.band(), expected, f"weekly at {percentage}%")

    def test_five_hour_edges(self):
        """95% of the five-hour window is where the operator said the agents stop."""
        for percentage, expected in ((84.9, usage.OPEN),
                                     (85.0, usage.TOP_OF_LIST_ONLY),
                                     (92.9, usage.TOP_OF_LIST_ONLY),
                                     (93.0, usage.REVIEWS_AND_LANDINGS_ONLY),
                                     (94.9, usage.REVIEWS_AND_LANDINGS_ONLY),
                                     (95.0, usage.NOTHING_NEW),
                                     (100.0, usage.NOTHING_NEW)):
            self.at(seven=0, five=percentage)
            self.assertEqual(usage.band(), expected, f"five-hour at {percentage}%")

    def test_the_weekly_barrier_is_never_reached_after_the_five_hour_one(self):
        """Weighted weekly-first: the same percentage never bites later on the week.

        The stop band is the exception that is level rather than weighted, because
        the operator named 95% of the five-hour window as the stop outright.
        """
        for name, seven, five, _ in usage.THRESHOLDS:
            self.assertLessEqual(seven, five, name)

    def test_the_stop_band_is_level_on_both_windows(self):
        stop = next(t for t in usage.THRESHOLDS if t[0] == usage.NOTHING_NEW)
        self.assertEqual((stop[1], stop[2]), (95.0, 95.0))

    def test_the_tightest_band_wins_when_both_windows_qualify(self):
        self.at(seven=76, five=98)
        self.assertEqual(usage.band(), usage.NOTHING_NEW)

    def test_one_window_alone_still_decides(self):
        self.at(seven=None, five=94)
        self.assertEqual(usage.band(), usage.REVIEWS_AND_LANDINGS_ONLY)

    def test_the_five_hour_window_alone_can_stop_the_fleet(self):
        self.at(seven=None, five=96)
        self.assertEqual(usage.band(), usage.NOTHING_NEW)

    def test_a_stale_reading_still_sets_a_band(self):
        """Eight hours old and at 96% weekly is still near the wall."""
        self.at(seven=96, five=0, age_hours=8)
        self.assertEqual(usage.band(), usage.NOTHING_NEW)
        self.assertTrue(usage.stale())

    def test_a_fresh_reading_is_not_stale(self):
        self.at(seven=10, five=10, age_hours=0.5)
        self.assertFalse(usage.stale())

    def test_the_staleness_edge(self):
        self.at(seven=10, five=10, age_hours=usage.STALE_HOURS - 0.1)
        self.assertFalse(usage.stale())
        self.at(seven=10, five=10, age_hours=usage.STALE_HOURS + 0.1)
        self.assertTrue(usage.stale())

    def test_a_missing_file_is_stale_and_missing(self):
        self.assertTrue(usage.missing())
        self.assertTrue(usage.stale())


class TestOverrides(UsageCase):
    def test_a_threshold_moves(self):
        os.environ["HEATER_TAPER_TOP_OF_LIST_SEVEN_DAY"] = "50"
        self.at(seven=55, five=0)
        self.assertEqual(usage.band(), usage.TOP_OF_LIST_ONLY)

    def test_a_threshold_can_be_loosened_too(self):
        os.environ["HEATER_TAPER_NOTHING_NEW_SEVEN_DAY"] = "99"
        self.at(seven=96, five=0)
        self.assertEqual(usage.band(), usage.REVIEWS_AND_LANDINGS_ONLY)

    def test_nonsense_falls_back_to_the_default(self):
        os.environ["HEATER_TAPER_TOP_OF_LIST_SEVEN_DAY"] = "soon"
        self.at(seven=76, five=0)
        self.assertEqual(usage.band(), usage.TOP_OF_LIST_ONLY)

    def test_every_band_has_both_variables(self):
        for name, *_ in usage.THRESHOLDS:
            self.assertIn(name, usage.ALLOWS, "every band needs a plain-words line")

    def test_how_many_agents_the_middle_band_leaves_out_moves_too(self):
        """Every other figure in the taper moves with a variable; so does this one."""
        self.assertIn(f"at most {usage.TOP_OF_LIST_AGENTS} agents",
                      usage.allows(usage.TOP_OF_LIST_ONLY))
        os.environ["HEATER_TAPER_TOP_OF_LIST_AGENTS"] = "5"
        self.addCleanup(os.environ.pop, "HEATER_TAPER_TOP_OF_LIST_AGENTS", None)
        self.assertIn("at most 5 agents", usage.allows(usage.TOP_OF_LIST_ONLY))

    def test_a_nonsense_agent_count_falls_back_to_the_built_in_figure(self):
        os.environ["HEATER_TAPER_TOP_OF_LIST_AGENTS"] = "a few"
        self.addCleanup(os.environ.pop, "HEATER_TAPER_TOP_OF_LIST_AGENTS", None)
        self.assertIn(f"at most {usage.TOP_OF_LIST_AGENTS} agents",
                      usage.allows(usage.TOP_OF_LIST_ONLY))

    def test_the_band_line_bearings_prints_carries_the_moved_figure(self):
        os.environ["HEATER_TAPER_TOP_OF_LIST_AGENTS"] = "6"
        self.addCleanup(os.environ.pop, "HEATER_TAPER_TOP_OF_LIST_AGENTS", None)
        self.at(seven=80, five=0)
        self.assertIn("at most 6 agents", "\n".join(usage.lines()))


class TestWeeklyCountdown(UsageCase):
    def test_days_left_comes_from_the_reset_time(self):
        self.at(seven=40, five=10, resets_in_days=2.5)
        self.assertAlmostEqual(usage.days_left(), 2.5, places=2)

    def test_no_reset_time_means_no_countdown(self):
        self.at(seven=40, five=10)
        self.assertIsNone(usage.days_left())

    def test_a_reset_in_the_past_is_not_negative(self):
        self.at(seven=40, five=10, resets_in_days=-1)
        self.assertEqual(usage.days_left(), 0.0)

    def test_the_age_of_the_reading_is_reported(self):
        self.at(seven=40, five=10, age_hours=3)
        self.assertAlmostEqual(usage.age_hours(), 3, places=1)


class TestStatusLineRecords(UsageCase):
    """The status line is the only thing Claude Code tells about the plan."""

    def render(self, payload: dict) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "hooks" / "statusline.py")],
                              input=json.dumps(payload), capture_output=True, text=True,
                              timeout=30, env={**os.environ})

    def payload(self, **rate_limits) -> dict:
        return {"model": {"display_name": "Opus"},
                "context_window": {"used_percentage": 12.0},
                "session_id": "s1",
                **({"rate_limits": rate_limits} if rate_limits else {})}

    def test_it_records_both_windows(self):
        self.render(self.payload(five_hour={"used_percentage": 18.5, "resets_at": 1789560000},
                                 seven_day={"used_percentage": 42.25, "resets_at": 1789824000}))
        reading = usage.read()
        self.assertAlmostEqual(reading["five_hour"]["used_percentage"], 18.5)
        self.assertAlmostEqual(reading["seven_day"]["used_percentage"], 42.25)
        self.assertEqual(reading["seven_day"]["resets_at"], 1789824000)
        self.assertTrue(reading["recorded_at"])

    def test_a_payload_without_the_fields_writes_nothing(self):
        """API-key auth, or a first render before any API response."""
        self.render(self.payload())
        self.assertEqual(usage.read(), {})
        self.assertTrue(usage.missing())

    def test_a_payload_without_the_fields_does_not_erase_what_is_known(self):
        self.at(seven=44, five=11)
        self.render(self.payload())
        self.assertAlmostEqual(usage.read()["seven_day"]["used_percentage"], 44)

    def test_one_window_alone_is_recorded(self):
        self.render(self.payload(seven_day={"used_percentage": 30.0}))
        self.assertIsNone(usage.read()["five_hour"])
        self.assertAlmostEqual(usage.read()["seven_day"]["used_percentage"], 30.0)

    def test_a_missing_reset_time_is_still_recorded(self):
        self.render(self.payload(five_hour={"used_percentage": 5.0}))
        self.assertIsNone(usage.read()["five_hour"]["resets_at"])

    def test_rubbish_in_the_fields_is_ignored(self):
        self.render(self.payload(five_hour="soon", seven_day={"used_percentage": "lots"}))
        self.assertTrue(usage.missing())

    def test_it_still_records_the_context_window(self):
        self.render(self.payload(seven_day={"used_percentage": 30.0}))
        self.assertIn("12%", self.render(self.payload(
            seven_day={"used_percentage": 30.0})).stdout)

    def test_it_fails_open_on_an_unwritable_state_directory(self):
        done = subprocess.run([sys.executable, str(ROOT / "hooks" / "statusline.py")],
                              input=json.dumps(self.payload(
                                  seven_day={"used_percentage": 30.0})),
                              capture_output=True, text=True, timeout=30,
                              env={**os.environ, "HEATER_STATE_DIR": "/proc/nope"})
        self.assertEqual(done.returncode, 0)
        self.assertTrue(done.stdout.strip())

    def test_record_never_raises(self):
        self.assertIsNone(usage.record({"rate_limits": None}))
        self.assertIsNone(usage.record({}))


class TestBearings(UsageCase):
    def test_it_names_both_windows_and_the_band(self):
        self.at(seven=42, five=18, resets_in_days=3)
        text = "\n".join(usage.lines())
        self.assertIn("42%", text)
        self.assertIn("18%", text)
        self.assertIn(usage.OPEN, text)
        self.assertIn("about 3 days left", text)

    def test_the_windows_are_labelled_by_the_stretch_of_time_they_cover(self):
        """"Session" would read as this conversation, which is not what it means."""
        self.at(seven=42, five=18)
        text = "\n".join(usage.lines())
        self.assertIn("last 7 days:", text)
        self.assertIn("last 5 hours:", text)
        self.assertNotIn("session (5 hour)", text)

    def test_a_window_with_no_figure_is_read_as_freshly_reset(self):
        """Claude Code drops a window once it resets; that is not a missing reading."""
        self.at(seven=42, five=None)
        text = "\n".join(usage.lines())
        self.assertIn("freshly reset with nothing used", text)
        self.assertNotIn("not reported", text)

    def test_a_window_with_no_reset_time_says_nothing_about_resets(self):
        """"resets reset time unknown" is the machinery talking to itself."""
        self.at(seven=42, five=18)
        line = next(l for l in usage.lines() if "last 5 hours" in l)
        self.assertIn("18% used", line)
        self.assertNotIn("reset time unknown", line)
        self.assertNotIn("resets", line)

    def test_the_time_left_is_written_for_a_person(self):
        self.at(seven=42, five=1, resets_in_days=0.25)
        self.assertIn("about 6 hours left", "\n".join(usage.lines()))

    def test_it_says_in_plain_words_what_the_band_allows(self):
        self.at(seven=96, five=0)
        self.assertIn(usage.ALLOWS[usage.NOTHING_NEW], "\n".join(usage.lines()))

    def test_the_stop_band_says_to_stop_the_agents_and_send_the_debrief(self):
        """The operator's instruction, in the one line the stoker reads."""
        meaning = usage.ALLOWS[usage.NOTHING_NEW]
        self.assertIn("Stop every agent", meaning)
        self.assertIn("bin/debrief.py", meaning)

    def test_the_plain_words_come_before_the_name_of_the_band(self):
        self.at(seven=96, five=0)
        line = next(l for l in usage.lines() if usage.NOTHING_NEW in l)
        self.assertLess(line.index("what may be started now"), line.index(usage.NOTHING_NEW))

    def test_it_says_plainly_when_there_is_no_reading(self):
        text = "\n".join(usage.lines())
        self.assertIn("no usage reading", text)
        self.assertIn("usage.json", text)
        self.assertIn("nothing has written", text)

    def test_a_file_that_exists_but_cannot_be_read_is_not_called_missing(self):
        usage.snapshot_path().write_text("not json\n", encoding="utf-8")
        text = "\n".join(usage.lines())
        self.assertIn("present but unreadable", text)
        self.assertNotIn("nothing has written", text)

    def test_a_reading_that_is_not_text_at_all_still_leaves_bearings_readable(self):
        """Bytes that are not text ended the run in a traceback and printed no
        report at all: the one file that says how much of the plan is left took
        everything else down with it."""
        usage.snapshot_path().write_bytes(b'{"seven_day": {"used_percentage": 96}'
                                          b', "note": "\xff\xfe"}')
        self.assertEqual(usage.read(), {})
        text, attention = self.quiet_report()
        self.assertIn("present but unreadable", text)
        self.assertTrue(attention, "a band nobody can read is not a safe band")

    def test_the_usage_section_comes_before_the_fleet(self):
        self.at(seven=10, five=10)
        with mock.patch.object(bearings, "fleet", return_value=([], False)), \
             mock.patch.object(bearings, "out", return_value=([], False)), \
             mock.patch.object(bearings, "heartbeats", return_value=([], False)), \
             mock.patch.object(bearings, "slots", return_value=([], False)), \
             mock.patch.object(bearings, "machine", return_value=([], False)), \
             mock.patch.object(bearings, "repository", return_value=([], False)), \
             mock.patch.object(bearings, "review_load", return_value=[]):
            text, attention = bearings.report()
        self.assertLess(text.index("## Plan usage"), text.index("## Fleet"))
        self.assertFalse(attention, "an open band with nothing waiting is not an alarm")

    def quiet_report(self):
        with mock.patch.object(bearings, "fleet", return_value=([], False)), \
             mock.patch.object(bearings, "out", return_value=([], False)), \
             mock.patch.object(bearings, "heartbeats", return_value=([], False)), \
             mock.patch.object(bearings, "slots", return_value=([], False)), \
             mock.patch.object(bearings, "machine", return_value=([], False)), \
             mock.patch.object(bearings, "repository", return_value=([], False)), \
             mock.patch.object(bearings, "review_load", return_value=[]):
            return bearings.report()

    def test_nothing_new_needs_attention(self):
        self.at(seven=96, five=0)
        text, attention = self.quiet_report()
        self.assertTrue(attention)
        self.assertIn(usage.NOTHING_NEW, text)

    def test_a_missing_reading_needs_attention(self):
        self.assertTrue(self.quiet_report()[1], "an unknown band is not a safe band")

    def test_an_old_reading_is_flagged_in_words_but_is_not_an_alarm(self):
        """Overnight every reading goes stale and the first reply refreshes it, so
        raising the flag for age alone would open every morning with a false alarm."""
        self.at(seven=10, five=10, age_hours=usage.STALE_HOURS + 1)
        text, attention = self.quiet_report()
        self.assertFalse(attention)
        self.assertIn("treat it as a guess until it refreshes", text)
        self.assertIn("hours ago", text)

    def test_an_old_reading_at_the_stop_band_is_still_an_alarm(self):
        self.at(seven=96, five=10, age_hours=usage.STALE_HOURS + 1)
        self.assertTrue(self.quiet_report()[1])

    def test_the_middle_bands_do_not_raise_an_alarm_on_their_own(self):
        """A taper is not an incident. Only the full stop is."""
        for percentage in (76, 86):
            self.at(seven=percentage, five=0)
            self.assertFalse(self.quiet_report()[1], f"weekly at {percentage}%")


class TestWakeSummary(UsageCase):
    def wake(self):
        os.environ["HEATER_ROLE"] = "stoker"
        self.addCleanup(os.environ.pop, "HEATER_ROLE", None)
        item = {"id": "abc", "kind": "finding", "summary": "s", "urgency": "normal",
                "project": "", "path": ""}
        with mock.patch.object(stop_hook.queue, "pending", return_value=[item]), \
             mock.patch.object(stop_hook.queue, "mark_delivered"), \
             mock.patch.object(stop_hook, "handover_decision", return_value=None):
            return stop_hook.handle({})["hookSpecificOutput"]["reason"]

    def test_an_open_band_is_not_mentioned(self):
        self.at(seven=10, five=10)
        reason = self.wake()
        self.assertNotIn("Usage band", reason)
        self.assertIn("fleet queue", reason)

    def test_a_tightened_band_leads_the_wake(self):
        self.at(seven=88, five=20)
        reason = self.wake()
        self.assertTrue(reason.startswith("Usage band "), reason[:60])
        self.assertIn(usage.REVIEWS_AND_LANDINGS_ONLY, reason)
        self.assertIn("88%", reason)

    def test_the_band_line_says_what_it_allows(self):
        self.at(seven=96, five=20)
        self.assertIn(usage.ALLOWS[usage.NOTHING_NEW], self.wake())

    def test_the_queue_still_reaches_the_stoker_under_a_band(self):
        self.at(seven=96, five=20)
        self.assertIn("fleet queue", self.wake())

    def test_it_is_one_line(self):
        self.at(seven=88, five=20)
        self.assertEqual(len(usage.wake_line().splitlines()), 1)


class TestTheWakeSurvivesABadReading(UsageCase):
    """The queue is stamped as delivered only after everything that can raise.

    The stop hook swallows any exception and ends the turn, so an item stamped
    before the throw is an item the stoker is never told about and never will be.
    The reader itself now answers "nothing known" to every broken file there is,
    so the throw is forced here instead: what is pinned is the ordering, not any
    one way of breaking the reading.
    """

    def setUp(self):
        super().setUp()
        self.previous_queue = os.environ.get("HEATER_QUEUE_DIR")
        os.environ["HEATER_QUEUE_DIR"] = str(Path(self.tmp.name) / "queue")
        os.environ["HEATER_ROLE"] = "stoker"
        self.addCleanup(os.environ.pop, "HEATER_ROLE", None)
        self.addCleanup(self.restore_queue)

    def restore_queue(self):
        if self.previous_queue is None:
            os.environ.pop("HEATER_QUEUE_DIR", None)
        else:
            os.environ["HEATER_QUEUE_DIR"] = self.previous_queue

    def break_the_reading(self):
        """Make the read throw, whatever it is that one day makes it throw."""
        patch = mock.patch.object(stop_hook.usage, "read",
                                  side_effect=OSError("the reading could not be read"))
        patch.start()
        self.addCleanup(patch.stop)

    def test_an_unreadable_reading_leaves_the_items_undelivered(self):
        item = stop_hook.queue.add("finding", "something the stoker must judge")
        self.break_the_reading()
        with mock.patch.object(stop_hook, "handover_decision", return_value=None):
            with self.assertRaises(OSError):
                stop_hook.handle({})
        self.assertEqual([i["id"] for i in stop_hook.queue.pending()], [item["id"]],
                         "the wake was lost: the item is marked as though it arrived")

    def test_the_turn_still_ends_cleanly_and_the_item_waits(self):
        stop_hook.queue.add("finding", "something the stoker must judge")
        self.break_the_reading()
        with mock.patch.object(stop_hook, "handover_decision", return_value=None), \
             mock.patch.object(sys, "stdin", io.StringIO("{}")):
            self.assertEqual(stop_hook.run(stop_hook.handle, "stop"), 0)
        self.assertEqual(len(stop_hook.queue.pending()), 1)

    def test_a_reading_that_is_not_text_no_longer_throws_at_all(self):
        """The file that used to force the throw is now answered, not raised on."""
        path = usage.snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'{"seven_day": {"used_percentage": 96}, "note": "\xff\xfe"}')
        stop_hook.queue.add("finding", "something the stoker must judge")
        with mock.patch.object(stop_hook, "handover_decision", return_value=None):
            reason = stop_hook.handle({})["hookSpecificOutput"]["reason"]
        self.assertIn("fleet queue", reason)
        self.assertEqual(stop_hook.queue.pending(), [])

    def test_a_readable_reading_still_delivers(self):
        stop_hook.queue.add("finding", "something the stoker must judge")
        self.at(seven=96, five=20)
        with mock.patch.object(stop_hook, "handover_decision", return_value=None):
            reason = stop_hook.handle({})["hookSpecificOutput"]["reason"]
        self.assertIn(usage.NOTHING_NEW, reason)
        self.assertEqual(stop_hook.queue.pending(), [])


if __name__ == "__main__":
    unittest.main()
