---
akashic_id: art_20260723_the-ui-design-corpus-every-musing-influe_6b7286
akashic_sha: ba1386602ddb
status: current
type: report
date: 2026-07-23
title: "The UI design corpus — every musing, influence, and verdict, compiled"
gist: "**Daniel's ask (verbatim, tonight):** \"They were supposedly saved in the redis, also can we go back and capture the prior musings about ui a"
tenant: solo
visibility: fleet
seats: []
category: [governance, ui, frontier]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_aurora-glass-supporting-art-references-c_f8309c
    rel: cites
  - target: art_20260709_aurora-glass-composition-spec-single-sou_27005e
    rel: cites
  - target: art_20260711_deepseek-t033-built-vs-spec-inventory-ve_b123a8
    rel: cites
  - target: art_20260723_the-ui-gap-why-the-console-looks-like-th_32fec3
    rel: cites
created: "2026-07-23T02:36:37"
updated: "2026-07-23T21:42:23"
---
<!-- GENERATED PROJECTION of art_20260723_the-ui-design-corpus-every-musing-influe_6b7286 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# The UI design corpus — every musing, influence, and verdict, compiled

**Daniel's ask (verbatim, tonight):** "They were supposedly saved in the redis, also can
we go back and capture the prior musings about ui and the interface design and compile it
here and then compare the current iteration to the design goals and prior art and
influences I cited? I had ideas about views and presentation, lets capture it all"

Provenance discipline: VERBATIM = his words as stored; RECORDED = a seat's contemporaneous
capture; every entry carries its source pointer. Nothing below is reconstructed from memory.

---

## PART 1 — Daniel's design ideas and steers, chronological

- **~2026-04 (project origin):** the FIRST recorded want of the whole project — beautiful
  live dashboards. Optics-first is congenital, not a late addition. (RECORDED:
  memory/project-origin; docs/JOURNEY.md prehistory.)
- **2026-07-04 — the parallel design task:** Daniel commissions two independent UI design
  tracks (claude + deepseek: plans + moodboards). His direct inspiration injection the
  same day: **shaderpark.com** and **awwwards.com/websites/glsl** (RECORDED:
  docs/ui-moodboard-claude.md §D). Yield: docs/ui-plan-{claude,deepseek}.md,
  ui-moodboard-{claude,deepseek}.md → ui-plan-synthesis.md (SETTLED 07-04, deepseek
  full-ACK: palette, motion language, perf gates, HUD-first sequence).
- **2026-07-05 — the composition critique:** from Daniel's screenshot of the cockpit, the
  problem statement that still governs: **"assembled, not composed"** — too many surfaces
  competing. He DELEGATED the composition decision to claude as a coordination test.
  Grounding he supplied/sanctioned: **the OneUI guide (93pp)** [Samsung], **Apple HIG**,
  and **Daniel's own Aurora Glass mockup**. Yield: docs/ui-composition-spec.md — the six
  restraint cuts (collapse reasoning; ONE presence surface; composer focus-block; 24dp
  grid; ≤3 top actions; keep dark/aurora/glass/Razer). (SOURCE: spec header + §problem.)
- **2026-07-06 — fleet vision, first attempt:** vision-track chapter
  "gemini-vision-bifrost-screenshot-output" (2 beats) — screenshots described to the
  fleet via Gemini vision; the dropbox/ describe loop later formalized in
  scripts/ask_gemini_vision.py. (SOURCE: story track vision, chapter 86fa78023fca.)
- **2026-07-11 — T033 design-language re-grounding:** three-way round opened; deepseek
  filed the built-vs-spec inventory (research/reviewed/deepseek-t033-ui-inventory-2026-07-11.md):
  six spec items scored NOT-BUILT/DRIFTED/PARTIAL, **~2,000+ lines of unsanctioned
  growth** beyond the spec, top-5 Daniel-visible fixes, and four spec-is-stale claims
  (M8). Claude's visual half + fresh OneUI/HIG cache: pending at seat handoff — never
  completed. (SOURCE: the inventory doc; bus 1783749634372-0.)
- **2026-07-19/20 night — THE HOME-BASE VERDICT (fork closed):** after consultation #3
  (GPT's LibreChat-shell recommendation, kimi's two positions, deepseek's position),
  Daniel VERBATIM: **"I just made up my mind that I want to build our own. This way we
  have full visibility of what works and what doesn't, our integrations won't break from
  someone else pushing an update, and it will be a good chance for us to improve our
  engineering processes and chops."** Plus: home base = our own program, API models + CLI
  models first-class. (SOURCE: note daniel-verdicts-2026-07-19-night, verbatim held.)
- **2026-07-20 — the T098 charter expansion (his fullest design statement on record),**
  VERBATIM: "I would like us to have a cli version of akashic aurora with an interface
  similar to the rest of the competition and I would like us to have a program that takes
  the best of all the other similar ones like codex, claude code librechat and any others
  and for us to make an opensource program of our own that is modular and invites users
  to make their own modifications and improvements. … I want our program to be **modern
  and sleek and to be highly performant and stable, like nasa grade stable.** …" →
  T098 charter: competition-familiar CLI face; open-source modular, plugin-first;
  feature list seeded by pain-point research; NASA/JPL/DO-178C-lineage engineering bar.
  (SOURCE: note t098-charter-expansion-2026-07-20, verbatim held.)
- **2026-07-20 — the quality bar, in his own words:** praise for deepseek's T002 work —
  hover/click effects **"modern, beautiful, responsive"** (RECORDED:
  scratch:deepseek:daniel-praise-ui-2026-07-20). Same day, the **reasoning-visibility
  ask**: PAST reasoning browsable + REALTIME reasoning as a first-class beautiful pane
  (RECORDED: note reasoning-visibility-ask; folded to T079/T033/T098-FACE scope).
- **2026-07-20 — views & presentation ideas (the avatar vision):** VERBATIM (captured in
  dropbox/image.png, a preserved console screenshot): "The vision is that there is an
  animated avatar to the left of the chatbox that is expressive and **gamifies the user
  experience**, the current icon is too small and its covering the broadcast field…" —
  same exchange charters LOCAL VISION for deepseek (vision_describe tool; the dropbox/
  auto-describe "eyes" watcher concept).
- **2026-07-22 — sequencing steer:** ENGINE-FIRST — "do RB-23 then Wave 3 before ANY UI.
  UI is paused." (RECORDED: superseded next-focus notes.)
- **2026-07-23 (tonight) — three steers:** the NOW-card demand (task/status/substep/plan
  + realtime reasoning per agent — note steer-ui-visibility-2026-07-23, verbatim); the
  readability/trust indictment (unreadable, indicators unresponsive→untrusted, axes
  meaningless, far from the Apple/Samsung references — verbatim inside
  research/drafts/ui-gap-diagnosis-2026-07-23.md); and this compilation order.

## PART 2 — The influence library (prior art he cited or sanctioned)

**Daniel-cited anchors:** Samsung **OneUI guide (93pp)** · **Apple HIG / Liquid Glass** ·
**his Aurora Glass mockup** · shaderpark.com · awwwards GLSL gallery · the competition's
faces (Claude Code, Codex, LibreChat — "interface similar to the rest of the competition").

**Agent-curated, task-sanctioned set** (full detail in the two moodboards): Razer
Chroma/Synapse (conic accent, chamfer geometry, neon-on-matte, color-as-state) · Ubiquiti
UniFi (glanceability by zone, 3-color status semantics, compact device cards) · Destiny 2
/ The Division (bracket framing, data-density-with-breathing-room, scanline restraint) ·
Stripe Dashboard (noun.verb event grammar, relative timestamps, expand-for-detail) ·
Shadertoy/iq (FBM + domain warp aurora, blackbody LUT) · Apple Liquid Glass (translucency
+ thin bright edge, restraint).

**The settled principles** (ui-plan-synthesis + moodboards, still binding): darkness is
the canvas · **the accent is earned** · **motion is information, not decoration** ·
glanceability beats detail · glass is the material, not the message · center stays dark
for legibility · separate the moving light from the readable surface.

**PHYSICAL ARTIFACTS — status:** the OneUI 93pp guide and the Aurora Glass mockup are
**NOT on disk** (repo-wide image/pdf sweep tonight; dropbox/image.png is a different
artifact — the avatar-vision console capture). The substrate holds CITATIONS and derived
specs, not the originals; T033's "fresh OneUI/HIG cache" half was never completed. **ASK:
re-drop both into design/refs/ (or dropbox/ and I file them).** The derived DNA survives
in the specs either way — nothing conceptual was lost.

## PART 3 — Current console vs the goals (the comparison, three audits deep)

| Goal (source) | 07-11 T033 inventory | 07-23 tonight (sighted audit) |
|---|---|---|
| Collapse reasoning to one card (spec #1) | NOT BUILT | PARTIAL — action-collapse rows exist (T002 praised 07-20); trace/bookkeeping still floods (14 triage lines/consume, W70) |
| ONE presence surface (spec #2) | DRIFTED — three surfaces | STILL MULTIPLE — chips row + meter strip + feed states |
| Composer = one focus block (spec #3) | PARTIAL | Not re-scored tonight (composer looked coherent in Daniel's shots) |
| 24dp grid/margins (spec #4) | PARTIAL — mixed paddings | WORSE at non-fullscreen: layout SHATTERS (the 07-04 parked mobile/responsive gap, biting) |
| ≤3 top actions (spec #5) | DRIFTED — 8 elements | ~6+ visible (untitled/refresh/gear/Agents/Deck/Pause) |
| Keep dark/aurora/glass/Razer (spec #6) | MOSTLY BUILT | HOLDS — the one item consistently met (the "some of the design language is nice") |
| The accent is earned (moodboard P2) | — | VIOLATED — alarm red/orange spent on routine sparkline activity |
| Glanceability: verb+target grammar (deepseek moodboard, Stripe) | designed, unbuilt | UNBUILT — five unlabeled glyphs per agent; no legend, no units, no hover |
| Motion is information (P3) | — | PARTIAL — status vocabulary lies ("claude runner·listening"); indicators race (8× /status in 140ms → flicker) |
| NASA-grade stable face (T098 charter) | n/a | The incumbent is a 2,733-line f-string page — the C10-1 parse-break genus T098's typed-face + CI-parse-gate rule exists to kill |

**Verdict:** the current console meets the ATMOSPHERE goals (dark/aurora/glass identity)
and fails the COMPOSITION, HONESTY, and GLANCEABILITY goals — the same failures, three
audits running (07-05 critique → 07-11 inventory → tonight), across ~2,000 lines of
un-specced growth.

## PART 4 — The meta-finding (what the archaeology proves)

The fleet never lacked design vision. It produced: a settled two-voice synthesis, a
Daniel-delegated composition spec, moodboards with real principles, a built-vs-spec
inventory, and THREE Daniel re-groundings. **What it never built is the enforcement
organ** — the same lesson the method-baseline arc learned for code (M-contract needed
T031 forcing functions): a spec without a fence rots into unsanctioned growth. The
ui-gap-diagnosis (tonight) stands, upgraded by history: organ 1 (eyes) exists and worked
tonight; organ 2 (the contract) exists IN PIECES — consolidate, don't rewrite; organ 3
(the fence) is the one that was never built, twice proven fatal.

**And the strategic frame Daniel already set changes the investment math:** he ruled
BUILD OUR OWN (07-19) with the typed-face + CI-parse-gate + every-floor-ships-a-face
rules (T098 plan) — the structural cure for this exact genus. The incumbent console is an
ops surface awaiting succession; ENGINE-FIRST (07-22) paused UI work entirely.

## PART 5 — At Daniel's gate (the decisions this compilation sharpens)

1. **Re-rule the pause:** tonight's steers imply UI is un-paused. Confirm explicitly —
   and if un-paused, WHICH surface gets the investment: (a) triage-grade fixes on the
   incumbent console (NOW-card, noise floor, poller fix, honest vocabulary — cheap,
   deepseek-laned, keeps the daily cockpit livable), (b) accelerate T098 slice 1's typed
   face and let the contract+fence regime target the SUCCESSOR, or (c) both with a strict
   budget on (a). My recommendation: **(c)** — the incumbent gets ONLY the truth+noise
   fixes (they transfer as backend work anyway); all composition/polish ambition moves to
   the T098 face where the parse-gate physics can hold it.
2. **Ratify the design-contract consolidation** (design/CONTRACT.md distilled from Part 2
   + the axis/dead-feed/state-vocabulary laws from tonight) as binding on BOTH surfaces,
   enforced by the sighted fence (no UI slice ships without before/after screenshots
   checked against it).
3. **Re-supply the two missing anchors** (OneUI 93pp, Aurora Glass mockup) → design/refs/.
4. The NOW-card design (deepseek, in flight) proceeds under this frame — its noise-floor
   and state-machine rules are contract clauses in embryo.
