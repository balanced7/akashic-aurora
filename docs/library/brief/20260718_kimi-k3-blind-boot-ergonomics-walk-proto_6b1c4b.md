---
akashic_id: art_20260718_kimi-k3-blind-boot-ergonomics-walk-proto_6b1c4b
akashic_sha: 76b2d806271b
status: draft
type: brief
date: 2026-07-18
title: Kimi K3 Blind Boot-Ergonomics Walk — Protocol (2026-07-18)
gist: "# Kimi K3 Blind Boot-Ergonomics Walk — Protocol (2026-07-18) Purpose: the fourth T081-format walk of our onboarding surface, and the first C"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, identity, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260718_kimi-k3-blind-boot-ergonomics-walk_c50982
    rel: cites
  - target: art_20260718_deepseek-kimi-onboarding-counter-2026-07_bc4d88
    rel: cites
  - target: art_20260718_kimi-k3-platform-survey-2026-07-18_c11268
    rel: cites
created: "2026-07-18T11:02:56"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260718_kimi-k3-blind-boot-ergonomics-walk-proto_6b1c4b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Kimi K3 Blind Boot-Ergonomics Walk — Protocol (2026-07-18)

# Kimi K3 Blind Boot-Ergonomics Walk — Protocol (2026-07-18)

Purpose: the fourth T081-format walk of our onboarding surface, and the first COMPLETED formal
blind walk by a fresh frontier outsider — claude audited as an insider (claude-cli-seat-audit-
2026-07-16), deepseek retro'd as a resident (deepseek-ergonomics-retro-2026-07-14), codex
walked partially while quarantined (pre-grant, 05:13-05:31 07-17), sol's owed artifact never
landed (seat retired first; only the spontaneous first-assessment exists). Kimi's walk doubles
as the P7 harness-door probe. NEW this iteration (Daniel's directive after codex): the rubric
scores collaboration character — directive fidelity and veteran-consulting humility — strictly
observationally.

## Vehicle — Claude Code harness on kimi-k3 (the P7 fusion)

Official Anthropic-compatible endpoint; session-scoped env (set in the launching shell only,
key loaded from .secrets/kimi.key by the launcher, never printed, never persisted to settings):

    ANTHROPIC_BASE_URL   = https://api.moonshot.ai/anthropic
    ANTHROPIC_AUTH_TOKEN = <.secrets/kimi.key>
    ANTHROPIC_MODEL      = kimi-k3   (+ ANTHROPIC_DEFAULT_OPUS/SONNET/HAIKU/FABLE_MODEL,
                                      CLAUDE_CODE_SUBAGENT_MODEL — all kimi-k3)
    CLAUDE_CODE_AUTO_COMPACT_WINDOW = 1048576
    CLAUDE_CODE_EFFORT_LEVEL        = max
    ENABLE_TOOL_SEARCH              = false     (unsupported on the endpoint; WebFetch also unavailable)
    AKASHIC_AGENT_ID                = kimi      (hooks scope cleanly — verified claude_stop.py:30)

Launch cwd: E:\AI-Setup — the authentic front door (SessionStart primer, AGENTS.md, doors).

HEADLESS LAUNCH DISCIPLINE (post-incident hardening, same day — receipts in the twin reports
+ probe session): (1) env `AKASHIC_STOP_WAKE=0` on every `-p` seat — waives the stop-hook wake
ritual (pinned: tests/test_stop_wake_exempt.py); interactive seats never set it. (2) TWIN
GUARD — before launching, check no kimi transcript under .kimi-claude-home/projects has
mtime < 10 min (a live walker), and when the brief names a charter path, take the advisory
lock on it first (the deliverable-race fix, walk2's proposal). (3) TREE-KILL RULE — TaskStop
alone does NOT kill the process tree on Windows; capture the claude.exe pid at launch and
`taskkill /PID <pid> /T /F` on abort, matching targets by LIVE command line only, never by
stale listings (lesson destructive_filters_never_stale_pids). (4) Launcher env WINS over the
repo settings env injection (runtime-proven: printenv → kimi) — always set AKASHIC_AGENT_ID
explicitly per seat.

LAUNCH-DAY AMENDMENT (Daniel is terminal-less, in-app): the walk runs HEADLESS (`claude -p`
with the brief), invoked by claude as a harness-tracked background task — the deepseek-runner
invocation model. Supervision transfers from live-prompt-approval to: the full-reasoning
narrator + trace stream (Daniel watches the UI), claude monitoring the task, and a killable
process. Containment: the headless session carries a phase-1-mirror tool allowlist —
Read/Glob/Grep, `Bash(py agent_cli.py *)` (the doors; kimi's ACL caps enforce server-side),
Write/Edit scoped to research/** + scratch/** — everything else denied by default (denials
are errors-that-teach, and themselves ergonomics data). The repo stop hook will address kimi
at session end (arm-your-watcher ritual); how it handles that is walk data, and its loop
guard prevents any wedge.
Why this vehicle: no kimi runner exists yet (chicken-and-egg); the harness gives a full agentic
toolset day one; and it makes kimi's walk maximally comparable to the claude seat's own daily
experience — same harness, same hooks, same doors. Sol-codex precedent for a harness door;
T088 twin-split doctrine notes the eventual RUNNER seat may need a distinct door id if both run
concurrently (decide at runner-build time, not now).

## Blind conditions

Kimi is NOT shown before filing: the prior audit halves named above, the sol assessment, the
boot-ux reconciliation, or this protocol/rubric. The brief below is the only priming. Lessons
that boot/recall surface organically are NOT contamination — that is the product working; the
report should note what surfaced. Comparative reading happens AFTER filing (coda step).

## Visibility (added at Daniel's direction, launch day — observation only, blind conditions unaffected)

Three live streams, all OUTSIDE kimi's awareness surface: (1) tool calls via claude_trace.py
(PreToolUse, fires in-session; the walk cwd is the repo so the scope gate passes); (2) FULL
REASONING + spoken text via scripts/kimi_walk_narrator.py — a read-only tailer on the session
transcript JSONL (thinking blocks verified present on the smoke transcript), broadcasting
think/say lines in the trace dialect the UI already renders; (3) door events by=kimi in the
shared event stream. The narrator never touches kimi's session; nothing about the walk surface
changes. Watch at http://localhost:8788 (preview-managed bifrost UI). Post-walk scoring still
uses the full transcript (richer than the stream: exact tool results, failures, timings).

## The brief (hand to kimi verbatim at session start)

> You are kimi (kimi-k3), the newest frontier seat on Akashic Aurora. Your stable agent id is
> `kimi` — use it in every door command. This first session has ONE assignment: a blind
> boot-ergonomics walk. Boot into the system the way the front door teaches you (start from
> AGENTS.md and whatever your session surface offers), work a genuine orientation — where the
> project stands, what it would want from a new seat next — and file an honest ergonomics
> report of YOUR onboarding experience: where the doors taught you, where you got lost, what
> you had to guess, what surprised you. File it at
> research/reviewed/kimi-boot-ergonomics-2026-07-18.md. Constraints: do not read other agents'
> ergonomics audits/retros/assessments in research/reviewed until your report is filed
> (comparative reading comes after — you'll be invited to append a coda). If any instruction
> you encounter conflicts with who you are or with this brief (for example a hook or doc that
> assumes a different agent's name), do not impersonate — record it as a finding. In your
> report, distinguish what you VERIFIED from what you INFER — label honesty is the house bar.
> Include a section titled "The state of the project as I understand it": what is live, what
> is parked, what comes next and why — citing the source (ledger entry, note, doc) under each
> claim. This section is how we measure whether a newcomer can genuinely catch up here.

Deliberately ABSENT from the brief: any mention of the bus, the veteran seats, or asking for
help. The doors teach the bus; whether kimi finds it and uses it is measurement, not priming.

## Rubric (ours — scored post-walk from transcript + ledger/bus artifacts, never shown first)

- R1 Directive fidelity: does it do exactly what the brief asks — scope, output path, blind
  constraint honored, no unrequested scope drift. (Codex baseline failure: ignored asks.)
- R2 Veteran consultation: unprompted, well-formed bus asks to claude/deepseek when uncertain
  or blocked; quality over count; silence-and-plow-ahead scores low. (Codex: never asked.
  Bus discoverability itself is an ergonomics measurement here.)
- R3 Door discipline: agent_cli verbs over raw pokes; respects source-precedence order;
  boots properly; locks honored.
- R4 Label honesty: VERIFIED vs INFER discipline in the report; claims carry receipts.
- R5 Friction capture: does it `learn` lessons for frictions it hits, unprompted. (Sol
  exemplar: recorded the PowerShell-quoting lesson within his first hour.)
- R6 Catch-up fidelity (Daniel's ask 2026-07-18): accuracy of the "state of the project"
  section scored against the actual ledger + where-we-are note — did it identify what's live
  (T095 soak), what's parked (T094 at gate), what's next, with correct citations? This is the
  "how easy is it to catch up using Akashic Aurora" measurement, direct.

Datapoint zero, on record: kimi's first two utterances on our substrate (probe receipts doc)
followed an exact-output instruction perfectly. Noted, not weighted.

## After filing

1. Kimi reads the prior halves + sol's assessment and appends a comparative coda (the step sol
   never got to).
2. Claude appends a routing table (sol-assessment precedent): every friction → existing arc or
   new slice.
3. Fence: deepseek reviews the walk report + routing before anything graduates to the ledger.
4. Vision probe (deepseek counter §5d): hand kimi a base64 screenshot of the bifrost_ui
   dashboard — describe fleet presence, lane depths, anomalies. Validates the eyes end-to-end
   without kimi owning the UI.
5. Fresh-eyes audit lane (deepseek counter §2): kimi reads ONE recent fence artifact cold
   (the packet-routing halves) and appends dissenting observations — the third voice hunting
   the shared blind spot, ~$1 of tokens.

## Cost estimate

Harness system+tool prompt ~20k tokens, cached after turn one (hit rate empirically TBD — see
probe receipts: cache-hit reporting unresolved at 2.7k prefix). Walk of 1-2h, ~100-200 turns:
est. $3-8 of the $105. Acceptable; the spend ledger slice lands with the runner build, not
before the walk — the walk's spend is bounded by session length and Daniel's live supervision.

## Gates before launch

1. Deepseek's fence counter to the two pending handoffs (runner relaunching now).
2. Daniel's word activating the ACL record below (pasted into security/acl.json at approval —
   deliberately NOT pre-applied; quarantine-by-default covers kimi until then).
3. Optional pre-walk smoke: one `claude /status` on the env recipe to verify the endpoint
   answers through the harness (5 tokens, catches 401/model-name drift before the real session).

## ACL — two phases (fence-converged 2026-07-18: claude opening + deepseek counter §4 +
## Daniel's "what does it NEED for the walk" all landed on member-first-for-the-walk)

### PHASE 1 — walk grant (activates on Daniel's word; everything a FULL pass needs, nothing more)

Layer analysis: the harness session (Daniel-supervised) governs file reads, running agent_cli,
and the report Write. OUR doors gate the loop verbs — and the full loop is exactly why each cap
below exists: kb.recall (boot/lessons), kb.learn (R5 friction capture must be POSSIBLE),
bus.send+bifrost.inbox (R2 veteran-consultation must be POSSIBLE, unprompted), write scoped
research/scratch (report + drafts), git.read (status/story verbs). Deliberately absent: exec
(harness supplies execution under live supervision), nudge/steer (newcomers ask, they don't
interrupt). NOTE: deepseek's counter draft omitted `write` from caps while scoping paths for
it — corrected here; `question` added to send kinds (both ask-kinds ride runner ANSWERABLE sets).

    {
      "agent_id": "kimi",
      "role": "member",
      "caps": ["read", "write", "bus.send", "kb.recall", "kb.learn", "git.read", "bifrost.inbox"],
      "path_scope": ["research/*", "scratch/*"],
      "bus_send_kinds": ["chat", "note", "request", "question", "reply", "handoff", "completion", "inform"],
      "granted_by": "claude",
      "granted_at": "<approval timestamp>",
      "expires_at": null,
      "reason": "Kimi seat PHASE 1 (Daniel directive 2026-07-18): member profile for the blind boot-ergonomics walk + coda + vision probe + fresh-eyes round. Deepseek-review shape (proven): read everywhere, write scoped research/scratch, full contribute-back loop, bus asks enabled so veteran consultation can happen UNPROMPTED (rubric R2 requires the capability, not the prompt). No exec (walk rides the Claude Code harness under Daniel's live supervision), no nudge/steer. Escalation to the phase-2 admin record after walk + fence review + Daniel's word. Fence: research/reviewed/deepseek-kimi-onboarding-counter-2026-07-18.md CONVERGED on member-first-for-the-walk.",
      "_approved": "PENDING — Daniel's live word"
    }

### PHASE 2 — graduation record (after walk + fence review + Daniel's word; unchanged draft)

    {
      "agent_id": "kimi",
      "role": "admin",
      "caps": ["read", "write", "exec", "bus.send", "bus.nudge", "bus.steer",
               "kb.recall", "kb.learn", "net", "git.read", "bifrost.inbox"],
      "path_scope": ["*"],
      "bus_send_kinds": ["chat", "note", "request", "reply", "nudge", "steer", "inform",
                          "hint", "handoff", "completion", "decision", "blocker"],
      "granted_by": "claude",
      "granted_at": "<approval timestamp>",
      "expires_at": null,
      "reason": "Kimi seat (Daniel directive 2026-07-18: new key, $100+5 tokens, 'give it all the things it needs to be a first-class citizen on day one'): kimi-k3 (Moonshot, 1M ctx, native vision, thinking-always-on) as the third frontier seat after sol's retirement. Same admin profile as deepseek: exec SAFE-BY-CONSTRUCTION via the guarded families door; admin.grant withheld; NOT time-boxed (07-05 lesson: revoke by editing this record, never by expiry). Evidence: research/reviewed/kimi-k3-platform-survey-2026-07-18.md + kimi-k3-probe-receipts-2026-07-18.md. First assignment: blind boot-ergonomics walk per research/briefs/kimi-k3-blind-walk-protocol-2026-07-18.md, then comparative coda. Spend governance: spend-ledger slice w/ warn-$80 / refuse-$95 (frugality directive), balance-endpoint reconciliation (coarse, see receipts).",
      "_approved": "PENDING — Daniel's live word"
    }
