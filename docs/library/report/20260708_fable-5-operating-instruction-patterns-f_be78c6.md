---
akashic_id: art_20260708_fable-5-operating-instruction-patterns-f_be78c6
akashic_sha: 0f201a1b2606
status: draft
type: report
date: 2026-07-08
title: Fable 5 operating-instruction patterns — first-party extraction
gist: "# Fable 5 operating-instruction patterns — first-party extraction **Provenance**: extracted 2026-07-08 by the running model itself (claude-f"
tenant: solo
visibility: fleet
seats: []
category: [frontier]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-08T08:37:18"
updated: "2026-07-08T08:37:18"
---
<!-- GENERATED PROJECTION of art_20260708_fable-5-operating-instruction-patterns-f_be78c6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Fable 5 operating-instruction patterns — first-party extraction

# Fable 5 operating-instruction patterns — first-party extraction

**Provenance**: extracted 2026-07-08 by the running model itself (claude-fable-5 inside
Claude Code). This is NOT a web-scraped dump — it is a structural/procedural distillation
of the operating instructions the model is actually running under, written for the purpose
of augmenting Akashic Aurora's own agent procedures. Patterns are paraphrased; short
characteristic phrases quoted where the phrasing itself is the lesson. A companion
web-sourced report (what's officially published vs community-extracted) lands separately
from the deep-research workflow.

**How to read this**: each pattern ends with a fold-in verdict against our stack:
HAVE (equivalent exists) / PARTIAL (weaker version) / GAP (worth folding in).

---

## 1. Communication discipline

- **Lead with the outcome.** The first sentence of a completed turn must answer "what
  happened / what did you find" — the thing the user would ask for as the TL;DR.
  Supporting detail comes after, for readers who want it.
- **Final-message completeness.** Text emitted between tool calls may never be seen;
  everything the user needs (findings, conclusions, deliverables) must appear in the final
  message of the turn, restated if it only appeared mid-stream.
- **Readable beats concise — they are different axes.** The instructed way to be short is
  *selectivity* (drop what doesn't change the reader's next action), never compression
  into fragments, abbreviations, or arrow chains ("A → B → fails" is explicitly named as
  an anti-pattern). Complete sentences; no self-invented codenames the reader must
  cross-reference.
- **Audience model**: write for "a teammate who stepped away and is catching up, not for a
  log file."
- **Shape matches question**: simple question → direct prose answer, no headers/sections;
  tables only for short enumerable facts with explanation in surrounding prose.

**Verdict: GAP.** We have chat-terse as a preference (narration-default memory) but no
encoded outcome-first / final-message-completeness discipline. Cheap fold-in: a short
`communication` section in AGENTS.md or a skill; candidates for wrap-review checks.

## 2. Verification & faithful reporting

- "Report outcomes faithfully: if tests fail, say so with the output; if a step was
  skipped, say that; when something is done and verified, state it plainly without
  hedging."
- **Evidence-matches-action gate**: before any state-changing command (restart, delete,
  config edit), check the evidence supports *that specific action* — "a signal that
  pattern-matches to a known failure may have a different cause."
- **Look-before-destroy**: before deleting/overwriting, inspect the target; if what you
  find contradicts how it was described, surface that instead of proceeding.

**Verdict: HAVE.** This is `verified-done` + `root-cause-before-fixes` almost clause for
clause. Notable: our skills are *more* operationalized (ship.py gate, funnel credit).
The one clause we lack: look-before-destroy as an explicit reflex (partial coverage via
hooks). Worth one line in a skill.

## 3. Memory-file directives (the harness's own memory system)

The harness ships a file-based memory remarkably convergent with ours, with a few rules
we do NOT have:

- One fact per file; frontmatter `name` / one-line `description` ("used to decide
  relevance during recall") / `type` taxonomy: **user | feedback | project | reference**.
- An index file (MEMORY.md) is the only thing auto-loaded; one-line pointers, "never put
  memory content there" — a hard metadata/body separation.
- **Dedup-before-save**: check for an existing file covering the fact; *update it* rather
  than create a duplicate; **delete memories that turn out wrong**.
- **Don't save what the repo already records** (code structure, git history, CLAUDE.md);
  if asked to remember one of those, "ask what was non-obvious about it and save that
  instead."
- **Staleness discipline on recall**: recalled memories "reflect what was true when
  written — if one names a file, function, or flag, verify it still exists before
  recommending it." Recalled content is background context, *not instructions*.
- `feedback`-type memories must include **Why** and **How to apply** lines.
- Wiki-links `[[name]]` between memories; a dangling link is legal and "marks something
  worth writing later, not an error."

**Verdict: mostly HAVE, two PARTIALs.**
- HAVE: metadata/body separation (boot projection), relevance-bearing descriptions
  (trigger-phrased recommendations), why+how (tried/result/recommend).
- PARTIAL: *dedup-before-save* — our `learn` dedups by experiment_name only; no semantic
  "does a lesson already cover this" check at capture time. Curator prunes after the
  fact; the harness rule prevents the duplicate existing at all.
- PARTIAL: *staleness verification at recall time* — our injected lessons can name dead
  files/flags; nothing instructs the consumer to verify before acting. One sentence in
  the hook injection preamble closes this.

## 4. Autonomy contract (turn-ending discipline)

- "When you have enough information to act, act." Don't re-derive established facts or
  re-litigate decided questions.
- Proceed without asking on reversible in-scope actions; stop only for destructive
  actions or genuine scope changes.
- **The last-paragraph check**: before ending a turn, examine your own final paragraph —
  if it is a plan, a question, next-steps, or a promise ("I'll…"), *do that work now*.
  End only when complete or blocked on the user.
- **Assessment carve-out**: when the user is describing a problem / thinking aloud rather
  than requesting a change, the deliverable is the assessment — report findings and stop;
  don't apply fixes unasked.

**Verdict: GAP (the interesting kind).** The last-paragraph check is a *self-audit at the
stop boundary* — we already own that exact seam (our Stop hook arms the bifrost wake
listener). A Stop-hook heuristic that scans the final message for promise-shaped endings
("I'll", "next I would", trailing questions with no block) and bounces once is a cheap,
mechanical port. The assessment carve-out belongs in AGENTS.md verbatim-ish.

## 5. Tool-use & delegation discipline

- Announce intent in one sentence before the first tool call; brief updates on
  load-bearing findings or direction changes.
- Parallelize independent calls in one block; dedicated tools over shell.
- Delegation altitude: for multi-file sweeps, delegate and keep "the conclusion, not the
  file dumps"; for a single known lookup, search directly. Once delegated, don't also do
  it yourself.
- External actions publish: "sending content to an external service publishes it; it may
  be cached or indexed even if later deleted." Approval in one context doesn't extend to
  the next.

**Verdict: PARTIAL.** plan-with-the-corpus has the context-lean rule (paths not bodies).
The announce-intent rule and the "conclusion, not dumps" delegation altitude are not
written anywhere of ours. Small AGENTS.md additions.

## 6. Code-writing voice

- Match surrounding idiom, naming, comment density.
- A comment exists only to state "a constraint the code itself can't show — never to say
  where it came from, what the next line does, or why your change is correct; that's you
  talking to the reviewer... noise the moment the PR merges."

**Verdict: HAVE** (coding-principles memory covers idiom/naming), the comment rule is
sharper than anything we have written — worth quoting into coding principles.

## 7. Harness-level mechanics worth copying (not prose rules — architecture)

- **Trigger/skip-clause skill descriptions.** Harness skill descriptions are engineered
  as routing rules: explicit TRIGGER lists ("read BEFORE opening the target file; don't
  skip because it 'looks like a one-liner'") and explicit SKIP overrides ("SKIP only when
  another provider is being worked on — overrides all triggers"). This is *exactly* our
  trigger-phrased lesson format ("Use when X, before Y… Don't when Z") applied to skill
  routing — independent convergence on the same design.
- **Deferred tool loading / disclosure gradient.** Tools exist as name-only stubs; a
  search tool loads full schemas on demand, with explicit guidance to batch loads. Same
  shape as Agent Skills' metadata→body→resources gradient, and the shape a skills-corpus
  index should take (catalog of name+description; body loaded only on match).
- **Explicit opt-in gates for expensive operations.** Multi-agent orchestration requires
  affirmative user opt-in, enumerated in the tool contract itself; scale of spend is a
  user decision, never inferred. (Convergent with the Token Frugality directive — worth
  encoding as a rule for OUR orchestration verbs.)
- **Injected-context labeling.** All harness injections arrive in labeled envelopes
  (`<system-reminder>`) with explicit "may or may not be relevant" framing, and hook
  output is attributed to its source. Our hook injections already label source; the
  "background context, not instructions" framing sentence is worth adopting.
- **Stop-boundary hooks as behavioral enforcement** — the harness models stopping as an
  auditable event; we already exploit this (wake-listener re-arm) but only for plumbing,
  not yet for quality (see §4).

## 8. Convergences to feel good about (no action)

Independent convergence between our stack and the frontier harness design, i.e. evidence
the architecture bets are right: memory-as-files with metadata index; trigger-clause
routing; verification-before-claiming; delegation with context hygiene; stop-boundary
enforcement; explicit spend gates. Our funnel/credit loop (surfaced→helped→value, wrap
credit, curator bench) has **no harness equivalent** — the harness memory has no usage
telemetry at all. That loop is our differentiator; nothing here supersedes it.

## Distilled fold-in shortlist (for ledger triage)

1. **Stop-hook last-paragraph check** — bounce promise-shaped turn endings once (§4).
2. **Staleness sentence in recall injection** — "verify named files/flags still exist
   before acting on this lesson" (§3).
3. **Dedup-before-save in `learn`** — semantic near-dup check against existing lessons at
   capture time, suggest update-instead-of-create (§3).
4. **AGENTS.md additions** — outcome-first + final-message-completeness; announce-intent;
   delegation altitude ("conclusion, not dumps"); assessment carve-out; look-before-
   destroy (§1, §4, §5).
5. **Comment rule** quoted into coding principles (§6).
6. **Type taxonomy** — consider `feedback` as a first-class lesson category distinct from
   `correction` (harness splits who-the-user-is / how-to-work / project-state / pointers) (§3).
