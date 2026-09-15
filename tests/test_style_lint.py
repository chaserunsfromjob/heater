#!/usr/bin/env python3
"""Tests for the rule-file style linter.

The linter is what stops rule files rotting into prose, so it is the one piece
of this repo that has to be trusted before anything else is.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import style_lint  # noqa: E402


class LintCase(unittest.TestCase):
    def lint_text(self, *files: str) -> list[str]:
        """Lint one or more in-memory rule files; return the finding codes."""
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index, body in enumerate(files):
                path = Path(tmp) / f"rules{index}.md"
                path.write_text(body, encoding="utf-8")
                paths.append(str(path))
            return [f.code for f in style_lint.lint(paths)]


class TestParsing(LintCase):
    def test_finds_top_level_bullets(self):
        rules = self.parse("- Cut from trunk.\n- Push to free a slot.\n")
        self.assertEqual([t for _, t in rules], ["Cut from trunk.", "Push to free a slot."])

    def test_joins_continuation_lines(self):
        rules = self.parse("- Cut every branch from trunk,\n  never from another open branch.\n")
        self.assertEqual(len(rules), 1)
        self.assertIn("never from another open branch", rules[0][1])

    def test_ignores_fenced_code(self):
        rules = self.parse("- Deploy the fleet.\n\n```sh\n- not a rule\n```\n")
        self.assertEqual(len(rules), 1)

    def test_reports_starting_line_number(self):
        rules = self.parse("# Heading\n\n- Cut from trunk.\n")
        self.assertEqual(rules[0][0], 3)

    def parse(self, body: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.md"
            path.write_text(body, encoding="utf-8")
            return style_lint.parse_rules(path)


class TestWordLimit(LintCase):
    def test_flags_over_limit(self):
        long_rule = "- Cut " + " ".join(["word"] * style_lint.MAX_WORDS) + ".\n"
        self.assertIn("LONG", self.lint_text(long_rule))

    def test_allows_exactly_the_limit(self):
        at_limit = "- Cut " + " ".join(["word"] * (style_lint.MAX_WORDS - 1)) + ".\n"
        self.assertNotIn("LONG", self.lint_text(at_limit))

    def test_code_span_counts_as_one_word(self):
        body = "- Run the suite with `python3 -m unittest discover -s tests -v --failfast`.\n"
        self.assertEqual(self.lint_text(body), [])


class TestOneRulePerBullet(LintCase):
    def test_flags_three_sentences(self):
        self.assertIn("MULTI", self.lint_text("- Cut from trunk. Push it. Merge it.\n"))

    def test_allows_rule_plus_exception(self):
        self.assertNotIn("MULTI", self.lint_text("- Cut from trunk. Escalate when trunk is red.\n"))


class TestImperative(LintCase):
    def test_flags_statement_opener(self):
        self.assertIn("OPENER", self.lint_text("- The stoker is the center.\n"))

    def test_flags_hedge_opener(self):
        self.assertIn("OPENER", self.lint_text("- Consider cutting from trunk.\n"))

    def test_allows_never(self):
        self.assertEqual(self.lint_text("- Never force-push.\n"), [])

    def test_allows_verb(self):
        self.assertEqual(self.lint_text("- Escalate an ambiguous product call.\n"), [])


class TestHistory(LintCase):
    def test_flags_banned_phrase(self):
        self.assertIn("HISTORY", self.lint_text("- Cut from trunk, as we used to do.\n"))

    def test_flags_iso_date(self):
        self.assertIn("DATE", self.lint_text("- Cut from trunk after 2026-01-01.\n"))

    def test_flags_written_date(self):
        self.assertIn("DATE", self.lint_text("- Cut from trunk after Jan 1, 2026.\n"))


class TestDuplicates(LintCase):
    def test_flags_exact_restatement_across_files(self):
        codes = self.lint_text("- Never force-push.\n", "- Never force-push.\n")
        self.assertIn("DUP", codes)

    def test_flags_restatement_within_one_file(self):
        codes = self.lint_text("- Never force-push.\n- Never force-push.\n")
        self.assertIn("DUP", codes)

    def test_punctuation_does_not_hide_a_duplicate(self):
        codes = self.lint_text("- Never force-push.\n", "- Never force-push\n")
        self.assertIn("DUP", codes)

    def test_flags_near_duplicate(self):
        codes = self.lint_text(
            "- Record the cost and change size of every review round.\n",
            "- Record the cost and change size of every review rounds.\n",
        )
        self.assertIn("NEARDUP", codes)

    def test_distinct_rules_are_not_duplicates(self):
        codes = self.lint_text("- Never force-push.\n", "- Never rewrite pushed history.\n")
        self.assertEqual(codes, [])


class TestShippedRuleFiles(unittest.TestCase):
    """The repo's own rule files must pass the linter they ship with."""

    def test_rules_directory_is_clean(self):
        root = Path(__file__).resolve().parents[1]
        findings = style_lint.lint([str(root / "rules")])
        self.assertEqual([str(f) for f in findings], [])


if __name__ == "__main__":
    unittest.main()
