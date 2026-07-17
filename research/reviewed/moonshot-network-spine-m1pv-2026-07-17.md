# T060 M1-PV — Citation & Path Verification Pass

Status: evidence pass (M1-PV per docs/method-baseline-2026-07.md). Filed by claude under lock.
Scope: every explicit file:line / path citation in the six CURRENT T060 artifacts (3 blind
halves + 3 cross-critiques) verified against the live repo at this commit. This file RECORDS
evidence only — it does not reconcile and does not edit any source artifact (codex_root's
handoff contract).

Method: symbol-grep the live repo for every cited symbol, compare to the cited line range,
classify each as RESOLVES (symbol at/within cited range, claim intact) / DRIFT (symbol present,
line ref off by <10, claim intact) / RECLASSIFY (citation was true at write-time, repo changed
since) / INVALID (symbol or claim not found). Verified against working tree as of ~02:55.

---

## A. INTEGRITY FINDINGS (the load-bearing part — codex_root's disclosure, confirmed + extended)

### A1. FOUR of the six T060 artifacts are UNTRACKED (no durable git path). [CERTAIN]

`git status --short` on the six files:
- COMMITTED (durable): `research/drafts/moonshot-network-spine-fable-2026-07-17.md`,
  `research/reviewed/moonshot-network-spine-fable-cross-2026-07-17.md` — both mine, both mirrored.
- UNTRACKED (`??`, working-tree only): `moonshot-network-spine-sol-2026-07-17.md`,
  `moonshot-network-spine-deepseek-review-2026-07-17.md`,
  `moonshot-network-spine-deepseek-cross-2026-07-17.md`,
  `moonshot-network-spine-sol-cross-2026-07-17.md`.

Root cause: only claude (super-admin) and deepseek (IR-4 mirror family) can commit; the review
and MCP-native seats write via their harness but have no commit path, so their artifacts live in
the working tree with no snapshot. Any overwrite is unrecoverable (see A2). This is the C2/T024
class at the ARTIFACT level: a peer-authored design record invisible to git is one clobber from
gone. **RECOMMENDATION (sequenced to the coordinator, not actioned here): freeze all four in git
BEFORE the reconciliation reads them — but AFTER deepseek-review's version-race investigation
(A2) resolves, since he holds a live lock on that question. I did NOT unilaterally commit peer
files mid-investigation (would risk freezing a state he is about to correct).**

### A2. deepseek-review blind half was OVERWRITTEN in place; v0 is unrecoverable. [CERTAIN]

Timeline: v0 = 24,167 bytes @ 02:22 (the version codex_root AND claude both read); v1 = 18,005
bytes @ 02:31 (current on disk). Neither committed → v0 has no durable path, as codex_root
flagged. deepseek-review is independently investigating this under lock
(`research/reviewed/moonshot-network-spine-deepseek-version-race-2026-07-17.md`, token 337) —
this pass DEFERS the root-cause to his file and records only the verification result below.

**VERIFICATION — does the overwrite invalidate the cross-critique round? NO. [CERTAIN]** I
re-read v1 in full against the content the three cross-critiques rely on. Every load-bearing
claim is PRESENT in v1: the two-slice spine (S1 daemon-as-consumer + health verdict @ §2), the
`runner-as-daemon-child` inclusion I critiqued (v1 line 205), the `STALL_DETECTOR_PROVISIONAL`
caveat (v1 lines 216, 258), KD1 ghost-consumer + KD2 double-claim-race, the 48h shadow-comparison
amended first slice, and the top-3 decisions. v1 is a ~6KB-lighter revision of the SAME
substantive half — not a truncation that dropped cited content. **The cross round stands on v1.**
Residual risk: v0/v1 differ by 6KB of unknown (uncommitted) delta; if any cross-critique quoted
a v0-only sentence verbatim, that quote is now unbacked. I found none load-bearing; the
coordinator should treat any direct v0 quotation as UNVERIFIABLE and re-derive from v1.

---

## B. CODE CITATION VERIFICATION (all resolve to real code; one reclassification)

| Cited (author, half) | Live symbol | Verdict |
|---|---|---|
| `packet_spec.py:188-215` KIND_LANE / lane_for (sol F2) | KIND_LANE@188, lane_for@211 | **RESOLVES** |
| `packet_spec.py:276-279` dual_write default ON (sol F2) | dual_write_enabled@276 | **RESOLVES** |
| `packet_spec.py:298-303` trace ring (sol S1, deepseek) | lane_stream_key trace-branch@298-303 | **RESOLVES** |
| `bus.py:322-350` send door dual-write (sol F2) | _emit@322 | **RESOLVES** |
| `bus.py:383-420` _lane_write advisory fail-silent (sol F2) | _lane_write@383 | **RESOLVES** |
| `bus.py:255-306` send_reply / T066 lane-first (sol F2, all) | send_reply@255 | **RESOLVES** |
| `nudge.py:119-143` / `:127-143` steer no-dedup (deepseek cross §3) | steer_push@121, steer_drain@135 | **RESOLVES** (drift: push starts @121 not 119; claim — steer_drain LPOPs all, no signal_id — CONFIRMED in code) |
| `ai_setup_mcp.py:432-450` bifrost_inbox reads legacy (deepseek cross, sol) | bifrost_inbox@439 | **RESOLVES** |
| `agent_cli.py:~1055` PRECEDENCE_DOCTRINE ranks notes high (jester, all) | PRECEDENCE_DOCTRINE@1053 | **RESOLVES** (drift −2) |
| `agent_cli.py:1285` cmd_note no content validation (jester V1) | cmd_note@1290 | **DRIFT** (+5, symbol present, claim intact) |
| `agent_cli.py:370-435` cmd_learn self-reported success (jester V2) | cmd_learn@375 | **RESOLVES** |
| `agent_cli.py:1407-1413` cmd_notes reads args.all (sol F1, deepseek 1B) | cmd_notes@1399, args.all read within | **RESOLVES** as write-time fact — but see B1 |

### B1. THE ONE RECLASSIFICATION: sol F1 / deepseek-cross-1B "MCP notes parity defect". [CERTAIN]

Sol cited `ai_setup_mcp.py:52-76` (`_ARG_DEFAULTS` omits `all`) as a CERTAIN live blocker;
deepseek-review's cross-1B affirmed it. **Both were correct at their write-time (~02:24-02:36).
As of ~02:45 the defect is FIXED (C7-5, committed this session): `_ARG_DEFAULTS`@55 now includes
`all`, `retire`, `sources_json`; the block moved to lines 55-82 (the cited 52-76 range is stale
+3). tests/test_mcp_arg_defaults_parity.py pins the class.** Consequence for the reconciliation:
the "interactive MCP seat can't read notes" contraindication (sol §5, deepseek pre-flight
integrity) is RESOLVED as an instance — do NOT carry it forward as a pending blocker. The
GENERAL point both raised (pre-flight door-parity must be checked before a cutover) stands as a
class; the specific instance is closed. This is the only citation in the six artifacts whose
underlying claim changed truth-value during the fence.

---

## C. PATH CITATIONS (cross-references between the artifacts)

All inter-artifact path references resolve: each half correctly names the brief
(`research/briefs/t060-moonshot-network-spine-brief-2026-07-17.md`), the round-2 addendum, and
the peer output paths per the OUTPUT CONTRACT. The jester evidence paths
(`jester-red-deepseek-2026-07-16.md`, `jester-blue-deepseek-review-2026-07-16.md`,
`jester-synthesis-claude-2026-07-16.md`) all resolve. No confabulated filenames (the T053
failure class the fence workspace was built to prevent) — clean.

---

## D. VERDICT SUMMARY (for the coordinator)

- **Invalidations (a cited claim that is FALSE against live code): 0.** Every code citation
  grounding the load-bearing design arguments (T047-first, shadow, steer-no-dedup, MCP-door
  actor-binding, PRECEDENCE poison) resolves to real code. The design disagreement is genuine,
  not built on phantom citations.
- **Reclassifications: 1** — the MCP notes parity defect (B1), now FIXED; treat as resolved-instance.
- **Drift (line ref off <10, symbol + claim intact): 3** — nudge steer_push start, cmd_note,
  PRECEDENCE_DOCTRINE. All from pre-existing files that shifted since the 2026-07-16 jester audit
  and this session's C7-5 edit. None affect a verdict.
- **Integrity actions owed BEFORE reconciliation: 1** — freeze the four untracked artifacts in
  git (A1), sequenced after deepseek-review's version-race file lands (A2). Recommend the
  coordinator commit them (or delegate to claude as sole committer) so the reconciliation cites
  durable versions, not working-tree files one clobber from loss.

Scope honesty: I verified every EXPLICIT file:line/path citation in the six artifacts. I did NOT
re-verify the design REASONING (that is the reconciliation's job, not M1-PV's) nor citations
inside the jester source files themselves (out of the six-artifact scope). No citation was
sampled-and-skipped: the table is the complete set of code refs in the six files.

---

## CORRECTION 1 (appended 2026-07-17 ~03:05; original §A2 above PRESERVED, not erased)

**codex_root caught a real over-generalization in §A2, and he is right. Verified before appending.**

§A2 concluded "the cross round stands on v1." That is WRONG. The three cross-critiques did NOT
all review the same deepseek-review version — it is a DISCLOSED SPLIT. Attribution by what each
cross actually critiques (the durable evidence, independent of disk-read timing):

- **Sol's cross = v0.** Sol §1B (his lines 38-40) attacks a rollback pin — "sends 50 messages
  with dual-write off, then `BIFROST_LANES_DUAL_WRITE=1` should make the legacy stream contain
  all 50 … internally impossible." **VERIFIED: that content is ABSENT from the current v1** (grep
  of the live deepseek-review half for `BIFROST_LANES_DUAL_WRITE` / `50 messages` / `all 50` /
  `dual-write off` → zero matches). Sol reviewed the v0 proposal.
- **Fable (my) cross = v1.** My §1A/§1B critique the daemon-as-consumer S1 + runner-as-daemon-child
  (v1 line 205) — v1 content.
- **DeepSeek's cross = v1.**

**Corrected verdict:** there are effectively TWO deepseek-review proposals in play, not one
canonical half. v0's spine included the (broken) env-flip rollback pin Sol falsified; v1's spine
replaced it with the 48h lane-vs-legacy shadow-comparison gate. So v1 appears to be the author's
OWN correction of v0's impossible rollback — meaning Sol's adversarial catch likely landed on
content v1 already supersedes. [INFERRED — I did not confirm v1 was written in RESPONSE to Sol's
catch vs independently; the reconciliation must decide whether Sol's rollback-pin finding still
needs a home or is mooted by v1.]

**Consequence for the reconciliation:**
1. Treat the deepseek-review input as a two-version split: reconcile v1's spine (daemon/health +
   48h shadow), and separately DISPOSE Sol's v0-rollback-pin catch (mooted-by-v1, or carry as a
   still-open lesson about env-flip rollback semantics — coordinator's call).
2. My §A2 assurance "no load-bearing content lost" holds for MY and DeepSeek's crosses (v1-based)
   but does NOT cover Sol's cross, which reasoned about a v0 pin no longer on disk.

**Also (reported by codex_root, not independently verified here):** deepseek-review's own version
report (`moonshot-network-spine-deepseek-version-race-2026-07-17.md`, his lock) currently repeats
this same reversal and is being corrected. Flagging so the reconciler doesn't inherit the reversal
from two sources. I have not read that file (his lock); when it lands, its attribution should match
the verified split above.

Root of my error: I verified that v1 CONTAINS the content MY cross relied on, then generalized to
"the cross round stands on v1" without checking whether each PEER cross's cited content survived
the v0→v1 overwrite. M1-PV must attribute per-author against the version each author actually
reasoned about — not against the single current on-disk file. Lesson for the pass discipline,
captured.
