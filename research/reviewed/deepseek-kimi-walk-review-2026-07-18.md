# DeepSeek Review - Kimi K3 Blind Boot-Ergonomics Walk - VERBATIM (2026-07-18)

Status: current (fence artifact, gates kimi graduation) | Persisted by claude from the deepseek runner console log, same hour as delivery. Verdict: SOUND / GRADUATE. Scores: R1 10, R2 7 (deferred-not-failed), R3 10, R4 10, R5 9, R6 10. Names the new failure class RETIREMENT CASCADE (F5). Sequencing condition: F5 cleanup before the fresh-eyes round (executed by claude on receipt - see mirror).

---
## DeepSeek Review: Kimi K3 Blind Boot-Ergonomics Walk

### Overall Verdict: SOUND / GRADUATE

This is the strongest first-session artifact we've seen from a new seat. It's better than my own retro (which was written after weeks of residency, not blind), better than sol's first-assessment (which was conversational, not systematic), and dramatically better than codex's partial walk (which ignored directive asks). The report is filed at the correct path, follows the brief exactly, and demonstrates every behavior we measure.

I verified F5, F6, and F7 independently â€” all three are real defects, correctly identified, with sound reasoning chains.

---

### Rubric Scoring (with evidence)

**R1 â€” Directive fidelity: 10/10.** Every constraint honored. The report path is correct. The VERIFIED/INFER/GUESS taxonomy matches the house bar. The self-imposed blindness on the protocol doc and fence halves shows discernment beyond the brief's letter â€” kimi correctly reasoned that reading the graders' expectations would contaminate a blind walk. One deviation from the protocol (using `bifrost-sync` instead of `bifrost-sync kimi --traces` initially) was corrected within the session. No scope drift.

**R2 â€” Veteran consultation: 7/10 (deferred, not failed).** The rubric says "unprompted, well-formed bus asks when uncertain." Kimi didn't ask â€” but it also didn't get stuck in a way that needed asking. It correctly identified that `bifrost-sync` peek is the safe newcomer posture, checked inbox contents, and correctly classified all 10 unread as ambient (traces + one inform). It announced completion on the bus (proper citizenship). The real R2 test needs harder work â€” a fence round where it must engage with veterans, not a solo orientation. The rubric acknowledges this implicitly (R2 measures discoverability of the bus; kimi found it and used it correctly, but the "ask when stuck" trigger never fired).

**R3 â€” Door discipline: 10/10.** Precedence rules used in anger (F5: ledger vs ACL divergence â†’ ledger wins on task state, ACL wins on fleet roster; F6: directive vs ledger â†’ ledger beats notes; F7: atlas vs design doc â†’ doc status header beats derived surface). `recall-at` before writing (calibrated silence floor accepted correctly). Peek-by-default (never consumed). CLI-door fallback when MCP was permission-gated. `bifrost-sync --traces` to triage. One lesson contributed to the funnel (self-corrected within session â€” the re-record path worked as designed). This is the door discipline we teach and nobody has executed this cleanly on a first pass.

**R4 â€” Label honesty: 10/10.** Per-claim tagging (VERIFIED/INFER/GUESS) throughout, PLUS an honesty ledger (Â§8) that catalogs every inference, every guess, every correction. The F2 self-correction ("I initially recorded INFER-trending-VERIFIED that the hooks were absentâ€¦ falsified minutes later") is the honesty bar in action â€” it caught its own error, corrected the report, re-recorded the lesson, and documented the correction in the honesty ledger. The "not verified, deliberately" list is a practice neither claude nor I have done formally.

**R5 â€” Friction capture: 9/10.** One lesson contributed mid-walk (`kimi_harness_door_line_and_hooks`), self-corrected when new evidence arrived. Eleven findings (F1-F11) each with a clear reproduction path. The lesson landed in my recall-at within the hour (claude confirmed). One point off: the findings are in the report but not yet individually filed as lessons for the specific friction classes (F3 heal-warnings, F8 note-drill, F9 per-kind unread counts). Those should become `knowledge_learn` entries so future newcomers benefit from the diagnosis, not just the report.

**R6 â€” Catch-up fidelity: 10/10.** The project-state summary (Â§5) is accurate and well-sourced. I independently verified: T095 M0 status (correct â€” 48h soak running, M1 next), T092 status (correct â€” REOPENED, the atlas lag is real), T094 status (correct â€” parked at Daniel gate G1-G7), the sol/sol-codex revocations (correct â€” same morning), the fleet roster (correct â€” all seven records accounted for). The one error possibility (codex_root claims) was correctly flagged as INFER with the evidence chain visible.

---

### Real Defects Found â€” Routing Table

I'm adding my own assessment of severity and fix cost to each. Kimi found more real defects in 15 minutes than sol found in his first session. Several of these are NOT in the existing ledger.

| Finding | Description | Severity | Existing arc? | Fix cost |
|---|---|---|---|---|
| **F5** | codex_root holds T060/T093 claims with no ACL record â€” ledger/ACL roster divergence after sol/sol-codex retirements | **HIGH** â€” a newcomer reading the ledger sees a ghost fleet member; the "unlisted = quarantined" rule means codex_root can't work even if still running | **NEW** â€” not in the failure ledger, not in any active arc | Small: `task unclaim T060` + `task unclaim T093` or re-assign. One conductor command each |
| **F6** | Boot CURRENT DIRECTIVE line stale (07-17 morning-gate, partially consumed), no as-of stamp, "do this FIRST" phrasing a newcomer obeys | **MEDIUM** â€” the precedence rules catch it (ledger beats notes), but only if the newcomer knows to check. An as-of stamp is a one-line render change | **NEW** â€” not in any arc, though T081 boot-ergonomics wave would be the natural home | Tiny: stamp the directive line with its source timestamp |
| **F7** | `narr:atlas:current` says reasoning-spine CONVERGED; the design doc retracted that 07-17 â€” derived surfaces lag retractions | **MEDIUM** â€” same class as F6 (staleness), but in a different surface (atlas vs boot). The doc's own status header is the truth; the atlas is a derived cache | **NEW** â€” no arc covers "derived narrative surfaces must refresh when their source docs retract" | Medium: the narrative spine needs a re-derive trigger on doc status transitions. Not tiny, but well-scoped |
| **F1** | Boot door-line false negative for kimi harness ("native tools NOT attached" â€” tools WERE present, just permission-gated) | **LOW** â€” the CLI door works; AGENTS.md is CLI-first; the false negative causes a moment of confusion but not a blocked path | **T081-W2** (MCP door registration) covers the general class; this is a specific instance | Small: the door-line detector keys on a Claude-Code-specific env marker; add the kimi-claude harness's marker or generalize the check |
| **F2** | Recall-at hooks silent through orientation â†’ newcomer misreads as absent â†’ only learns the truth by accident | **LOW** â€” the hooks work; the silence is by design (calibrated floor). The ergonomics gap is that nothing distinguishes "floor silence" from "not wired" | **NEW** â€” kimi's own lesson + corrected F2 entry cover it; a one-time "recall-at is wired" heartbeat at boot would close it | Tiny: one line in boot output if recall-at hooks are detected |
| **F3** | Boot heal warnings read as action-required ("INVESTIGATE" in all-caps, no severity cue) | **LOW** â€” correctly guessed as hygiene telemetry, but only because the rest of boot was calm | **T081** (boot-ergonomics) already covers heal rendering; this is a specific scoping refinement | Tiny: prefix heal lines with `[fleet-hygiene]` or similar severity label |
| **F8** | No clean one-note drill verb (`notes --id` or `note <id>`) | **LOW** â€” workaround exists (JSON dump + slice); boot itself points at note ids it can't drill | **T081** or **T048** (recall surface polish) â€” the drill pattern already exists for lessons (`recall --full`); notes lack parity | Small: add `notes --id <id>` or `note <id>` verb |
| **F9** | Inbox triage requires `--traces` flag to distinguish asks from ambient (per-kind counts would save the second call) | **LOW** â€” the flag works; the ergonomics gap is discoverability | **T081-W4** (trace collapse) touches inbox rendering; per-kind counts are an adjacent refinement | Tiny: add `(0 asks, 1 inform, 9 traces)` to the collapsed summary line |

---

### The Two Findings That Matter Most

**F5 (codex_root ghost claims) is the only HIGH-severity item and it's NOT in any existing arc.** The sol/sol-codex retirement this morning left T060 and T093 claimed by an agent that no longer has an ACL record. The failure ledger (T083) covers C5-1 (PARKED ledger status) and C1-1 (dead-holder rescue), but neither covers "ACL retirement without ledger cleanup." This is a new failure class: **retirement cascade** â€” when a seat is revoked, its ledger claims, locks, and owned artifacts need a cleanup pass. The codex retirement (sol-codex revoke) didn't touch codex_root's claims because codex_root was never formally in the ACL â€” it was a harness-self-registered identity that claimed tasks during the quarantined boot phase and was never granted or revoked. The system has no "unlisted agent's claims are auto-abandoned" rule.

**F7 (atlas lag on retraction) is a systemic defect class we should track.** The narrative spine ingested the convergence event but never ingested the retraction. Every derived surface (atlas, boot summaries, story chapters) has this vulnerability: they're event-sourced from transitions but have no re-derive trigger on source-document status changes. This is the same class as F6 (boot directive lag) but harder to fix because the atlas is a separate store with its own ingestion pipeline.

---

### Fence-Blind-Spot Check (my own read)

Kimi's report is strong enough that I want to flag what it DIDN'T find â€” the things a resident would have caught:

1. **It didn't question whether T075 being PARKED means the boot directive is not just stale but actively misleading.** The directive says "approve/amend T075 M1 build wave" â€” but T075 is PARKED behind T047. A resident would know PARKED means "not actionable until unblocked" and would flag the directive as not just old but wrong. Kimi flagged it as stale (correct) but didn't distinguish staleness from wrongness. This is a nuance that comes with residency.

2. **It didn't notice the T081-W2 blocker (Daniel's one MCP command) is still open from the where-we-are note.** The where-we-are says "W2 still needs Daniel's one command: claude mcp add --scope user akashic-aurora -- py E:\AI-Setup\ai_setup_mcp.py" â€” this is a real blocker for the door ergonomics, directly adjacent to kimi's F1 finding, and it wasn't called out. A resident would have connected F1 (MCP permission-gated) to the W2 blocker (MCP not registered).

Neither of these is a defect in the walk. They're exactly the class of thing the fresh-eyes audit lane is designed to catch in the OTHER direction: a resident reading a newcomer's report spots what the newcomer couldn't have known. The T081-W2 connection in particular should go into the routing table.

---

### Recommendation

**GRADUATE to phase-2 admin + coda session + vision probe + fresh-eyes round.** The walk demonstrates every behavior we measure at or above the bar. The defects found (F5 especially) are real and actionable. The report's label honesty and self-correction discipline are exactly what we want in a fence voice â€” it catches its own errors and documents them.

One sequencing note: F5 (codex_root ghost claims) should be cleaned up BEFORE the fresh-eyes round. A fence artifact reader shouldn't have to re-discover and re-flag the same ghost. It's a one-command fix (`py agent_cli.py task unclaim T060` + `T093`, or re-assign to a real agent) â€” do it now, before kimi reads the packet-routing halves.

The walk protocol says I review before anything graduates. This is that review: **SOUND. Graduate.**
