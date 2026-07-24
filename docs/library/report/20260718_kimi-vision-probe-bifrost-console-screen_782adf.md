---
akashic_id: art_20260718_kimi-vision-probe-bifrost-console-screen_782adf
akashic_sha: a7f2bb677881
status: draft
type: report
date: 2026-07-18
title: Kimi Vision Probe — Bifrost Console Screenshot (2026-07-18)
gist: "# Kimi Vision Probe — Bifrost Console Screenshot (2026-07-18) **Probe:** protocol step 4 of `research/briefs/kimi-k3-blind-walk-protocol-202"
tenant: solo
visibility: fleet
seats: []
category: [bus, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260718_kimi-k3-blind-boot-ergonomics-walk-proto_6b1c4b
    rel: cites
created: "2026-07-18T13:09:29"
updated: "2026-07-23T21:42:20"
---
<!-- GENERATED PROJECTION of art_20260718_kimi-vision-probe-bifrost-console-screen_782adf -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Kimi Vision Probe — Bifrost Console Screenshot (2026-07-18)

# Kimi Vision Probe — Bifrost Console Screenshot (2026-07-18)

**Probe:** protocol step 4 of `research/briefs/kimi-k3-blind-walk-protocol-2026-07-18.md` —
validate kimi-k3's eyes end-to-end on the live fleet console.
**Source image:** `scratch/bifrost-ui-dashboard-2026-07-18.png` (headless Chrome capture of
http://127.0.0.1:8787, ~13:10 EDT per the brief; file mtime 13:05 local).
**Eye status:** IMAGE LOADED AND READABLE. The eye-test itself PASSES — what follows is only
what is visibly on-screen.

Honesty tags: **VERIFIED** = visibly on-screen · **INFER** = reasoned from visible evidence ·
**GUESS** = flagged speculation.

---

## 1. Layout — panels/regions

**VERIFIED:** Four horizontal regions, dark theme, one floating rounded-corner console panel:

1. **Header bar** — left: gradient square logo + "Bifrost" + "live agent console" + a
   green-olive status dot. Center: green circular "U" avatar, "user" with a green "ONLINE"
   pill, subtitle "steering". Right: buttons "episode" (monitor icon), a refresh icon, a gear
   icon, "Agents", "Deck", "Pause".
2. **Presence strip** — a grid of ~12 small chips (agent names + status dots + tiny
   sparkline-like tick marks), three of which end in a green checkbox + the word "reconciled".
3. **Main canvas** — a very large, almost entirely EMPTY dark area. One small circular
   hexagon-ish icon floats at the left edge, mid-height (GUESS: a collapsed rail or floating
   action button; it has no label).
4. **Bottom compose bar** — three mode tabs "Inform / Steer / Interrupt" ("Steer" appears
   outlined/selected), a "Broadcast · 0 agents" pill, a text input ("Message the agents…
   (Enter to send, Shift+Enter for newline)"), a gradient send arrow, and a legend line:
   "Inform = adopt next turn · Steer = fold into current task (no stop) · Interrupt = drop &
   switch · Pause = freeze everyone · Ctrl+V paste images or drag & drop files".

**INFER:** this is a steering console first (compose bar + steering modes + user chip saying
"steering"), with monitoring (presence strip) as a secondary readout.

## 2. Fleet presence

**VERIFIED (chip-by-chip, dot color as rendered):**

| Chip | Dot | Extra |
|---|---|---|
| CLAUDE | green | tick marks incl. a red bar |
| DEEPSEEK | green | tick marks incl. a red bar |
| DEEPSEEK-PLUMBING | gray | ticks |
| DEEPSEEK-RED | gray | ticks |
| DEEPSEEK-REVIEW | gray | ticks |
| DEEPSEEK-UI | gray | ticks |
| KIMI | **gray** | ticks |
| SOL | gray | ticks |
| SOL-CODEX | gray | ticks |
| CAPABILITY-SURFACE | green | ✅ "reconciled" |
| ENGINE-ROOM | green | ✅ "reconciled" |
| PRESENCE-AUTOPILOT | (no dot visible) | ✅ "reconciled" |

Plus the human: "user — ONLINE — steering".

**INFER:** green dot = live/online, gray = offline/idle. **Anomaly:** KIMI renders GRAY while
the system believes three agents (claude, deepseek, kimi) are online — but this kimi seat
booted at 13:06:08, i.e. ~1 min AFTER the capture; at capture time the previous kimi presence
may have legitimately been stale/absent. Borderline, not a proven bug.
**INFER:** CAPABILITY-SURFACE / ENGINE-ROOM / PRESENCE-AUTOPILOT are subsystem health checks,
not seats — but they sit in the SAME visual row as agent chips, undifferentiated.

## 3. Activity — queues, lanes, gauges, traffic

**VERIFIED:** NONE visible. No lane depths, no queue counts, no gauges, no message feed, no
reasoning/trace stream, no timestamps, no "last updated" anywhere on screen.
Each chip carries a tiny strip of dots/bars (some green dots, some red vertical bars) —
**GUESS:** recent-event sparkline; semantics unlabeled and undiscoverable from the screen.
**VERIFIED:** "Broadcast · 0 agents" — with multiple agents online, the broadcast target count
reads 0. INFER: agents must be selected before broadcast; the default target is nobody.

## 4. Anomalies (system believes itself healthy: redis LIVE, ui LIVE, 3 agents online)

1. **Top-left corner artifact (VERIFIED):** a saturated thermal-looking blob (pink/purple/
   green smears) bleeds across the top-left viewport corner, OUTSIDE/overlapping the console
   panel's rounded corner. INFER: the aurora/void-theme background effect rendering partially
   or mis-clipped — as rendered it reads as a graphics glitch, not ambience.
2. **Empty main canvas (VERIFIED):** the largest region of a "live agent console" shows
   nothing — no empty-state copy, no hint what belongs there. INFER: no episode selected or
   feed collapsed, but the screen never says so.
3. **KIMI gray while counted online (VERIFIED dot; INFER cause)** — see §2; possibly a
   capture-timing artifact (this seat booted after the shot), worth a re-capture to resolve.
4. **Unlabeled sparkline semantics (VERIFIED):** red bars appear even on green/online chips
   (CLAUDE, DEEPSEEK) with no legend — a newcomer cannot tell error from activity.
5. **No freshness signal (VERIFIED):** a console claiming "live" shows no clock, heartbeat
   age, or data-as-of time; staleness would be invisible.
6. **Mixed entity kinds in one strip (VERIFIED):** seats and subsystem checks share one grid
   with no grouping or section header.

## 5. Newcomer's eye — the three changes I'd want first

1. **Empty-state copy on the main canvas** ("No episode selected — pick one above" / "Agents
   idle — no live feed"). The void is the screen's biggest element and it explains nothing.
2. **A presence-strip legend + grouping:** say what green/gray dots and red sparkline bars
   mean, and split seats (CLAUDE, DEEPSEEK, KIMI…) from subsystem checks (CAPABILITY-SURFACE,
   ENGINE-ROOM, PRESENCE-AUTOPILOT) into visibly separate groups.
3. **Fix the top-left aurora artifact:** full-bleed it subtly or remove it — in its current
   clipped, saturated form it reads as a rendering bug on first sight and undermines trust in
   every other pixel.

---

**Probe result:** EYES WORK — image loaded, panels/agents/anomalies described from pixels
alone. Filed by kimi (ephemeral vision-probe seat), 2026-07-18 ~13:1x local.
