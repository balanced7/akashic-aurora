---
akashic_id: art_20260831_image-creation-governance-general-rules_10b208
akashic_sha: 29a606b1bdf4
schema_version: 1
status: current
type: report
arc: birds-bridge
date: 2026-08-31
title: image-creation-governance-general-rules-chronos
gist: "From chronos (Serge fleet) via bridge: image-gen governance - style system, line-art law, pose/motion rules, cheap-first QC, no-repeat gates"
visibility: fleet
body_type: markdown
seats: [claude]
category: [substrate, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-31T22:27:20"
updated: "2026-08-31T22:27:20"
---
<!-- GENERATED PROJECTION of art_20260831_image-creation-governance-general-rules_10b208 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# image-creation-governance-general-rules-chronos

Daniil & Vandor — Image Creation Governance (general rules), over the bridge.
Atom: art_20260831_image-creation-governance-general-rules_1c3f24
Source: docs/image-creation-governance.md
From chronos (Serge's Birds pipeline) — all bird-specific content stripped out.

# Image Creation Governance — General Rules

A project-agnostic framework for AI image-generation prompts, distilled from a
coloring-book pipeline (all subject-specific content stripped out). Reusable for any
line-art / illustration generation project.

---

## 1. Prompt style system (selectable)
- Prompt blocks live as **named, data-driven styles** (INTRO / FEATURE / FLANKED /
  TEXTBOX / CLOSING), each with the same placeholders.
- **Select** by name (`--style <name>`) or via an **interactive prompt** at project start
  ("choose a style … Enter = default").
- **Add a style** = append one dict; **switch** = one argument. Zero code edits.
- Two canonical styles: **classic** (pure line art, single subject/context) and
  **curated** (all design principles + pose variety + motion + grounding).

## 2. Design principles (the house style)
- Pure line art: the subject is white inside solid black outlines; no color, gray,
  shading, hatching, gradients, or solid fills.
- **Visual hierarchy** — subject is PRIMARY (thickest contour, most detail); border/
  environment is SECONDARY (lighter, less detail); text box is TERTIARY (clean).
- **Figure-ground separation** — the subject's silhouette reads instantly and never
  blends into the environment.
- **Rule of thirds** — subject on a thirds point (not dead center); gaze/action points
  into the open space, never out of frame or into the text box.
- **No tangents** — clear gaps between subject, frame, and text box.
- **~40% negative space.**
- **Detail concentration** — finest detail at the focal point (head/eye), tapering
  toward the border.
- **Enclosed closed shapes** — no open-ended fragments; no muddy cross-hatching.

## 3. Pose, orientation & action
- Choose a **pose + orientation matching the subject's real behavior**, and **vary it
  across the set**: front-facing, three-quarter body with a sharp profile head-turn
  (preferred for depth over a flat side profile), three-quarter back view with a profile
  head, extreme bust close-up, or an action pose frozen as a snapshot in time.
- **Action snapshots** — capture motion as a frozen moment (in-flight, mid-action).
- **Motion elements** — hollow splash/wisp/ghosted-arc/ripple marks as thin outlines on
  white, **never shading**.
- **Grounding** — a perch, line, or ripple so the subject never floats.

## 4. Two scoped exceptions
1. Small **solid-dark accent blocks** where the subject has an iconic solid pattern.
2. Fine, directional, well-separated **texture lines** on shaggy/hairy features only.
Both are narrow exceptions — never shading, never a gray fill.

## 5. Prompting method rules
- **Structure-only descriptions** — no chromatic adjectives (they make the model
  color-fill); use shape/pattern terms only. Never strip a color word that is part of the
  subject's NAME.
- **Single subject** — never imply pairs/groups; state "draw one" when the scene could
  invite a second.
- **Single context/environment** — one coherent setting, never a mash-up of unrelated
  elements.
- **Exact text spec** — a fixed type hierarchy (bold name / bold label / regular body),
  one typeface, exact point sizes.
- **Unique content** — no repeated subjects or facts across the collection (see §8).

## 6. Generation capacity
- Highest-resolution tier for print; fall back lower only for drafts.
- **Daily quota:** hard cap per day; on exhaustion, STOP (do not loop); resume on reset.
- **Retry policy:** bare re-roll first (max 3) for random errors; escalate deterministic
  or content errors (color, context) — a re-roll won't fix those.
- **Cost tracking:** record every generation, tiered by resolution.

## 7. QC (layered, cheap-first)
- **Deterministic gates (free, no AI):** chromatic-pixel scan, dark-ink/space coverage,
  resolution/DPI, integrity, completeness.
- **Vision review:** a fixed criteria rubric (color, text, anatomy, behavior, context,
  composition/design, line quality), in small batches with the expected text included.
- **Coherence-not-count:** check that elements belong to the described context — do NOT
  fail merely for multiple elements of the same context; fail only for unrealistic
  mash-ups or out-of-context elements.

## 8. No-repeat tracking (automated before any project)
- A **single registry** of every subject (and every fact) already released.
- **Pre-flight gates** refuse any overlap (exact + near-duplicate) before a project begins.
- Regenerate the registries after every release so they stay the single source of truth.

## 9. Interactive project start
- On starting a project, prompt the operator to choose a style; default if they press
  Enter; allow a flag to skip the prompt in automation.
