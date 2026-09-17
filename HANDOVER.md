# Handover

Written on `main`, 2026-09-17 about 22:10Z, on the Mac, after a machine
compaction (the session ran to 35% context twice; the second time no
handover preceded it, so this is rebuilt from the repository and the
transcript summary). Verify with `bin/handover.py`. A snapshot, not a log;
rewrite, do not append.

Read `README.md` for what is built, `OPINIONS.md` for the operator's
positions, `rules/` for the rules, pokerbot's `BUILD_PLAN.md` for the stages,
and the commit messages for why. None of that is repeated here.

## Stop state

The weekly meter read 98% at 22:03Z (resets Mon 21 Sep 01:00 EDT). The
operator's cap for this week's key work was 97% ("lastly, we can go up to
97% usage"), so the session stopped: no fixer for round 6, no more GTO
Wizard spots. Bearings' band is NOTHING_NEW. Start nothing before the reset.
Nothing is running. Dispatch `e6dfe622fa6f` stays OPEN on purpose so
`land` can find its lease (see traps).

## What is in flight

- `e6dfe622fa6f` heater, the one-round rule for document-only changes
  (branch worker/e6dfe622fa6f @ bfd0a82, pushed; checkout
  `~/.heater/worktrees/heater/dc76881cb2a5`; dispatch OPEN). Six rounds so
  far: r1 fail 6, r2 fail 4, r3 fail 3, r4 pass wording-only, r5 fail 2,
  r6 fail 2 substantive + 2 wording, findings in full in
  `handover/findings-e6dfe622fa6f-docrule-r6.md`. NEXT: fixer in that same
  checkout (no new lease; tell it to read the worker's checkout directly)
  scoped to F1-F4, then round 7; code change, so two consecutive
  wording-only rounds; then `bin/dispatch.py land e6dfe622fa6f --gate "bash
  bin/gate.sh"` and `git push origin main`; then `bin/inbox.py done` on
  921f9190a071. The r3 decision, recorded in the store note: the one-round
  rule reaches only a change landed from its own leased checkout.

## The GTO Wizard preflop answer key: where it stands

Data lives in `handover/gto_key/` in this repository (checkpointed, 187
spots): `spots.jsonl` (one JSON record per spot: code, depth, actions,
acting seat, pot, action list with frequency and combos, and for each of the
169 hands the [actionIndex, frequency] pairs, "-" meaning not in range),
`plan.py` (prints which spots of a solution/depth are still pending),
`ingest.py` (turns the browser's `S|...` lines into records, refuses
duplicates and short grids), and `reference_preflop_2026-09-17.md` (the
protocol header, now out of date on four points below).

Done: 6-max cEV with-cold-calls 3x (`Cash6mGeneral_6mcEVR3`) at 200, 150,
100 (50 spots each: every open, every seat facing every open, opener vs
every 3-bet, 3-bettor vs 4-bet) and 37 of 50 at 50bb. Run
`python3 handover/gto_key/plan.py Cash6mGeneral_6mcEVR3 50 6 40
facing,vs3bet,vs4bet` for the 13 pending (UTG and HJ vs 4-bet from each
seat behind, CO/BTN/SB vs 4-bet).

Remaining, in order, per "make it even a little bit more thorough than you
think it needs to be" and "check with gto wizard like 1.5x more": 6-max 125
(interior check); 6-max 300 in the no-cold-calls 2.5x tree as the deep
anchor (250 is not in the library); 8-max `Cash8mLiveGeneral_8mcEVR3` at
300, 250, 200, 175, 150, 125, 100 (77 spots each; no 50); 9-max three
solutions at 100bb NL50-rake and 150/200 LIVE-rake (96 spots each; no cEV,
no 50); heads-up `CashHuGeneral_cEVR2` at 100 only (operator: HU comes from
open-source solves). Second pass if the meter allows: 6-max no-cold-calls
2.25x (matches fchpa half-pot) and 8-max 2.5x. Library codes and depths are
in queue item b39685936d47 (dismissed, words kept).

The protocol header must change before the write-up: 250bb is absent from
the library (300 no-cold-calls stands in); per-hand grid frequencies replace
"range as text"; heads-up at 100bb only; the solver MAY ingest this data
(operator: "use whatever resources available ... then fill in the gaps
yourself"), so the file must mark HELD-OUT spots before the solve starts and
theory agreement scores only those. Write-up is a worker job on a pokerbot
branch at `research/results/theory_agreement/reference_preflop_2026-09-17.md`
plus the data file, draft PR, document-only landing. Task 87c10184262e
(score 70) records the four 17 Sep operator decisions in BUILD_PLAN.md
Stage 4 first; the verbatim words are in queue items 5ff93dccc2a2,
37271a7dfe2d, 6bab1d206405, f163a1348282.

## How the browser walk works (only this session knew)

GTO Wizard spots are URL-addressable:
`https://app.gtowizard.com/solutions?solution_type=gwiz&gametype=<code>&depth=<bb>&preflop_actions=<A-B-C>&history_spot=<number of actions>`
with tokens F, C, R<size> (all-in is R<stack>). The page's localStorage
holds the reader scripts under keys `hxsrc`, `spotsrc`, `chunksrc`,
`rowsrc`, `descsrc`, `libsrc` (they survive reloads while the operator's
Chrome profile does). Per spot: navigate, then
`eval('window.__spot='+localStorage.getItem('spotsrc')); eval('window.__chunk='+localStorage.getItem('chunksrc')); await window.__spot()`,
then `window.__chunk(0)`, `(1)`, `(2)` to read the `S|...` line in
1000-char slices (the extension truncates any single output near 1200
chars). `__spot` also stores the line at `localStorage['hk_'+depth+'_'+actions]`
so a batch whose output was lost is recovered with
`window.__last=localStorage.getItem('hk_50_F-R3-F')` and the chunks. Feed
lines to `ingest.py` on stdin as `U|code|depth|actions` then the `S|` line.
The grid reads per-hand frequencies from the stacked CSS background layers
of `.ra_table_cell`, colours matched to the `.sab_btn` action buttons.
Limits found: batches of 4-5 spots (about 20 actions) are safe, larger
ones time out; a return value containing "=" or code-like text is blocked
by the extension, so returns use ":" separators; the page cannot reach
localhost or the clipboard, so data passes through the conversation; after
many navigations the renderer freezes ("Runtime.evaluate timed out"),
fixed by navigating again. GTO Wizard signs the Mac out when another device
signs in; the operator was asked to keep other devices closed. The
operator gave standing permission to stay in the browser as long as needed.

## Traps still live (from the previous handover, still true)

- NEVER `git checkout -B <worker branch>` inside a lease made for another
  dispatch (task f642286f63f2 is the fix). A reviewer or fixer on an
  existing branch reads the WORKER's own checkout with the worker's
  dispatch kept open, or a detached worktree in the scratchpad.
- Closing a dispatch `--outcome pushed` deletes its checkout; `land` then
  cannot find a lease. Keep the worker's dispatch open until `land`.
- `land` does not push main; push it.
- `bin/store.py review` refuses `--verdict pass` with findings unless
  `--wording-only`; `--duration` is seconds as a float; the store is
  `store/reviews/`.
- `bin/inbox.py check --summary` needs the summary text as an argument.
- The auto-mode safety classifier times out now and then and blocks Bash
  or Agent for a minute; retry, do not reroute.
- Bearings' auto-push may push worker branches; reconcile at the end of
  every wake.

## Other state only this session knows

- The operator's job order given at the start: (1) the key, (2) fixer and
  rounds for e6dfe622fa6f, (3) nothing new before the Monday reset. (1) and
  (2) are both mid-way, stopped by the cap.
- Daniel-Shiven's pokerbot invite was pending at the last check.
- The task list dropped task f2ff0c6cbe23 (CLAUDE.md dickreuter wording,
  score 30) past the cap when 87c10184262e was promoted; nothing about the
  bot was lost.

## Cost

Weekly meter 89% at session start (17:29Z), 98% at 22:03Z; the browser
walk itself, run inside the stoker's own context, is what spent it. Six
review rounds on e6dfe622fa6f in total, none carrying a dollar figure (task
3919e7a17ec6). Round 6 alone: about 76k tokens, 30 tool calls, 55 minutes.
