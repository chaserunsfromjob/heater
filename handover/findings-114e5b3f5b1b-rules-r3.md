# Licence / GitHub-rules / engine-decision change 114e5b3f5b1b — round 3 findings (pass; wording only)

Delete this file, and `findings-114e5b3f5b1b-rules-r{1,2}.md`, in the landing
commit. Branch worker/114e5b3f5b1b, checkout
`C:\Users\chase\.heater\worktrees\pokerbot\rules` on the PC, tip 0414439 as
reviewed. Recorded in the store as round 3 (f2a9c4d7e186). Lens default.
FIRST wording-only round; fixer applies W1-W2, then confirming round 4; if
wording-only, land.

Sound and not to be re-checked: rounds 1 and 2's lists; round-2 F1 verified
against LICENSE:156-158 (round 2's :155-157 was a citation slip in the
note); W2-W4 applied; CLAUDE.md every bullet imperative under fifty words,
no history, nothing decided beyond the four sources; forefront section
byte-identical to origin/main but for the added bullet (proved by sha256);
no stale private/fedden claim anywhere outside vendor/; suite 25 passed;
design checker 680; LICENSE sha unchanged.

Not raised, do not re-open: CLAUDE.md:17 "adapt the engine instead" beside
"reference only" is for the reconciliation (the forefront section must stay
byte-identical); CLAUDE.md:39 is round 2's W3 applied verbatim;
REFERENCE_NOTES.md:503-504 and :554 are inside a reference record.

- W1 (wording) RESOURCES_BOTS.md:1010-1011 "its Plan records stage 1 as
  superseded by the reconciliation" — CLAUDE.md now says superseded full
  stop, with the reconciliation settling what replaces it. Resolve:
  "records stage 1 as superseded, with what replaces it left to the
  reconciliation." The next sentence is right as it stands.
- W2 (wording) README.md:9 "That permission cannot be taken back" has no
  antecedent, and the sentence runs about fifty-seven words. Resolve: "The
  licence's permission cannot be taken back"; break after "…so long as they
  keep to the licence's conditions." and start "Making the repository
  private later, or putting it under a different licence, would only change
  what people get from that point on." Content unchanged.

Every finding wording only: YES.

Round-3 cost: 20 tool calls, about 12 minutes, no fetch; no dollar figure.
Three rounds on this change so far.
