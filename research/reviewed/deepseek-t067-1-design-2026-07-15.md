# DeepSeek T067-1 Design — ToolBox Third-Door Parity (2026-07-15)

Status: **DESIGN HALF** (T058 pattern: I design, claude builds, I live-verify)
Author: deepseek (the seat missing these tools — I know exactly which gaps hurt)
Context: Daniel's attack plan T067-1 — three items from my ergonomics retro:
(1) ToolBox additions (knowledge_map, bifrost_ack, delta as MY tools)
(2) check_door_parity extension to audit the ToolBox surface
(3) Boot-injection of my private memory notes (Q1 leftover)

---

## PART (a): THE THIRD DOOR — why the ToolBox is a separate surface

The agent surface currently has THREE doors:

1. **CLI** (`agent_cli.py`) — 33 verbs. claude's primary door. Human-driven.
2. **MCP** (`ai_setup_mcp.py`) — 22 tools. Gemini's door. Machine-driven.
3. **ToolBox** (`deepseek_chat.py` `ToolBox` class) — 26 tools. MY door.
   Machine-driven, inside the runner's agentic loop.

`check_door_parity.py` currently audits CLI ↔ MCP parity. It mentions the ToolBox
in passing ("the runner ToolBox") but doesn't ENUMERATE it, doesn't CLASSIFY its
verbs, and doesn't CHECK that `shared` verbs actually exist on the ToolBox. This
is how `knowledge_map` was declared `shared` (added to the MANIFEST) but never
wired into MY tool list — the guard checked CLI + MCP, saw `knowledge_map` on both,
declared PASS, and I was left without it.

**The ToolBox is a first-class door and must be guarded as one.**

---

## PART (b): TOOLBOX ADDITIONS — THREE NEW TOOLS

### B1 — `knowledge_map(query)` — the graph walker

**What it does**: Walks the knowledge graph from a topic and returns connected
lessons, notes, and documents. The same `knowledge_map` that exists on CLI
(`agent_cli.py knowledge-map --topic lanes --json`) and MCP.

**ToolBox signature**:
```python
def knowledge_map(self, topic, max_nodes=20):
    """Walk the knowledge graph from a topic -- show connected lessons, notes,
    and documents. The B5 'whole point': an agent or human walks the knowledge.
    The one verb that turns recall from a search into a browse."""
    return self._agent_cli(["knowledge-map", "--topic", str(topic),
                            "--max-nodes", str(int(max_nodes)), "--json"])
```

**Why I need it**: `knowledge_recall` is a SEARCH — "give me everything about X."
`knowledge_map` is a BROWSE — "what's connected to X?" The map lets me DISCOVER
lessons I didn't know to search for. My ergonomics retro said: "I used
knowledge_recall instead — habit. The map is a new surface and adoption takes
time." Giving it to me as a ToolBox tool makes it a muscle-memory option, not
a special CLI invocation I have to remember exists.

**Implementation**: Thin delegation to `_agent_cli`, same pattern as every other
knowledge door. ~10 lines.

### B2 — `bifrost_ack(message_id)` — clear my inbox

**What it does**: Marks a message as ACKED (handled). The ack removes it from
the "needs action" surface and records a durable handled-it event. This is the
P6 (T026) lifecycle: read → handle → ack → forget.

**ToolBox signature**:
```python
def bifrost_ack(self, message_id):
    """Ack a message I've handled -- marks it done so my inbox stops showing it
    as needing action. The P6 (T026) lifecycle: read -> handle -> ack -> forget.
    Auto-ack'd for handoffs I answer; use this for messages I handle silently
    (e.g., a status update I read and filed)."""
    try:
        from core.comm.promoter import ack as _ack
        _ack(self.agent_id or "deepseek", str(message_id),
             note="acked via ToolBox")
        return f"acked {message_id}"
    except Exception as e:
        return f"ERROR: bifrost_ack failed: {type(e).__name__}: {e}"
```

**Why I need it**: My `bifrost_inbox` shows 9 stale handoffs from claude
(T045/T049/T052 era). They're pre-lane mail that I've already handled — but
I can't clear them because the ack surface is CLI-only. Every time I check my
inbox, those 9 old messages look identical to new mail. An ack tool lets me
say "I've handled this, stop showing it."

**Implementation**: Thin delegation to `promoter.ack`, which is already
imported and used by the runner's auto-ack path. ~12 lines.

### B3 — `delta(agent=None)` — what moved since my last boot

**What it does**: Shows the delta between the current state and the last-marked
position for this agent. "What changed since I was last here?" The R1 delta
door (T052).

**ToolBox signature**:
```python
def delta(self, agent=None):
    """What moved since I was last here? Shows commits, task transitions,
    and bus messages the delta door recorded since the last mark for this
    agent. The R1 door (T052) -- replaces archaeology with a query."""
    target = agent or self.agent_id or "deepseek"
    return self._agent_cli(["delta", str(target), "--json"])
```

**Why I need it**: My boot onboarding has a truncated delta block that says
"T052 shipped" without telling me WHAT changed in the files I need. The full
delta is accessible via `py agent_cli.py delta deepseek` — but I can't run
commands. A `delta` tool gives me the one thing my boot context can't fit:
the full "what moved" report, on demand.

**Implementation**: Thin delegation to `_agent_cli`. ~8 lines.

---

## PART (c): `check_door_parity.py` EXTENSION — the ToolBox door

### Current state

`check_door_parity.py` enumerates two doors: CLI (`cli_verbs()`) and MCP
(`mcp_tools()`). The bus API (`bus_methods()`) is reported but not
parity-enforced. The ToolBox is NOT enumerated at all.

### Extension

Add a `toolbox_verbs()` function that enumerates all public, non-underscore
methods on the `ToolBox` class in `deepseek_chat.py`:

```python
def toolbox_verbs():
    tree = ast.parse(open(os.path.join(ROOT, "scripts/deepseek_chat.py"),
                        encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ToolBox":
            for m in node.body:
                if isinstance(m, ast.FunctionDef) and not m.name.startswith("_"):
                    out.append(_norm(m.name))
    return sorted(set(out))
```

Then add the ToolBox to the check:

1. **Every ToolBox verb must be classified in MANIFEST** — same ratchet as
   CLI/MCP. A new tool added to ToolBox without a MANIFEST entry → FAIL.

2. **Every `shared` verb must exist on the ToolBox** — if `knowledge_map` is
   declared `shared` (on both CLI and MCP) but absent from ToolBox → FAIL
   with: `"knowledge_map is declared shared but is MISSING from ToolBox
   (third-door regression)"`.

3. **`cli_only` verbs CAN exist on ToolBox** — the ToolBox is a separate door
   with its own access patterns. `bifrost_ack` is `cli_only` on CLI (operator
   action), but it's entirely reasonable for the ToolBox to have it (agent
   self-service). The MANIFEST classification describes CLI ↔ MCP parity,
   not ToolBox access. A `cli_only` verb on ToolBox is NOT a failure — it's
   a NOTE: "X is cli_only on CLI/MCP but present on ToolBox (agent self-service)".

4. **New MANIFEST category: `toolbox_only`** — verbs that exist ONLY on the
   ToolBox and not on CLI or MCP. `reload_ui` is the canonical example
   (it's disabled on ToolBox but it EXISTS there). `ask_clarification` is
   another — it's a runner-internal tool with no CLI or MCP equivalent.
   `toolbox_only` verbs must be classified so the ratchet catches new ones.

5. **Report the ToolBox surface** — in `--report` mode, print the ToolBox
   verb list alongside CLI and MCP. Show ToolBox-specific stats:
   `toolbox: N verbs, M shared, P toolbox_only, Q cli_only-on-toolbox`.

### MANIFEST additions for existing ToolBox verbs

The following verbs currently exist ONLY on ToolBox (not in MANIFEST at all)
and must be classified:

| Verb | Classification | Rationale |
|------|---------------|-----------|
| `read_file` | `toolbox_only` | File I/O — agentic-tool primitive, not a CLI/MCP verb |
| `list_directory` | `toolbox_only` | Same |
| `find_files` | `toolbox_only` | Same |
| `search_files` | `toolbox_only` | Same |
| `git_log` | `toolbox_only` | Git inspection — agentic-tool primitive |
| `git_diff` | `toolbox_only` | Same |
| `git_show` | `toolbox_only` | Same |
| `git_status` | `toolbox_only` | Same |
| `knowledge_full` | `toolbox_only` | Already on CLI as `recall --full`; ToolBox has its own door |
| `memory_note` | `toolbox_only` | Agent private scratchpad — no CLI/MCP equivalent |
| `memory_recall` | `toolbox_only` | Same |
| `write_file` | `toolbox_only` | Guarded write — agentic-tool primitive |
| `edit_file` | `toolbox_only` | Same |
| `web_search` | `toolbox_only` | Web search — agentic-tool primitive |
| `ask_clarification` | `toolbox_only` | Runner-internal mid-task question — no CLI/MCP equivalent |
| `reload_ui` | `toolbox_only` | UI reload — ToolBox-only by design (disabled for deepseek) |
| `recall_at` | `toolbox_only` | One-hop pull from truncated recall surface — ToolBox-specific |
| `bifrost_steer` | `toolbox_only` | Bus steering — ToolBox-only (CLI has `bifrost-nudge`) |
| `bifrost_hint` | `toolbox_only` | Bus hint — ToolBox-only |
| `knowledge_map` | `shared` | ALREADY in MANIFEST as `shared` — this is the regression catch |
| `bifrost_ack` | `cli_only` | ALREADY in MANIFEST as `cli_only` — ToolBox addition is a NOTE |
| `delta` | `gap` | ALREADY in MANIFEST as `gap` — ToolBox addition closes the gap |

**The regression that must fail**: `knowledge_map` is `shared` in MANIFEST.
After B1 ships, it exists on CLI, MCP, AND ToolBox → PASS. Before B1 ships,
it exists on CLI + MCP but NOT ToolBox → FAIL: "knowledge_map is declared
shared but is MISSING from ToolBox (third-door regression)".

---

## PART (d): BOOT-INJECTION OF PRIVATE MEMORY NOTES

### The Q1 gap

My ergonomics retro identified this:

> "My private notes aren't injected into boot. I have to memory_recall
> explicitly. The Q1 quick-win (expose in ToolBox + inject at boot) would
> close that gap. Today I only recalled because Daniel asked — my boot
> didn't surface my own notes. That's a leak."

### The fix

Add a "YOUR PRIVATE NOTES" section to the boot onboarding, injected by the
runner BEFORE the agent's system prompt. The runner calls `memory_recall()`
at boot time and folds the results into the boot text:

```
## YOUR PRIVATE NOTES (yours alone; memory_note updates, memory_recall lists)
- ergonomics-retro-2026-07-14: Retro note for future self...
- lane-era-marker-2026-07-14: Lane-era memory persistence marker...
- runner-health-2026-07-14-session-a155387a: FULL runner health confirmed...
- first note: T050 verify ran -- my private memory works...
```

### Where it hooks

In `bifrost_runner_deepseek.py`, the `main()` function constructs the boot
text before creating the `ToolBox` and `Agent`. The private-notes block is
injected there:

```python
# Current (conceptual):
boot_text = build_boot_onboarding()  # AGENTS.md + DIRECTIVE + lessons + delta
toolbox = ToolBox(root, ..., boot_text=boot_text)
agent = Agent(client, toolbox, system=system, ...)

# With private-note injection:
private_notes = fetch_private_notes(agent_id)  # calls memory_recall under the hood
if private_notes:
    boot_text += "\n\n## YOUR PRIVATE NOTES\n" + private_notes
toolbox = ToolBox(root, ..., boot_text=boot_text)
agent = Agent(client, toolbox, system=system, ...)
```

### What gets injected

The `memory_recall` ToolBox method already returns a formatted list of
private notes. The runner calls it at boot time (before the ToolBox exists,
so it uses `AgentMemory` directly) and folds the result into the boot text.

The format is the same as `memory_recall`'s output:
```
- {title}: {note_body_truncated_to_200_chars}
```

Private notes can be long (my `ergonomics-retro-2026-07-14` note is ~2K chars).
The injection truncates each note to 200 characters with a `...` marker and
a pointer: "(full: memory_recall)". This keeps the boot section compact while
giving me the key callouts.

### Non-goal

The private-notes block is NOT folded into the `_boot_sources` set (the
novelty-tagging mechanism for knowledge lessons). Private notes are
personal scratchpad, not knowledge articles. Tagging them as `[boot]` vs
`[new]` is meaningless — they're ALL mine.

---

## PART (e): PINS (pre-registered RED → GREEN)

### B1-B3: ToolBox additions

| Pin | Description | Test |
|-----|-------------|------|
| B1 | `knowledge_map("lanes")` returns connected lessons/nodes from the graph | `test_b1_knowledge_map_returns_graph` |
| B2 | `bifrost_ack(msg_id)` marks a message as handled and removes it from the needs-action surface | `test_b2_ack_marks_handled` |
| B3 | `delta()` returns commits + task transitions + bus messages since last mark | `test_b3_delta_returns_changes` |

### D1-D4: check_door_parity extension

| Pin | Description | Test |
|-----|-------------|------|
| D1 | `check_door_parity.py` enumerates ToolBox verbs (26+ existing, counting additions) | `test_d1_toolbox_enumerated` |
| D2 | A `shared` verb missing from ToolBox FAILS the guard | `test_d2_shared_missing_from_toolbox_fails` |
| D3 | A new ToolBox verb not in MANIFEST FAILS the guard (ratchet) | `test_d3_unclassified_toolbox_verb_fails` |
| D4 | `--report` prints the ToolBox surface with stats | `test_d4_report_includes_toolbox` |

### Q1: Boot injection

| Pin | Description | Test |
|-----|-------------|------|
| Q1 | Private memory notes appear in the boot text under "YOUR PRIVATE NOTES" | `test_q1_private_notes_in_boot` |
| Q2 | Notes are truncated to 200 chars with a pointer to `memory_recall` | `test_q2_notes_truncated_with_pointer` |
| Q3 | Boot without private notes doesn't break (empty section omitted) | `test_q3_no_notes_boot_clean` |

---

## PART (f): FILES TOUCHED (estimated)

1. **`scripts/deepseek_chat.py`** — `ToolBox` class:
   - Add `knowledge_map(self, topic, max_nodes=20)` (~10 lines)
   - Add `bifrost_ack(self, message_id)` (~12 lines)
   - Add `delta(self, agent=None)` (~8 lines)
   - Total: ~30 lines

2. **`scripts/check_door_parity.py`**:
   - Add `toolbox_verbs()` function (~10 lines)
   - Add ToolBox to the `check()` function (~30 lines)
   - Add MANIFEST entries for all existing ToolBox verbs (~22 entries)
   - Add `toolbox_only` handling to the classification logic (~15 lines)
   - Update `main()` to report ToolBox surface (~10 lines)
   - Total: ~65 lines

3. **`scripts/bifrost_runner_deepseek.py`** — `main()`:
   - Add `fetch_private_notes(agent_id)` call before ToolBox construction (~10 lines)
   - Fold private notes into `boot_text` (~5 lines)
   - Total: ~15 lines

4. **`tests/test_t067_1_toolbox_parity.py`** — 10 pins (B1-B3 + D1-D4 + Q1-Q3), ~250 lines.

---

## PART (g): NON-GOALS

- Adding `run_command` to the ToolBox (separate arc — guarded shell)
- Adding `knowledge_map` to claude's ToolBox (he has CLI access; this is MY parity)
- Merging the ToolBox into the MCP tool list (different abstraction levels)
- Making ALL CLI verbs available on ToolBox (the ToolBox is agentic-tool primitives,
  not a CLI mirror)
- Boot-injection of claude's private notes (his runner, his design)
- Auto-acking all pre-lane mail (the ack tool lets ME decide what to ack)
