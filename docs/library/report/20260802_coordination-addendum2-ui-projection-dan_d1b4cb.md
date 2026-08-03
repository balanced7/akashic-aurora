---
akashic_id: art_20260802_coordination-addendum2-ui-projection-dan_d1b4cb
akashic_sha: cd5c2cfb7dd8
schema_version: 1
status: current
type: report
date: 2026-08-02
title: coordination-addendum2-ui-projection-daniil
gist: "# Addendum 2: the UI projection — sensors rendered as light Status: current (2026-08-02, claude#30e6af5c). PROJECTION LANE per the two-speed"
visibility: fleet
body_type: markdown
seats: []
category: [substrate, bus, coordination]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-02T21:32:45"
updated: "2026-08-02T21:32:45"
---
<!-- GENERATED PROJECTION of art_20260802_coordination-addendum2-ui-projection-dan_d1b4cb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# coordination-addendum2-ui-projection-daniil

# Addendum 2: the UI projection — sensors rendered as light

Status: current (2026-08-02, claude#30e6af5c). PROJECTION LANE per the two-speed rule
(WORKING-METHOD.md Part 1b): fence-LITE, gated on whether Daniil can SEE it — kimi's
gateway review ruled this split explicitly (capture = substrate, renders = projection).
Rides the same reconciliation gate as the main design + addendum 1. Cannot render real
data until the sensor hash (substrate slice 1) exists.

## Daniil, verbatim

"all of these sensors will be able to pipe information into the ui so I can understand
from the api level what is going on with each AI as well as its reasoning. for the ui we
could do colors to signify reasoning level, token rate, task status. the agents working
could glow blue or green when its not 0."

## Visual grammar: three channels, three data families

HUE = CODEBOOK STATE, computed at read time, never stored: composing=blue,
tool-running=green, idle=dim neutral, wedged=amber, throttled=red-violet shift,
truncation (finish_reason=length) = a discrete flash event. The pixel IS the diagnosis.

GLOW INTENSITY = RATE: brightness proportional to tokens/sec (Daniil's "not 0" made
continuous). REASONING LEVEL from the gateway's separately-countable reasoning vs content
chunks: thinking-heavy tints violet, output-heavy tints green — deliberation vs production
visible per agent, live.

BADGE/CHIP = TASK STATUS from the standing: claimed / round N of M / heads-down (turns
left) / concluded. Discrete, not a glow — status is a fact, not an intensity.

## Honest-rendering laws (each kills a failure class measured tonight)

1. BRIGHTNESS DECAYS WITH SIGNAL AGE. Luminance derives from last_chunk_at recency; a
   glow can never freeze at its last state. A frozen green glow on a dead agent is the
   ghost page in pixels (F5 class). Death = watching a light fade. Unrepresentable, not
   guarded.
2. UNSENSED IS A COLOR, NOT DARKNESS. gateway_coverage=unsensed renders visibly (hatched
   grey-violet), same alarm tier as wedged, never as calm idle (kimi's coverage law at
   the pixel layer; otherwise the UI is born with the roster's disease).
3. EVERY NUMBER WEARS ITS AGE (T120 at the dashboard): rate/spend/state chips carry
   their staleness.
4. PER-SEAT SPEND METER: wallet state as a filling bar (receipt: kimi past its warn line
   was discovered in a log tail tonight; Daniil steers budgets by hand and could not see
   them).
5. Reasoning stream excerpt per agent panel: EXISTS (live trace feed, 2026-07-04) — this
   addendum recolors and reframes it, does not rebuild it.

## Division of labor (ratified boundary, unchanged)

claude: backend feed — sensor hash -> SSE/poll endpoint + snippets. deepseek: owns
bifrost_ui.py integration and wires the render. deepseek-ui: design consult — the
blue/green must sit inside the ratified Aurora Glass analogous palette
(indigo/periwinkle/violet family) and the MEASURED 60fps motion budget
(design/CONTRACT.md v1); glow-pulse animation fits the budget, never fights it.

## Sequencing

Blocked on substrate slice 1 (the sensor hash) for real data. Everything else —
palette mapping, decay curve, panel layout — can be designed and even mocked against
recorded sensor data from the probe battery's wire captures as soon as they land.
