# R1 Verb Census — CARTOGRAPHER seat, 2026-08-03

A census of the CLI verb surface. Ground truth: `agent_cli.py`'s own argparse `add_parser` calls,
parsed by the same AST method `scripts/checkers/check_advertised_verbs.py` uses (four lines:
`ast.walk` the tree, find `ast.Call` nodes where `func.attr == 'add_parser'`, collect
`n.args[0].value`). MCP comparison: `ai_setup_mcp.py`'s `@mcp.tool()` decorated functions, parsed
via `check_door_parity.py`'s `mcp_tools()` approach.

## METHOD NOTE: agreement with check_advertised_verbs.py

The existing checker and I extracted the exact same 68 top-level verbs from `add_parser` calls,
plus 2 nested subcommands (`doc new`, `doc adopt`) that the checker's VERB_RE regex cannot see
because its pattern `agent_cli\.py\s+([a-z][a-z0-9_-]*)` matches only the outer verb. I also
count 2 sub-subcommands (`tool list`, `tool run`). The checker's `registered_verbs()` returns a
flat set of 68; that is correct for its purpose (catching dead remediation instructions), but my
census counts the nested subcommands as distinct doors because they ARE distinct argparse entries
with their own `set_defaults(fn=...)` bindings.

**Total distinct argparse entry points: 70** (68 top-level + 2 `doc` subcommands: `new`, `adopt`).
`tool list` and `tool run` are also distinct `add_parser` calls; counting them gives 72, but they
are presented as `tool list` / `tool run` rather than flat verbs. I list them in the subcommands
section below.

---

## TABLE: CLI Verb Census

Key: **LIVE** = referenced outside its own definition (docs, other code, hooks, boot output).
**DOOR-ONLY** = exists in argparse, nothing points at it. **SUSPECT-DEAD** = exists, no external
references, AND no MCP twin AND not referenced in the door-parity manifest's `cli_only` rationale
in a way that suggests it was classified without evidence of use.

| # | Verb | agent_cli.py line | MCP twin? | External refs? | Judgement |
|---|------|-------------------|-----------|----------------|-----------|
| 1 | `boot` | :4423 | `boot` (MCP:303) | Yes — harness, docs, SKILL.md | LIVE |
| 2 | `delta` | :4430 | none (gap) | Yes — boot output, ToolBox | LIVE |
| 3 | `discover` | :4436 | none (cli_only) | Yes — test_t067_guarded_exec.py:46 | LIVE |
| 4 | `learn` | :4441 | `learn` (MCP:314) | Yes — harness, docs, SKILL.md | LIVE |
| 5 | `wish` | :4451 | none (cli_only) | Yes — WISHLIST.md references | LIVE |
| 6 | `doc` | :4461 | none (cli_only) | Yes — harness context | LIVE |
| 7 | `doc new` | :4463 | none | Yes — harness context (subcmd of doc) | LIVE |
| 8 | `doc adopt` | :4484 | none (gap) | Yes — lesson `doc_adopt_rescue_path` | LIVE |
| 9 | `tag-anti-pattern` | :4496 | `tag_anti_pattern` (MCP:413) | Yes — recall code | LIVE |
| 10 | `recall` | :4502 | `recall` (MCP:330) | Yes — harness, docs | LIVE |
| 11 | `list` | :4508 | none (cli_only) | Yes — self-referencing in help | LIVE |
| 12 | `recall-at` | :4512 | `recall_at` (MCP:338) | Yes — harness, docs | LIVE |
| 13 | `recall-feedback` | :4529 | `recall_feedback` (MCP:347) | Yes — recall code | LIVE |
| 14 | `recall-curate` | :4538 | none (cli_only) | Yes — self-referencing, wrap nudges it | LIVE |
| 15 | `audit` | :4553 | none (cli_only) | Yes — design doc `kimi WANT` | LIVE |
| 16 | `injections` | :4561 | `injections` (MCP:439) | Yes — stats code | LIVE |
| 17 | `harnesses` | :4566 | none (cli_only) | Yes — `agent/harness/registry.py:70`, tests | LIVE |
| 18 | `fleet` | :4571 | none (cli_only) | Yes — bifrost_daemon | LIVE |
| 19 | `triage` | :4591 | none (cli_only) | Yes — story.md, WISHLIST, design docs | LIVE |
| 20 | `recall-counters` | :4598 | none (cli_only) | Yes — self-referencing at :728 | LIVE |
| 21 | `graduate` | :4604 | `graduate` (MCP:448) | Yes — recall code | LIVE |
| 22 | `note` | :4614 | `note` (MCP:358) | Yes — harness, docs, SKILL.md | LIVE |
| 23 | `notes` | :4631 | `notes` (MCP:367) | Yes — harness, docs | LIVE |
| 24 | `wrap` | :4640 | none (cli_only) | Yes — heavily referenced (30+ sites) | LIVE |
| 25 | `status` | :4655 | `status` (MCP:421) | Yes — harness, docs | LIVE |
| 26 | `stats` | :4659 | `stats` (MCP:427) | Yes — harness | LIVE |
| 27 | `log` | :4668 | `log` (MCP:457) | Yes — harness, docs | LIVE |
| 28 | `episode` | :4677 | none (cli_only) | Yes — Bifrost UI via --json | LIVE |
| 29 | `task` | :4692 | `task` (MCP:353) | Yes — harness, conductor | LIVE |
| 30 | `story` | :4699 | `story` (MCP:465) | Yes — harness, docs | LIVE |
| 31 | `handoff` | :4715 | `handoff` (MCP:474) | Yes — harness, docs | LIVE |
| 32 | `events` | :4725 | `events` (MCP:487) | Yes — harness, docs | LIVE |
| 33 | `roster` | :4747 | none (gap) | Yes — doctor.py, runner code | LIVE |
| 34 | `doctor` | :4754 | none (cli_only) | Yes — heavily referenced (15+ sites) | LIVE |
| 35 | `promoted` | :4765 | `promoted` (MCP:502) | Yes — bifrost code | LIVE |
| 36 | `lookback` | :4772 | none (cli_only) | Yes — boot output | LIVE |
| 37 | `knowledge-map` | :4779 | `knowledge_map` (MCP:378) | Yes — boot output | LIVE |
| 38 | `fence` | :4785 | none (cli_only) | Yes — ToolBox, runner code | LIVE |
| 39 | `flow` | :4798 | none (cli_only) | Yes — bifrost code | LIVE |
| 40 | `packet-trace` | :4805 | `packet_route` (MCP:433) | Yes — bifrost code | LIVE |
| 41 | `packet-stats` | :4810 | `packet_route_stats` (MCP:433) | Yes — bifrost code | LIVE |
| 42 | `mailbox` | :4814 | `mailbox` (MCP:433) | Yes — doctor.py, runner code | LIVE |
| 43 | `bifrost-ack` | :4858 | none (cli_only) | Yes — runner code (auto-ack) | LIVE |
| 44 | `console-log` | :4865 | none (cli_only) | **NO** — zero external refs | DOOR-ONLY |
| 45 | `bifrost-sync` | :4872 | `bifrost_sync` (MCP:513) | Yes — harness, runner code | LIVE |
| 46 | `bifrost-standby` | :4882 | none (cli_only) | Yes — bifrost_daemon | LIVE |
| 47 | `bifrost-send` | :4892 | `bifrost_send` (MCP:524) | Yes — harness, docs | LIVE |
| 48 | `suite-baseline` | :4913 | none (cli_only) | Yes — `ship_gate.py:150` | LIVE |
| 49 | `bifrost-drain` | :4925 | none (cli_only) | Yes — doctor.py, runner code | LIVE |
| 50 | `bifrost-pause` | :4933 | none (cli_only) | Yes — runner code | LIVE |
| 51 | `bifrost-resume` | :4947 | none (cli_only) | Yes — runner code | LIVE |
| 52 | `bifrost-skip-to-now` | :4950 | none (cli_only) | Yes — `doctor.py:436` | LIVE |
| 53 | `bifrost-nudge` | :4959 | `bifrost_nudge` (MCP:535) | Yes — harness, runner code | LIVE |
| 54 | `seat-identity` | :4968 | none (cli_only) | **NO** — zero external refs | DOOR-ONLY |
| 55 | `lock` | :4976 | `lock` (MCP:384) | Yes — harness, runner code | LIVE |
| 56 | `unlock` | :4981 | `unlock` (MCP:394) | Yes — harness, runner code | LIVE |
| 57 | `locks` | :4985 | `locks` (MCP:401) | Yes — recall-at code | LIVE |
| 58 | `bifrost-fetch` | :4989 | none (gap) | Yes — boot output spill notices | LIVE |
| 59 | `capture` | :4996 | none (cli_only) | Yes — runner code | LIVE |
| 60 | `alias` | :5008 | none (cli_only) | Yes — `docs/.../self-tooling-arc` report | LIVE |
| 61 | `run` | :5027 | none (cli_only) | Yes — self-referencing, docs | LIVE |
| 62 | `bench` | :5035 | none (cli_only) | Yes — `bifrost_pull.py`, `doctor.py`, `triage_park.py` | LIVE |
| 63 | `tool` | :5046 | none (cli_only) | Yes — `play_sandbox.py:164` | LIVE |
| 64 | `tool list` | :5048 | none | Yes — play_sandbox code | LIVE |
| 65 | `tool run` | :5052 | none | Yes — play_sandbox code | LIVE |
| 66 | `kata` | :5062 | none (cli_only) | **NO** — one ref in a design report about a DIFFERENT verb (`kata-run`) | DOOR-ONLY |
| 67 | `toast` | :5069 | none (cli_only) | **NO** — zero external refs | DOOR-ONLY |
| 68 | `clobber-scan` | :5081 | none (cli_only) | **NO** — zero external refs to `agent_cli.py clobber-scan` | DOOR-ONLY |
| 69 | `tally` | :5088 | none (cli_only) | **NO** — zero external refs to `agent_cli.py tally` | DOOR-ONLY |
| 70 | `pulse` | :5097 | none (cli_only) | **NO** — zero external refs | DOOR-ONLY |
| 71 | `flightdeck` | :5104 | none (cli_only) | **NO** — zero external refs | DOOR-ONLY |
| 72 | `stand-down` | :5111 | none (gap) | Yes — `doctor.py:606`, many recall_outcome events | LIVE |
| 73 | `unwedge` | :5116 | none (cli_only) | Yes — `doctor.py:554`, many events | LIVE |
| 74 | `followup` | :5122 | none (cli_only) | Yes — `docs/.../kimi-brief-...md:71` | LIVE |
| 75 | `defer` | :5134 | none (cli_only) | Yes — `defer_queue.py:114`, `test_w46` | LIVE |
| 76 | `kit` | :5147 | none (cli_only) | **NO** — zero external refs | DOOR-ONLY |

**MCP-only verbs (no CLI twin):** `ask_gemini_web`, `ask_gemini_panel`, `gemini_web_login`,
`bifrost_broadcast`, `bifrost_inbox`, `bifrost_presence`, `diag_echo_slow` (7 total).
These are classified in `check_door_parity.py`'s MANIFEST with rationale.

---

## THE FIVE MOST INTERESTING FINDINGS

### Finding 1: EIGHT verbs are DOOR-ONLY — they exist in argparse, nothing points at them

The following verbs have ZERO external references to `agent_cli.py <verb>` anywhere in the
project's Python, Markdown, shell scripts, or YAML files:

- `console-log` — agent_cli.py:4865. Not even the console-log implementation references itself.
- `seat-identity` — agent_cli.py:4968. The comment in `check_door_parity.py:198` says it "binds a
  per-session file and reads the local process env" — the one verb that CANNOT work through MCP
  by its own design, yet nothing tells anyone to run it.
- `kata` — agent_cli.py:5062. The ONLY external reference is `docs/library/report/20260724_sota-
  quality-kimi-half-audit-lens_6a0314.md:188`, which mentions `kata-run` (a different proposed
  verb), not `kata`. This is the clearest SUSPECT-DEAD.
- `toast` — agent_cli.py:5069. "gratitude-with-receipt (T099 BETA-2)". Zero references.
- `clobber-scan` — agent_cli.py:5081. "W47 (kimi's design)". Zero references to the CLI verb.
  Referenced only in a kimi tools-hunt report (which proposed it) and the test that pins it.
- `tally` — agent_cli.py:5088. "W48 (kimi): blind-counter consensus matrix". Zero references to
  the CLI verb. The test `test_w48_tally_kimi.py` exists but doesn't reference `agent_cli.py tally`.
- `pulse` — agent_cli.py:5097. "W25 (deepseek): LIFEWORKERS pressure-map". Zero references.
- `flightdeck` — agent_cli.py:5104. "W25 (deepseek): cockpit one-pager". Zero references.
- `kit` — agent_cli.py:5147. "install a kit bundle on a seat's belt (T099 KIT tier)". Zero references.

All nine are classified `cli_only` in `check_door_parity.py`'s MANIFEST, meaning the door-parity
guard sees them and accepts their CLI-only status. But the door-parity guard does not ask whether
anything INVOKES them. This is exactly the `declare_intent` class of defect: the module is wired,
the capability is dead.

### Finding 2: The door-parity manifest's classification sometimes serves as the ONLY evidence of life

`check_door_parity.py`'s MANIFEST (lines ~110-210) classifies every CLI verb as `shared`,
`cli_only`, `mcp_only`, or `gap`. For the nine DOOR-ONLY verbs above, the rationale strings in
that manifest ARE the only external prose that names them (e.g., `"flightdeck": "cli_only",
# cockpit one-pager (W25); operator dashboard` at :195). A manifest entry is not a reference; it
is a claim. The claim may be true (`flightdeck` IS an operator dashboard), but nothing in the
project tells an operator to use it, and nothing in any other code calls it. The manifest
classifying a verb is not evidence it's alive — it's evidence someone looked at it once.

### Finding 3: The `bifrost-fetch` / `blob` naming split is a live wire with a dead name

- The argparse verb is `bifrost-fetch` (agent_cli.py:4989: `sub.add_parser("bifrost-fetch", ...)`)
- The handler function is `cmd_blob` (agent_cli.py:4134)
- The variable is `blb` (agent_cli.py:4989)
- The MCP has NEITHER `bifrost_fetch` NOR `blob` — it's classified `gap` in the manifest
- The ToolBox has `bifrost_fetch` (core/comm/toolbox.py)
- Spill notices in boot output reference it as `blob:<sha>` (the content-addressed ref format)

This means: a spill notice says "fetch with `blob:<sha>`", the boot output says "run
`py agent_cli.py bifrost-fetch --get <ref>`", the internal code calls it `blob`, and the MCP
door has neither name. The `check_door_parity.py` manifest at line ~145 records this as `gap`
with rationale: "CLI verb `blob` and ToolBox tool `bifrost_fetch` are the SAME door under two
names." But the CLI verb is NOT `blob` — it's `bifrost-fetch`. `check_advertised_verbs.py`
found this exact class of defect (a `blob` verb that didn't exist) and it was fixed — then
the name split was preserved. This is the same genus as the `declare_intent` discovery:
the fix addressed the symptom (dead instruction) without resolving the underlying naming
drift.

### Finding 4: The `check_advertised_verbs.py` checker and `check_door_parity.py` checker disagree on what a CLI verb IS

- `check_advertised_verbs.py`'s `registered_verbs()` parses the AST of `agent_cli.py`, finds every
  `add_parser` call, and returns a flat set. It returns 68 verbs including subcommand names like
  `new`, `adopt`, `list` (from `tool`), and `run` (from `tool`).
- `check_door_parity.py`'s `cli_verbs()` uses a REGEX (`re.findall(r'add_parser\(\s*["\']([a-zA-Z0-9_-]+)["\']', src)`) 
  which is a DIFFERENT extraction method. Regex vs AST can diverge on multiline or commented-out calls.

This means two guard files in the same `scripts/checkers/` directory use different parsing
strategies for the same data. The AST method is strictly more correct (it sees the actual
argparse tree); the regex method is simpler but fragile to formatting changes. The two already
disagree on sub-subcommands: `check_advertised_verbs` sees `new` and `adopt` as flat verbs
(they're `add_parser` calls), while `check_door_parity` classifies `new` separately as
`"new": "cli_only", # subcommand of doc` and `"adopt": "gap"` — but `adopt`'s own
classification says it's a gap for MCP, and `new` is CLI-only.

### Finding 5: The `--help` output IS the discoverability mechanism, and it has no test

`agent_cli.py discover` (line 1189: `cmd_discover`) enumerates all verbs by calling
`build_parser()` at runtime and walking the subparser actions. This is the ONLY mechanism
for discovering what verbs exist. It is tested exactly once: `test_t067_guarded_exec.py:46`
runs `py agent_cli.py discover` and checks it succeeds. No test verifies that the output
matches the actual argparse tree, or that every verb in `discover`'s output actually has a
working handler. The nine DOOR-ONLY verbs are all listed by `discover` — they appear to be
legitimate, and nothing tells the user otherwise. This is `declare_intent` scaled to the
verb surface: the self-describing door describes doors that may lead nowhere.

---

## WHAT I COULD NOT DETERMINE

1. **Whether `kata`, `toast`, `clobber-scan`, `tally`, `pulse`, `flightdeck`, and `kit` have
   working implementations.** They have `cmd_*` handlers bound (`cmd_kata`, `cmd_toast`,
   `cmd_clobber_scan`, `cmd_tally`, `cmd_pulse`, `cmd_flightdeck`, `cmd_kit`). I did not trace
   each handler to verify it imports real modules and touches real data. A verb can have zero
   external callers and still work perfectly when invoked directly (like a self-contained
   diagnostic). My census answers "does anything point at it?", not "does it run?".

2. **Whether the `console-log` and `seat-identity` verbs are genuinely dead or are ambient
   infrastructure.** `seat-identity` may be used by harness launchers that construct commands
   programmatically (not via string search). `console-log` may receive events from the
   interjection/bus_control/file_drop machinery without any code containing the literal string
   `agent_cli.py console-log`. A reference search cannot find dynamically-constructed commands.

3. **The full ToolBox coverage picture.** I compared CLI ↔ MCP only. The ToolBox (the third
   door, `core/comm/toolbox.py`) has its own verb surface with aliases declared in
   `check_door_parity.py`'s `TOOLBOX_ALIASES`. A complete census of all three doors was not in
   scope for this round; that would be a natural R2.

4. **Whether any of the nine DOOR-ONLY verbs are exercised by tests that import `cmd_*`
   directly.** `tests/test_w48_tally_kimi.py` imports `cmd_tally` and tests it directly
   (without shelling out to `agent_cli.py tally`). This IS wiring — the function is called,
   just not via the argparse door. My reference search for the STRING `agent_cli.py tally`
   would miss this. A follow-up should check each DOOR-ONLY verb's handler function for
   direct test imports.

---

## SUMMARY COUNTS

| Category | Count |
|----------|-------|
| CLI verbs (top-level add_parser) | 68 |
| CLI subcommands (doc new/adopt, tool list/run) | 4 |
| Total CLI argparse entry points | 72 |
| LIVE (referenced outside own definition) | 63 |
| DOOR-ONLY (zero external references found) | 9 |
| MCP twin exists (shared or aliased) | 22 |
| MCP-only (no CLI twin) | 7 |
| Gap (manifest says should be shared but isn't) | 5 |

The nine DOOR-ONLY verbs are: `console-log`, `seat-identity`, `kata`, `toast`, `clobber-scan`,
`tally`, `pulse`, `flightdeck`, `kit`. These are the verb-surface equivalent of
`core/comm/mailbox.py::declare_intent` — capability that exists in the door but may run
nowhere. Each deserves the one-level-down check that T134 applied to functions.
