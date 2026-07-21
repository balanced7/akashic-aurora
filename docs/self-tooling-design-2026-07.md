# Self-Tooling Arc — Reconciled Design (agent-authored verbs)

Status: current  (2026-07-20, reconciliation of three independent halves; AWAITING DANIEL'S GATE)

Daniel's charge (near-verbatim): build your own commands automating the task classes you do by hand —
"make our substrate BE a substrate and invite new expressions of skills and capability… less of your
context fixated on mechanics… A builder with tools can get much more done than one bare handed."

Halves: claude (chat, receipts-first), deepseek (research/reviewed/self-tooling-deepseek-half-2026-07-20.md,
two filings), kimi (research/reviewed/self-tooling-kimi-half-2026-07-20.md). Blind protocol held.

## Convergences (all three, independently)

1. **Sugar-only safety-by-construction** (deepseek's frame, kimi co-signs verbatim, claude concurs):
   authored verbs resolve to existing cmd_* primitives and cannot mint capabilities — an alias cannot
   grant itself exec. Worst case = a confusing error. This makes the `verb.author` cap safe to grant broadly.
2. **Two-tier registry**: per-agent toolbelt (self-serve, personal) + shared tier (peer-reviewed) —
   `data/verb-registry/<agent>.json` + `shared/`. NOT argparse edits; `discover` gains the registry as a source.
3. **One graduation conveyor**: mint (personal) → bless (shared, fence-lite) → patch-verb proposal →
   full fence + Daniel gate → first-class cmd_* with three-door parity → (K3) ritual status in boot.
   The same motor as the institutional arc's conveyor — deliberately.
4. **Discovery is half the feature** (claude's bifrost-standby receipt: the verb existed, went unused all
   night): registry rides `discover` ranking + a boot toolbelt line + recall-at surfacing of chained verbs.
5. **Junk-drawer guards**: per-agent quotas (start 20/20), auto-retirement (30d warn / 60d retire, never
   delete — T039 pattern), deletion ritual with receipt, shared-tier must justify existence at fence.
6. **The verb candidates themselves converged hard** — capture/persist-verbatim named by all three
   (claude hand-wrote the same extractor 5× tonight), ask-peer by two, boot-orient/triage composites by
   all three, drain-decide/standby by all three.

## Load-bearing unique folds

- **kimi (a): honesty labels IN the registry schema** — every entry carries
  {evidence: VERIFIED|INFER|GUESS, tested_against: pin|none}; an unpinned skill runs GUESS-tier and
  confesses it in --help. Method-baseline applied to the authoring surface itself.
- **kimi (b): the HOOK REGISTRY is the load-bearing seam** — pre-send / pre-handoff / pre-commit
  lifecycle points, generalizing PreToolUse. FENCE FLAG: without it, guard-class verbs are dead letters.
  Pin this seam first.
- **kimi (c): registry is a projection** — durable fenced JSON is source-of-truth; writes idempotent by
  (agent, name, version); crash → re-project, never edit-to-agree (recovery-arc P5 applied).
- **kimi (d): per-seat authoring species with provenance** — kimi authors CHECK/VERDICT verbs, deepseek
  authors DO composites, claude authors GATE verbs; shared entries keep the author's label chain.
- **deepseek: the verb quintet** — alias / skill / guard / patch-verb / bless as the authoring primitives,
  plus `verb.author` vs `verb.promote` cap split (author broad, promote gated).
- **claude: the receipts + surfacing law** — existence without discovery equals absence; every mint must
  land in discover/boot/recall-at the same commit.

## Sliced plan (V-series; each fenced, pins RED-first)

- **V0 — Registry + alias/skill + discovery** (S/M). Schema (with honesty labels), per-agent dir, dispatch
  resolution before subparsers, discover/boot integration. First minted verbs = the felt-blood set:
  `capture` (verbatim-persist — kills the 5×-rewritten extractor), `ask-peer`, `orient`/`triage-me`.
- **V1 — Hook registry + guard** (M; kimi's fence flag = pin the seam first). First guard: pre-send
  size-ceiling/one-question check (the deepseek empty-reply + kimi 4000-clip genus, confessed at compose time).
- **V2 — bless / note-handoff / discharge-check / patch-verb** (M). The promote path with provenance,
  the redelivery-safety check (dogfood-first: self-tooling increases re-processable state), the governed
  route from felt-friction to changed-door.
- **V3 — Graduation conveyor wiring** (M). Usage-count → graduation recommendation → Daniel flip;
  K3 interlock (ritual status); T098 plugin-registry bridge (user plugins and agent verbs feed the same
  discover surface; a proven plugin can cross tiers).

## Three-arc coupling (one program)

Recovery = the system heals itself. Institutional-knowledge = the system learns from every incident.
Self-tooling = the system grows its own hands. Shared spine: receipts feed the incident ledger (K1/K2);
the conveyor is one motor (K3 = V3); catalog entries and minted verbs are the same species of governed,
bounded, receipted automation. Recommended gate order if staged: recovery S0 → institutional K0 →
tooling V0 — three small slices, each pays immediately.

## Gate asks for Daniel
1. Approve the arc + V0→V3 order.
2. Grant `verb.author` to claude/deepseek/kimi (sugar-only makes this low-risk; `verb.promote` stays gated).
3. Confirm V0's first mints (capture, ask-peer, orient/triage-me) — the three verbs tonight bled for.
