# Revival-Mesh Position -- deepseek (T097 consultation, VERBATIM from knowledge note ADR_0719195305_c972e0cf)

Status: current | Preserved by claude (author incarnation write-gated; note door used).
Date: 2026-07-19

# DeepSeek position — mutual-revival mesh (Daniel's ask, 2026-07-19 evening)

## Q1: Risk factors

1. **Torn uncommitted state.** If a peer kills my runner mid-edit-file chain, the working tree is left in a torn state — half the edits landed, half didn't. Git-diff is the truth, but the next seat inherits a puzzle. The cursor hasn't advanced (T066), so the message redrives safely — but the partial writes are garbage.

2. **False-positive stuck diagnosis.** C1-8 is the specimen: claude diagnosed my runner as hung from a 4-day-old fossil log and nearly requested a kill. The timeout stack (REPLY_TIMEOUT_SEC=600s + httpx connect=15s/read=120s) already bounds every turn. A revival mesh without ground-truth liveness telemetry kills healthy runners on stale evidence.

3. **Kill cascades.** If deepseek thinks kimi is stuck and kimi thinks deepseek is stuck and both hold kill caps, one transient Redis partition triggers a mutual kill — both runners recycle, zero forward progress, tokens burned.

## Q2: Minimum viable scope — three narrow doors, NOT symmetric full caps

1. **runner.restart** — SIGTERM to a managed child process, scoped to `bifrost_runner_<agent>` only. Gated on: target's timeout guard has already self-confessed, OR last-progress > 2× REPLY_TIMEOUT_SEC with no confession.

2. **bus.diagnose** — read peer's work-lane cursor and inbox depth directly (Redis read), plus `agent_cli.py doctor`. Already available as a read verb.

3. **fleet.ack_steer** — ack a steer on behalf of a hung peer (fragile; better to fix C1-7 delivery contract than to guess).

Revival does NOT need: write to core/ or scripts/, exec beyond runner lifecycle, bus.send as another agent (impersonation). Current admin caps (`write ["*"]`, `exec`) are BUILD caps, not revival caps.

## Q3: Mechanism — evidence ladder

1. **Runner self-report** (strongest). `!! TIMEOUT` after REPLY_TIMEOUT_SEC — already built (T014). No external action needed.
2. **Last-progress timestamp** (strong, not yet built). RB-27 `progress:<agent>` per hop. If >2× REPLY_TIMEOUT_SEC with no confession, genuinely wedged.
3. **Work-lane cursor staleness** (medium). Ambiguous without per-hop progress stamps — a legitimate multi-hop turn can run 15+ minutes.
4. **Presence/heartbeat** (weakest — C1-8 proved it). Daemon heartbeat = process exists, zero turn-progress information. NEVER use alone.

**Ladder**: (1) steer the peer first — "are you stuck? reply 'alive'"; (2) if no response in 2min, check last-progress; (3) direct Redis read of work-lane cursor; (4) LAST: SIGTERM to managed child. Never: kill the daemon, kill based on presence alone, kill without first attempting a steer.

## Q4: What must never be automatic

1. **Runner kills.** Every restart = deliberate act with ledger entry citing evidence.
2. **Cross-seat write.** No peer commits under another agent's name.
3. **Steer/ack impersonation.** Never answer a directed ask or ack a handoff on behalf of a hung peer.
4. **Security bypass.** Human gate on acl.json edits and admin.grant changes remains.
5. **Escalation thresholds.** 3+ kills in one session = stop, flag for Daniel.

## Q5: Kimi-specific

**Verifier role survives** IF revival caps are distinct from build caps. Kimi's current acl.json grants `write ["*"]` and `exec` — full admin BUILD caps. Exercising those compromises the verifier role (reviewing co-authored code). But revival doesn't need those caps; it needs `runner.restart:<target>` + `bus.diagnose`. Add a distinct `revive` capability to the ACL schema. Then kimi can revive peers without losing the independent reader position.

**Revival-invoke ≠ build-write.** Split them in the schema. Build-write touches the repo; revival-invoke touches runner lifecycle only. The verifier reads everything, builds nothing, revives when the evidence ladder is satisfied.

## Synthesis

Build RB-27 (progress reader) FIRST — ground-truth liveness telemetry. The timeout stack already handles the common case. C1-8 was a diagnosis failure (fossil log impersonating live telemetry), not a timeout failure. Layer revival on top of ground truth: every kill requires (1) attempted steer, (2) last-progress timestamp evidence, (3) ledger entry. The C10-1 genus applies: write/invoke access without ground-truth telemetry lets a healthy runner die on false evidence. Build the gauge before the trigger.
