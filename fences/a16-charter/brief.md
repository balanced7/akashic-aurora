# Fence a16-charter: brief

## CHARTER
Daniel approved a new arc for the KeyLab / sound-room / VFX project on 2026-10-22: "Feel free to commit, if it deserves its own arc for proper workflow then lets do another arc."

This fence decides what arc A16 is, following the A15 precedent:
1. a proposal;
2. his provisional yes;
3. this fence: half_a = claude, half_b = deepseek, written blind and independently;
4. M1-PV, then reconciliation;
5. Daniel ratifies the rank and the name.

Nothing is minted until the reconciliation exists.

## INPUTS
His words, verbatim (2026-10-22):
- "I've been feeling really guilty about having a $1300 keyboard and not using any of its fancy functions. If arturia refuses to build actually useful FL studio integration, we will build it ourselves."
- "I want this thing we're building, low latency audio play space, where we can craft sounds and IMPORT them to FL, can you imagine the workflows and collaboration?"
- "both instrument hosting and effects chains, so this would work detached and with FL"
- "We need to tie in our UI work to incorperate the keylab, and for the vfx page and arsenal pages to interact with the keylab display with menus and adaptive beautiful coloring."
- "Can you think of how to tie in obs integration and how we can change modes on the keyboard depending on what tool requested it last ... perhaps a keylab key combo."
- "I want the full vision, no shortcuts or hedges, every feature you could think of and want."

Evidence you may read:
- research/reviewed/keylab-liberation-2026-10-22/daniel-asks-2026-10-22.md (all his asks), and docs/WISHLIST.md W266-W297.
- arsenal/keylab/ (README.md lists every fact confirmed on the hardware), commit c37ff191.
- House structure:
  - docs/ORG.md
  - docs/library/design/20260901_the-estate-program-fourteen-arcs_c432a7.md
  - docs/library/design/20260902_the-one-program-reconciliation_e1bbbc.md (section 5 is the A15 precedent)
  - docs/library/ruling/20260903_appetite-ranking-2026-09-03_375c23.md
  - docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md (media-suite)
- The research reports at docs/library/report/20261022_* (surface map, Spotify beat, BPM sources, VST hosting, SysEx protocol).

## RULES OF ENGAGEMENT
- Blind halves. Until your own half is sealed, do NOT open:
  - the other half;
  - the draft vision synthesis, docs/library/design/20261022_keylab-lit-vision-v2_c76424.md;
  - research/reviewed/keylab-liberation-2026-10-22/vision-* or keylab-lit-*.

  The divergence is the value.
- Read-only everywhere except your own slot.
- Cite repo-relative paths, with a line number only if you read that line. M1-PV checks every citation, and an invented line counts as fabricated.

## THE QUESTION
What should arc A16 be? Cover each of these:
- mandate
- why an arc rather than tracks inside an existing arc
- boundary against A12 THE FACE (the Bifrost UI) and media-suite (piano, First Light, Play)
- tracks
- width under docs/ORG.md
- a first slice with acceptance pre-registered BEFORE anything is built
- seats
- risks
- what only Daniel decides

## OUTPUT CONTRACT
Verdict lines `V1.`, `V2.`, and so on, one claim each. Each verdict line carries exactly one tag from [CERTAIN] [DESIGN] [INFERRED] [UNCERTAIN], and is followed by "Resolving citations:" and repo-relative paths.

Write and seal your half through the door:
- `py agent_cli.py fence write a16-charter --slot half_b --file <your file> --by deepseek`
- `py agent_cli.py fence seal a16-charter --slot half_b --by deepseek`
