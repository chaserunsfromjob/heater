# Evaluation strategy 45e49ce81e40 — round 5 findings (fail; F1-F6 substantive)

Delete this file, and `findings-45e49ce81e40-evaluation-r{3,4}.md`, in the
landing commit. Branch worker/45e49ce81e40, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\evaluation` on the PC, tip aff7e7f
as reviewed. Recorded in the store as round 5 (c5d8e2f7a913). Lens default.
Lines in EVALUATION_STRATEGY.md at aff7e7f; re-locate by content.

Sound and not to be re-checked: round 4's list; every derived figure in the
document recomputed independently and correct (sample-size and paired-ρ
tables, band weights and Σw²=0.315, full grid 6,781,440 / 235.47 h, nightly
141,280 / 4.906 h, routine 28,256, today's-engine 24 cells / 169,536 /
5.887 h / family 24, engine 1,528 s and 143 s and the ~550 ratio, worker
breakeven 3.92, n_eff and the 28.1 / 28.9 / 22.4 deltas, LBR grid 22 of 55
points ≤ pot, factorials, deck arithmetic); round-4 F1 (no weighted
headline until 8 and 9 deal — the right option under §3.5 point 2), F2
(X6/X1 rewrites exact against trunk REFERENCE_NOTES.md:451-455 and the
seat sweep), F4 (Q2 separates the operator's ordering from the four design
choices), F5, W1, W2, W4, W5, W6 all resolved; the "partly answered" opener
and §3.5's "20" clause are required extensions; the checker is
encoding-safe (stdout reconfigured at :975-982 — verified on a cp1252
console), standard library, mutation tests real, the five-copies gate check
real; 46 internal links resolve; the engine figures unchanged at the survey
tip 6720c8a; suite 29 passed; checker 207 match; no design decision settled.

- F1 (substantive; false claim about a source) :312-316. "neither [Burch et
  al. 2018] nor the White and Bowling 2009 paper it credits writes the
  letters out" — White & Bowling 2009, "Learning a Value Analysis Tool for
  Agent Evaluation", IJCAI-09 pp. 1976-1981
  (webdocs.cs.ualberta.ca/~bowling/papers/09ijcai-mivat.pdf, HTTP 200
  2026-09-17 00:33Z) expands it twice: §3 "We call this general approach …
  MIVAT, the Informed Value Assessment Tool" and the conclusion; DIVAT is
  "the Ignorant Value Assessment Tool". Burch et al. never expand it (true
  half). Resolve: delete the parenthetical; at first use write the plain
  words first and the name last ("the correction for lucky and unlucky
  cards — its authors call it the Informed Value Assessment Tool, MIVAT"),
  cite White & Bowling 2009 §3 and conclusion; keep the Burch half if
  worth keeping.
- F2 (substantive; self-contradiction) :1006-1009 vs :1986. "its own
  earlier draft gave figures three to four times lower because the machine
  was busy" — the provenance row says the earlier draft (54afe67) gave
  56,414, HIGHER than the current 47,564 / 4,438; at 54afe67 the table is
  56,414 / 6,273 / 781 vs current 47,564 / 8,526 / 746 — no three-to-four
  ratio anywhere. Resolve: drop the clause, or state what is checkable: the
  earlier draft gave one unlabelled 56,414 on a busy machine with no load
  recorded; the current draft gates on load and separates the two betting
  modes; the two are not comparable. Do not carry the survey's cross-draft
  ratio.
- F3 (substantive; overclaim about the checker) :1940-1943 and
  tools/check_evaluation_numbers.py:29-30. "A figure that appears in more
  than one place is checked in every place" / "mutating any derived figure
  … anywhere, makes this script exit 1" — false as built: Checker.prose
  asserts one phrase exists; every_occurrence is used for two things only.
  Mutations that EXIT 0: :930 "powered to detect: 28.1" → 28.7; :1112
  budget table "Detects pooled" 28.1 → 28.7 (check_budget_table reads
  columns 2-6 only); :929 "cells: 20" → 25; :936 "elapsed: 4h51m" → 4h59m;
  :1236 §4.1's "240" cells → 260. Resolve: extend the checker to cover the
  example report block (cells, powered to detect, elapsed), the budget
  table's seventh column, and §4.1's cell count, preferring every_occurrence
  for any figure that recurs; add mutation tests for each; then keep the
  sentences. Or weaken both sentences to say truthfully what is pinned.
- F4 (substantive; self-contradiction) :1189-1194 and §4.5:1439 vs
  :1642-1646. Tier 0 "passes at every n from 2 to 9 … Nothing else … is
  worth building until Tier 0 is green" while the engine section says the
  vendored engine caps at seven seats and lists the invariants as buildable
  now — Tier 0 can never go green on today's engine. Resolve: define green
  as every invariant passing at every seat count the engine can deal, with
  the seat counts it cannot deal recorded as NOT RUN, never as passed (as
  :1648-1650 already requires of strength results); point Tier 0 at the
  today's-engine block; same in §4.5.
- F5 (substantive; stale operator decision) :1634-1640 and the
  today's-engine block :1656-1698. "Which engine the project runs on instead
  is a live question that four surveys … will settle" — the operator
  decided 2026-09-16 (heater fb353c6): OpenSpiel `universal_poker` is the
  engine road, fedden/poker_ai reference only, dickreuter/Poker the capture
  reference; only the action-chooser carve-out stays open. Recorded in
  worker/114e5b3f5b1b's CLAUDE.md, not yet on trunk (trunk CLAUDE.md:7
  still says "Built on fedden/poker_ai"). Resolve: replace the sentence
  with the recorded decision and its citation (as the operator's recorded
  decision, not a repository fact); re-frame the today's-engine block as
  what the currently vendored code can exercise while the move to OpenSpiel
  is in progress, not as the shape of a nightly acceptance run (the
  arithmetic stays); keep the "this document does not answer it" guard.
- F6 (substantive, small) :313 "the White and Bowling 2009 paper" has no
  Sources entry (`<a id="s-…">`). Add one if F1 keeps the citation.
- W1 (wording) :1586 "Three of them are partly answered" — X2 is a flat no.
  "three have answers on main, two of them partial", or name them.
- W2 (wording) acronyms not written out first: SE :381, SD :382, HULHE :593,
  VPIP :1913, ACPC :297 (full name at :255/:282 never joined to it); SHA
  (:800, :930, :1527, :1538, gate text) never explained — gloss once
  OUTSIDE the quoted gate: the fingerprint identifying one exact version of
  the code.
- W3 (wording) :995, :1713, :1986 cite the engine survey at autosave 52bd81d;
  both figures unchanged at 6720c8a (46,745/47,564/48,410 fcpa;
  4,251/4,438/4,628 fullgame; "median of six repeats" right). Cite 6720c8a.
- W4 (wording) tools/check_evaluation_numbers.py:990,994 prints "N figures"
  but counts assertions including structural checks; say "checks".
- W5 (wording) :936 "elapsed: 4h51m" beside a run sized at 4.906 h (4h54m);
  round it to the derived figure or mark the line illustrative.

Every finding wording only: NO.

Round-5 cost: 38 tool calls, about 22 minutes, five fetches (arXiv abs and
PDF; IJCAI PDF found at the second address); no dollar figure. Five rounds
on this change so far.
