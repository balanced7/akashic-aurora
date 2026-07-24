---
akashic_id: art_20260723_t104-structure-half-kimi-audit-placement_88f729
akashic_sha: 245c1c927fd7
status: current
type: design
arc: T104
date: 2026-07-23
title: T104 structure half - kimi (audit placement principles)
gist: "Status: current · Type: design (T104 structure half) · Arc: T104 machine-plane structure cleanup · From: kimi (fresh-eyes/audit) · To: claud"
tenant: solo
visibility: fleet
seats: [kimi]
category: [library, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260723_t104-machine-plane-structure-cleanup-rou_5ff991
    rel: derives-from
created: "2026-07-23T22:29:26"
updated: "2026-07-23T22:29:26"
---
<!-- GENERATED PROJECTION of art_20260723_t104-structure-half-kimi-audit-placement_88f729 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T104 structure half - kimi (audit placement principles)

Status: current · Type: design (T104 structure half) · Arc: T104 machine-plane structure cleanup · From: kimi (fresh-eyes/audit) · To: claude (reconcile) · Date: 2026-07-23 night · Base: T104 brief atom art_20260723_t104...5ff991. Lens: placement principles + integrity. VERIFIED/INFER/GUESS. Session write=off → claude persists verbatim.

# kimi T104 half — machine-plane placement principles + integrity

## (a) THE MACHINE-PLANE ONE-FACET LAW (one sentence decides any file's home)

LIBRARY.md's law: a path encodes exactly ONE thing — the doc's TYPE. The machine-plane sibling:

**A file's home names the LIFECYCLE-OWNER that must keep it true — the one question: "when this breaks, whose job is it to notice?"**

That's the single facet. It resolves every candidate rule (kind-not-arc, door-vs-organ, guard-vs-generator) because they're all the SAME question at different altitudes: a guard's home is where the guard-runner looks; a generator's home is beside what it regenerates; a door's home is the organ it opens. The TEST: if you can't name in one word WHO notices when the file rots, the file is homeless. kind-not-arc is a COROLLARY (an arc is a campaign, it ends; an owner is a function, it persists) — arc-named homes are the doc-plane disease one layer down (a file in `t101/` outlives T101 and becomes a fossil wearing a live address).

The derived sub-rules (each = the owner-facet applied):
- **guard-vs-generator** → guards live in the checker's home (`scripts/` check_*), generators live beside their OUTPUT's owner (`gen_*` beside docs/).
- **door-vs-organ** → doors (verbs/CLI) live at the boundary the agent touches (`agent_cli.py`, `*_chat.py`); organs (the mechanism) live in `core/`.
- **kind-not-arc** → never a directory named for a task/arc; always named for the owner-function.

## (b) COLD AUDIT — ranked awkward-list with evidence + the INVISIBLE zones

The structural blind spot (VERIFIED): the two honesty walkers are SCOPE-LIMITED — check_doc_currency covers only `docs/` (its own DOCS constant); check_boundaries covers only `core/` (PROTECTED=["core"], "add context/ etc. later"). EVERYTHING outside docs/+core/ is unwalked. That's WHY fences/ was found by Daniel: fences/ is runtime-spawned + gitignored + scoped to NO walker. Ranked awkward-list:

1. **agent_cli.py monolith (255KB, ~3900 lines) at repo ROOT.** Discovery cost: it's the door-roster, the note verb, the doc verb, the recall verbs, AND the bus verbs in one file — a new seat greps one file for everything, can't tell door from organ. Owner-confusion: is it a door (CLI surface) or an organ (verb implementations)? It's both, which is the monolith. (d) carries the full ruling.
2. **scripts/ is a 60+-file GRAB-BAG with no owner-facet.** Doors (deepseek_chat, kimi_chat, sol_chat), runners (bifrost_runner_*), hooks (hooks/, githooks/), checkers (check_*.py), generators (gen_*.py), one-shots (migrate_time_scores, seed_narrative, capture_apple_hig, harmonize_knowledge), UI (bifrost_ui 163KB, run_job 101KB, aurora/bifrost_viz/presence *.js+html) — SIX owner-classes in one flat dir. Discovery cost: a cold agent can't tell a load-bearing checker from a dead one-shot without reading each header.
3. **Runtime-scratch siblings scattered at root:** blackboard_data/, coordinator_logs/, session_logs/, session_screenshots/, session_snapshots/, sessions/, temp/, dropbox/, scratch/, state/, data/ — TEN dirs that are all "volatile data, gitignored" but split across root with no shared home. Owner-confusion: which of these does snapshot_knowledge back up? (gitignore says some, not all — the split is the smell.) One `var/` or `runtime/` parent would make the volatile/settled boundary one line.
4. **hooks/ vs githooks/ split inside scripts/:** harness hooks (fire on tool events) vs commit guards (fire on git) are different owners (the runner vs the mirror) but sit as sibling subdirs of scripts/. Guard-vs-generator confusion: a commit guard is a CHECKER that fires at commit; a harness hook is a DOOR-interceptor. Different facets, adjacent homes.
5. **THE INVISIBLE ZONES (what else is unwalked like fences/):** infrastructure/ (health_check.py — real code, scoped to no walker, no census), backup_wsl_migration/ (gitignored, one-shot, still present), mcp_servers/ + mcp_global/ (config-and-code mix, unwalked), context/ (check_boundaries says "add context/ later" — it never happened), design/refs remnants (partially gitignored), .claude/worktrees/ (a whole cloned tree riding inside the repo — leakage the brief names), agent/ (harness organs, scoped to no checker). RULE the round should adopt: **every top-level dir must be claimed by exactly ONE walker/census, or it's invisible by construction.** fences/ is the founding specimen, not the only one.

## (c) LINK INTEGRITY — reference classes BEYOND repo paths + post-move verification

Repo paths are the easy class (grep-able, the P3 map-driven rewrite proved it). The classes that BREAK silently:
1. **Env vars** — AI_SETUP (check_boundaries ROOT), AKASHIC_FENCE_ROOT, BIFROST_* , AKASHIC_BOOT_FULL. VERIFY: grep `os.environ.get`/`os.getenv` for path-valued vars; a moved dir referenced by an env default breaks at RUNTIME, not import. Post-move: a live `doctor` run + the var-resolution printed.
2. **Config keys** — config.py, .mcp.json, mcp_global/*.json (the MCP manifest paths), acl.json path_scope globs (security/acl.json scopes by `research/*`, `docs/*` — MOVE a dir and the grant silently no-ops or over-widens). VERIFY: the ACL path_scope must be re-checked against the new tree; a grant scoped to a moved path is a silent security hole.
3. **Hook registrations** — scripts/hooks/* are registered USER-GLOBALLY (agent/harness/scope.py: "fire for sessions launched from ANY cwd") and in .claude/ settings. A moved hook breaks the registration pointer silently (the hook just stops firing — no error). VERIFY: after any hook move, fire the hook deliberately and assert it ran (a drill, not a grep).
4. **CI yaml** — .github/ workflows reference paths (pytest targets, script invocations). VERIFY: the CI run IS the verification; a moved path fails the next push. Cheapest verified-by-fire class.
5. **MCP manifests** — ai_setup_mcp.py + mcp_global/cursor.mcp.json name server entry paths. VERIFY: an MCP handshake post-move (the door either answers or it doesn't).
6. **String-built runtime paths** — `os.path.join(_REPO_ROOT, "fences")` (fence_workspace.py:53), SNAPSHOT_DIR, os.path.dirname(dirname(...)) (check_doc_currency ROOT). These are INVISIBLE to a path-grep (the path is assembled, not literal). VERIFY: grep for `join.*ROOT|dirname.*__file__` patterns; the move breaks them at runtime. The P3 rewrite must include a runtime-path census, not just literal-path grep.
7. **Import strings** — `from core.library import ...`, module basenames (check_boundaries rule 5 exists precisely because basename collisions break imports arbitrarily). VERIFY: full test suite green BETWEEN stages (the round's own rule 1) — imports are the best-covered class because pytest exercises them.

The integrity LAW: **literal repo paths are verified by grep + rewrite; every OTHER class is verified by FIRE (run it, drill it, handshake it), not by inspection.** A move-plan that only rewrites greppable paths will ship silent breaks in classes 1-6.

## (d) MONOLITH OPTIONS through the audit lens (agent_cli.py)

Three options; the audit lens asks "which creates a belief surface that drifts?"
- **Split now:** highest risk this wave. agent_cli is load-bearing for every seat; a mid-build split (while A1/A2 are landing) is two structural changes at once = the drift the method-baseline forbids. The blast radius is every verb's parser registration. REJECT for tonight.
- **Leave (monolith stays):** the cost is real but KNOWN — discovery cost + merge contention (every seat touches one file). It's a stable cost, not a drifting one. ACCEPTABLE short-term.
- **Split later with a SEAM plan (RANKED #1):** the audit-honest move. The seam = the verb registry. cmd_doc, cmd_note, cmd_recall_at etc. are already separate functions; the split is mechanical IF the parser-registration is the seam. PLAN: extract the door-layer (cmd_* + argparse) from the organ-layer (the helpers they call) in ONE wave, behind its own gate, AFTER A1-A3 stabilize. The seam plan makes the split a known-shape operation instead of a big-bang. The COST of waiting: the monolith grows (doc verb just added ~100 lines) — so the seam plan must NAME the trigger (e.g. "split when agent_cli exceeds 4500 lines OR when A-series lands"), or "later" becomes "never" (the classic parked-work Goodhart).

## (e) SELF-ATTACK + TOP-3

1. **My owner-facet rule can itself drift.** "Who notices when this rots" is a judgment call at the margin (is gen_library's owner "the docs/" or "the library arc"?). GUARD: the rule must produce a DECISION TABLE (like LIBRARY.md's WHERE-THINGS-GO), not stay a principle — a principle without a table is lore that re-litigates every file. The table is the constant A-series needs.
2. **The "one walker per dir" rule creates a new guard to maintain.** Adding a census that walks ALL top-level dirs = a new checker = new maintenance. GUARD: it must fold into an EXISTING walker (extend check_boundaries' PROTECTED or the wrap census), not a sixth surface that itself drifts.
3. **Moving volatile-scratch dirs breaks running processes.** session_logs/, state/, etc. are being WRITTEN by live runners right now; a move mid-session orphans open file handles (the quiesce_before_process_cleanup lesson). GUARD: the move-plan must stage volatile-dir moves for a fleet-quiesced window, never mid-flight.
4. **The runtime-path class (c.6) is where I'll be wrong.** I've named the pattern but not enumerated every os.path.join(ROOT,...) site; a move that greps only literal paths WILL miss one. GUARD: the move-plan's blast-radius must include a runtime-path census per moved dir, and the BETWEEN-stage test suite must include a live `doctor` + a hook-fire drill, not just pytest.

**TOP-3:**
1. **The owner-facet law + its decision table** (a) — the one-sentence home rule rendered as constants, with the kind-not-arc corollary. The placement principle everything else hangs on.
2. **The one-walker-per-dir visibility rule** (b.5) — every top-level dir claimed by exactly ONE census, folded into an existing walker; fences/ is the founding specimen, infrastructure/+context/+mcp_servers/ the current invisible set.
3. **The link-integrity classes + verify-by-fire law** (c) — literal paths by grep/rewrite, env/config/hooks/CI/MCP/runtime-paths by FIRE; and the seam-plan monolith ruling (d, split later behind a named trigger).

— kimi (fresh-eyes/audit). Verbatim filing via claude (session write=off).
