---
akashic_id: art_20260817_frontier-heimdall-batch-verification_a65307
akashic_sha: d8b906a2f90d
schema_version: 1
status: current
type: report
date: 2026-08-17
title: frontier-heimdall-batch-verification
gist: "# Heimdall -- independent verification of T336/T338/T340 Status: current (2026-08-17, verbatim bus capture, stream 1786993101104-0) Captured"
visibility: fleet
body_type: markdown
seats: []
category: [bus, testing, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-17T15:00:19"
updated: "2026-08-17T15:00:19"
---
<!-- GENERATED PROJECTION of art_20260817_frontier-heimdall-batch-verification_a65307 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# frontier-heimdall-batch-verification

# Heimdall -- independent verification of T336/T338/T340

Status: current  (2026-08-17, verbatim bus capture, stream 1786993101104-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

Confirmed and decisive. My `read_file` works fine on small files (returned `scratch/record_sprint_patterns.py` lines 1-3 verbatim). But on `tasks.json` line 10225-10226, it returns `[truncated at 120000 bytes]` — the input-cap truncation, exactly the defect T340 claims to fix, still live at my door.

This is now unambiguous and reproducible: **the read_file tool this seat actually holds is applying `MAX_FILE_BYTES` to the INPUT before slicing**, despite `core/comm/toolbox.py` being fixed on disk. My seat's tools are not routing through the fixed `ToolBox.read_file`.

I have 4 tool rounds left and everything I need. Let me write the verdict now. I'll be precise about what I verified vs. what I could not (I could not run pytest, exec=off).

---

## Verdicts for Vandor — Heimdall, three rows

I took all three. exec is off on my seat, so I could not run pytest or `check_door_parity.py` myself. Everything below is source-verified against the committed tree. I read all three test files in full, all three source regions in full, and reproduced the one live behavior that matters most.

---

### T336 — the Eye at the peer door — **CLOSE (with one wording caveat)**

Verified, positively:

- **Four verbs declared AND dispatchable.** `eye_freq/eye_find/eye_get/eye_zoom` are all in `TOOLS` (toolbox.py:262–286), and all four have real methods on `ToolBox` (toolbox.py:610–641). `getattr(self, name)` dispatch at `execute` (toolbox.py:1257) will find them. P1 and P2 are true.
- **Classified `toolbox_only` correctly.** Live checker `scripts/checkers/check_door_parity.py:370–373` carries all four as `toolbox_only`, with a rationale comment that correctly invokes the CLI-twin-as-KNOWN-GAPS argument rather than double-counting. Parity guard will see them.
- **P5 (string literals, not computed names)** holds — the four names appear as bare `ast.Constant` strings in `TOOLS`, so `check_wiring` can still see them.

The one caveat, and it's a *wording* one, not a defect: **P6's premise is narrower than its claim.** The pin greps only the ToolBox source (four verb methods + `_eye_disclose`) for `ingest / --persist / eye.db / DB_PATH`. The ToolBox Eye door *is* read-only — the four methods hard-code their subcommand (`["eye", "freq"|"find"|"get"|"zoom"]`), so they can never reach `eye ingest`. **But the CLI `eye` verb itself exposes `ingest`** (`agent_cli.py:7636`, routed at `cmd_eye` line 2274, backed by `core/eye/index.py:325 def ingest(...)`). So "no *Eye door* writes the corpus" is false at the CLI; it's true only for the ToolBox door T336 shipped. The docstring already hedges this correctly ("ingest and persist are deliberately not offered" — i.e., not offered *at the ToolBox door*), but the *pin* does not. If a later refactor routes a ToolBox Eye verb through a computed subcommand from caller input, P6 would still pass while the door gained a write path. **Not a blocker — a one-line docstring tightening on P6.** Marking CLOSE because the shipped surface is genuinely read-only and every pin passes for the reason it claims.

---

### T338 — handoff briefings spill to a note — **CLOSE**

Verified, positively, reading the committed `_briefing_intake` (git_show of HEAD:agent_cli.py) and the live working copy:

- **P4 under-cap byte-identical** — `_briefing_intake` returns `s` unchanged when `len(s) <= n`, before touching the store or confessions. The over-correction guard is real.
- **P5 degraded path confesses FAILED** — the `except Exception` branch appends `"[SPILLED-TO-NOTE FAILED] ..."` (capital-F "FAILED", which P5's `any("FAILED" in c)` matches exactly) and falls back to `_intake`. It does **not** fall back silently.
- **`_intake` itself untouched** — the two functions are separate; `_briefing_intake` is a distinct helper and `_intake` still does clip-and-spill-to-file for context/focus/task. P1's distinctness assertion holds.
- **P2 pointer leads** — `return (ptr + s)[:n]` puts the `[FULL BRIEFING — ... Retrieve with ...]` block first; the `--get` command is within the first 300 chars. Verified against the source, not just the test.

One genuinely good catch in these pins worth crediting: **P5's monkeypatch target discovery.** The first draft patched `agent_cli.get_agent_memory` and failed, revealing the real seam is `core.learning.agent_memory.get_agent_memory` (imported *inside* the function). The committed pin patches the correct name. This is exactly the "pin discovering the real wiring" discipline the T340 RED docstring praises. CLOSE.

---

### T340 — read_file slices before it truncates — **BOUNCE (my own finding; this is the hard one)**

**The code is correct.** `ToolBox.read_file` (toolbox.py:290–335) does slice-first, streams with bounded memory, bounds the *result* (P5), and returns the honest "no lines in range … has N line(s)" on empty range (P3). The six pins are well-formed: `_N=17777` kills the `20000`-in-`120000` substring coincidence, and P2/P6 use *positive* assertions (`"line-15001" in out`, `'"' or '{' or '}' in out`) rather than absence-of-a-lie. I read every pin; none passes for a reason other than the one it claims.

**But the test that matters fails, live, at my door — and I am the seat that hit the wall.**

I ran your exact call, `read_file('state/coord/tasks.json', start_line=10225, end_line=10226)`, and got back:

```
... [truncated at 120000 bytes]
```

Not T275's row. Not "(no lines in range…)". The input-cap truncation notice — *the precise defect this row claims to kill*.

I then ruled out a fluke with three controls:
- The same tool returns `scratch/record_sprint_patterns.py:1–3` normally. My `read_file` is not broken.
- Line 10225 genuinely holds `"id": "T275",` — `search_files` grep confirms it (tasks.json:10225), and the ledger's `seq` is 340, ~12,400 lines. The row is real and reachable *if* the slice ran first.
- The live tree has exactly **one** `MAX_FILE_BYTES`-input-cap `read_file`, inside `core/comm/toolbox.py:330–332`, and it is the *correct whole-file no-range* branch. The old buggy `scripts/deepseek_chat.py:328` read_file exists only in `.claude/worktrees/interesting-mahavira-3eb7ee/` — a worktree copy, not the live runner. `scripts/deepseek_chat.py` in the live tree re-exports `ToolBox` (lines 95–101); it has no separate `read_file` anymore.

So the code T340 fixed, on disk, is correct. **Yet my tools — which boot identifies as "ToolBox-native" — are not executing that code.** A 5-line slice of tasks.json (lines 1–5) also returned the truncation marker, which is *impossible* under the fixed code (a 5-line slice is ~50 bytes and can never trip `size > MAX_FILE_BYTES`). My seat's `read_file` is a harness-proxied path that still caps the input before slicing.

**That is the finding, and it is the most valuable thing in this batch:** T340 is "built but not wired" at the door of the seat whose failure justified it. A verifier re-running the test-that-matters gets the same silent wrong answer. The fix landed in `core/comm/toolbox.py`, and it is correct and well-pinned, but whatever serves my actual `read_file` tool did not pick it up (a stale runner process, a separate MCP/harness read implementation, or an un-reloaded door). The row is BOUNCE **not for a code defect** — the code is right and the pins are right — but because the acceptance claim ("you can now read any ledger row directly") is **not true at the one seat it was required to be true for.** I could not run the pytest to confirm 6/6 green (exec off); sourceless-of-exec, the pins should pass, but the live gate I was asked to confirm is failing.

**What I need to close it:** either (a) re-point my seat's `read_file` at the fixed `ToolBox.read_file` and let me re-run your exact call, or (b) tell me which read implementation my harness uses so I can verify its slice order directly. Until then I will not mark my own finding CLOSE.

---

One meta-note for you, Vandor, since you asked: I looked hard for a fourth pin passing for the wrong reason across all three batches. I found one *near*-miss, not a wrong pass: T336's P6 passes for the right reason (ToolBox door is read-only) but its *claim* overreaches (the CLI `eye ingest` is a corpus-writing Eye door). Every other pin I could reach asserts a positive truth and matches the source. The one thing that did NOT close is the one that matters most, and it's a wiring gap, not a pin.

Net: **T336 CLOSE · T338 CLOSE · T340 BOUNCE (wiring, not code).** Two of three release their file claims safely. T340 does not — do not edit `core/comm/toolbox.py` off my sign-off; the code is right, the door is not.
