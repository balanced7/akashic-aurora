---
akashic_id: art_20260709_aurora-glass-composition-spec-single-sou_27005e
akashic_sha: 0566d10f8b1a
status: current
type: design
date: 2026-07-09
title: Aurora Glass — Composition Spec (single source of truth)
gist: "_Authored by claude 2026-07-05, decision delegated by Daniel as a coordination test. Grounded in the OneUI guide (93pp), Apple HIG, and Dani"
tenant: solo
visibility: fleet
seats: []
category: [memory, coordination, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260709_aurora-glass-composition-spec-single-sou_27005e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Aurora Glass — Composition Spec (single source of truth)

_Authored by claude 2026-07-05, decision delegated by Daniel as a coordination test.
Grounded in the OneUI guide (93pp), Apple HIG, and Daniel's Aurora Glass mockup. Every agent
building UI reads THIS and builds to it. Ship in small slices, commit, claude reviews each._

## The problem (from Daniel's screenshot)
The cockpit is DARK + functional but **assembled, not composed** — too many surfaces competing:
3 "thinking" status rows + separate thinking bubbles + a wall-of-text log + dim trace lines + a
garbled gradient recipient bar. OneUI's core lesson is **restraint**: group and CUT.

## Restraint decisions (claude's calls — these are the cuts)
1. **Collapse reasoning/traces.** 💭 thinking + 🔧 tool traces must NOT stream as a wall. Group
   consecutive traces per agent into ONE collapsible "reasoning card" — collapsed by default to a
   single line (`💭 deepseek reasoning · 6 steps ▸`), expand on click. This is the #1 declutter.
2. **One presence surface.** Keep (a) message-bubble avatars and (b) the compact composer-docked
   presence avatar. **REMOVE** the redundant top "agent thinking" status rows and the separate
   floating "thinking • • •" bubbles. Who's-doing-what lives in ONE place.
3. **Composer = one focus block.** The fidelity ladder + recipient selector + input + send collapse
   into ONE rounded glass container (OneUI focus block), not scattered elements. Kill the garbled
   full-width gradient bar; the recipient becomes a small agent-icon selector inside the block.
4. **Grid + margins.** 24dp min margins, consistent 8/16/24 spacing, everything aligned to the
   centered 1180px column.
5. **Hierarchy.** One prominent title ("Bifrost / live agent console"), ≤3 top actions, calm log.
6. **Keep:** the dark base, subtle aurora (top bands only), the Void theme option, glass material
   (`blur(26) saturate(1.35)`), Razer chamfer + the glow on the active fidelity segment.

## Lanes (one owner per file/area — no collision)
- **deepseek-plumbing** → `scripts/bifrost_ui.py` (SOLE owner for this pass — one owner per file):
  reasoning-card collapse (#1) + composer focus-block (#3) + recipient/garble fix + remove top status
  rows (#2) + 24dp grid/margins (#4) + hierarchy (#5). All in-file work is yours; nobody else edits it.
- **claude** → design LEAD: this spec + REVIEW every plumbing slice against it + the mockup + owns the
  standalone visual modules (`presence-cloud.js`, `presence-rail.js`, `theme-void.js`, `aurora-shader.js`)
  and iterates them if review finds gaps. Does NOT edit `bifrost_ui.py` during the pass (zero collision).
- **deepseek** (main) → `core/comm/context_hints.py` + runners (its current work) — NON-UI, no collision. Stay.
- **deepseek-ui** → read-only design review (its role); hand lessons to claude/deepseek to persist.

## Sequence
plumbing ships a slice → commits → reload → claude reviews vs spec + Daniel eyeballs → iterate.
claude builds reasoning-cards in parallel (standalone, no collision). No agent edits another's file.

## Definition of done
A stranger glances at the cockpit and it reads CALM: one title, one presence surface, a tidy log
with collapsed reasoning, one composer focus-block. Nothing competing. Matches the mockup's composure.
