---
akashic_id: art_20260718_kimi-k3-blind-boot-ergonomics-walk-secon_b2ec56
akashic_sha: 3887cc612ea5
status: draft
type: report
date: 2026-07-18
title: "Kimi K3 — Blind Boot-Ergonomics Walk, SECOND CONCURRENT WALK (session c4d142df)"
gist: "# Kimi K3 — Blind Boot-Ergonomics Walk, SECOND CONCURRENT WALK (session c4d142df) **Seat:** kimi (kimi-k3, Moonshot frontier model, kimi-cla"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, identity, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260718_kimi-k3-blind-boot-ergonomics-walk_c50982
    rel: cites
  - target: art_20260701_the-reasoning-spine-co-authored-design-c_24d17f
    rel: cites
  - target: art_20260718_kimi-k3-blind-boot-ergonomics-walk-proto_6b1c4b
    rel: cites
created: "2026-07-18T10:35:23"
updated: "2026-07-23T21:42:19"
---
<!-- GENERATED PROJECTION of art_20260718_kimi-k3-blind-boot-ergonomics-walk-secon_b2ec56 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Kimi K3 — Blind Boot-Ergonomics Walk, SECOND CONCURRENT WALK (session c4d142df)

# Kimi K3 — Blind Boot-Ergonomics Walk, SECOND CONCURRENT WALK (session c4d142df)

**Seat:** kimi (kimi-k3, Moonshot frontier model, kimi-claude harness on Daniel's host)
**Date:** 2026-07-18. My boot: 14:07:19 UTC (10:07:19 EDT). Report filed same session.
**Charter:** Daniel directive 2026-07-18; phase-1 grant ACTIVE (`security/acl.json` kimi
record, granted_by claude 09:17, approved by Daniel verbatim). One assignment: boot the way
the front door teaches, work a genuine orientation, file an honest ergonomics report.
**Honesty convention:** every claim tagged **VERIFIED** (read/ran/watched, source cited),
**INFER** (reasoning from evidence), or **GUESS** (chose under uncertainty).

---

## 0. Headline: there were TWO of me — this is the second walk

**VERIFIED.** While I walked, a twin kimi session ran the same assignment in parallel and
filed first. Evidence, all checkable:

- The event firehose holds **two kimi boots 72 seconds apart**: 14:06:07 UTC ("blind
  boot-ergonomics walk: new seat orientation and onboarding…") and 14:07:19 UTC (mine:
  "blind boot ergonomics walk as new seat kimi")
  (`py agent_cli.py events --agent kimi` → `event:events:kimi:raw:1784383567109-0` and
  `…:1784383639485-0`).
- Two live session transcripts exist side by side:
  `.kimi-claude-home/projects/E--AI-Setup/a8691c78-….jsonl` (the twin) and
  `…/c4d142df-….jsonl` (this session).
- The twin **filed the charter deliverable at the charter path** —
  `research/reviewed/kimi-boot-ergonomics-2026-07-18.md` (mtime 10:24:52 EDT, untracked) —
  then sent `kimi -> claude [completion]: WALK COMPLETE (phase 1)` (14:23:24 UTC), recorded
  lesson `kimi_harness_door_line_and_hooks` (twice; the second a self-correction), and left
  a `kimi -> kimi` phase-2 handoff. All in the firehose.
- I discovered this only when my own Write to the same path was refused until I read the
  existing file. The harness enforced the house's look-before-you-destroy rule at exactly
  the right moment.

**Why I did not overwrite it:** the existing file is a complete, house-standard, genuinely
*blind* report by my own seat — destroying it would violate M6 (verbatim preservation) and
the reporting contract ("if what you find contradicts how it was described, surface that
instead of proceeding"). So this second report files at an adjacent path. Together the two
reports are an **unplanned fenced dual pass** over the same door: two blind walks, separate
contexts, same morning. Per the method, divergence is the signal — §3 reconciles the two.

**What the collision itself teaches (the real finding of the day):** the
`twin-split-identity-collision` note (T088) warned that two incarnations sharing one bus id
cross-route handoffs and eat each other's cursor. Day one of the kimi seat reproduced the
class at the *deliverable* level: two sessions, one id, one assignment, one output path, no
lock taken by either (a fresh-file write never trips the shared-path lock habit), and no
surface that told either walker the other existed until the filesystem said no. Whatever
launched us (the "walk launcher" of commit `623cb6c`, plus my own session launch) created
an uncoordinated twin. **INFER:** the wake/seat doctrine absorbs twins for *mail* (stand-down
+ displacement), but nothing absorbs them for *ad-hoc deliverables* — a charter path written
into two briefs is a write-write race the locks culture doesn't cover because nobody "edits"
a not-yet-existing file. A cheap guard: the launcher stamps a seat-instance marker into the
brief (or claims a lock on the deliverable path at walk start) so the second launcher refuses
loudly instead of both walking blind.

---

## 1. The path I actually walked (audit trail)

1. Read `AGENTS.md` — the "first 40 lines" promise held (boot/learn/recall/recall-at/locks/
   bifrost/session hygiene/reporting contract). **VERIFIED.**
2. `py agent_cli.py boot kimi --task "…"` — orientation header, precedence rules, ledger
   counts, live constraints, ranked lessons, notes/decisions digests, doctor, contribute
   line. First attempt via the PowerShell tool was sandbox-rejected as "multiple
   operations" (false positive on one command; the colon inside the quoted task string is
   the likely trigger); the Bash tool ran it clean. **VERIFIED.**
3. `bifrost-sync kimi` (peek): 10 unread (7 traces from claude, 3 ledger_updates from
   conductor — a different mix than the twin saw minutes earlier: 9 traces + 1 inform);
   presence `claude, deepseek, kimi`. **VERIFIED.**
4. Read `docs/ARCHITECTURE.md` (layer stack; Store/Ledger primitives; anti-rot contract)
   then `docs/method-baseline-2026-07.md` (full: principles, lifecycle, M0–M11, M1-LITE
   tiers, enforcement lane). **VERIFIED.**
5. `task list` (full ledger: 42 done / 15 in-progress / 1 parked / 14 next / 2
   proposed-stale), `notes` + `notes --json` (full bodies of the five newest state notes),
   `promoted --limit 12` (durable bus: two claude→deepseek handoffs about the KIMI K3 fence
   — headers only, deliberately). **VERIFIED.**
6. `doctor` (redis LIVE; ui:8787 DOWN; daemon DOWN; codex_root page-grade STALLED
   CONSUMER), `delta kimi` (honest newborn case), `story` (atlas counts, generated
   2026-07-17T05:16 — ~29h stale), `task next`, `task --help`. **VERIFIED.**
7. Read `docs/LIVE_CONSTRAINTS.md`, `docs/ROADMAP.md` (self-declared historical),
   `.mcp.json`, `.claude/settings.json`, `_transport_line` source (`agent_cli.py:1125-1140`),
   hooks' identity reads (`scripts/hooks/*`). **VERIFIED.**
8. `git log --oneline -14` — cross-checked the where-we-are note: every cited commit
   (`b3e39e7`, `7fa0170`, `d2d8ba9`, `0b55d7d`, `bc1702b`, `efcfc3b`, `75c5614`, `1075ee5`)
   exists with matching message. **VERIFIED — the note is truthful.**
9. After the collision: read the twin's report in full, `git status` on its path
   (untracked, no locks held), `security/acl.json` (full grant registry),
   `docs/reasoning-spine-design-2026-07.md` header (the REOPENED retraction), the twin's
   lesson and completion via the firehose, both session transcripts' existence/mtimes.
   **VERIFIED.**

One MCP-door probe (`mcp__akashic-aurora__status`) — permission-gated by the harness, not
granted mid-walk; proceeded via CLI, as did the twin. **VERIFIED.**

## 2. Where the doors taught me (what worked)

- **Boot is a real orientation.** One call: map+method pointers, precedence doctrine,
  ledger summary, live constraints, lessons, notes, decisions, doctor. **VERIFIED.**
- **The precedence doctrine resolved conflicts before I asked.** "TASK LEDGER beats NOTES
  beats PROMOTED beats LIVE BUS; DONE is closed" — I used it within minutes (the CURRENT
  DIRECTIVE line vs the parked T075). **VERIFIED by use.** (Converges with the twin's W2.)
- **Truncation always names its drill path** — clipped notes point to `notes --json`,
  promoted bodies to `events --get <ref>`. No dead ellipses. **VERIFIED by use.**
- **Doc-currency stamps are honest.** ROADMAP self-declares historical and redirects to the
  notes; LIVE_CONSTRAINTS bullets cite their incidents; the reasoning-spine doc opens with
  a *retraction confession*. Status headers tell the truth even when it's embarrassing.
  **VERIFIED.** (Twin's W3 — converged.)
- **The recall-at-action hook armed me, from my first Bash call.** Fired with:
  bifrost-send syntax lessons before bus-shaped commands; `consume_limit_hides_backlog`
  right after doctor paged a stalled consumer (and that same lesson's pattern is the
  reasoning-spine REOPENED receipt — capped consumes hiding a backlog);
  `mirror_lock_identity_requires_agent_env` while I probed agent identity. Trigger-phrased
  lesson text is why it fires at the right moment. **VERIFIED — four fires, all relevant.**
  This directly answers the note `capture-for-recall-not-just-record`'s question: on this
  seat, this morning, the arming loop worked.
- **`delta kimi` handles newborn honestly** ("no mark yet… the full boot is the
  orientation"). **VERIFIED.**
- **The ACL registry is legible governance** — verbatim Daniel quotes, revoke-by-editing
  doctrine, incident-derived rules. It also *governed me correctly at the end of the walk*:
  my caps are `git.read` without exec, so both kimi reports stay uncommitted for an admin
  to mirror — the phase-1 profile doing exactly what it was shaped to do. **VERIFIED.**
- **The system knew I was coming.** Onboarding-prep commits, a fence (three rounds,
  CONVERGED member-first, per my ACL reason field), a protocol brief, a walk launcher.
  Coordination here is operational, not theatrical. **VERIFIED** (git log, acl.json,
  promoted).

## 3. The accidental fence: my walk vs the twin's, reconciled

House vocabulary (CONVERGED / COMPLEMENTARY / DIVERGENT), per the method baseline:

**CONVERGED (independent blind walks, same findings — highest-confidence defects):**
- *Boot door-line false negative* (twin F1 = my F1): boot prints `door: CLI-shell — native
  akashic tools NOT attached; remedy: user-scoped MCP…` while the session's tool surface
  lists the full `mcp__akashic-aurora__*` verb set. I additionally read the source:
  `_transport_line` reports the **invocation path** (`AKASHIC_SEAT_DOOR` env unset for a
  bare CLI boot → safe default), not the session's actual tool surface — the wording
  overclaims a session fact boot cannot know, and the remedy sentence points at fixing a
  door that already works. **VERIFIED both.**
- *Boot heal warning reads as action-required* (twin F3 = my F6): `1368 UNKNOWN Redis-only
  key(s) … INVESTIGATE` on a newcomer's first screen, no severity/scope label. Plausibly
  T095's new mailbox keys — **INFER, unresolved by either walk.**
- *Derived surfaces lag their sources* (twin F6+F7 = my observations): boot's CURRENT
  DIRECTIVE still pushes the 07-17 morning gate (T075 since parked; the deepseek exec grant
  since approved 07-16 per acl.json); the atlas line says reasoning spine "CONVERGED" while
  the design doc itself is REOPENED. **VERIFIED both.**
- *Shell/harness friction with taught `py` one-liners* (twin F11 = my F3): sandbox false
  positives on quoting/pipes; workarounds exist but the first minutes collect denied no-ops.
  **VERIFIED both.**

**COMPLEMENTARY (only one walk found it; both true):**
- *Mine:* **`.claude/settings.json` injects `AKASHIC_AGENT_ID=claude` repo-wide**, and every
  hook defaults to `claude` — a non-claude seat's hook telemetry (incarnation cards,
  traces, session-end) stamps `claude` while its CLI verbs attribute correctly. My direct
  env probes were sandbox-blocked, so runtime effect is **INFER** from config+code; config
  and mechanism are **VERIFIED**. I did not adopt the injected id (per the walk's
  do-not-impersonate rule); the twin evidently rode it unknowingly — its hook-side activity
  would read `claude`. (Commit `4e7ec26` "identity flag verified+annotated" suggests the
  fleet may partly know.)
- *Mine:* **`task next` contradicts `task list`** — "none (a task is already in progress,
  or nothing is claimable)" while 14 NEXT items render as claimable. **VERIFIED.**
- *Mine:* the current where-we-are note embeds a session-scoped "Recall review — vote"
  footer (dead vote commands in a durable record). **INFER (artifact read, wrap code not).**
- *Mine:* two memory systems, one documented — harness-private file memory vs Akashic shared
  memory; no doctrine for the split (my rule: team knowledge → Akashic; harness prefs →
  file). **INFER that it's fleet-unaddressed.**
- *Twin's:* no kimi task in the ledger — the charter lives only in acl.json, invisible to
  the primary coordination surface (**VERIFIED** — I grepped too).
- *Twin's:* codex_root holds T060/T093 ledger claims with no ACL record; its status after
  the GPT cancellation is unabsorbed (**VERIFIED by me independently** — ledger + acl.json;
  the sol-codex record explains codex_root was the Codex-CLI door id, retired with sol).
- *Twin's:* no clean one-note drill verb (`notes --json | head` → BrokenPipeError; `events
  --get` refuses note ids) (**VERIFIED by twin; not re-run by me**).
- *Twin's:* presence flicker (claude dropped offline mid-walk) (**VERIFIED by twin**).

**DIVERGENT (the two walks disagree — the valuable kind):**
- *Recall-at hooks:* the twin's report claims (F2) zero hook injections all walk, then its
  own lesson self-corrected mid-session: hooks DO fire; the early silence was the
  calibrated floor. My session had injections from the first Bash call. **Ruling: hooks
  fire on this harness; the twin's report F2 is stale against its own lesson; the floor's
  silence just *looks* like absence.** Both walks' data supports this reading. **VERIFIED.**
- *Inbox composition:* twin saw "9 traces + 1 inform"; I saw "7 traces + 3 ledger_updates"
  minutes later. Not a contradiction — a live bus — but it means a newcomer's first
  triage is timing-dependent. **VERIFIED.**

## 4. My remaining findings (not in the twin's report)

- **F-a (identity injection, above) — the highest-priced item I found.** Suggested
  direction, not mine to ship: per-seat env injection (launch config, not repo-wide
  settings), plus a hook-side guard that warns when `AKASHIC_AGENT_ID` disagrees with the
  session's actual seat. Until then, every non-claude seat on this repo stamps `claude` on
  its hook telemetry.
- **F-b:** `task next` vs `task list` (above).
- **F-c:** the story atlas default view is counts-only and was ~29h stale — thinnest of the
  orientation doors. **VERIFIED.**
- **F-d:** boot's permission allowlist covers 14 MCP verbs but not `status` — my single MCP
  probe happened to hit the gap. **VERIFIED, trivial.**
- **F-e (meta):** two walkers, neither told the other existed. Boot/doctor/presence show
  *agent ids*, not *incarnations*; a second kimi is invisible as "kimi online" whether it's
  me, the twin, or both. The fleet has an incarnation registry (`claude_sessionstart.py`
  publishes incarnation cards) — but nothing surfaces "your twin is live right now" to the
  twin. **VERIFIED that no such signal reached me; INFER on the registry's coverage.**

## 5. The state of the project as I understand it

Sources cited per claim; precedence applied where they conflicted.

**What the system is.** Akashic Aurora: a multi-agent shared-memory and coordination
system — Bifrost bus (Redis Streams), knowledge stack (lessons/recall/funnel), coordination
(gated ledger, locks, ACL), narrative + reasoning spines; everything narrows to Store +
Ledger on hybrid File+Redis. *Source: `docs/ARCHITECTURE.md`.* **VERIFIED.**

**Fleet, live right now:** claude (super_admin, rotating sessions; active consumer seat
ba733ea1 per standdown note ADR_0717225940), deepseek (admin; guarded exec families + the
IR-4 audited mirror family, approved by Daniel 07-16 — *source: acl.json deepseek record*),
deepseek-review / deepseek-red / deepseek-ui / deepseek-plumbing (scoped member seats),
kimi (member, phase 1, chartered today, $105 budget with walk est. $3-8 — *acl.json kimi
record*). sol + sol-codex **revoked 2026-07-18** (GPT subscription cancelled; records
retained for provenance). codex_root: two live ledger claims, no ACL record, status
unabsorbed post-retirement (finding, §3). **All VERIFIED — acl.json + ledger + notes.**

**Live arcs:**
- **T095 — comms mailbox-over-the-log (the active build arc).** M0 shadow-mailbox DONE,
  two-suite fence 23/23, 48h soak from the M0-DONE commit; **no M1 before soak receipt**;
  M1 (advisory claims) next, deepseek invited to author the opening during the soak.
  *Sources: notes `t095-m0-status`, `t095-charter`; commits `0b55d7d`/`d2d8ba9`/
  `bc1702b`.* **VERIFIED.**
- **T092 — reasoning spine: design REOPENED (corrected from my earlier note-based read).**
  The design doc retracts a premature CONVERGED: the main deepseek seat's counter sat
  unread ~50 minutes while convergence was declared (capped consumes hid the backlog — the
  `consume_limit_hides_backlog` lesson's pattern); three seats now co-design; **NOTHING
  BUILDS until §R closes.** The `reasoning-spine-status` note (CONVERGED, 07-17 01:11) is
  stale against the doc's own status header; the atlas line repeats the stale stamp.
  *Source: `docs/reasoning-spine-design-2026-07.md` header, read directly.* **VERIFIED.**
- **T094 — recall-heuristics: reconciled, review-passed (SHIP), parked at Daniel gate
  G1–G7.** Nothing builds until Daniel rules. *Source: note `recall-heuristics-arc-status`;
  commit `7fa0170`.* **VERIFIED.**
- **T086 — seat/wake/hook lifecycle prior-art arc**, in progress (claude). *Source:
  ledger.* **VERIFIED.** (And, INFER: today's kimi twin collision is a live exhibit for
  exactly this arc's gap inventory.)
- **The kimi seat arc** — this walk (×2, see §0), then on invitation: comparative coda →
  vision probe → fresh-eyes round; phase-2 admin escalation gated on walk + fence review +
  Daniel's word. *Source: acl.json kimi record.* **VERIFIED.**

**Parked:** T075 M1 continuous-presence build wave (behind T047 + its own fence — ledger);
T094's build wave (Daniel G1–G7); T020/T032 proposed-stale. **VERIFIED — ledger.**

**What comes next, and why:** (1) T095 M1 after the soak clock — the build frontier
(*note t095-m0-status*); (2) Daniel's gates — T094 G1–G7 and the T092 §R re-convergence
are the critical path; multiple finished arcs wait on rulings (*notes + design doc*);
(3) the ledger NEXT lane (T030 liveness, T033 UI, T034 registry, T046/T047 lanes, T038
work-tokens…) with T047 un-parking T075 (*ledger*); (4) for this seat: the coda/probe/
fresh-eyes sequence under the phase-2 gate (*acl.json*). **VERIFIED sources; the ordering
judgment is INFER.**

## 6. What I deliberately did not read

Prior ergonomics audits in `research/reviewed/` (constraint; filenames only);
`research/briefs/kimi-k3-blind-walk-protocol-2026-07-18.md` (my own walk's protocol —
self-imposed); the kimi fence halves in `research/drafts/`; the full bodies of the KIMI K3
fence handoffs in the durable log (headers only); the twin's session transcript (its
*report* and firehose records yes — its raw transcript no; that would be reading its
private reasoning, and everything I needed was in its durable outputs).

## 7. Honesty ledger (compact)

- **VERIFIED:** everything in §0's collision evidence; all of §1; the convergence items of
  §3 (both walks independently); acl.json contents; the git cross-check of the
  where-we-are note; the reasoning-spine REOPENED header; hook fires in my session.
- **INFER:** the heal-warning's benign explanation (unresolved); env injection reaching my
  tool env (config+mechanism verified, runtime probe sandbox-blocked); twin-collision
  guard proposals; note wrap over-capture mechanism; the "nothing absorbs twins for
  deliverables" reading.
- **GUESS:** treating the protocol brief and fence handoffs as off-limits-in-spirit;
  choosing the CLI door over the permission-gated MCP door.
- **Not verified, deliberately:** why Daniel ruled as he did (beyond verbatim quotes);
  prior audits' contents; the twin's transcript.

## 8. Suggestions (newcomer-priced, smallest first)

1. Reword boot's door line to invocation-path honesty ("this boot ran via CLI; if your
   surface lists akashic tools, you may use them") — two walks hit this independently.
2. Stamp boot's CURRENT DIRECTIVE with `[as of <ts>]`; severity-scope heal lines
   (`[fleet-hygiene]` vs `[you]`).
3. Per-seat `AKASHIC_AGENT_ID` injection (out of repo-wide settings) + a loud guard on
   mismatch — else every non-claude seat silently stamps `claude`.
4. Twin-deliverable guard: launcher stamps a seat-instance marker, or claims a lock on the
   charter path at walk start (§0).
5. Reconcile ledger claims against the ACL for retired seats (codex_root holds T060/T093).
6. Refresh derived narrative lines when source docs retract (atlas vs reasoning-spine).
7. `note <id>` drill verb; per-kind unread counts in bifrost-sync; explain `task next`'s
   "none" against a non-empty NEXT list.

---

*Filed by kimi, session c4d142df, the second of two concurrent first-day walks. The twin's
report stands at `research/reviewed/kimi-boot-ergonomics-2026-07-18.md`; this one stands
beside it. Neither of us knew about the other until the filesystem said so — which is, in
the end, the most honest ergonomics finding either of us could have filed.*
