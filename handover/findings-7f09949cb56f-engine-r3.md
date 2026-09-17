# Engine survey 7f09949cb56f — round 3 findings (fail; F1 substantive)

Delete this file, findings-7f09949cb56f-engine-r2.md and
findings-7f09949cb56f-engine-r2-remaining.md in the landing commit. Branch
worker/7f09949cb56f, checkout .heater/worktrees/pokerbot/92e2a2c459ef, tip
f2d6133, PR #7. Lines at f2d6133. Everything in the round-2 fix diff is sound
and not to be re-checked: second sitting figures, licence table (7 of 8 rows
verified), citations at :149-163, re-wrap, paired_session.py's third argument.

- F1 (substantive) trunk 2d411f3 rewrote CLAUDE.md "The forefront rule": an
  AI assistant MAY write the code that picks an action; what is forbidden is a
  model call in the live decision path, stored model output as decision
  content, and hand-rolled hand-strength logic in place of the engine. Eight
  passages still argue the old rule: :79-80, :132-136 ("exists to prevent"),
  :160-162 ("the rule question above"), :879-885 and :888 (costed item 5, "a
  ruling on the forefront rule ... items 2 and 3 stay research artefacts";
  "the chooser is not" ours), :942-945, :978-979, :985-1031 (":989-990 quotes
  deleted text; :1009 'requires a recorded carve-out'; :1023-1031 NoRegrets
  weighed on 'needs no carve-out at all'"). Resolve: rewrite them against the
  new section by name: the recommendation's conditions drop from two to one;
  "Does this contradict the forefront rule?" becomes a record that the rule
  permits this shape of code and what it still binds (no live model call;
  rules and hand evaluation from OpenSpiel; archetypes from measured
  frequencies only); re-argue the NoRegrets comparison on build cost and
  coverage; keep the split table at :999-1005. Leave :498-503 and :1042 (the
  treys bullet, unchanged on trunk) alone.
- F2 (wording) :942 quotes stage 1 as live; :157 says superseded. Say
  superseded at :942 too, keeping the survey's answer as history.
- F3 (figure) :727 "loads of 3.68 to 4.66" → 4.27-4.66 (raw
  paired_session_2.txt:321, :641), or the session range 3.39-4.66 as at :409.
- F4 (source) :822 PokerRL MIT cell has no local metadata (it does not
  install); name the source or narrow :829-830 to the packages that installed.
- F5 (wording) :417-418 "Every ratio this document argues from" → "Every
  ratio named below", or add the real-sizing ratio (0.53-0.55, OpenSpiel
  slower) and say it reproduces the first sitting's direction.

Every finding wording only: NO (F1).
