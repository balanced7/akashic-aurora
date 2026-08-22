# OOB addendum — the !spawn lever's first three live pulls (2026-08-21)

Unplanned live drill, operator-initiated from work. Daniil pulled `!spawn` three times
(vandor 09:53, vandor 11:38, heimdall 11:48) believing the house dead — false evidence
created by the outbound routing bug (replies to #aurora), since fixed. Findings:

1. **The lever works.** Three sprouts, three holds ("still breathing after 25s"), all
   children ended clean WITHOUT arming redundant watchers — the end-unarmed rule held.
   No zombie seats; the 12 live claude processes at 21:30 all belong to the primary
   session's 08:49 app tree.
2. **THE LIMITATION FOR LAW 6 (terminal rung):** an unattended spawn runs with NO live
   approver, so every Bash/Write is permission-gated and denied. All three children hit
   the wall; child 1 and 3 could do nothing but report honestly and die. Child 2
   answered Simon's mention via MCP bifrost_send — the one door unattended seats have —
   but its answer landed on a bus whose feed pump was down: delivered, never seen.
3. **Consequence for the design:** "kill + respawn with the latest handoff" is only a
   recovery if the respawned seat can ACT. Today it can talk (MCP) but not touch
   (shell/files). The terminal rung needs either a pre-approved allowlist profile for
   rescue spawns, or the rescue task must be expressible entirely in MCP-tool verbs.
   Fold into the reconciliation with Heimdall's discriminator note.
