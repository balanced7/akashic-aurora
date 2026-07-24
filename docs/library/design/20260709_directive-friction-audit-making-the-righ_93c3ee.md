---
akashic_id: art_20260709_directive-friction-audit-making-the-righ_93c3ee
akashic_sha: fc46e714153d
status: fossil
type: design
date: 2026-07-09
title: Directive Friction Audit — making the right thing the easy thing
gist: "> A friction analysis of the agent directives in this system, and the optimizations that make > them get done *right, every time*. Grounded "
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, conducting, audit]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260709_directive-friction-audit-making-the-righ_93c3ee -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Directive Friction Audit — making the right thing the easy thing

> A friction analysis of the agent directives in this system, and the optimizations that make
> them get done *right, every time*. Grounded in the real hook/door wiring + the behavioral-design
> and LLM-agent-reliability literature. Written 2026-06-30.

## TL;DR

**Reliability is a property of design, not diligence.** A directive that depends on an agent
*remembering* to do it will be skipped under load; one the system makes automatic or frictionless
gets done every time. This repo already paves most of the path with hooks — the remaining failure
surface is the handful of directives still left to agent diligence: **boot, learn, note, feedback,
bus-sync, handoff, and end-of-session ship**. The fixes are mechanical: push each one leftward on
the spectrum **forcing-function > just-in-time prompt > documentation > memory**, *without* adding
context noise (the lever and the noise-budget are in tension; the resolution is always
*just-in-time + silent-when-empty + small-by-default*).

---

## 1. Thesis — why "diligence" is the wrong foundation

The user's principle: *if you want the right thing done, make it as easy to do as possible.* The
rigorous form is the **Fogg Behavior Model**: a behavior fires only when **Motivation, Ability, and
a Prompt converge at the same moment** (B = MAP) — miss any one and the behavior does not happen,
no matter how good the system is ([Fogg Behavior Model](https://www.thebehavioralscientist.com/articles/fogg-behavior-model)).

For an **agent**, this collapses in a useful way:

- **Motivation is not a usable lever.** An agent's "want" is just its instructions and in-context
  salience, and that decays as the task fills the window. You cannot reliably dial it up.
- So reliability ≈ **Ability × Prompt**: maximize *ease*, and supply a *cue at the exact moment of
  need*. Fogg's own taxonomy maps directly: *facilitator* prompts (make it cheap/quick), *signal*
  prompts (remind when ability is already high), *spark* prompts (raise motivation — least useful
  for us).
- Fogg's ability rule — *"simplicity is a function of your scarcest resource at that moment"* — tells
  us **which** friction to cut: for an agent mid-task the scarce resources are **working context**
  (don't make me hold steps in my head) and **steps/tokens** (activation energy). Cut those
  specifically.

The agent-specific evidence is blunt: production agent systems converge on **bounded autonomy** —
"an LLM *proposes* actions but the **platform enforces** correctness" — because when you let the
model *choose* whether to follow a step, completion can fall **as low as 4%**; the fix is
"architectural: eliminate the choice entirely"
([Production conversational agents, arXiv 2505.23006](https://arxiv.org/pdf/2505.23006);
[AgentSpec runtime enforcement](https://cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf)).

> **Corollary — the reliability spectrum.** Every directive lives somewhere on
> **forcing-function → just-in-time prompt → documentation → tribal memory**. The further right,
> the more it leaks. The whole optimization is: *move each directive as far left as its
> value and risk justify.*

---

## 2. The optimum directives — what "right" even is

The canonical agent lifecycle (from `AGENTS.md` + the `agent_cli.py` door). "Done right" is the
behavior; **value** is the cost of skipping it; **freq** is how often it should fire.

| # | Directive | "Done right" means | Value | Freq |
|---|-----------|--------------------|-------|------|
| D1 | **Identity** | a stable `AKASHIC_AGENT_ID` so writes/locks/handoffs attribute correctly | high (provenance, locks) | once/session |
| D2 | **Boot** | load the ~9k-token distilled context + notes + unread mail at task start | high (avoids rework/re-decide) | once/session |
| D3 | **Recall-at-action** | see relevant lessons + peer lock *before* an edit/command | high (avoids known traps) | every edit/cmd |
| D4 | **Act under locks** | claim a lock before editing a shared path; respect peers' locks | high when multi-agent | per shared edit |
| D5 | **Learn** | record a real lesson (a fix that worked, an approach that failed, a gotcha) | **highest** (compounding memory) | per discovery |
| D6 | **Note** | durable where-we-are / decision state (write-once) | high (continuity) | per decision/checkpoint |
| D7 | **Feedback** | teach recall what was load-bearing | medium (ranking quality) | per useful recall |
| D8 | **Bus-sync** | read unread Bifrost mail at turn start (multi-agent) | medium (coordination) | every turn (multi-agent) |
| D9 | **Wrap / ship + mirror** | gate (boundaries+tests) then persist commits/lessons/notes at session end | high (durability) | end of session |
| D10 | **Handoff** | brief the next agent on where you left off | high when switching | end of session/switch |

---

## 3. A friction taxonomy

Each finding below names its friction **type**, so the fix targets the right thing:

1. **Discovery** — do I know this directive exists / that it applies *now*?
2. **Timing/recall** — is there a cue at the exact moment, or must I remember on my own?
3. **Activation energy** — steps, typing, context-switch, tokens to actually do it.
4. **Cognitive load** — must I form intent, choose among options, or hold state in my head?
5. **Fragmentation** — is it split across CLI / MCP / files / env vars?
6. **Verification** — do I know I did it right?
7. **Error-recovery** — does a mistake teach the fix, or fail silently?
8. **Trust** — do I believe the output enough to act on it?

---

## 4. The reliability spectrum, mapped to *this* system

The hooks are wired user-globally (`C:\Users\L5\.claude\settings.json`, absolute paths to
`E:/AI-Setup/...`, `AKASHIC_AGENT_ID=claude`). So for the `claude` agent on this machine, a large
part of the path is **already paved** — credit where due:

**✅ Automatic (forcing-function / hook — fires every time, zero diligence):**
- **D3 Recall-at-action** — `PreToolUse` on Bash + Edit|Write|NotebookEdit injects relevant lessons
  as `additionalContext`. *(This is why recall hints appear on every tool call, even from
  `C:\Users\L5`.)*
- **D4 Respect peer locks** — `PreToolUse` `check_write` fails **closed-with-teaching** on a peer's lock.
- **git-guard** — `PreToolUse` `check_bash` vets git commands.
- **D7 (implicit half)** — `PostToolUse` credits a FAIL→SUCCESS flip automatically.
- **Cache warm + prune** — `SessionStart`.
- **Ambient session draft** — `PreCompact` + `SessionEnd` draft a where-we-are note.
- **D1 Identity** — set in global env (for `claude`, this machine).

**⚠️ Diligence-dependent (documentation/memory — the actual failure surface):**
- **D2 Boot** — `SessionStart` only *warms the cache*; it never loads context. Boot is manual.
- **D5 Learn** — fully manual. *(highest value × highest forgettability — the #1 target.)*
- **D6 Note** — fully manual.
- **D7 Feedback (explicit useful/noise)** — manual (and, per the epistemic-risk register, the wrong
  signal as currently shaped).
- **D8 Bus-sync every turn** — manual; asking for a command *every turn* is the most-skipped directive.
- **D4 Claim your own lock** — manual.
- **D9 Promote/commit the wrap** — the draft is automatic; promoting + the gated ship is manual.
- **D10 Handoff** — manual.

> The pattern is the whole story: **everything on the ✅ list happens because a hook supplies both a
> perfect Prompt (fires at the exact moment) and maximal Ability (the system acts, not the agent).
> Everything on the ⚠️ list lacks the Prompt — there is no cue at the moment of need — so it rides on
> memory and leaks.**

---

## 5. Per-directive findings + fixes

Ordered by leverage (value × frequency × current friction).

### D5 — Learn (lesson capture) · the highest-leverage fix
- **Friction:** Timing/recall (no cue at the moment a lesson exists), Activation energy (a long
  multi-flag command), Cognitive load (compose experiment-name + tried + result + recommend +
  category + success from memory).
- **Fixes (push to JIT + facilitator):**
  1. **Prompt at the moment of insight.** `PostToolUse` *already* detects a FAIL→SUCCESS flip — the
     exact instant a lesson was just earned. Extend it to surface a single silent-when-irrelevant
     line: *"you just got X working after a failure — `learn` it? (one line)."* This converts D5 from
     memory to a **signal prompt**.
  2. **Auto-draft from the session.** At wrap, draft candidate lessons from the diff + the
     FAIL→SUCCESS events (the ambient-capture machinery already exists for notes). Capture becomes a
     **byproduct of the work**, not a separate chore — the agent edits a draft instead of authoring
     from scratch.
  3. **Pre-fill defaults.** `--category` and `--success` inferred from context; `--experiment`
     suggested from the touched files. Cuts activation energy + cognitive load (Fogg's scarcest-resource rule).

### D2 — Boot
- **Friction:** Timing/recall (nothing fires it), Discovery (a new agent may not know to).
- **Fix:** make `SessionStart` *inject* context, not just warm it — but **carefully**, because boot
  is deliberately ~9k tokens and "more context makes models worse." So inject a **light auto-boot**
  (RECENT NOTES + top blockers + unread-mail count, a few hundred tokens) as `additionalContext`,
  with the full `boot` one advertised hop away. Zero-diligence context load *without* context rot.

### D8 — Bus-sync every turn
- **Friction:** Timing/recall at its worst — a per-*turn* manual command is essentially never done
  reliably.
- **Fix:** fold it into a turn-start hook (`UserPromptSubmit`) that surfaces **unread** mail only,
  **silent when the inbox is empty** (same discipline as recall). Never rely on per-turn diligence.

### D1 — Identity
- **Friction:** Fragmentation (an env var), Error-recovery. Automatic for `claude` here, but
  **fragile**: hardcoded, machine-specific, and still **unset for `cursor`** → provenance holes
  (this is the upstream of Factor 1's laundering and the `[unverified]`/unknown-author tags).
- **Fix:** derive identity at the door (one-time setup check that fails **closed-with-teaching** —
  the pattern already used for locks), so a missing `AGENT_ID` is impossible to ignore rather than
  silently defaulting to `unknown`.

### D9 / D10 — Wrap-ship / Handoff
- **Friction:** Timing/recall — the draft auto-captures, but *promoting* it (and handing off) is manual.
- **Fix:** at `SessionEnd`, surface the draft prominently and, if work looks unfinished, emit a
  **closing checklist** (Gawande: 5–9 critical items, time-boxed — checklists cut error dramatically
  by making the easy-to-skip steps explicit; [Checklist Manifesto](https://grahammann.net/book-notes/the-checklist-manifesto-atul-gawande)).
  Keep `ship` as the **one-command paved path** (it already gates boundaries+tests+commit — a clean
  control poka-yoke).

### D7 — Feedback
- **Friction:** Timing/recall + Trust, and (per the register) it rewards *agreement*, not correctness.
- **Fix:** lean on **implicit, causally-attributed corroboration** (the ranking & feedback slice);
  if an explicit vote is ever asked, append it as a one-keystroke affordance on the recalled line —
  never a separate remembered step.

### D3 / retrieval — already automatic, but generalize the *pull*
- Recall-at-action is the model fix (hook = perfect prompt + max ability). The open gap is the
  **one-hop pull to ground truth** (the in-flight "recommend less, retrieve more" slice). That work
  *is* this audit's principle applied to the retrieval directive; generalize it everywhere a
  surfaced pointer should expand to the full faithful record in one advertised step.

---

## 6. Cross-cutting design principles (the reusable rulebook)

1. **Don't rely on motivation.** Maximize Ability and supply a Prompt at the moment of need.
2. **Forcing function for must-happen; JIT prompt for should-happen; docs only as backstop.**
   The platform enforces; the agent proposes (bounded autonomy).
3. **Prompt at the moment of action, not at session start** — cues injected early are gone by the
   time they're needed.
4. **One door, one hop** — kill fragmentation and activation energy; the cheap path must be the
   correct path, so satisficing lands on "right."
5. **Defaults do the work** — pre-fill the hard parts; make capture a *byproduct* of the work
   (auto-draft from what already happened), not a separate chore.
6. **Fail closed, and teach the fix in the error** — the existing lock/agent-id pattern, applied
   everywhere a directive is mandatory.
7. **Confirm completion** — close the loop so the agent knows it landed (verification friction).
8. **Keep the obligatory list short** (5–9, checklist-sized) — every required step competes for the
   same scarce attention.
9. **Reduce friction *without* adding noise.** Ease and context-rot are in tension; the standing
   resolution is **just-in-time + silent-when-empty + small-by-default**. (This is the same
   discipline as the epistemic-risk work — they are one program.)

---

## 7. Prioritized roadmap

| Rank | Change | Lever | Type | Touches |
|------|--------|-------|------|---------|
| 1 | JIT "learn it?" prompt on FAIL→SUCCESS + auto-drafted lessons at wrap | signal prompt + facilitator | quick-win → project | `claude_posttooluse.py`, wrap |
| 2 | Light auto-boot injected at `SessionStart` (notes + blockers + mail count); full boot one hop away | facilitator | quick-win | `claude_sessionstart.py` |
| 3 | Turn-start bus-sync hook, silent-when-empty (`UserPromptSubmit`) | signal prompt | quick-win | new hook + settings |
| 4 | One-hop pull to full record + "N of M" escape (the in-flight slice) | facilitator | in progress | `at_action.py`, `agent_cli.py` |
| 5 | Identity fail-closed-with-teaching at the door; kill `unknown` author | forcing function | quick-win | door + `learning_store.py` |
| 6 | SessionEnd closing checklist + prominent wrap-draft surfacing | checklist | project | `claude_sessionend.py` |
| 7 | Pre-filled `learn`/`note` defaults inferred from session context | facilitator | project | door |

**Guardrail on the whole program:** every added prompt must be *silent when it has nothing to say*
and *small when it does* — otherwise we trade diligence-friction for context-rot, which is a worse
deal. Measure success by *directives-done-without-being-asked*, not by how many reminders we emit.

---

## 8. Connection to in-flight work

This audit and the **epistemic-risk register** (`note: epistemic-risk-register`) are the same design
program from two angles: the register makes the surfaced knowledge *honest*; this audit makes the
right *actions* frictionless. They meet at the same rule — *make the cheap path the correct path,
keep it silent until it has something to say.* The "ranking & feedback" slice (roadmap #4) is the
first shared deliverable.
