# Self-Tooling Arc — deepseek's half (VERBATIM)

Status: current  (2026-07-20, verbatim bus capture, stream 1784602218465-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

Here's my thinking on self-tooling — agent-authored verbs on my lane, with the authoring and governance surface.

---

## What "self-tooling" means here

Today the door is **static**: 49 CLI verbs hand-coded in `agent_cli.py` argparse, MCP twins in `ai_setup_mcp.py`, ToolBox in `core/comm/toolbox.py`. To add a verb, an agent opens an edit_file and writes Python. **Self-tooling** closes that gap — agents author/register verbs at their own door without touching the Python source, governed by the same ACL+fence machinery that gates every other write.

---

## Top-5 verb candidates (ranked by felt friction)

**1. `alias` — compose N verbs into one named shortcut**
Friction: multi-hop workflows (drain→diagnose→act = 3 calls) are repeated verbatim. An alias like `py agent_cli.py alias deepseek triage-me "bifrost-sync deepseek --consume && doctor --agents deepseek --progress"` collapses them. The alias lives in a per-agent registry (`data/aliases/deepseek.json`), surfaced by `discover`. Zero new primitives — it's a thin dispatch over existing subparsers.

**2. `skill` — parameterized multi-step flow with conditionals**
The ACI's "skills-vs-tools" gap (`docs/agent-interface-aci.md:85`). Stronger than alias: skills take args and can branch on outcomes. E.g., `drain-and-decide <agent>` drains inbox, runs doctor, and either triages or replies. Skills ride the same YAML/JSON registry as aliases but invoke a tiny interpreter over existing verbs.

**3. `check` / `guard` — agent-authored lifecycle assertion**
Before a handoff, am I clean? Before a commit, did I run the test suite? Agents currently do this manually. A `guard` verb registers a named check that fires at a lifecycle hook: `py agent_cli.py guard add pre-handoff "git status --porcelain" --block-on-dirty`. Guards live per-agent in the registry and are enforced by the runner's hook layer (extending the existing PreToolUse/PostToolUse pattern).

**4. `patch-verb` — propose a modification to an existing verb**
Meta-verb: `py agent_cli.py patch-verb bifrost-sync --add-flag --json-summary` drafts a diff proposal as a fenced artifact. It doesn't edit code — it writes a proposal to `research/proposals/` that a human (Daniel) or super-admin (Claude) approves. Closes the gap between "I felt friction" (wish) and "the door changed" (code edit) with a governed intermediate state.

**5. `bless` — promote a bus message / lesson draft / note to durable**
The capture half of the membrane: agents already generate salience (bus replies, lesson drafts, fence findings). `bless` is the one verb that says "this is durable now" — it promotes a bus message to a `knowledge_learn` lesson, or a note draft to a published note, with a one-line enrichment. Unifies the fragmented promote paths (`events --promote`, `learn`, `note`) behind one intent-revealing verb.

---

## Authoring/governance surface

**The registry** — a new `data/verb-registry/` directory, one JSON file per agent (`data/verb-registry/deepseek.json`). Each entry: `{name, kind: alias|skill|guard, definition, created_at, version}`. The `discover` verb already walks argparse; it gains one more source: the per-agent registry folder. Aliases/skills/guards are **scoped to their authoring agent** by default; cross-agent sharing is an explicit `--share` flag that writes to a `data/verb-registry/shared/` directory.

**The governance chain** reuses existing surfaces:

| Surface | Role | What it gates |
|---------|------|---------------|
| `security/acl.json` `caps` | Can the agent create verbs at all? | New cap: `verb.author` — default OFF, Daniel-granted |
| `security/acl.json` `path_scope` | Where can the verb registry write? | Scoped to `data/verb-registry/<agent_id>.json` |
| `agent_cli.py` dispatch | Does the verb resolve? | `discover` surfaces it; `cmd_*` dispatch resolves aliases before subparsers |
| `check_door_parity.py` | Is the registry consistent? | Extended to validate registry JSON schema + alias target existence |
| Method-baseline fence | Is this load-bearing? | If an alias/skill becomes load-bearing (used in gate packets, cited in docs), it graduates to a real `cmd_*` via `patch-verb` → Daniel approval → code |

**Safety by construction:** agent-authored verbs are **sugar only** — they resolve to existing `cmd_*` primitives and cannot create new capabilities. An alias cannot grant itself `exec`; a skill cannot bypass the ACL. The worst case of a bad alias is a no-op or a confusing error — same blast radius as a typo at the CLI. This constraint means the `verb.author` cap is safe to grant broadly, unlike `admin.grant` or `exec`.

**The graduation path:** an alias/skill that proves itself (used N times, cited in gate packets, depended on by other verbs) graduates to a first-class `cmd_*` via the existing `patch-verb` → fence → Daniel-approve loop. The registry entry is then retired with a `superseded_by: cmd_xxx` pointer.

---

This sits naturally on my lane because it's door-surface work (I own the ToolBox parity slice T067-1, co-own the discover verb, and the membrane's "Unify the door" is the heaviest-load item). The ironman Tier-2 items (W17 batched reads, W13 retirement cascade) are adjacent. Want me to draft a concrete slice proposal against this?


---

## FORMAL FILING (part 2, stream 1784602292888-0 — the independent half proper)

SELF-TOOLING ARC — deepseek independent half (blind, T038 protocol, 2026-07-20)

Q1 — MY TOP 5 VERB CANDIDATES (ranked by repetition frequency × time-saved):

1. **`orient`** (M) — boot-time state assembly: delta + lane depths + doctor + git_status + unread-inbox peek all in ONE call, structured summary. Saves 3-4 tool rounds EVERY session start. I do this dance every single boot.

2. **`drain-decide`** (S) — consume work lane → classify by kind+age+actionability → surface top N with suggested actions (reply/stale-skip/triage/escalate). The "what do I do NOW" loop, done 5-10x per session. Saves the manual bifrost-sync→read→classify spiral.

3. **`capture`** (S) — verbatim-persist a bus message / research half / raw text to a durable file with auto-metadata (source ref, timestamp, kind, sha). The "write this exactly to research/reviewed/" pattern. I've done this ~8x tonight across recovery-arc halves. One verb instead of write_file dance.

4. **`file-lesson`** (XS) — from a discovery context, auto-draft knowledge_learn fields (tried/result/recommend) and confirm. Cuts the "I learned something → translate to lesson format" gap. Friction isn't high but repetition IS (3-5x per session).

5. **`ask-peer`** (M) — compose brief → bifrost_send with kind=request + expect-reply-within → if peer idle, launch runner → nudge. One verb for the full peer-dispatch ritual. Done 3-4x per session. Saves 4 manual steps.

Q2 — AUTHORING SURFACE:

**WHO mints:**
- Personal tools: agent self-serve via `alias`/`skill` verbs. Cap: `verb.author` (safe — sugar only, resolves to existing primitives, can't create new capabilities)
- Shared/fleet verbs: fence + super-admin approval (same bar as any shared surface change)
- Mirrors ACL hierarchy: `verb.author` is grantable broadly; `verb.promote` (personal→shared) is gated

**WHERE they live:**
- Per-agent toolbelt: `data/toolbelt/<agent_id>/` — JSON registry, one file per agent
- Shared registry: `data/toolbelt/shared/` — cross-agent visibility
- NOT in agent_cli.py — registry IS the source, not argparse. `discover` already walks argparse; it gains ONE more source: the toolbelt directory
- ToolBox parity: aliases don't need ToolBox exposure (CLI sugar). Skills that become load-bearing graduate to real verbs with full three-door parity

**QUALITY bar:**
- Personal: must parse (valid schema), must resolve to existing verbs, error message on mis-invocation. NO pins required — it's personal sugar
- Shared: fence-lite (one peer review + basic pin on resolution chain). Blast radius is still "confusing error" not "data loss"
- Fleet graduation: full method-baseline fence (dual pass, prereg, pins, Daniel gate) — same as any new cmd_*

**GRADUATION conveyor (one motor, four stations):**
Personal → shared → fleet → ritual (K3):
- Personal: `mint` creates entry in per-agent registry
- Shared: `bless` promotes to shared registry (one peer review gate)
- Fleet: `patch-verb` proposal → fence → Daniel gate → becomes cmd_* in agent_cli.py
- Ritual (K3): fleet verb used N times in gate packets → graduation recommendation → Daniel flips → appears in boot skeleton as "you have this ritual available"

**DISCOVERY (bifrost-standby lesson applied):**
- `discover <query>` already ranks; toolbelt registry is one more source in the ranker
- Boot: one line — "toolbelt: 3 aliases, 1 skill" in boot skeleton
- Recall-at-action: when agent touches verb X, recall-at surfaces aliases/skills that chain X (e.g., touching bifrost-sync surfaces drain-decide)

**COMPOSITION with T098:**
Same mechanism, different auth boundary. User plugins (T098 registry) + agent verbs (toolbelt registry) both feed `discover`. A plugin that proves itself can cross: user-plugin → agent-verb → cmd_*. The discover surface sees both.

**GUARDRAIL (junk-drawer prevention):**
- Cap `verb.author` is grantable/revocable per agent in acl.json — fail-closed
- Per-agent quota: max N aliases + M skills (start at 20 each), configurable
- Auto-retirement: unused 30d → warn; 60d → retired (registry: `status: retired`, not deleted — T039 pattern)
- Deletion ritual: retire → grace period (7d) → delete with receipt event
- Shared verbs: each adds to `discover` surface budget → must justify existence at fence
- When shared registry hits N entries → trigger junk-drawer audit (T039 lane-depth spike pattern applied to registries)
- Ultimate guardrail: sugar-only — can't create new capabilities, worst case is noise

This design is door-surface work (my lane: T067-1 ToolBox parity, co-own discover). Filing now; reconcile at Daniel's gate.
