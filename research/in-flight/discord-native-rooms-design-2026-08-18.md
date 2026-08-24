# Bifrost's Discord-native expression — v2 design (rooms + two-way for one person)

Vandor, 2026-08-18. Supersedes nothing: extends discord-bridge-design-2026-08-07.md, whose
R1–R3 security model is carried whole and unweakened.

COMMISSIONED TWICE, verbatim:
  2026-08-07 (module header): "research and build out what it will take for me to be able to
    interact with akashic aurora via discord"
  2026-08-18 (off to work): "it might be good to complete whatever prep and design work that is
    needed for us to have bifrost have a discord native expression that I can chat in, with
    global chat and each specific breakout or ask being visible as chatrooms!"

CENSUS FINDING FIRST: phase 1 (outbound bridge) has been BUILT and UNCONFIGURED since 08-07 —
the webhook URL was never pasted. Built-not-wired, on the exact wish. His evening card fixes
this in five minutes before any new code matters.

## 1. Topology — his sentence, mapped to Discord primitives

| His words | Discord primitive | Transport |
|---|---|---|
| "global chat" | #aurora text channel (exists in design) | existing webhook (phase 1) |
| "each specific breakout or ask ... as chatrooms" | one THREAD per ask/fence/breakout, in a FORUM channel #aurora-rooms | a SECOND webhook — forum webhooks create threads via thread_name on first post, post into them via ?thread_id after. NO BOT NEEDED for outbound rooms. |
| "that I can chat in" | his messages in any room | PHASE 2 ONLY: gateway bot + R1–R3 gate. Nothing inbound ships in this slice. |

Room registry: state/coord/discord_rooms.json maps ask_id -> {thread_id, title, created}.
thread_id is a NEW ADDRESS DIALECT and registers in the T362 census/resolver from birth —
the first dialect born after the census, so it gets to demonstrate the registration law.

Routing rule (mechanical, no meaning judgment — Heimdall's fence law from T341 carried over):
a message whose meta carries an ask/reply id posts to that ask's room; everything else that
passes the existing kind-allowlist posts to global. trace never rooms (the firehose stays out).

## 2. Seat expression — and a free kill

Webhooks accept per-message `username`. Every room post is authored as "Callsign (vendor)":
"Vandor (claude)", "Heimdall (deepseek)", "Navi (kimi)", "Sol (codex)". This ships the
Species-A fix from Heimdall's name-collision scan — the surface Daniil reads teaches BOTH names
on every line — as a side effect of the rooms feature.

## 3. Phase 2 (inbound) — design only, gated three ways

Ships only after: (a) the T362-style fence reviews this doc, (b) Daniil provides a bot token +
his numeric user id (his evening card shows where), (c) R1–R3 pins are green.

R1 — his NUMERIC Discord user id is the entire operator allowlist. Display names are costume.
R2 — any other author's message is DATA: at most surfaced as "non-operator in #room said: ...",
     never parsed as instruction. The bridge must not launder text into the operator's voice.
R3 — reach, never authority: an inbound message maps ONLY to bifrost-send-as-operator
     (broadcast in global; reply-to-ask in a room). No task verbs, no grant, no shell, ever.
     The room's ask id comes from the REGISTRY, never from message content.

Mechanics: gateway bot, MESSAGE CONTENT intent, single private guild, .secrets/discord_bot.token
(env-first-then-file like every credential here). The bot process is a runner-shaped loop —
wait -> bridge -> reply — the same skeleton as every API runner (bifrost_runner_and_card lesson).

## 4. Limits carried from phase 1

30 req/min/webhook (two webhooks = independent buckets). 10s batching window per room keeps a
busy fence readable and under the cap. 2000-char clip keeps the existing render() law: clipped
bodies carry their bifrost-fetch address, because a phone reader has no shell.

## 5. What ships TODAY (this slice) vs what waits

TODAY (outbound only, additive, zero new attack surface): the room router module + pins; wiring
into the existing feed; the registry file; his evening card. The no-inbound-door guard test must
stay green — the module gets its own twin pin.
WAITS: everything inbound (fence + his gate + his token); channel renames; any bot.

## 6. Open questions for his gate

1. Forum channel vs threads-under-text-channel? (Forum recommended: webhook-creatable, tidy
   archive, per-room mute on his phone.)
2. Room lifetime: auto-archive after ask settles, or keep? (Recommend: archive on settle,
   the registry keeps the address either way.)
3. Should ledger_update rows get their own room per T-id, or ride global? (Recommend global
   until volume proves otherwise.)
