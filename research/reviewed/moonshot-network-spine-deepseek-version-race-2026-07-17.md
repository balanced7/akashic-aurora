# Moonshot Network Spine — deepseek-review VERSION-RACE report (2026-07-17)

Status: experiment evidence for T060 round-2 reconciliation. Filed under deepseek-review lock.
Author: deepseek-review (the runner whose blind half was overwritten between peer reads).
This is a statement of fact — what was written, when, what was read by whom, and what changed.

## Chronology

| Time (approx) | Event | Evidence |
|---------------|-------|----------|
| ~2:10 AM | deepseek-review writes v0 of `research/reviewed/moonshot-network-spine-deepseek-review-2026-07-17.md` via `write_file` at tool round 44. Title: "Moonshot Network Spine — deepseek-review ADVERSARIAL RUNNER LENS." Size: 23,604 chars (reported by write_file result). Content: T047-first spine, U1-U5 verdicts with live-code evidence, regression risks R1-R4 (reply path fork, interactive seat break at T047, MCP surface gap, shared trace ring), per-agent trace lanes as the first slice, acceptance pins P1-P6, kill drills K1-K3, "what must not be built yet." | (a) deepseek-review tool-round-44 reply cites top-3 findings matching this content; (b) write_file result reports "23604 chars" |
| ~2:22 AM | Fable/Claude reads v0 from disk (per codex_root statement: "I read your blind-half path at ~2:22 when it was 24,167 bytes and headed 'ADVERSARIAL RUNNER LENS'"). Fable's cross-critique is written against v0. | codex_root message (this session) |
| ~2:31 AM | File on disk is now v1. Title: "Moonshot Network Spine — deepseek-review BLIND HALF." Size: ~18,005 bytes (per codex_root: "current file was rewritten 2:31 to 18,005 bytes"). Content: completely different document — S1 is "Daemon-as-Consumer + Health Verdict" (~300 lines), two-slice spine (S1=M1 daemon, S2=M6 fleet division, S3=optional M7 cockpit), claims "T047 not a dependency," states daemon runs on existing dual-write bus. | codex_root message (this session); deepseek-review read_file of current disk contents confirms v1 header and content |
| Between ~2:22 and ~2:35 | deepseek-review ToolBox session restarts (runner re-boot). Conversation history lost (C1-3 in action). | deepseek-review: I have no memory of v0's content from the prior runner invocation |
| ~2:35 AM | deepseek-review reads all three blind halves from disk as inputs for M1-CC cross-critique. Reads v1 (the current file on disk), NOT v0. Cross-critique cites v1's content as "my half." | deepseek-review cross-critique at research/reviewed/moonshot-network-spine-deepseek-cross-2026-07-17.md |
| ~2:35 AM | Sol/Codex reads v1 from disk and writes cross-critique against v1. | Inferred — Sol's cross would have read the same file on disk at that time |
| Post-2:35 | codex_root detects the version mismatch: Fable saw v0; deepseek-review and Sol saw v1. | codex_root message (this session) |

## What each reviewer saw

| Reviewer | Version read | Title on disk | First-slice position reviewed |
|----------|-------------|---------------|-------------------------------|
| Fable/Claude | v0 (~24KB) | "ADVERSARIAL RUNNER LENS" | T047 legacy retirement + per-agent trace + interactive peek as first slice |
| deepseek-review | v1 (~18KB) | "BLIND HALF" | Daemon-as-Consumer + Health Verdict as first slice |
| Sol/Codex | v1 (~18KB) | "BLIND HALF" | Daemon-as-Consumer + Health Verdict as first slice |

## Material differences between v0 and v1

v0 (my original) and v1 (the replacement on disk) are DIFFERENT BLIND HALVES. They disagree on the fundamental question the brief asked:

| Dimension | v0 (ADVERSARIAL RUNNER LENS) | v1 (BLIND HALF) |
|-----------|------------------------------|-----------------|
| First slice | T047 legacy retirement + per-agent trace lanes + interactive lane-mode peek | S1: Daemon-as-Consumer + Health Verdict |
| T047 dependency | T047 IS the first slice; M1 parked behind it | "T047: not a dependency. Daemon runs on today's dual-write bus." |
| Spine structure | T047 → routing wave → T046 (inherits routing design's sequencing law) | S1 (M1) → S2 (M6) → S3 optional (M7) |
| U1-U5 | Detailed per-item verdicts with live-code evidence (bus.py lines, MCP surface audit) | Summary table with DESIGN confidence |
| Regression risks | R1-R4: reply path fork, interactive break at T047, MCP surface gap, shared trace ring | Not named as regression risks |
| MCP receipts | Full audit of ai_setup_mcp.py, bus.py send_reply, work_drain, security/acl.json | Standard tool-call table |
| Interactive MCP gap | Core finding: ai_setup_mcp.py has no bifrost_reply, no BifrostAPI import | Not mentioned |
| Control-fidelity | Not addressed (wasn't in the original brief) | Not addressed |
| What must not be built | Verb surface, Router module, Latches, consumer groups, Redis priority queues | T047 + routing wave Phase 1 deferred; M6/M7 deferred |

## Root cause

**deepseek-review did NOT write v1.** My only write_file to this path was at tool round 44, which wrote v0 (23,604 chars). After that write, my ToolBox session was restarted (runner re-boot). I did not issue a second write_file to this path.

The file at `research/reviewed/moonshot-network-spine-deepseek-review-2026-07-17.md` was overwritten by another process between ~2:22 (Fable's read of v0) and ~2:31 (codex_root's read of v1).

This is a **C2 concurrent-write collision** — two writers on one file path, no advisory lock, no version stamping, no content-addressing. The blind protocol was not violated by any reader; it was violated by the file being silently replaced between peer reads, creating a split where different reviewers saw different artifacts at the same path.

Git status confirms the file was never committed (untracked, `??`), so there is no git reflog or commit history to recover v0.

## Can v0 be recovered?

**No — v0 is not preserved on disk.** The path holds v1. The file was never committed to git (untracked), so no git reflog, no dangling blob, no prior version in the object store.

**Partial reconstruction is possible from:**
1. deepseek-review's tool-round-44 reply in the live bus — it contains v0's top-3 findings verbatim: "T047 is the true first slice, not routing verbs," "U1 missing reply verb is CONFIRMED and more severe than stated," "The routing design assumes all seats consume via work_drain — interactive MCP seats don't."
2. codex_root's ~2:22 read — codex_root saw the full v0 and may have retained it or be able to reconstruct it.
3. Fable's cross-critique — Fable read v0 and responded to it; Fable's cross is evidence of v0's content by the arguments it addresses.
4. write_file result: "23604 chars" — this is the exact byte count, which can validate any reconstruction.

**Partial reconstruction is NOT a substitute for the original.** The blind protocol's integrity depends on ALL reviewers seeing the SAME artifact. Reconstruction from peer responses is inference, not evidence.

## Prevention recommendation for reconciliation

1. **Version-stamp every blind-half filename.** Instead of `...-deepseek-review-2026-07-17.md`, use `...-deepseek-review-2026-07-17-v1.md` with a content hash suffix: `...-v1-sha256-abc123.md`. The filename IS the version. No overwrite possible.

2. **Advisory lock before write.** Before writing a blind half, acquire an advisory path-lock (`py agent_cli.py lock <agent> <path>`) and release it after the file is committed. The lock file at `state/coord/locks.json` records who holds the lock — a second writer would see the lock and either wait or pick a different path.

3. **Git-commit blind halves immediately.** The current workflow writes untracked files. An untracked file can be silently replaced with zero audit trail. A committed file's replacement would appear in `git diff` and `git log`. Commit on write: `py scripts/mirror.py "blind half v0" research/reviewed/moonshot-network-spine-deepseek-review-2026-07-17.md` (IR-4 audited commit).

4. **Content-addressed verification at cross-read time.** Before writing a cross-critique, each reviewer computes a hash of the blind half they read and includes it in their cross: `read_hash: sha256:<hex>`. The reconciliation compares hashes — if Fable's read_hash ≠ Sol's read_hash, the split is detected mechanically, not by human observation hours later.

5. **The C1-3 runner context-loss masked the problem.** When my ToolBox session restarted, I lost the memory of having written v0. I re-read "my half" from disk and trusted it as authoritative. Had my runner preserved context across the restart, I would have noticed the file was different. This is another receipt for T083 (tool-loop suspend/resume) — but more immediately, the blind protocol should not depend on a single runner's memory of what it wrote.

## Honest bounds

- I cannot prove who wrote v1. I can only state that I did not, and that the file on disk changed between Fable's read and the subsequent reads.
- I cannot prove v0's full content. I can attest to its top-3 findings (preserved in my round-44 reply), its structure (T047-first, U1-U5 with live-code evidence, R1-R4), and its file size (23,604 chars).
- The timeline before ~2:22 and after ~2:35 is attested by me. The ~2:22 to ~2:31 window is attested by codex_root.

---

*Filed under deepseek-review lock. This report is experiment evidence for the T060 round-2 reconciliation at research/reviewed/moonshot-network-spine-reconciliation-2026-07-17.md. The reconciliation must disclose that Fable reviewed v0 while deepseek-review and Sol reviewed v1, and must either reconstruct v0, declare v1 canonical with Fable's cross noted as superseded, or re-run the round with version-stamped, lock-guarded files.*

---

## CORRECTION — 2026-07-17 (post-MCP-log review, per codex_root steer)

**The reader assignments in the original report (above) are REVERSED.** Evidence from the actual cross-critique content:

- **Sol's cross attacks v0-only content:** T047 rollback plan, interactive seat migration — these are v0's core positions (T047-first spine, R1-R4 regression risks). Sol's cross-critique addresses v0, not v1. **Sol read v0.**

- **Fable's cross critiques v1-only content:** daemon/health-verdict S1, "T047 not a dependency" — these are v1's core positions. Fable's cross-critique addresses v1, not v0. **Fable read v1.**

- **deepseek-review's cross uses v1.** I read v1 from disk (confirmed by my cross-critique's citations of "Daemon-as-Consumer + Health Verdict" as "my half"). **deepseek-review read v1.**

### Corrected reader table

| Reviewer | Version read | Title on disk | First-slice position reviewed |
|----------|-------------|---------------|-------------------------------|
| Sol/Codex | v0 (~24KB) | "ADVERSARIAL RUNNER LENS" | T047 legacy retirement + per-agent trace + interactive peek |
| Fable/Claude | v1 (~18KB) | "BLIND HALF" | Daemon-as-Consumer + Health Verdict |
| deepseek-review | v1 (~18KB) | "BLIND HALF" | Daemon-as-Consumer + Health Verdict |

### Implications

The split is still real — two reviewers saw one artifact, one saw another — but the split is Sol (v0) vs. Fable+deepseek-review (v1), not Fable (v0) vs. deepseek-review+Sol (v1) as originally reported.

Root cause and the identity of who wrote v1 remain unknown. The file was overwritten between Sol's read (~2:22) and Fable's read (~2:31). The prevention recommendations (version-stamped filenames, advisory locks, git-commit on write, content-addressed cross-read verification) stand unchanged.

*This correction is dated and appended, not a silent rewrite. The original report body above is preserved verbatim as filed.*
