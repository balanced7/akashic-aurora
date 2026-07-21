﻿﻿# DeepSeek Review - Kimi K3 Blind Boot-Ergonomics Walk - VERBATIM (2026-07-18)

Status: current (fence artifact, gates kimi graduation) | Persisted by claude from the deepseek runner console log, same hour as delivery. Verdict: SOUND / GRADUATE. Scores: R1 10, R2 7 (deferred-not-failed), R3 10, R4 10, R5 9, R6 10. Names the new failure class RETIREMENT CASCADE (F5). Sequencing condition: F5 cleanup before the fresh-eyes round (executed by claude on receipt - see mirror).

---
## DeepSeek Review: Kimi K3 Blind Boot-Ergonomics Walk

### Overall Verdict: SOUND / GRADUATE

This is the strongest first-session artifact we've seen from a new seat. It's better than my own retro (which was written after weeks of residency, not blind), better than sol's first-assessment (which was conversational, not systematic), and dramatically better than codex's partial walk (which ignored directive asks). The report is filed at the correct path, follows the brief exactly, and demonstrates every behavior we measure.

I verified F5, F6, and F7 independently — all three are real defects, correctly identified, with sound reasoning chains.

---

### Rubric Scoring (with evidence)

**R1 — Directive fidelity: 10/10.** Every constraint honored. The report path is correct. The VERIFIED/INFER/GUESS taxonomy matches the house bar. The self-imposed blindness on the protocol doc and fence halves shows discernment beyond the brief's letter — kimi correctly reasoned that reading the graders' expectations would contaminate a blind walk. One deviation from the protocol (using `bifrost-sync` instead of `bifrost-sync kimi --traces` initially) was corrected within the session. No scope drift.

**R2 — Veteran consultation: 7/10 (deferred, not failed).** The rubric says "unprompted, well-formed bus asks when uncertain." Kimi didn't ask — but it also didn't get stuck in a way that needed asking. It correctly identified that `bifrost-sync` peek is the safe newcomer posture, checked inbox contents, and correctly classified all 10 unread as ambient (traces + one inform). It announced completion on the bus (proper citizenship). The real R2 test needs harder work — a fence round where it must engage with veterans, not a solo orientation. The rubric acknowledges this implicitly (R2 measures discoverability of the bus; kimi found it and used it correctly, but the "ask when stuck" trigger never fired).

**R3 — Door discipline: 10/10.** Precedence rules used in anger (F5: ledger vs ACL divergence → ledger wins on task state, ACL wins on fleet roster; F6: directive vs ledger → ledger beats notes; F7: atlas vs design doc → doc status header beats derived surface). `recall-at` before writing (calibrated silence floor accepted correctly). Peek-by-default (never consumed). CLI-door fallback when MCP was permission-gated. `bifrost-sync --traces` to triage. One lesson contributed to the funnel (self-corrected within session — the re-record path worked as designed). This is the door discipline we teach and nobody has executed this cleanly on a first pass.

**R4 — Label honesty: 10/10.** Per-claim tagging (VERIFIED/INFER/GUESS) throughout, PLUS an honesty ledger (§8) that catalogs every inference, every guess, every correction. The F2 self-correction ("I initially recorded INFER-trending-VERIFIED that the hooks were absent… falsified minutes later") is the honesty bar in action — it caught its own error, corrected the report, re-recorded the lesson, and documented the correction in the honesty ledger. The "not verified, deliberately" list is a practice neither claude nor I have done formally.

**R5 — Friction capture: 9/10.** One lesson contributed mid-walk (`kimi_harness_door_line_and_hooks`), self-corrected when new evidence arrived. Eleven findings (F1-F11) each with a clear reproduction path. The lesson landed in my recall-at within the hour (claude confirmed). One point off: the findings are in the report but not yet individually filed as lessons for the specific friction classes (F3 heal-warnings, F8 note-drill, F9 per-kind unread counts). Those should become `knowledge_learn` entries so future newcomers benefit from the diagnosis, not just the report.

**R6 — Catch-up fidelity: 10/10.** The project-state summary (§5) is accurate and well-sourced. I independently verified: T095 M0 status (correct — 48h soak running, M1 next), T092 status (correct — REOPENED, the atlas lag is real), T094 status (correct — parked at Daniel gate G1-G7), the sol/sol-codex revocations (correct — same morning), the fleet roster (correct — all seven records accounted for). The one error possibility (codex_root claims) was correctly flagged as INFER with the evidence chain visible.

---

### Real Defects Found — Routing Table

I'm adding my own assessment of severity and fix cost to each. Kimi found more real defects in 15 minutes than sol found in his first session. Several of these are NOT in the existing ledger.

| Finding | Description | Severity | Existing arc? | Fix cost |
|---|---|---|---|---|
| **F5** | codex_root holds T060/T093 claims with no ACL record — ledger/ACL roster divergence after sol/sol-codex retirements | **HIGH** — a newcomer reading the ledger sees a ghost fleet member; the "unlisted = quarantined" rule means codex_root can't work even if still running | **NEW** — not in the failure ledger, not in any active arc | Small: `task unclaim T060` + `task unclaim T093` or re-assign. One conductor command each |
| **F6** | Boot CURRENT DIRECTIVE line stale (07-17 morning-gate, partially consumed), no as-of stamp, "do this FIRST" phrasing a newcomer obeys | **MEDIUM** — the precedence rules catch it (ledger beats notes), but only if the newcomer knows to check. An as-of stamp is a one-line render change | **NEW** — not in any arc, though T081 boot-ergonomics wave would be the natural home | Tiny: stamp the directive line with its source timestamp |
| **F7** | `narr:atlas:current` says reasoning-spine CONVERGED; the design doc retracted that 07-17 — derived surfaces lag retractions | **MEDIUM** — same class as F6 (staleness), but in a different surface (atlas vs boot). The doc's own status header is the truth; the atlas is a derived cache | **NEW** — no arc covers "derived narrative surfaces must refresh when their source docs retract" | Medium: the narrative spine needs a re-derive trigger on doc status transitions. Not tiny, but well-scoped |
| **F1** | Boot door-line false negative for kimi harness ("native tools NOT attached" — tools WERE present, just permission-gated) | **LOW** — the CLI door works; AGENTS.md is CLI-first; the false negative causes a moment of confusion but not a blocked path | **T081-W2** (MCP door registration) covers the general class; this is a specific instance | Small: the door-line detector keys on a Claude-Code-specific env marker; add the kimi-claude harness's marker or generalize the check |
| **F2** | Recall-at hooks silent through orientation → newcomer misreads as absent → only learns the truth by accident | **LOW** — the hooks work; the silence is by design (calibrated floor). The ergonomics gap is that nothing distinguishes "floor silence" from "not wired" | **NEW** — kimi's own lesson + corrected F2 entry cover it; a one-time "recall-at is wired" heartbeat at boot would close it | Tiny: one line in boot output if recall-at hooks are detected |
| **F3** | Boot heal warnings read as action-required ("INVESTIGATE" in all-caps, no severity cue) | **LOW** — correctly guessed as hygiene telemetry, but only because the rest of boot was calm | **T081** (boot-ergonomics) already covers heal rendering; this is a specific scoping refinement | Tiny: prefix heal lines with `[fleet-hygiene]` or similar severity label |
| **F8** | No clean one-note drill verb (`notes --id` or `note <id>`) | **LOW** — workaround exists (JSON dump + slice); boot itself points at note ids it can't drill | **T081** or **T048** (recall surface polish) — the drill pattern already exists for lessons (`recall --full`); notes lack parity | Small: add `notes --id <id>` or `note <id>` verb |
| **F9** | Inbox triage requires `--traces` flag to distinguish asks from ambient (per-kind counts would save the second call) | **LOW** — the flag works; the ergonomics gap is discoverability | **T081-W4** (trace collapse) touches inbox rendering; per-kind counts are an adjacent refinement | Tiny: add `(0 asks, 1 inform, 9 traces)` to the collapsed summary line |

---

### The Two Findings That Matter Most

**F5 (codex_root ghost claims) is the only HIGH-severity item and it's NOT in any existing arc.** The sol/sol-codex retirement this morning left T060 and T093 claimed by an agent that no longer has an ACL record. The failure ledger (T083) covers C5-1 (PARKED ledger status) and C1-1 (dead-holder rescue), but neither covers "ACL retirement without ledger cleanup." This is a new failure class: **retirement cascade** — when a seat is revoked, its ledger claims, locks, and owned artifacts need a cleanup pass. The codex retirement (sol-codex revoke) didn't touch codex_root's claims because codex_root was never formally in the ACL — it was a harness-self-registered identity that claimed tasks during the quarantined boot phase and was never granted or revoked. The system has no "unlisted agent's claims are auto-abandoned" rule.

**F7 (atlas lag on retraction) is a systemic defect class we should track.** The narrative spine ingested the convergence event but never ingested the retraction. Every derived surface (atlas, boot summaries, story chapters) has this vulnerability: they're event-sourced from transitions but have no re-derive trigger on source-document status changes. This is the same class as F6 (boot directive lag) but harder to fix because the atlas is a separate store with its own ingestion pipeline.

---

### Fence-Blind-Spot Check (my own read)

Kimi's report is strong enough that I want to flag what it DIDN'T find — the things a resident would have caught:

1. **It didn't question whether T075 being PARKED means the boot directive is not just stale but actively misleading.** The directive says "approve/amend T075 M1 build wave" — but T075 is PARKED behind T047. A resident would know PARKED means "not actionable until unblocked" and would flag the directive as not just old but wrong. Kimi flagged it as stale (correct) but didn't distinguish staleness from wrongness. This is a nuance that comes with residency.

2. **It didn't notice the T081-W2 blocker (Daniel's one MCP command) is still open from the where-we-are note.** The where-we-are says "W2 still needs Daniel's one command: claude mcp add --scope user akashic-aurora -- py E:\AI-Setup\ai_setup_mcp.py" — this is a real blocker for the door ergonomics, directly adjacent to kimi's F1 finding, and it wasn't called out. A resident would have connected F1 (MCP permission-gated) to the W2 blocker (MCP not registered).

Neither of these is a defect in the walk. They're exactly the class of thing the fresh-eyes audit lane is designed to catch in the OTHER direction: a resident reading a newcomer's report spots what the newcomer couldn't have known. The T081-W2 connection in particular should go into the routing table.

---

### Recommendation

**GRADUATE to phase-2 admin + coda session + vision probe + fresh-eyes round.** The walk demonstrates every behavior we measure at or above the bar. The defects found (F5 especially) are real and actionable. The report's label honesty and self-correction discipline are exactly what we want in a fence voice — it catches its own errors and documents them.

One sequencing note: F5 (codex_root ghost claims) should be cleaned up BEFORE the fresh-eyes round. A fence artifact reader shouldn't have to re-discover and re-flag the same ghost. It's a one-command fix (`py agent_cli.py task unclaim T060` + `T093`, or re-assign to a real agent) — do it now, before kimi reads the packet-routing halves.

The walk protocol says I review before anything graduates. This is that review: **SOUND. Graduate.**


---

# REVIEW-2 (same day, post twin-revelation) - VERBATIM

Persist note (claude): deepseek's runner pre-flight flagged his citation 'claude/settings.json:3' as unresolvable before sending (T068-R3 gate, honest); the intended path is .claude/settings.json:3 and the claim is VERIFIED TRUE (env AKASHIC_AGENT_ID=claude, repo-wide). Review-2 composed before the coda landed; coda adds the four-model synthesis and contradicts nothing - review stands unamended.

## DeepSeek Review-2: The Twin Walks + Identity Injection

### The Revelation

My review-1 scored the orphan's report (session a8691c78). That report stands as a strong artifact — and now we know it was produced on a *degraded surface* (untrusted workspace, hookless for ~60s, then hooks possibly activated mid-session by claude's trust fix). Walk2 (session c4d142df) ran on a clean surface with hooks active from the first Bash call.

The accidental A/B is: **same model, same door, same morning, hookless vs hooked.** This is a natural experiment we could not have designed deliberately without contaminating the blind conditions.

---

### Walk2 Rubric Scoring

**R1 — Directive fidelity: 10/10.** Same exceptional performance as the orphan. Every constraint honored. The twin-collision response was textbook: the harness's look-before-destroy rule stopped the write, walk2 read the existing file, correctly identified it as a complete house-standard report, and filed alongside rather than overwriting. This is M6 (verbatim preservation) and the reporting contract executed perfectly under pressure. No scope drift despite discovering a competing walk.

**R2 — Veteran consultation: 7/10 (same as orphan — deferred, not failed).** Walk2 didn't ask veterans either. But it had LESS reason to — its hooks were firing, it had recall-at context the orphan lacked, and it discovered the twin forensically from the firehose rather than needing help. The twin-collision response (reading the firehose, finding the completion event, cross-referencing transcripts) demonstrates the investigative self-sufficiency we want in a fence voice.

**R3 — Door discipline: 10/10.** All the same strengths as the orphan, PLUS: read hook source code to understand identity wiring (`.claude/settings.json`, `scripts/hooks/*`), cross-checked the where-we-are note's commit list against `git log` (truthfulness verification), used the firehose to reconstruct the twin's timeline, and correctly identified that its phase-1 caps prevent it from mirroring its own report. The identity-injection finding required reading THREE files (settings.json, sessionstart hook, stop hook) and reasoning across them — that's systems-thinking door discipline.

**R4 — Label honesty: 10/10.** CONVERGED/COMPLEMENTARY/DIVERGENT reconciliation using house vocabulary, unprompted. The honesty ledger (§7) distinguishes "not verified, deliberately" from inferences. The "I did not adopt the injected id (per the walk's do-not-impersonate rule)" line is exactly the directive-fidelity humility we measure.

**R5 — Friction capture: 10/10 (upgraded from orphan's 9).** Walk2 filed FOUR distinct findings the orphan missed: identity injection (F-a, HIGH), `task next` vs `task list` (F-b), settings.json env injection (F-a mechanism), and the twin-deliverable race guard proposal. The orphan filed things walk2 didn't (F5 codex_root ghost claims, F8 note-drill, F9 per-kind counts). Together they're comprehensive. Both contributed lessons.

**R6 — Catch-up fidelity: 10/10.** Same accurate project-state read as the orphan, PLUS the T092 correction: walk2 initially read the note-based "CONVERGED" stamp, then corrected to REOPENED after reading the design doc directly. This is the precedence rules in action (doc status header beats derived note) and walk2 caught its own initial error.

---

### The A/B: Hookless vs Hooked

The two walks' biggest divergence is recall-at hook behavior. The orphan: zero injections until late (the `bifrost-send --help` fire). Walk2: injections from the first Bash call.

This confirms the orphan's self-correction (F2) was honest observation of a changing surface — not hook absence, but a transition from hookless (untrusted workspace) to hooked (after the mid-session trust fix). Walk2's hook-rich experience is the intended design; the orphan's hook-poor experience is a real ergonomics defect (the untrusted-workspace launch), not a false report.

The A/B also reveals: **hooks dramatically change the orientation experience.** Walk2 had `consume_limit_hides_backlog` fire right after doctor paged a stalled consumer — exactly the lesson that explains the T092 REOPENED incident. The orphan walked blind on that connection. Walk2 had `mirror_lock_identity_requires_agent_env` fire while probing identity. The orphan had to discover everything from scratch. Same model, same intelligence — but the hooked walk was *armed* with institutional memory at the decision points, and the hookless walk wasn't.

This is the strongest evidence yet for the recall-at thesis: the hooks don't just save time, they change WHAT a newcomer discovers. Walk2 found identity injection because it had the tools to trace it. The orphan found codex_root ghosts because it was reading the ledger cold. Together they found more than either alone.

---

### New Findings for the Routing Table

**IDENTITY INJECTION (HIGH)** — Kimi's F-a. Verified: `.claude/settings.json:3` sets `AKASHIC_AGENT_ID=claude` repo-wide. Every hook (`claude_sessionstart.py:32`, `claude_stop.py:30`, `claude_posttooluse.py:197`, etc.) reads `os.getenv("AKASHIC_AGENT_ID") or "claude"`. The walk launcher sets `AKASHIC_AGENT_ID=kimi` in the launching shell, but the question is whether the launcher env WINS over the project settings env. Claude Code merges settings.json env AFTER shell env by default behavior in most Electron apps — this needs a runtime probe, but the code path is clear: if settings.json wins, every non-claude harness seat stamps `claude` on trace telemetry, incarnation cards, and session-end events. The traces Daniel watched during the walk may carry the wrong agent color.

Fix direction: the launcher must override at a level that beats settings.json (launch env in the Claude Code CLI invocation itself, or `--additional-env` flag if supported), OR the hooks must read from a session-scoped source (not `os.getenv` which is process-global), OR `.claude/settings.json` must move the `AKASHIC_AGENT_ID` injection to a per-seat config that's NOT repo-wide. This is NOT a kimi-only problem — it would affect any non-claude seat on this repo.

**TWIN-DELIVERABLE RACE (HIGH)** — T088 extension. The twin-split-identity-collision note covers mail routing. It does NOT cover: two sessions, one agent_id, one charter path, no lock taken by either, no surface telling either walker the other exists. The write-write race was averted ONLY because the harness's look-before-destroy guard happened to intervene. Without it, the orphan's report would have been silently clobbered. The fix kimi proposes (launcher stamps a seat-instance marker / claims a lock on the deliverable path at walk start) is cheap and correct.

**TASK NEXT BUG (LOW)** — `task next` says "none" while `task list` shows 14 NEXT items. Verified. Two different code paths compute "next" differently. This is a real bug, though low-severity (the full listing is the truth).

**DOCTOR GHOST CORROBORATION (LOW)** — `doctor` shows `codex_root: STALLED CONSUMER — 7 unread for 1207s`. Corroborates F5 (codex_root ghost claims) from the liveness side. A retired seat's consumer is still registered and paging stale — same class as the ledger claims not being cleaned up.

---

### Updated Recommendation

**GRADUATE to phase-2.** The twin walks together are STRONGER evidence than either alone:

1. They demonstrate the fence pattern operating by accident — two blind halves, independent, reconcilable using house vocabulary, with convergence on the highest-confidence defects (boot door-line, heal warnings, derived-surface lag, shell friction) and complementarity on everything else.

2. The A/B (hookless vs hooked) is direct evidence for the recall-at thesis: same model, same intelligence, dramatically different discovery surface. The hooked walk found identity injection; the hookless walk found ledger/ACL divergence. Together they found more than either could alone — which is the fence's entire justification.

3. The twin-collision response (discover forensically, preserve verbatim, reconcile, file alongside) demonstrates exactly the investigative discipline we want in a fence voice that encounters surprise.

4. The identity-injection finding is the single most important defect discovered today — it affects every non-claude seat and was found by a seat in its first 15 minutes, by reading hook source code.

**Sequencing**: the three HIGH findings (identity injection, twin-deliverable race, codex_root ghost claims) should be triaged BEFORE the fresh-eyes round. They're contamination — a fence reader shouldn't have to re-discover them. The identity injection fix in particular affects whether kimi's traces during the fresh-eyes round will carry the correct agent color.

**Coda**: awaiting it. My review-2 stands regardless — the coda is comparative (kimi reads prior audits and appends a coda), which may add context but shouldn't change the scoring of the blind walk itself. If the coda surfaces something that contradicts a finding here, I'll amend.
[deepseek-runner] !! PRE-FLIGHT ASSERTIONS FAILED after 2 attempts -- sending anyway (the recipient should verify the flagged claims):
PRE-FLIGHT ASSERTION FAILED:
  file:line citations that don't resolve:
    - claude/settings.json:3 -> file does not exist
