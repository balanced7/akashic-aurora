---
akashic_id: art_20260716_hardening-slices-deepseek-blind-half-202_91d41c
akashic_sha: bd878da85e09
status: draft
type: report
date: 2026-07-16
title: Hardening Slices — deepseek blind half — 2026-07-16
gist: "Inputs: docs/failure-ledger-2026-07.md (C4-2 crash retrospective, C7-4 MCP boot hang, C8-3 hook double-fire); research/reviewed/jester-synth"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260716_jester-forge-synthesis-pass-a-claude-arc_49a170
    rel: cites
created: "2026-07-16T22:45:24"
updated: "2026-07-23T21:42:19"
---
<!-- GENERATED PROJECTION of art_20260716_hardening-slices-deepseek-blind-half-202_91d41c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Hardening Slices — deepseek blind half — 2026-07-16

Inputs: docs/failure-ledger-2026-07.md (C4-2 crash retrospective, C7-4 MCP boot hang, C8-3
hook double-fire); research/reviewed/jester-synthesis-claude-2026-07-16.md (P1/P2
mechanical gates); stranded S5/S6 working-tree files.

Five slices. Each: root-cause analysis (file:line), proposed mechanism, pre-registered pins, risks.

---

## S1 · C7-4 MCP boot() hang — diagnosis + fix

### Root-cause analysis

The symptom: `boot()` via MCP hangs in the RESPONSE path. The work executes — the boot
event lands on the ledger (22:11:40) — but the MCP client sees nothing until user-interrupt.
CLI `boot` returns in 345ms. Reproduced 2/2 warm+cold; 9 other MCP tools return instantly.

The mechanism (ai_setup_mcp.py):

```python
# ai_setup_mcp.py line ~90
def _run(fn, **overrides) -> str:
    ns = argparse.Namespace(**{**_ARG_DEFAULTS, **overrides})
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            fn(ns)           # <-- calls cmd_boot(ns), captures stdout
    except SystemExit:
        pass
    ...
    return buf.getvalue().strip() or "(no output)"
```

`cmd_boot` (agent_cli.py:161) is the LARGEST render in the CLI: it prints orientation
headers, lessons, notes, decisions, funnel pulses, boot trim, doctor lines. But the
render is pure `print()` — it completes in ~345ms when called from the CLI.

What's DIFFERENT about the MCP path? **`cmd_boot` writes to stderr.** Lines like:

```python
# agent_cli.py ~190
print(f"[boot] {_line}", file=sys.stderr)
```

And critically, the cold-start reconciler (`heal_report()`), the pre-warm path, and
the auto-logger all touch stderr. `redirect_stdout(buf)` captures stdout — stderr is
untouched and goes to the parent's stderr fd. That's fine for stdio MCP (stderr is
the debug channel). But there's a subtler interaction:

**Hypothesis: `cmd_boot` imports or touches a module that attempts a blocking Redis
operation under `redirect_stdout`.** The key suspect is the `HybridStore` cold-start
reconciler at agent_cli.py ~196:

```python
_st = create_store(prefer_redis=True)
if isinstance(_st, HybridStore) and _st.redis_available:
    for _line in _st.heal_report():
        print(f"[boot] {_line}", file=sys.stderr)
```

`heal_report()` iterates Redis keys (`store.keys("learn:*")`) and compares against
File. If Redis is in a degraded state (the exact scenario during the C4-2 crash night
— daemon dead, fleet dark, Redis possibly overloaded with tombstones/unacked work),
a `keys()` scan can block on the server. Under `redirect_stdout`, the GIL is held by
the `StringIO` context manager while `keys()` blocks — and the MCP event loop (which
also needs to service the response socket) starves.

But the CLI path doesn't block on `keys()`? The CLI runs `cmd_boot` as a standalone
process — Redis blocking blocks the process, which then returns. The MCP server runs
`cmd_boot` IN-PROCESS. If a Redis operation blocks for 30+ minutes (connection timeout
vs server-side `KEYS *` on a large dataset), the in-process MCP loop is wedged. The
boot EVENT logs because `capture_event` writes through the Store's write path
(independent Redis connection or FileStore fallback), but the `heal_report()` read
path shares the bus Redis client and blocks.

**Alternative/additional hypothesis: response payload size.** `cmd_boot` produces
8-12KB of text (the full boot render). The MCP framing sends this as a single JSON-RPC
response. If the MCP transport has a write buffer that fills (the client is slow to
read or the OS pipe buffer is smaller than the payload), `print()` blocks inside
`redirect_stdout`. The `mcp` library's stdio transport may not use non-blocking I/O.

**Diagnosis plan** (pre-registered, to be executed before any fix):

1. **Reproduce with capped payload**: run `boot()` via MCP with `AKASHIC_BOOT_FULL=0`
   (if that exists) or with a stubbed `cmd_boot` that prints a short message → does
   it return? (Isolates payload-size vs import-path.)
2. **Reproduce with heal_report disabled**: monkey-patch `HybridStore.heal_report` to
   no-op → does it return? (Isolates Redis keys() scan.)
3. **Reproduce with stderr capture**: redirect stderr to `/dev/null` (or NUL) → does
   it return? (Isolates stderr buffer pressure on the MCP transport.)
4. **Instrument the MCP boot path**: wrap `_run(fn, ...)` with a `timeout` — if
   `cmd_boot` doesn't return within 10s, log what line it's stuck on (add a
   `sys.settrace` diagnostic or line-level timing).

### Proposed mechanism

Once diagnosed, the fix is structural — decouple the HEAVY boot work from the MCP
response path:

**Option A (fast path for ready state):** `cmd_boot` already has a primer-aware fast
path (W13). Ensure the MCP `boot()` tool hits this fast path — the SessionStart hook
pre-computes the boot payload, `cmd_boot` reads it from a sidecar file, and the MCP
response is a few `print()` calls. The heavy reconciler/doctor work is skipped in the
fast path because it was done at session start.

**Option B (subprocess isolation):** Instead of `_run(cmd_boot, ...)` calling
in-process, spawn `py agent_cli.py boot ...` as a subprocess with a timeout
(`_run_script` already exists; use it). The subprocess blocks independently; the MCP
event loop stays responsive. Timeout after 30s → return the partial output + a
warning. The boot event still fires (the subprocess runs agent_cli, which calls
`capture_event`). This is the nuclear option — it also fixes any FUTURE blocking
regression in `cmd_boot` without needing to audit every import.

**Recommended: Option B for the MCP boot tool specifically.** The other MCP tools are
fast because their `cmd_*` functions are trivial renders; `cmd_boot` is the only one
that runs a cold-start reconciler, pre-warms caches, and renders 8KB. Subprocess
isolation is proportional — one tool, one `_run_script` call. Keep `_run()` for the
other 20+ tools.

### Pre-registered pins

- **S1-P1 (diagnosis)**: probe 1 (capped payload) passes/fails → recorded in the
  failure ledger under C7-4 with the verdict.
- **S1-P2 (diagnosis)**: probe 2 (heal_report disabled) → verdict recorded.
- **S1-P3 (diagnosis)**: probe 3 (stderr redirect) → verdict recorded.
- **S1-P4 (diagnosis)**: probe 4 (trace instrumentation) → blocking line identified.
- **S1-P5 (fix)**: MCP `boot()` returns within 10s when Redis is reachable (warm start).
- **S1-P6 (fix)**: MCP `boot()` returns within 35s when Redis is unreachable (cold
  start + subprocess timeout).
- **S1-P7 (fix)**: boot event still lands on the ledger (subprocess runs agent_cli
  which writes it).
- **S1-P8 (regression)**: all other MCP tools (learn, recall, status, notes, handoff,
  bifrost_send, etc.) still return <2s each.
- **S1-P9 (regression)**: CLI `py agent_cli.py boot claude` still works identically
  (untouched code path).

### Risks

- **Subprocess overhead**: launching a Python process per boot adds ~200-400ms. For a
  tool called once per session, this is negligible. If called per-turn, it adds up — but
  boot IS the session-start ritual; calling it mid-session is already an anti-pattern.
- **Environment passthrough**: `_run_script` inherits `os.environ`; the subprocess needs
  the same `AKASHIC_SEAT_DOOR=mcp` so its transport line renders correctly. Pass it
  explicitly.
- **If diagnosis reveals a different root cause (not heal_report)**: the subprocess
  fix still works — it defends against any unknown blocking path in `cmd_boot`. But
  we also fix the root cause directly.

---

## S2 · C8-3 Hook double-fire — single registration surface + race-proof dedup

### Root-cause analysis

The double-fire is caused by `claude_pretooluse.py` being registered on TWO surfaces:

1. **Project-level** (`.claude/settings.json` lines ~87-95): relative-path matchers
   for `Bash` and `Edit|Write|NotebookEdit`.
2. **User-level** (`~/.claude/settings.json`, per docs/DEPLOY.md lines ~101-102):
   absolute-path matchers for the same tool categories, installed as part of the
   "read bootstrap" flow so hooks fire from any working directory.

Both fire on every matched tool call. Claude Code merges project + user hook configs
— it does not deduplicate by command string.

The consequence chain is:

- **Funnel inflation**: `log_injection()` in `_recall_context()` runs twice per action.
  Each call increments `recall:use:<lesson_id>.surfaced`. The surfaced denominator is
  ~2× inflated → the headline value metric (4.2% helped/surfaced) is roughly half the
  true rate. The C8-3 ledger entry: "the GAUGE INVERSION theme's own gauge was lying."
- **Anti-repeat can't save it**: `load_seen(session_id)` reads the seen-set, then both
  hooks run `mark_seen(session_id, srcs)`. But both read before either writes — classic
  TOCTOU race. The seen-set is per-session tempdir, so both hooks share the same file;
  the second hook's `load_seen` returns the pre-first-mark state.
- **session_signals double-fire**: The C8-3 entry notes that `claude_sessionend.py` also
  double-fires (both PreCompact and SessionEnd matchers in `.claude/settings.json` are
  project-level only — but user-level registration of SessionEnd is also documented).
  The SessionEnd hook fires once from project-level PreCompact + once from project-level
  SessionEnd — that's a different root cause (two matchers in the SAME config), but the
  fix is the same pattern.

The C8-3 ledger entry (docs/failure-ledger-2026-07.md:63) already identifies the root
cause: "two registration surfaces, no single source of truth, no dedup at the hook."

### Proposed mechanism

**Phase 1 — Single registration surface**: The project-level `.claude/settings.json` is
the source of truth (git-tracked, version-controlled). The user-level registration
(docs/DEPLOY.md Option B) should be removed from the deploy instructions. The
project-level config already uses relative paths and the scope guard (`_in_scope`)
makes it a silent no-op outside the repo. The "read bootstrap" flow works with
project-level hooks as long as Claude is launched from the repo root — which AGENTS.md
already instructs.

If user-level registration is genuinely needed (Claude launched from arbitrary cwd with
no project-level config), the user-level entry should be a SINGLE registration that
references the project-level hook script by absolute path, AND the project-level config
should DETECT the user-level registration and remove its own duplicate entries.

**Phase 2 — Race-proof dedup at the hook**: Even with one registration surface, a
future config migration or Claude Code update could re-introduce double-firing. Add a
per-process dedup guard inside `claude_pretooluse.py`:

```python
# claude_pretooluse.py, at module level
import hashlib, os, time

_DEDUP_DIR = os.path.join(tempfile.gettempdir(), "akashic_hook_dedup")
os.makedirs(_DEDUP_DIR, exist_ok=True)

def _dedup_check(hook_name: str, data: dict, ttl_s: int = 5) -> bool:
    """True if this exact hook firing was already processed within ttl_s.
    Uses an atomic file-create as the lock (O_CREAT|O_EXCL via open('x'))."""
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {})
    fingerprint = hashlib.sha256(
        f"{hook_name}:{tool}:{ti.get('command','')}:{ti.get('file_path','')}".encode()
    ).hexdigest()[:16]
    marker = os.path.join(_DEDUP_DIR, fingerprint)
    try:
        with open(marker, "x") as f:
            f.write(str(time.time()))
        return False  # first firing — proceed
    except FileExistsError:
        # Check if marker is stale
        try:
            age = time.time() - os.path.getmtime(marker)
            if age > ttl_s:
                os.remove(marker)
                with open(marker, "x") as f:
                    f.write(str(time.time()))
                return False  # stale marker — refresh and proceed
        except Exception:
            pass
        return True  # duplicate — skip
```

This is file-system atomic (no Redis dependency, no import overhead) and race-proof
(`open('x')` = O_EXCL on the filesystem, which is atomic on all platforms). The TTL
clears stale markers from crashed hooks.

**Phase 3 — Funnel correction**: After Phase 1 lands, the funnel's historical data
(pre-fix) is known-inflated. Emit a gauge correction event so consumers of the funnel
(CLI `stats`, boot render) can annotate the pre-fix era. Not a data rewrite — the raw
counters stay as-is, but `snapshot()` gains a `double_fire_era` flag when the window
includes pre-fix timestamps.

**Phase 4 — Census check**: Audit ALL hook registrations across all surfaces (project
`.claude/settings.json`, user `~/.claude/settings.json`, and Cursor's equivalent if
any) for EVERY hook script. The C4-2 crash night showed `session_signals` double-fired
(FIVE signals in 2s for what should have been 2-3). A one-time census script or boot
check warns if any hook script is registered more than once across surfaces.

### Pre-registered pins

- **S2-P1 (Phase 1)**: After removing user-level PreToolUse registration, a Bash call
  produces exactly ONE recall-at-action injection (verified via `log_injection` count
  in the injection ledger — `py agent_cli.py injections` shows one entry per action).
- **S2-P2 (Phase 1)**: All PreToolUse guard functions still fire (git-veto, lock-veto)
  — verify by attempting a blocked operation and confirming the deny.
- **S2-P3 (Phase 2 dedup)**: With BOTH registrations intentionally active (test harness
  simulates the pre-fix state), the atomic dedup suppresses the second firing. Pin:
  `_recall_context` is called exactly once despite two hook invocations.
- **S2-P4 (Phase 2 dedup)**: A crashed first hook (kill -9 mid-execution) leaves a stale
  marker; the second firing 6s later proceeds (TTL=5s). Pin: after `time.sleep(6)`, the
  dedup passes through.
- **S2-P5 (Phase 3)**: `snapshot(hours=168)` (7-day window that includes pre-fix data)
  returns `double_fire_era: true`. After 7 days of post-fix data, it returns `false`.
- **S2-P6 (Phase 4 census)**: A boot-time check enumerates all hook registrations and
  warns on duplicates. Pin: with user-level dup removed, boot is silent. Simulate a
  duplicate → boot prints a WARNING line.
- **S2-P7 (regression)**: SessionEnd fires ONCE (one `session_signals` event per session
  end, verified via `py agent_cli.py events --kind session_signals`).
- **S2-P8 (regression)**: `claude_posttooluse.py` (PostToolUse) still fires correctly
  — it was never double-registered, but the pin verifies the config doesn't lose it.

### Risks

- **User-level registration removal breaks the read-bootstrap flow**: If a user launches
  Claude from outside the repo and relies on user-level hooks, removing them degrades
  safety. Mitigation: Phase 1 keeps user-level IF it's the ONLY registration (census
  detects project-level presence and skips user-level). The deploy doc is updated to
  say "pick ONE."
- **Atomic file-create on Windows**: `open('x')` is O_EXCL and works on Windows Python
  3.3+. Verified. But tempdir cleanup (OS reboot, disk cleanup) could clear the dedup
  directory — the dedup is best-effort; a miss means one double-fire, not a crash.
- **Funnel correction accuracy**: The `double_fire_era` flag is honest but imprecise —
  it's based on whether the window includes any pre-fix timestamps, not whether each
  specific counter was double-counted. This is acceptable for a gauge annotation.

---

## S3 · P2 ACL cap-ceiling pre-commit gate

### Root-cause analysis

The Jester synthesis (research/reviewed/jester-synthesis-claude-2026-07-16.md §P2)
identifies the trust-escalation vector: an agent with `admin.grant` capability can
add any cap to any agent, including caps the granter itself doesn't hold — creating
a privilege chain where the blind lead the blind. BLUE detector D4 (cap-ceiling)
proposes a mechanical pre-commit check.

The current state: `security/acl.json` is git-tracked and human-auditable, but
nothing mechanically validates grant consistency at commit time. An agent (or human)
can stage a grant that gives `deepseek` the `admin.grant` cap while `granted_by:
deepseek` — which doesn't hold `admin.grant` itself. This is the FM-5 class: a
single-file escalation.

The pre-commit hook at `scripts/githooks/pre-commit` (the C4 backstop via
`scripts/hooks/pre_commit.py`) currently checks peer-locks and comprehensibility
drift. Adding an ACL ceiling check is ~40 lines in the same hook.

### Proposed mechanism

**Gate**: `scripts/hooks/pre_commit.py:_check_acl_ceiling()` — runs when
`security/acl.json` is staged. Algorithm:

1. Parse the staged version of `security/acl.json` (not the working tree — `git show
   :security/acl.json` to get the staged content).
2. Parse HEAD's `security/acl.json` (or empty grants list if first commit).
3. For each grant in the staged version that is NEW (agent_id not in HEAD) or MODIFIED
   (caps added compared to HEAD):
   a. Collect the set of caps being ADDED (staged caps minus HEAD caps for that agent).
   b. For the `granted_by` agent, resolve its caps at HEAD (the granter's authority is
      what's ALREADY committed, not what's in this commit — no self-escalation).
   c. If any added cap is NOT in the granter's HEAD caps → BLOCK with a message naming
      the cap, the granter, and the ceiling violation.
4. `granted_by: root` is exempt (bootstrap authority).

**Escape hatches**:

- **Human override**: `git commit --no-verify` bypasses all pre-commit hooks (standard
  git escape hatch). The hook prints a loud warning when bypassed.
- **First-commit bootstrap**: When HEAD has no `security/acl.json` (initial commit),
  the check passes — you can't ceiling-check against nothing. The `root` grant itself
  must be in the first commit.
- **Granter self-upgrade in the same commit**: If `claude` adds a cap to itself AND
  grants it to `deepseek` in the same commit, the ceiling check uses HEAD caps for the
  granter — so `deepseek`'s grant would BLOCK if `claude` didn't have the cap at HEAD.
  **This is correct behavior** — the granter must already hold the cap before granting
  it. To add a cap to yourself AND grant it in one commit: commit the self-upgrade
  first, then the grant. Two commits, enforceable order.

### Pre-registered pins

- **S3-P1**: Staging a grant where `granted_by` lacks the granted cap → `git commit`
  blocked with a message naming the cap and the ceiling violation.
- **S3-P2**: Staging a grant where `granted_by` HAS the cap → commit proceeds.
- **S3-P3**: `granted_by: root` grants any cap → commit proceeds (root exemption).
- **S3-P4**: First commit (no HEAD acl.json) → commit proceeds (bootstrap exemption).
- **S3-P5**: Modifying a non-cap field (e.g. `reason`, `expires_at`) for an existing
  grant with unchanged caps → commit proceeds (no new caps to check).
- **S3-P6**: `git commit --no-verify` bypasses the check → commit proceeds, hook prints
  "ACL ceiling check BYPASSED" to stderr.
- **S3-P7**: Granter self-upgrade + grant in same commit → grant blocked (granter uses
  HEAD caps). Self-upgrade alone proceeds.
- **S3-P8**: Staging a file that is NOT `security/acl.json` → ceiling check is a no-op
  (no false blocks on unrelated commits).
- **S3-P9 (regression)**: All existing pre-commit checks still run (peer-lock C4,
  comprehensibility drift). The ceiling check is additive.

### Risks

- **The `git show :file` approach**: On Windows, `git show :security/acl.json` works
  correctly (colon syntax is cross-platform). Verified.
- **HEAD missing acl.json**: Gracefully handled (empty grants list). The bootstrap
  exemption prevents first-commit blockage.
- **Staged deletion of a grant**: Not gated — removing a grant is always safe. The
  check only gates ADDED caps.
- **Race with concurrent commits**: The pre-commit hook runs against the staged content,
  which is a snapshot. A concurrent push can't change the staged content between check
  and commit. The remote can reject a push if the remote HEAD advanced (standard git
  non-fast-forward), but that's a push-time concern, not a commit-time concern.

---

## S4 · P1 Ground-truth gate v1 — note/lesson cross-check

### Root-cause analysis

The Jester RED team proved (V1/V2, research/reviewed/jester-synthesis-claude-2026-07-16.md
§1-2) that a `where-we-are` note or a knowledge lesson can claim task status that
contradicts `state/coord/tasks.json` — and the PRECEDENCE_DOCTRINE ranks notes above
all live evidence, so the lie becomes fleet truth. BLUE independently converged: the
only ungameable ground truth is a MECHANICAL, no-model check.

The attack surface:
- `knowledge_note(title="where-we-are", note="T081 is DONE and shipped...")` — a
  write-once note that can claim any task status.
- `knowledge_learn(experiment="...", recommend="T075 is APPROVED")` — a lesson that
  embeds a task-status claim in its body.
- The PRECEDENCE_DOCTRINE: NOTES (write-once) > PROMOTED bus messages > LIVE BUS,
  with no cross-validation against the task ledger (`state/coord/tasks.json`).

The C9 antidote: when a note or lesson makes a checkable claim about task state,
cross-check it against the mechanical source. v1 scope: task-id + status token
patterns only (prose fabrication is out of scope until a richer claim-extractor).

### Proposed mechanism

**Write-time check (accept-but-flag)**: In `knowledge_note()` and `knowledge_learn()`,
after the content is accepted, scan it for patterns matching `(T\d{3}).*?(proposed|
approved|claimed|in_progress|verifying|done|blocked|parked|abandoned|next)` and
cross-check against `state/coord/tasks.json`. If the note/lesson claims a status that
disagrees with the task ledger:

- **NEVER block the write** — notes are write-once and the claim may be legitimate
  (e.g. a forward-looking statement: "T090 will be proposed tomorrow"). Blocking a
  write-once note on a parse error is data loss.
- **Flag LOUD**: the `knowledge_note`/`knowledge_learn` return value includes a
  `[GROUND-TRUTH MISMATCH]` banner naming the task, the claimed status, and the
  actual ledger status. The agent sees it at write time.
- **Write a `ground_truth_flag` event** to the event firehose so the fleet sees it.

**Boot-time check (re-check live)**: In `cmd_boot()`, after rendering the WHERE-WE-ARE
note, scan the note body for task-status claims. For each claim:

1. Parse: `(T\d{3})` + status token.
2. Look up the task in `state/coord/tasks.json`.
3. If the claim disagrees with the ledger → render a MISMATCH BANNER in the boot output,
   directly below the WHERE-WE-ARE note. The banner names the task, the claimed status,
   and the actual ledger status. It also prints the drill-down command:
   `py agent_cli.py task show T075`.

This is a pure string/ledger comparison — zero models, zero ambiguity on structured
claims. v1 deliberately leaves prose-only claims untouched ("everything is fine",
"the system is healthy") — those need a richer claim-extractor in a later wave.

**Scope of v1**: Only the `where-we-are` note (title match) and any note whose body
contains `T\d{3}`. Lessons are scanned at boot time when they surface in the boot
context (the top few lessons); a lesson claiming "T081 is DONE" while the ledger says
`verifying` triggers the banner.

### Pre-registered pins

- **S4-P1 (write-time flag)**: Writing a `where-we-are` note claiming "T042 is DONE"
  while `state/coord/tasks.json` shows T042 as `verifying` → note is ACCEPTED, return
  value includes `[GROUND-TRUTH MISMATCH] T042: claims DONE, ledger says verifying`.
- **S4-P2 (write-time no false positive)**: Writing a `where-we-are` note claiming
  "T081 is DONE" while the ledger shows T081 as `done` → note accepted, NO mismatch
  banner.
- **S4-P3 (write-time no parse)**: Writing a note with no `T\d{3}` pattern → accepted
  silently (no scan triggered).
- **S4-P4 (write-time forward-looking)**: Writing "T090 will need review" → accepted
  silently. The pattern `T090` exists but no status token match → no mismatch.
- **S4-P5 (boot-time banner)**: Booting with a `where-we-are` note that claims T042 is
  DONE while ledger says `verifying` → boot output renders a MISMATCH BANNER directly
  below the note.
- **S4-P6 (boot-time clean)**: Booting with a `where-we-are` note whose claims all match
  the ledger → no banner.
- **S4-P7 (boot-time lesson check)**: A lesson surfaced in boot claiming "T075 is
  APPROVED" while ledger says `proposed` → banner rendered below the lesson section.
- **S4-P8 (regression)**: Boot without a `where-we-are` note → no scan, no banner, no
  crash.
- **S4-P9 (regression)**: `knowledge_note` for a non-where-we-are title with task claims
  → still scanned (any note can carry claims), but write is never blocked.

### Risks

- **False positives on forward-looking claims**: "T090 will be proposed" matches
  `T090.*proposed` → false flag. Mitigation: exclude claims preceded by "will",
  "should", "may", "might", "could", "plan to", "intend to". A simple exclusion list,
  documented as v1 scope. False negatives on crafty phrasing are acceptable.
- **Task ledger format changes**: If `state/coord/tasks.json` schema changes, the
  cross-check breaks. Mitigation: fail-open — a parse error on the task ledger reads
  as "unable to verify", not "mismatch." The banner says `[GROUND-TRUTH: unable to
  read task ledger]` instead of a false mismatch.
- **Performance**: Scanning every note body on every boot for `T\d{3}` patterns is a
  regex over ~5-10 notes × ~500 chars each = negligible.

---

## S5 · T086-S5/S6 finish — why tests were failing + supervisor C4-2 charter

### Current state of stranded work

My S5 and S6 files sit untracked in the working tree (per `git status`):

- `scripts/bifrost_runner_deepseek.py` — MODIFIED (S6 reply dedup: `_reply_already_sent`
  gains the Store backstop path, `_mark_reply_sent` writes to both Redis and Store).
  The edit compiles clean and was reviewed by claude pre-crash.
- `tests/test_t086_s5_daemon_supervisor.py` — NEW (S5-C1: SIGTERM cascade pin).
- `tests/test_t086_s6_reply_dedup.py` — NEW (S6-D1 through S6-D4: dedup pins).

The S5 test was **failing 3× at 21:53** (failure-ledger C4-2). Root cause analysis:

### Why S5 was failing

`test_t086_s5_daemon_supervisor.py` (line 1-97) spawns a daemon with `--spawn-runner`,
waits for "runner spawned" on stdout, sends SIGTERM/CTRL_BREAK, and expects clean exit
within 10s. The test uses a throwaway Redis namespace.

The three consecutive FAILs at 21:53 suggest a pattern, not a flake. Likely causes:

1. **Daemon lock contention**: The test uses `BIFROST_NAMESPACE=<throwaway>` but the
   daemon's `DaemonLock` key is `{ns}:daemon:{agent}` — if the throwaway namespace
   isn't properly isolated from the live namespace, the test daemon contends with the
   live daemon (or a leftover lock from a prior test run). The `_stable_token` path
   (`~/.akashic/daemon_{agent}.id`) is NOT namespaced — two daemons for the same agent
   in different namespaces get the same stable token. On `acquire()`, the second daemon
   sees the key already held and exits 0 (refusal). The test sees "refused" → calls
   `pytest.skip` — but if the refusal message format changed, the test might not detect
   it and hangs instead.

2. **Redis not reachable during the crash cascade**: At 21:53, the fleet was going dark.
   If Redis was intermittently unreachable, the daemon's bus probe (`bus.online and
   bus.probe()`) could fail, causing it to exit 2 ("bus OFFLINE at launch"). The test
   reads stdout for "runner spawned" and if the daemon exits before spawning, it hangs
   for 30s then fails.

3. **Runner child startup race**: The daemon spawns the runner as a ManagedChild. If the
   runner fails to start (e.g., DeepSeek API key issue, Python path issue, import error),
   the daemon's `_on_runner_exit` fires immediately. The test expects "runner spawned"
   then sends SIGTERM — but the runner may have already crashed before the test sends
   the signal, and the daemon is in backoff or tripped state.

**Fix for the test itself** (separate from the daemon code it tests):

- Add a pre-test cleanup: delete any leftover `{ns}:daemon:{agent}` key before spawning.
- Add a `--stable-token` override to the daemon so tests can use a throwaway token that
  doesn't collide with the live `~/.akashic/daemon_{agent}.id`.
- Add a readiness signal beyond "runner spawned" — the daemon should print "runner
  ready" (or similar) when the runner has actually connected to the bus. The test waits
  for that signal before sending SIGTERM.
- Add a timeout guard in the test: if the daemon exits before printing "runner spawned",
  capture its stdout/stderr and `pytest.fail` with the actual output (not a hang).

### The supervisor's C4-2 charter

The C4-2 crash (docs/failure-ledger-2026-07.md:247-276) is S5's charter receipt: **the
daemon supervisor owns the pid inventory so "clean up processes" becomes a supervisor
verb with a safe kill-list.**

Currently, `ManagedChild` in `scripts/bifrost_child.py` tracks ONE child per instance
(runner or listener). The daemon in `scripts/bifrost_daemon.py` holds a `listeners: Dict`
and optionally one `child` for the runner. But nothing provides a fleet-wide "quiesce
before clean" verb.

**C4-2 charter — three elements**:

**Element 1 — Owned pid census**: The daemon maintains a `_pid_census` dict that maps
every spawned child (runner, listeners, and any future managed processes) to its pid,
spawn time, and role. This is the kill-list for safe cleanup. The census is printed by
a new daemon control verb: `py agent_cli.py daemon census <agent>` → lists every pid
the daemon owns, its role, uptime, and health.

**Element 2 — Quiesce verb**: `py agent_cli.py daemon quiesce <agent> [--timeout 30]`:
1. Land in-flight work: signal each managed child to finish its current unit of work
   (for the runner: complete the current message; for listeners: drain the current
   inbox peek). Wait up to `timeout` seconds.
2. Mirror stranded sibling work: for each child, if it has unsaved output (the runner's
   summary file, a listener's pending handoff), flush it to disk.
3. Wind down at session level: send SessionEnd to each child's owning session (if
   applicable).
4. Report: which children were quiesced, which timed out, and what was saved.
5. After quiesce, `daemon reap` kills the census list safely (SIGTERM → 5s → SIGKILL).

**Element 3 — Cleanup refusal mid-test**: The daemon's `daemon reap` verb refuses to
run if any managed child is in a `running` state with a test marker
(`_AISETUP_TEST_ISOLATED=1` in its environment). Override with `--force`. The daemon
also exposes a `daemon guard` status that the cleanup script can query: "am I safe to
kill?" — returns `{"safe": false, "reason": "2 children in test: runner(t086s5), ..."}`.

### S6 — already built, needs commit

The S6 reply dedup is reviewed clean and compiles. The change in
`scripts/bifrost_runner_deepseek.py` (+29 lines) adds:
- `_reply_already_sent`: Redis EXISTS first (fast path), then Store get (durable
  backstop). Fail-open: any probe error → not-sent.
- `_mark_reply_sent`: Redis SET + Store SET, both best-effort. TTL = `REPLY_TIMEOUT_SEC + 60`.
- Pins: S6-D1 (Redis fast path), S6-D2 (Store backstop), S6-D3 (dual-write), S6-D4
  (fail-open on probe error).

### Pre-registered pins (S5)

- **S5-P1 (test fix)**: `test_t086_s5_daemon_supervisor.py` passes consistently (3/3
  runs) after the test fixes above.
- **S5-P2 (census)**: `py agent_cli.py daemon census deepseek` returns a JSON list of
  managed children with pid, role, uptime, and state.
- **S5-P3 (quiesce)**: `daemon quiesce` with a live runner → runner finishes current
  message, flushes summary, daemon reports "1 quiesced, 0 timed out."
- **S5-P4 (quiesce timeout)**: `daemon quiesce --timeout 1` with a runner in a long
  operation → "0 quiesced, 1 timed out: runner (pid X)".
- **S5-P5 (reap refusal)**: `daemon reap` while a child has `_AISETUP_TEST_ISOLATED=1`
  → refused with a reason naming the child.
- **S5-P6 (reap force)**: `daemon reap --force` → proceeds regardless.
- **S5-P7 (guard status)**: `daemon guard` returns `{"safe": true}` when no children
  are in test, `{"safe": false, ...}` when they are.
- **S5-P8 (regression)**: Existing daemon tests (T075 M1, T086-S1 regression) still
  pass.

### Pre-registered pins (S6)

- **S6-D1**: `_reply_already_sent` returns True when Redis EXISTS returns True.
- **S6-D2**: `_reply_already_sent` returns True when Redis is down but Store has the key.
- **S6-D3**: `_mark_reply_sent` writes to both Redis and Store.
- **S6-D4**: `_reply_already_sent` returns False when both Redis and Store raise
  (fail-open — duplicate reply is cheaper than dropped reply).
- **S6-D5 (regression)**: Existing runner tests (RB-26 killpoints, T066 reply path)
  still pass.

### Risks (S5)

- **Census is in-memory**: A daemon restart loses the census. Mitigation: the census is
  advisory for cleanup; the OS pid table is the ground truth. The daemon re-owns children
  on restart by checking pidfiles.
- **Quiesce timeout vs data loss**: A child that ignores SIGTERM for `timeout` seconds
  may lose in-flight work. This is already the case today (C4-2 killed without quiesce).
  The quiesce verb makes it BETTER, not perfect.

### Risks (S6)

- **Store TTL semantics**: `store.expire()` may not be supported by all backends
  (FileStore doesn't auto-expire). Mitigation: the `_reply_already_sent` check reads
  the Store value and compares its timestamp. Stale entries (> TTL) are treated as
  not-present. This is a minor refinement — in practice, reply dedup keys are small
  and the FileStore's total size is bounded by the number of unique messages per
  `REPLY_TIMEOUT_SEC` window (~600s × maybe 10 msg/s = 6000 entries, negligible).




