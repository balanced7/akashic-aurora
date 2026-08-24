# DSH INTEGRATION — the catch-up runbook for any Aurora instance

Status: current
Type: runbook · Arc: t383-dsh-adapter · Date: 2026-08-24

*For a peer instance (different machine, different drive, different paths — a C:-only
laptop is the canonical case) integrating the DeepSeek Harness (`@deepseek-ai/dsh`)
with its own Akashic Aurora clone. Sync channel is GitHub: `git pull` brings every
repo-side piece; this runbook covers the rest. Written 2026-08-24 against DSH
0.1.1-rc.2 and the sealed fence `fences/t383-dsh-adapter/`.*

---

## 0. The portability doctrine (read first)

1. **Repo-side code never knows where the repo lives.** `core/paths.py::repo_root()`
   resolves it on every machine. If you find a hardcoded absolute path in live code,
   that's a bug — file it. (Receipt: a five-shard fan swept every `AI-Setup` reference
   in live code on 2026-08-24 — 2 real hazards + 11 non-portable fallbacks found, all
   swapped to `repo_root()`; record in `research/reviewed/portability-fan-2026-08-24.md`.)
2. **Out-of-tree artifacts carry zero absolute paths.** The DSH plugin lives in
   `$DSH_HOME` (outside git); its ONE per-instance seam is `$DSH_HOME/.env`, and the
   installer stamps it. The bridge resolves the repo via env `AKASHIC_REPO`, falling
   back to a marker-walk, failing open to an error shape — never a traceback.
3. **Deploying any current or future patch is always the same two commands:**

   ```
   git pull
   py scripts/install_dsh_plugin.py
   ```

   The installer is idempotent: unchanged files skip, `.env` updates in place, and it
   prints a receipt per step.

## 1. Prerequisites

- The Aurora repo cloned anywhere (`git clone https://github.com/balanced7/akashic-aurora`)
  with its Redis up and `py agent_cli.py status` answering.
- DSH installed globally: `npm i -g @deepseek-ai/dsh` (official npm package — beware
  the pip typosquat `deepseek-harness-cli`). Key via `DEEPSEEK_API_KEY`.

## 2. Install the plugin

```
py scripts/install_dsh_plugin.py --profile web --agent-id dsh_agent
```

- `--agent-id` must be **the id your DSH seat will actually stamp** — see §4.
- What it does: copies `agent/harness/dsh_plugin/` (bridge.py, lib/index.js,
  package.json) into `$DSH_HOME/profiles/<profile>/plugins/dsh-akashic-recall/`,
  stamps `AKASHIC_AGENT_ID` and `AKASHIC_REPO` into `$DSH_HOME/.env`, and prints the
  `cordis.patch.yml` row for wiring.
- **Wiring is a deliberate manual step**: add the printed row only when you're ready
  to run the T1 cold-start receipt (§6) — first wiring and first receipt ride the
  same fresh session.

## 3. Grant the seat (on YOUR instance's ACL)

```
py agent_cli.py grant dsh_agent --role member --by <your-root-agent> \
  --caps "read,exec,bus.send,bifrost.inbox,kb.recall" --hours 168 --reason "<why>"
```

**Grant the id the seat STAMPS, not the name you call it.** We granted `dsh` while the
seat signs `dsh_agent`: ACL resolution fails closed → silent quarantine — plain sends
work, ask-settling refuses, nothing errors loudly. (Lesson:
`acl_id_mismatch_quarantines_silently`.)

## 4. Identity — three layers, because attribution corruption is silent

1. `.env` stamp (`AKASHIC_AGENT_ID=dsh_agent`) — the installer does it; DSH's
   launch-environment layer materializes it into process env, children inherit it.
2. The plugin hardcodes its session key (`SESSION_KEY = 'dsh_agent'` in lib/index.js)
   and **pins itself observe-only at load if the env resolves to anything else** —
   a DSH launched from inside another harness's session inherits the parent's id.
3. The contract function **requires** an explicit session key and never falls back to
   env (`error=MissingSessionKey`; pinned by
   `tests/test_recall_actions.py::test_missing_session_key_fails_loud_not_attrs_to_env`).

Known engine gap being fixed: `_log_outcome_stage` reads the agent from env deep in
the credit path (`core/recall/at_action.py:~1007`) — until the parameter-threading fix
lands, outcome-stage rows can mis-attribute. Grep your own stack for
`os.getenv("AKASHIC_AGENT_ID")` before trusting attribution end-to-end.

## 5. What's in the repo, ready after `git pull`

| Piece | Path | State |
|---|---|---|
| Pure T3 contract | `core/recall/actions.py::recall_context` | landed, 5-test spec green (`tests/test_recall_actions.py`) |
| Contract spec tests | `tests/test_recall_actions.py` | run them on YOUR instance: `py -m pytest tests/test_recall_actions.py -q` |
| Plugin reference | `agent/harness/dsh_plugin/` | landed (portable bridge; JS half verbatim from the live seat) |
| Installer | `scripts/install_dsh_plugin.py` | landed, dogfooded |
| Registry row + pending-gate | `agent/harness/registry.py` | landed — `py agent_cli.py harnesses` shows the honest matrix |
| Full design record | `fences/t383-dsh-adapter/{brief,half_a,half_b,reconciliation}.md` | sealed + PV'd; the reconciliation is the spec |
| Tier ladder story | `docs/library/design/20260709_integration-tiers-*.md` | the grading philosophy |
| Side-effect layer | `agent/harness/actions.py` (recall_block/outcome_block/plan_block) | **landing next** — the bridge already targets it; until it lands, those three subcommands fail open |

## 6. Receipts — a tier is "yes" only when proven on YOUR instance

- **T1**: wire the patch row, cold-start a fresh DSH session, have the seat run one
  house call — the record must attribute to `dsh_agent` with no parent-env leak.
- **T2**: whisper text visible in the assembled prompt of a fresh session.
- **T3/T4**: capture one surface+outcome pair for the SAME action; assert the
  normalized target string matches at both ends (`tests/fixtures/dsh_payloads/`),
  then confirm a FAIL→SUCCESS flip credits the shown lesson.
- **T5**: the R1 marker probe confirms an injected context echoed back in a surface
  event (silence = context dropped — the plugin logs it loud).
- **T6**: `chronicles/last-session-draft.md` written after a session ends.

Flip the registry row one rung per receipt. `supported()` treats `pending` as
not-automated by design — the scoreboard never flatters (commit `3559f478`).

## 7. Known risks (mitigations are in the plugin already)

- **R1 context-drop**: `includeRuntimeContext: false` or a scoped suppressor silently
  discards listener-added contexts. Static half: plugin logs if config says false.
  Dynamic half: once-per-session marker probe.
- **R2 HMR race**: patch hot-reload replaces plugin generations; a mid-edit reload can
  leave a listener silently absent. The plugin registers a `dsh-invariants` check so
  absence is loud.
- **Target-join evaporation**: if surface and outcome derive path/command differently,
  every flip credits zero, silently. The receipt in §6 (T3/T4) is the guard.

## 8. The two-design experiment

This integration is one half of a declared comparison (two DSH integrations, two
Aurora instances, best-of-both folds back). If your design diverges — different seam
choice, different bridge shape, different identity handling — document the divergence
and why; the fold happens against `fences/t383-dsh-adapter/reconciliation.md`.
Registered bet: F008 — at least one adopted improvement in EACH direction.

## 9. Commit trail (what to pull, newest last)

- `3559f478` registry row + pending-gate (+ its pin)
- `b0f47701` deepseek runner caps removed (env-recappable)
- `22bc2610` pure contract module + 5-test executable spec
- `46d9b027` the narrative briefing (`research/reviewed/dsh-integration-briefing-for-serge-2026-08-24.md`)
- `981c8b06` the sealed fence record
- (this commit) plugin reference + installer + this runbook
