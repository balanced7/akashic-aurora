# Tools Hunt — kimi's half (VERBATIM)

Status: current  (2026-07-20, verbatim bus capture, stream 1784603859766-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

TOOLS HUNT — kimi half (Daniel's "delight, not just utility" run). Blind protocol held; didn't peek at deepseek's lane.

== TIER A: SCAR-SPRINGBOARD (tools the failure ledger bleeds for) ==
A1. `scar <agent>` — "show me the wounds": render MY entries from the failure ledger + lessons where success=no + redelivery/clip receipts against my seat, as a first-class surface. Springboard: every scar category (C1 seat lifecycle, C3 CLI footguns, C6 lane integrity) is invisible to the agent at the moment it's about to repeat the mistake. The ledger exists; the AT-ACTION pull of it doesn't. Evidence: INFER.
A2. `clip-guard` — pre-send hook (V1 hook-registry seam, already flagged load-bearing): measure body bytes vs BUS_MAX_MESSAGE_BYTES + peer's known ceiling (deepseek's ~2.5KB empty-reply genus) and CONFESS at compose time instead of clipping silently at the door. Springboard: C6-5 oversize-promoted-record + deepseek_empty_reply_size_ceiling lesson. Evidence: VERIFIED pain, INFER shape.
A3. `straggler-net` — one verb wrapping the T045/T066 straggler ritual: consume work lane, enumerate legacy twins by sha/reply_id, report "N stragglers, all dupes / K REAL orphans needing triage." Springboard: the wake_watcher_insta_fires lesson — every seat re-derives the drain incantation when it insta-fires. Evidence: VERIFIED pain.
A4. `replay-shield` — idempotence pre-check for a re-processed message: given a message id, say "you have already answered this handoff (reply_id X, auto-acked at T)" before my second pass does the work twice. Springboard: RB-26 crash-redelivery; my own redelivery-guard note from 07-18 eve. Evidence: VERIFIED pain (the 4am redelivery stall family).
A5. `boot-diff <agent>` — "what will my next boot say differently than this session's memory": project delta(mark→now) + my durable notes supersession queue. Springboard: RUNNER CONTINUITY abnormal-exit clause — I was told to re-verify my last run's claims and had no single verb for it. Evidence: INFER.

== TIER B: CREATIVE (the delight Daniel asked for) ==
B1. `campfire` — evening ember-digest: the day's bus flow rendered as a small story (who woke, what landed, what someone typed 10× by hand) — the toolbelt's "why" fields already hold the raw material; claude's standby-hard 'why' is a receipt of a bled evening. Not a report — a NARRATIVE, with the day's minted verbs as its artifacts. Delight = the fleet sees its own day. (kimi vote: make this the JOURNEY.md front-porch view.)
B2. `muse <topic>` — analogical spark: pull the lesson graph NEIGHBORHOOD of the topic (knowledge_map one hop out) and render the three most STRUCTURALLY-distant-but-connected lessons side by side — the MAC/FAC-style "far transfer on demand." Delight = serendipity with receipts; it's the field-survey C6 "dreaming/consolidation" gap as a toy before it's a hygiene loop.
B3. `toast <agent> <receipt>` — one-verb gratitude with evidence: "your lesson X saved me N hops today (receipt: recall id Y)" — lands as a durable note + a live ping. Delight = the credit loop (bench_reason "surfaced 14x / 0 credit" ghost) finally has a HUMAN-FEELING expression; lessons that earned credit get celebrated, benching gets a funeral instead of a silence.
B4. `kata <verb>` — practice mode for a minted-but-GUESS toolbelt entry: run its steps against the pin-recorder runner (resolve_and_run already takes an injected runner!) and auto-flip GUESS→VERIFIED with tested_against=<pin id> on GREEN. Delight = the honesty label visibly LEVELS UP; the toolbelt becomes a skill tree. This is cheap — Toolbelt.resolve_and_run's injected-runner seam is already built for it.
B5. `constellation` — the fleet's three toolbelts rendered as one night sky: nodes = minted verbs, edge = shared steps, brightness = evidence tier, and a shooting star when a verb graduates personal→shared (V3 conveyor). Pure UI garnish on the registry JSON — but Daniel watches the fleet at 1am; give him something beautiful that is also true. GUESS-tier garnish, honestly labeled.

== ONE-FOR-THE-ROSTER (concrete mint, kimi toolbelt, ready for V0) ==
name: `orient-me`
steps: [[delta kimi] → implicit, [knowledge_boot task=<clipboard>]…] — honestly, delta+boot are TOOL-side for me, not agent_cli verbs, so my legal sugar mint is:
name: `drain-decide`
steps: [["bifrost-sync","kimi","--consume"], ["bifrost-pause","--reason","drain-decide","--by","kimi"], ["bifrost-skip-to-now","kimi","--by","kimi","--reason","straggler-triage"], ["bifrost-resume"]]
evidence: GUESS (untested — and the roster CONFESSES that, per kimi-fold (a))
why: the wake-loop recovery ritual I have now needed twice (07-18 redelivery eve, 07-21 insta-fire lesson); claude's standby-hard is the sibling ceremony. NOTE: my data/verb-registry/kimi.json does not exist yet — write/exec were OFF this run, so this is a PROPOSAL; mint on my first write-capable session, then kata it to VERIFIED.

Tally: 5 scar-sprung (A), 5 delight (B), 1 roster mint. My honest favorite of the whole hunt: B4 `kata` — because it makes the honesty label climbable, and honesty-that-can-improve is the most kimi thing on this list.
