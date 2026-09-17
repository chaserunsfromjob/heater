# Pre-registered preflop answer key from GTO Wizard, 2026-09-17

Purpose: a blind answer key for Stage 4's solved preflop baseline. Recorded
BEFORE the baseline exists, so the baseline is graded against it and nothing
here is copied into the bot's tables. The theory-agreement harness (task
2cad7f367ed1) compares the bot's search frequencies over the fchpa menu against
these spots; size translation is the harness's job (ACTION_TRANSLATION.md 7),
nothing is translated by hand here.

Written by the stoker from the operator's signed-in Chrome (tier NLH Cash
Ultra). Workers cannot reach the site.

## Protocol (written before the first spot)

- Site: app.gtowizard.com, Study library, No-Limit Hold'em cash (operator, 2026-09-17: 'this should be no limit holdem by the way').
- Depths: 50, 100, 150, 200, 250bb (operator, 2026-09-17, verbatim: 'we should get gto solutions for 50bb, 100bb, 150bb, 200bb, 250bb. and then our own solver should adapt for any in between those.'). Any depth the library lacks is named here and skipped.
- Seat counts: 2, 6, 8, 9 (the scoreboard's weighted seat counts, weights
  n2=0.200 n6=0.500 n8=0.150 n9=0.150). Order of work: 6-max at every depth
  first, then 2, 8, 9; whatever the meter cap cuts off continues after the
  Monday 21 Sep reset.
- Per seat count, record the exact solution set, stack depth, rake and open
  size shown on screen.
- Spot order, per seat count and depth: (1) first-in opening decision from
  every position; (2) big blind facing each position's open; (3) small blind
  facing each open; (4) the opener facing the big blind's 3-bet; (5) the
  opener facing a 3-bet from each seat behind. The operator asked on
  2026-09-17 for the key to be 'even a little bit more thorough than you
  think it needs to be', which is why (3)-(5) are in scope rather than
  optional.
- Per spot: the action frequencies shown (raise / call / fold %, and any
  split raise sizes), and the range as text as the site copies it.
- Budget: 4 points of the weekly plan meter (read 89% at start; stop at 93%).
  Re-read bin/bearings.py "Plan usage" every 25 spots.
- Meter reads: start 89% (2026-09-17T17:43Z).

## Spots

