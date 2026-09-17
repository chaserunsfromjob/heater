# codex/tonight (the classmate's branch): required changes before merge

Fresh reviewer, 2026-09-17, tip ca8339e, judged against the rewritten
forefront rule (branch worker/972241b6f99a). Verdict FAIL in every group;
the betting-rules fix is sound in substance but not separable and not
verified here (no environment on this Mac has pokerkit). Supersedes
codex-tonight-assessment-2026-09-17.md; delete both when the branch lands or
is abandoned. Posted to the classmate as a GitHub issue (see the link in the
fleet commit that added this file).

A. Make the operator's rule text win
1. CLAUDE.md: revert to trunk, then take the operator's version from
   worker/972241b6f99a. His text says four things the operator did not: the
   ban is "superseded" (it is narrowed: assistants may write decision code,
   no model may decide live or have its output frozen in); the laptop
   ceiling is removed (it is kept); the GitHub section is deleted; the
   Licence section is deleted.
2. CLAUDE.md:45 restore the closing line that fleet-wide rules apply.
3. CLAUDE.md:37-41 his own working arrangement moves to AGENTS.md.
4. AGENTS.md:17-19 delete the two authorisation lines; point at CLAUDE.md.
5. research/LEGACY_GUIDANCE.md delete.
6. tools/check_design_numbers.py:284-286 restore FOREFRONT_SOURCE =
   "CLAUDE.md"; let the rule-rewrite branch (which retires or re-points that
   check) land first.
7. OPPONENT_MODEL_DESIGN.md:3-8 delete the banner.
8. README.md:9-10 delete "Original coded strategies ... now in scope."

B. The short-all-in reopening fix
9. REOPENING_REPAIR.md:36 says 192 tests passed; PROGRESS.md:53 says 177.
   One command, one number, quoted beside it.
10. REOPENING_REPAIR.md:11-13 records two rules interpretations (checked
    player loses re-raise right; fractional odd chips) only in a note. Put
    them to the operator for CLAUDE.md before the code merges.
11. pokerkit_rules.py:16, engine.py:346-347 make PokerKit the referee; the
    rule names OpenSpiel. Open the PR, state the OpenSpiel defect and the
    evidence, ask for the bullet to be amended. Do not merge before.
12. pokerkit_rules.py:39-45 the betting-ends override is bundled in; split
    it or say why it is the same defect.
13. Not separable: pokerkit_rules.py imports engine.py (365 lines, landed
    with the strategy modules). Reorder so engine.py, pokerkit_rules.py,
    test_reopening_rules.py, REOPENING_REPAIR.md, research/patches/ land
    as one series without policies.py, ranges.py, responses.py or search.

C. Strategy modules against the letter of the new rule (permitted in kind)
14. ranges.py:61-83 hand-written opponent model that reads hand strength;
    derive from measured action frequencies or ask to amend the bullet.
15. responses.py:21-22 fold .35 / raise .20 hand-picked and fed to the
    rollout search (river_search.py:129-131, turn_search.py:81-83). Replace
    with a prior computed from recorded counts, or cite the measurement.
16. card_controls.py:21-25 three hand-written styles with a 12% bluff rate;
    mark them test opponents and assert no code path feeds one to search.
17. responses.py:17-19 duplicates policies.py:35,37 constants; import.
Passes: no model call, no stored model output (grepped); every policy
deterministic with a seeded rng; hand ranking from OpenSpiel; treys test-only.

D. Result JSON
18. research/results/*.json 19 files, 1.9 MB, 75,119 of 83,040 added lines;
    nothing in code reads them. Keep the seven small summaries the prose
    quotes (~770 lines); drop the per-trial dumps; record command and seed
    beside every quoted number.
19. .gitignore:10-12 ignores runs/ but the dumps live in research/results/.

E. Merge into main at b5924bf
20. Conflicts: CLAUDE.md (two hunks), README.md (one hunk).
21. DANGEROUS silent auto-merge: tools/check_design_numbers.py keeps
    FOREFRONT_SOURCE = "research/LEGACY_GUIDANCE.md"; the check goes green
    while checking nothing. Change 6 fixes it.
22. OPPONENT_MODEL_DESIGN.md auto-merges his banner onto main's rewrite.
23. Rebase only after worker/972241b6f99a lands.
24. No pull request exists; open one first.

Unverifiable here: his tests (pokerkit, pyspiel, numpy, scipy missing from
every venv on this Mac); 177/192 passing unproven. Review cost: 22 tool
calls, ~75k tokens.
