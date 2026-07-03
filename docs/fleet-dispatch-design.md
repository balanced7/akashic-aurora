# Fleet dispatch — an intelligent, easy structure for calling local models

Written 2026-07-03 (user ask: "make the local agent pool more powerful in a compact way … an
intelligent and easy to use structure for using and calling said llms"). Grounded in the actual
invocation surface (see the local-model infra map) and the R013 small-models evidence base
(research/reviewed/frontier-small-models-2026-07.md). PRE-build design — the first slice ships in the
same commit as its door (capability_without_a_door).

## The gap (why this exists)

Two frictions, both real in the current tree:

1. **Model knowledge is FRAGMENTED.** The set of local models and their properties lives in at least
   four places that can drift: a PowerShell array in `run_model_bakeoff.ps1`, prose in
   `scripts/local/NOTES.md`, the scrubber regex in `anonymize_bakeoff.py`, and the launcher's default.
   Worse, the *bakeoff verdicts* — why gpt-oss:20b and qwen were eliminated — live only in a chronicle
   note. There is no single place that answers "which models do we have, what are they good at, and
   which are disqualified and why."

2. **There is NO way to call a local mini for a BOUNDED SUBTASK.** Today a local model can only be
   invoked by launching a full Claude Code session (agentic path: `launch_local_agent.ps1`,
   `run_research_day.ps1`). That is the right tool for multi-step work and the wrong tool for
   "summarize this page" / "classify this" / "extract these fields as JSON" — the exact subtasks a
   compact specialist model is *for*. The pool cannot be composed until a single-shot call exists.

## The structure

Four parts, each a thin layer over what already works. Verb-noun vocabulary: **roster** (who's
available) → **select** (pick one for a job) → **call** (invoke it) → **door** (`agent_cli fleet`).

```
                         core/fleet/models.json   ← single source of truth (data)
                                 │
        core/fleet/roster.py  ── models() · get(tag) · select(capability, constraints)
                                 │                    (pure-local, hermetic; availability probe is opt-in)
        core/fleet/caller.py  ── call(tag, prompt, …) → text | JSON
                                 │                    (Ollama /api/generate; num_ctx pulled from the spec)
        agent_cli.py  ──────────  fleet list | fleet select | fleet call     (the door)
```

Two calling **modes**, both served by the roster:

- **AGENTIC (exists).** Launch a Claude Code session backed by a model for multi-step tasks. The
  launcher owns the process environment; the roster's job is only to *provide* the model's spec (tag,
  ctx, agent_id) so the launcher/research-day/bakeoff scripts stop hard-coding it. Roster **provides,
  does not drive** — it is a data module, never a daemon.
- **DIRECT (new — this slice).** `call(tag, prompt) → text/JSON` for bounded subtasks. One function to
  point any specialist at a prompt and get an answer back, without the ceremony of a full session.

## The roster (single source of truth)

`core/fleet/models.json` — one row per local model. Schema:

| field | meaning |
|---|---|
| `tag` | Ollama tag, e.g. `qwen3.5:9b` (the identity) |
| `agent_id` | AKASHIC_AGENT_ID for credit attribution, e.g. `qwen_local` |
| `family` / `arch` | `qwen` / `9B dense`; for humans + the bakeoff |
| `host` | default `http://127.0.0.1:11435` (native Ollama, NOT 11434) |
| `context` / `context_max` | pinned num_ctx (avoids the 4K silent-truncation trap) / hardware ceiling |
| `vram_gb` | measured on-GPU footprint at the pinned ctx (the fit constraint) |
| `throughput_toks` | measured gen tok/s (the ranking signal when several fit) |
| `status` | `active` \| `tested` \| `candidate` \| `gated` |
| `capabilities` | labels the selector routes on: `generalist`, `research`, `tool-use`, `extract`, `summarize`, `classify`, `faithful`, `long-context` |
| `notes` | one line for humans |
| `disqualifier` | non-null ⇒ WHY it's gated (e.g. "citation laundering, bakeoff 2026-07"). Encodes the verdict that today lives only in prose. |

**The roster earns its keep three ways:** (1) the launcher/bakeoff/research-day scripts read it
instead of hard-coding arrays; (2) `call()` pulls `context` from it so even a one-shot call never hits
the 4K-default truncation trap; (3) `status`/`disqualifier` make the bakeoff verdict a queryable fact,
not tribal knowledge.

v0 is seeded from the bakeoff (glm-4.7-flash `active`; qwen3-coder:30b, gpt-oss:20b `gated` with their
disqualifiers) plus the R013 top-5 as `candidate` rows (qwen3.5:9b/4b, granite-4.0-h-small,
gemma-3-12b-it, qwen3-8b) — so the registry is also the round-2 bakeoff worklist.

## Select (capability + constraint routing)

`select(capability=None, status="active", max_vram=None, min_context=None) → spec | None`. Filters the
roster and returns the best fit; fail-soft (`None`, never a raise). v0 ranks by throughput among the
models that fit — **deterministic, not learned**. A learned local-vs-frontier router is deliberately
future work: it needs the R016 capability map and real usage data, and a value-optimized router would
walk straight into the F2 Goodhart trap the epistemic-risk register warns about. Route on declared
capability now; learn later, if ever, with the same "measure before you optimize" discipline.

## Call (the direct caller)

`call(tag, prompt, *, system=None, max_tokens=512, temperature=0.2, fmt=None, timeout=120, host=None,
opener=None) → str`. Over Ollama's native `/api/generate` (same endpoint preflight already proves on
this box). Design choices, each earned:

- **`temperature=0.2` default** — the fleet recipe (higher → malformed output / tool params).
- **`num_ctx` from the roster spec** — the caller looks up the tag and pins context, so a direct call
  inherits the same truncation defense as an agentic session.
- **`fmt="json"`** — sets Ollama's `format` param for constrained JSON. R013 finding 7: small models
  emit 0% *usable* JSON under naive prompting; grammar/format scaffolding is mandatory, so the caller
  makes it a first-class argument, not an afterthought. (A future `call_json(tag, prompt, schema)` can
  pass a full GBNF/JSON-schema grammar.)
- **`opener` injectable** — tests pass a fake transport; no network, hermetic. Same discipline as the
  injectable stores elsewhere in core.
- **Raises `FleetCallError` on failure, does not return "".** A read (recall/triage) is fail-soft-silent;
  a *call* is a request for a result — a failed subtask must be visible, never a silent empty string
  that the caller mistakes for an answer. The door catches it and prints a clean error.

## The door

`agent_cli.py fleet <action>` — same door agents already use:
- `fleet list [--json]` — the roster + (opt-in `--probe`) live availability from `/api/tags`.
- `fleet select --capability extract [--max-vram 8] [--min-context 32000]` — show the pick + why.
- `fleet call --model qwen3.5:9b --prompt "…" [--json] [--system "…"]` — a one-shot call (also the
  manual smoke test for a newly-pulled model, before it earns `active`).

## Doctrine & constraints (what keeps this honest)

- **core = stdlib-only** (deploy_kit_public): `json` + `urllib` only, no new deps.
- **Provides, does not drive**: the roster hands specs to the launcher scripts; those still own the
  process environment. No daemon, no hidden global state.
- **Reuse preflight, don't reinvent**: the roster does a *light* availability check (`/api/tags`,
  opt-in); deep fitness (tool-calling, canary, throughput) stays `preflight_local_model.py`'s job.
- **Fail-soft reads, honest calls**: `models()/select()` degrade to empty; `call()` raises on failure.
- **Separate from the harness registry**: `agent/harness/registry.py` is the runtime-tier axis
  (T0–T6); this is the model-tier axis. Different data, kept apart on purpose.

## Minimal first slice (this commit)

roster (`models.json` + `roster.py`) + `caller.py` + the `fleet` door + hermetic tests. Enough to
`fleet list`, `fleet select`, and `fleet call` a bounded subtask today. Specialist rows (embedders,
rerankers, extractors, guard/router minis) get added as R016 lands — the schema already holds them.

## Composition patterns (designed; built as the roster fills)

From R016's capability map — the payoff of a callable pool is *composing* small models:
1. **draft-then-verify** — a fast mini drafts, a faithful mini (or a deterministic check / FAITH-1) verifies.
2. **embed → retrieve → small-generate** — a tiny embedder feeds recall; a small model writes the answer.
3. **classify → route → specialist** — a classifier mini picks the lane; a specialist does the work.
4. **small-extract + frontier-reason** — a mini pulls structured fields; the frontier model reasons over them.

Each is a few `call()`s composed — which is exactly why the direct caller is the unlocking primitive.

## Open questions
- When several models fit, is throughput the right tiebreak, or should faithfulness/capability-fit weight higher? (v0: throughput; revisit with R016.)
- Roster availability: reconcile against `/api/tags` at read-time (slower, always-fresh) or on an explicit `fleet refresh`? (v0: opt-in `--probe`.)
- When does `select` auto-trigger `preflight` vs trust a cached verdict? (v0: never auto; preflight stays a launch-time gate.)
- The local↔frontier escalation policy for the A0 assistant loop (015) consumes this selector — designed there, not here.
