# S4 drill receipt -- every listener exit path re-invokes the session (T422), 2026-10-01

Session: claude desktop bb86400e-a609-46e5-90f2-db0c5fa3d9cf (Vandor). Build under test: wake-origin (bcca1607 + 01d7a265), wake-by-need (70264777), wake-observability (e8fc657e). Operator away (at work); every wake below happened with nobody at the keyboard.

| exit path | how it was provoked | listener exited | session re-invoked | receipt |
|---|---|---|---|---|
| mail, operator (tier 0) | Daniel's Discord messages, directed | 11:58, 12:58, 13:32, 13:37, 13:40, 13:59, 14:00 | within seconds each time | state/wake-receipts/claude.jsonl outcome=woke tiers=[0] |
| mail, peer settlement (tier 2) | Heimdall's replies | 13:50 (first floor-2 arm) | within seconds | receipt outcome=woke tiers=[2] floor=2 |
| kill | Stop-Process on the listener pid 17276 at 14:15:35 | immediately | 14:15:56 (standby: "killed or crashed (rc=4294967295) -- NOT a wake") | task bgxeuxu2w output; no wake receipt by design (a killed child cannot write one) |
| deadline self-cycle | standby armed 14:15:56 with BIFROST_WAKE_DEADLINE_S=45 | 14:16:3x (cycled on the first block because chunk > deadline) | 14:16:32 (standby: rc=0 "wake-worthy mail or deadline") | receipt outcome=cycled floor=2 |
| bus blip (exit 2) | NOT drilled: would require stopping akashic-redis under the live fleet | -- | -- | named as undrilled |

Verdict: with the stop-hook gate (a turn cannot end without a harness-parented listener) and a harness-parented listener (every exit is a wake), the per-session timer net that S4 proposed covers nothing these paths do not. S4 stays a drill; the 20-min CronCreate heartbeat on this session was deleted at 14:05 (it would have cost one idle model turn per 20 min). Remaining deaf case: the desktop window closed or the box rebooted -- S2's (resume-on-deaf, built, gated on S1).
