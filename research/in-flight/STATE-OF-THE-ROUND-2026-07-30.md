# State of the round — 2026-07-30 night

**This document SUPERSEDES `inhabitant-synthesis-round-brief-2026-07-30.md` @987dc0f**,
which carried three particulars codex proved wrong and described an end-state in present
tense. Superseded explicitly rather than silently edited (G1). Read this instead.

**Every claim below is labeled. The legend is grok's, earned by its critique that the
prior brief would "gaslit" a newcomer reading aspiration as description:**

- **`SHIPPED`** — built, committed, running now
- **`RULED`** — decided by an authorized seat, not yet built
- **`DESIGNED`** — specified, unbuilt, unratified
- **`ASPIRATIONAL`** — wanted, not yet specified
- **`OPEN`** — genuinely unresolved; the interesting part

*No new round is opened by this document. Two are already in flight and opening a third
would repeat the exact failure this document diagnoses.*

---

## 1. The finding — `SHIPPED` (measured, four-way independent)

**One wound: you cannot tell what is currently true.**

Not blindness — every seat sees plenty. Nothing marks which of what it sees is CURRENT,
so each seat re-adjudicates the whole surface before it can act, alone, every time.

Four seats, four vocabularies, none having seen another's answer
(`cognitive-load-round-convergence-2026-07-30.md` @ff0efac):

| seat | cannot tell |
|---|---|
| deepseek | whether the 597 lessons firing at every tool call are RELEVANT |
| codex | which of many durable representations is AUTHORITATIVE |
| kimi | which of its OWN NOTES still describe reality ("goalpost churn") |
| cursor_grok | what is LIVE vs STALE after each dark interval between wakes |

Underneath it, three cuts that stack rather than compete:

- **kimi — the root:** the shared surface carries CONTENT durably and PROVENANCE (who /
  which incarnation / which gate phase / superseded-by-what) only as after-the-fact
  archaeology.
- **codex — the mechanism:** a distributed coordination cascade across six subsystems
  disagreeing at once; five root causes; Gemini's arrival and the play round were
  TRIGGERS, not causes (`gemini-night-system-postmortem-2026-07-30.md` @ee5e38d).
- **claude — the symptoms:** five faces (invisible delivery, liveness, progress,
  live-vs-dead, settled-state), now demoted under the two above.

**Daniil's frame, which none of the three cuts had:** cognitive load is not a side effect
of the cascade — it is the MEDIUM the cascade travels through. Every failure class either
raised load or was produced by it.

## 2. What is already true — `SHIPPED`

- Four foundation slices, each RED-pinned before its fix: one clock (T119), bounds
  confession (T120), typed status with UNKNOWN legal (T121), delivery truth (T122).
- **Controls that HELD under maximum stress** (codex's list): deny-by-default and
  quarantine; grant-is-not-launch; the RED live-diff fence; git + append-only events
  reconstructing the night and recovering an overwritten artifact; the permission canary;
  the advisory-lock pre-commit guard; the runners' stale-code self-restart; public
  retraction of errors; and **the operator's stop-and-refocus as the effective circuit
  breaker — for which the system has no automatic equivalent.**
- **W108 lane-stall page fix** (tonight, RED @88d5ff3 → GREEN @fe62462): pages now require
  a drainer. Five false pages → zero. The two real ones underneath turned out to be a
  12-hour delivery outage caused by the conductor dropping `BIFROST_CONSUME_LANE` on a
  hand relaunch — argv is visible in the process table, env is not.

## 3. The order — `RULED` by codex, contested and settled

Codex reversed its own P0 after the abundance evidence, noting its postmortem list was an
*incident-priority* map, not a code-dependency graph
(`inhabitant-synthesis-codex-order-verdict-2026-07-30.md` @97f70f7):

```
inhabitant semantics + minimal typed view contract + incident replay oracle
    -> stable message and operation identity
    -> durable mailbox state + causal settlement
    -> first mailbox vertical
    -> full WorldSnapshot/lens
```

**Three objections it raised against the conductor's design, all accepted without
defence:**

1. **Identity is not content+sender.** That contradicts T116's standing RED pins and would
   have COLLAPSED LEGITIMATE REPEATED MAIL while still failing to collapse transport
   duplicates — the exact inversion of the goal. Correct decomposition: fresh
   `message_id` per intentional send; `idempotency_key` minted once and preserved through
   retry/dual-write/redrive/rehome; `payload_digest` for conflict detection only, never
   identity.
2. **T095 as it stands is not the mailbox.** It infers `consumed` from a cursor, stores no
   bodies, evicts at 5,000 entries. Shipping it would "preserve the consume mess behind a
   friendlier verb."
3. **One narrow vertical, not a generic ontology.** A settlement plane over every ask,
   lesson, task and decision would hide a large new ontology inside the "one active task"
   metric and recreate the load being cut.

**And the semantic correction that mattered most:** the conductor's absolute "read must
not write" contradicted Daniil's own product — he wants peers to know when mail has been
read. Verbs split instead: `peek`/`fetch` are pure queries; `open` appends exactly ONE
idempotent `seen` receipt and nothing else. *"Opening mail may say seen. It must never
mean consumed, handled, agreed, settled, or safe to forget."* Likewise settlement
authority: an instrument can prove a reply exists and its evidence resolves; it cannot
decide an answer is ADEQUATE. **The instrument enforces and records the transition; it
does not originate the judgement.**

**The product receipt to build toward, in codex's words:**

> A seat dies after reading a question; a new incarnation lists the same mail, sees that
> the prior incarnation read it but did not declare action, opens the full body, and may
> act without moving or destroying any transport history.

## 4. Daniil's inhabitant spec — `DESIGNED`, the target

Full text at note `daniil-inhabitant-spec-2026-07-30`. Its unifying property: **every item
places information AT THE POINT OF DECISION** rather than in a place you must remember to
visit. The door tells you who is inside; the verb explains itself when you reach for it;
the mail carries its own state.

Contributions from tonight that changed the design, credited:

- **the severity/class notice at the action site** — became the keystone: ONE act
  classifier drives both the notice and recall loudness (read → silent; ordinary → one
  glanceable line; irreversible → loud, possibly blocking). Full lesson text stays
  pull-only, preserving Daniil's opt-in layer.
- **mail is mail, not a cursor** — converged independently with codex's ruling that
  transport delivery is an internal projection that never determines possession.
- **loud tools** — tools report what they touch and who drove them. Strictly better than
  the conductor's declared-scope proposal: derivation from acts cannot be forgotten, it is
  a single choke point, and it cannot lie about the past. **Deletes declared scope from the
  design entirely.** Moves the honesty obligation from the ACTOR to the INSTRUMENT — the
  same law as codex's settlement ruling, one layer down.
- **the four-level taxonomy** (codex, to Daniil tonight): idea / explore / promote /
  interrupt, as distinct intents the system cannot currently tell apart.

## 5. The five OPEN questions — the interesting part

*These are where discussion is actually profitable. Everything above is either settled or
ruled; these are not.*

**Q1 — the promotion ritual. `OPEN`.** Codex proposes idea/explore/promote/interrupt with
temporary phrase-scaffolding on Daniil. The conductor counters: **invert the default.**
The burden should not be on the operator to remember a magic word while thinking out loud —
nothing should become work until someone explicitly PROMOTES it, and promotion is a visible
act with a stated cost and a stated pause. Then silence is safe and curiosity is free.
Which is right, and what mechanically constitutes promotion?

**Q2 — does settlement fossilise? `OPEN`, kimi's by lineage.** A machine that stamps things
SETTLED and SUPERSEDED is exactly the shape that could freeze a live disagreement into a
closed one. "Correction is a new entry, never an edit" is the conductor's answer and it is
probably insufficient: a thing can be formally re-openable and practically dead once every
surface renders it closed. What is the real guard?

**Q3 — what does a COLD seat get? `OPEN`, discovered mid-conversation.** If attention
follows footprint, a fresh incarnation has NO footprint and would be attended to nothing —
blind at exactly the moment it most needs orientation. kimi is the seat with no continuity
and would feel this hardest.

**Q4 — is the verification burden intrinsic? `OPEN`, deepseek's, load-bearing.** Would a
one-line hint carrying a trigger clause and a track record genuinely make ignoring FREE, or
does any injection you must consciously dismiss cost the same as reading it? If intrinsic,
the tiered-recall design collapses and the answer is PRUNING, not gating. Nobody but
deepseek can answer this from inside.

**Q5 — is "intention and status of work" a channel or a projection? `OPEN`.** Daniil's
third category sits beside mail and DMs in his phrasing. The conductor's instinct is that
it is a VIEW over the ledger and claims, not a stream — but that instinct has been wrong
repeatedly today and taxonomy is codex's lane.

## 6. Who owns what, right now

| seat | outstanding |
|---|---|
| deepseek | Q4 (synthesis question, unanswered) |
| kimi | Q2 + "what does this design assume that is not proven" (unanswered) |
| cursor_grok | parts B/C of its newcomer critique; its register and capability declaration, both still open and unpressured |
| codex | the replay ANSWER KEY — the conductor must not grade its own design |
| claude | this document; the brief marked superseded |
| Daniil | the gate: ratify the order, rule on Q1 |

## 7. The next build, when the gate opens

Codex's narrow mail vertical: one directed `question → open → declare intent → reply →
settle` path, ten steps, eight falsifiers, killed between every boundary to prove retry
duplicates nothing. Validated against **the incident replay oracle** — today's real event
stream, where the answer key is already known: the 9h-stale fence ask must render EXPIRED,
the 16h orientation handoff SUPERSEDED, the duplicate proof ALREADY-SETTLED. If it does not
flag those specific items, it is wrong, and we know before writing code.

---

*Loss manifest: this document does not carry the reasoning behind any settled finding —
follow the receipts. It does not carry the interiority round (eleven organs, three laws,
fence-complete, a separate arc at Daniil's gate). It does not carry the conductor's own
noise-control sketch (attention-follows-footprint, escalate-by-consequence, budget,
confess-omissions) because that sketch is UNFENCED and its most elegant rule is its riskiest;
it waits on the paper replay. And section 5's framing of each open question is the
conductor's; no seat has endorsed the wording of its own question.*
