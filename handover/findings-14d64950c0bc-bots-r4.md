# Bots survey 14d64950c0bc — round 4 findings (fail, 2 substantive)

Delete this file in the landing commit. Branch worker/14d64950c0bc at fd21a22,
checkout `.heater/worktrees/pokerbot/b1f72dd635fa`. The round-4 fixer was
dispatched with these. All four round-3 failures were confirmed fixed; every
sampled citation, price page, GitHub figure and the ppl-interpreter
reproduction held. The two fails are one-sentence defects in section 5.

Lines in RESOURCES_BOTS.md.

- F1 :982-992 The second "shipped example" of CLAUDE.md's allowed row
  "Substituting an opponent model into the engine's own solver" describes
  "an opponent input to engine-side search … the engine chooses the action"
  and attributes it to ENGINE_ALTERNATIVES.md. That sibling (checkout
  `.heater/worktrees/pokerbot/92e2a2c459ef`, sections "What this means for the
  plan in CLAUDE.md" :780-793 and "Does this contradict the forefront rule?"
  :824-834) places the hook ("Hook A - the rollout policy, per seat") inside
  our own `research/engine_alternatives/chooser.py`, in the column "Written
  by us (the chooser)", says "The engine never picks", and says adopting it
  "requires a recorded carve-out to the forefront rule". Nothing in the
  survey ships an opponent input to decision-time search (NoRegrets --rnr-*
  is training-time, :309-324; robopoker and DecisionHoldem are c ✗, :433,
  :417). Resolve: describe the hook as the sibling does (a per-seat rollout
  policy inside a decision-time chooser, our code, needing a ruling); drop
  "engine-side" and "the engine chooses the action" for that case; remove it
  from the shipped examples or label it an unbuilt design taken from
  ENGINE_ALTERNATIVES.md. The first example (NoRegrets --rnr-model /
  --rnr-opponent / --rnr-p with clone) is sound; leave it.
- F2 :972-974 The engine's side of the forefront table is enumerated as six
  rows; `/Users/chasethompson/pokerbot/CLAUDE.md:28` has a seventh:
  "Combining live-field rates into a quantity that drives a poker decision —
  multiplying the fold rates of the opponents in the current hand to gate a
  bluff, for one". Its permitted counterpart is reproduced at :975-981, so
  the reader gets the permission without its limit while :971 claims the
  survey "neither widens nor narrows" the boundary. Resolve: add the row.
- W3 (wording) :116-119 vs :457-458, :549-552 the restated mark rule admits
  only vendor technical references or price pages, yet PokerSnowie's c ✗
  rests on the vendor's adaptivity claim and Warbot's d ✗ on third-party
  accounts. Both marks are right. Add two clauses to :107-122: a vendor's
  statement that its product does NOT do something may carry a ✗; consistent
  third-party evidence may carry a platform mark, named as third-party.
- W4 (wording) :43-45 "Nothing surveyed plays 7, 8 or 9 seats with real bet
  sizing" contradicts OpenHoldem's a ✓ / b ✓ at :156-164 until the "ships
  no strategy" qualifier at :888-892; carry the qualifier into the bullet.
- W5 (wording) :965-968 "Identity-keyed exploitation has exactly one shipped
  design" ignores Shanky's `Opponent =` by-name branching in 3.12 (:500-512).
  One clause: OpenHoldem fetches the statistics itself, Shanky matches a
  hand-written list.
- W6 (wording) acronyms unexpanded at first use: ACPC :203, MCCFR :210 (also
  :422, :693), VM :99 (explained only at :148), NLHE :336, MTT/SNG :495,
  DON :524, RSS inside the quotation at :257 before :260-262 explains it,
  SB/BB/UTG/MP/CO/BTN at :583 missing from the glossary :68-88.
- W7 (wording) the lead recommendation first appears at :908-916 of 1052;
  section 1 (:15-67) carries none. One line in section 1.
- W8 (wording) :946-947 names RESOURCES_SOLVERS.md and RESOURCES_EXPLOITATION.md
  as though on trunk; say they are companion surveys not yet landed.
- W9 (wording) :257-258 quotes "150-210M infosets, 36-45 GB RSS: memory-bound";
  BASELINES.md:1183-1184 reads "(map at 150-210M infosets, 36-45 GB RSS):
  memory-bound". Quote exactly or paraphrase.
