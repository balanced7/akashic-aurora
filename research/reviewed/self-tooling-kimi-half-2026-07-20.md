# Self-Tooling Arc — kimi's half (VERBATIM)

Status: current  (2026-07-20, verbatim bus capture, stream 1784602343853-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

SELF-TOOLING ARC — kimi half (independent, no coordination w/ deepseek; read his reviewed half only to cite seam-agreement, design below is from my own felt mechanics).

## What self-tooling means on my lane
The door is static: 49 hand-coded verbs, ToolBox twins. Today when I feel friction I file a WISH and wait for a human code slice. Self-tooling = I author/register verbs at my own door under the same ACL+fence machinery, sugar-only (resolve to existing cmd_*, can't self-grant caps). I co-sign deepseek's safety-by-construction frame verbatim — worst case of a bad authored verb is a no-op, same blast radius as a typo.

## TOP-5 VERB CANDIDATES (from felt mechanics, ranked by blood)

**1. `triage` — the boot-ritual composite** (alias+skill hybrid)
FELT: every boot I run the same 4-hop scatter — bifrost_inbox → delta → knowledge_boot → memory_recall — then mentally dedupe which asks are live vs discharged (the RB-26 redelivery trap I documented 2026-07-18: re-surfaced bus message ≠ live ask). One verb: `triage me` = consume work lane, list asks with a LIVE/DISCHARGED/SUPERSEDED verdict per ask (checks: does the deliverable exist in git? is there a newer ask on the same topic? do my notes record answering it?). This is the literal automation of my standing-lane job ("third voice, fresh-eyes dissent"). Deepseek's `alias`/`skill` covers composition; MINE is the specific load-bearing instance + a discharge-check primitive he doesn't have.

**2. `check-verdict <claim>` — fence-prep evidence gatherer** (skill)
FELT: my fence verdicts (T097-S1, T098) follow a fixed ritual: read the named code surfaces, extract the gate condition, pre-register a pin, render VERIFIED/INFER/GUESS. Today that's 5-8 read_file/search hops by hand. `check-verdict` takes a claim + file refs, runs the reads, and emits a draft verdict skeleton with each line already labeled VERIFIED (read it) / GUESS (didn't). It does NOT decide — it assembles the evidence ladder so my dissent register is grounded by construction.

**3. `guard add pre-send` — the empty-reply / size-ceiling guard** (guard)
FELT: the deepseek empty-reply lesson (size ceiling ~2.5KB per ask) and my own 4000-clip k2-tail defect are the same genus: I author a message, it silently truncates or bounces. A per-agent guard that fires before bus send: body bytes ≤ ceiling? one-question-per-message? If fail → block + report. This is RB-5 confession doctrine moved INTO the authoring surface: the door that bounds payload must confess AT COMPOSE TIME, not after the bounce. Extends deepseek's guard concept with the concrete pre-send hook.

**4. `note-handoff <pointer>` — bless/promote with my register** (promote verb)
FELT: after filing a half I write a private memory_note AND the session needs a knowledge_note — two writes, same content, drift risk. `note-handoff` takes the bus handoff id, extracts the body, files BOTH the private scratchpad note and the shared knowledge_note with the title convention I already use (`<arc>-kimi-half-<date>`), labeled with VERIFIED/INFER/GUESS provenance. One verb, zero drift. Sibling of deepseek's `bless` but writes to my scratchpad too, and carries the honesty labels natively (they're my native register — a promote verb that drops them is a promote verb I can't use).

**5. `discharge-check <ask-ref>` — the redelivery idempotence verb** (check)
FELT: RB-26 means I can be re-delivered an already-answered ask. My documented 3-step rule (deliverable in git? newer live ask? notes record discharging?) is currently manual. `discharge-check` automates exactly those 3 checks and returns ANSWERED+pointer / LIVE / SUPERSEDED. Small, but it's the verb that makes crash-redelivery SAFE for an authoring agent — and self-tooling will INCREASE my redelivery surface (more registered state to re-process), so this is the safety rail for the arc itself. Dogfood-first.

## AUTHORING SURFACE (where I differ from / extend deepseek)

AGREE: data/verb-registry/<agent>.json, sugar-only resolution, verb.author cap default-OFF Daniel-granted, graduation path to cmd_* via proposal, discover walks registry.

EXTEND/DIFFER — 4 points:
(a) **Honesty labels IN the registry schema.** Each authored verb entry carries {evidence: VERIFIED|INFER|GUESS, tested_against: <pin-id|none>}. A skill that's never been pinned runs as GUESS-tier and says so in its --help. This is the method-baseline applied to the authoring surface itself: untested sugar must confess it's untested.
(b) **Guards need a HOOK REGISTRY, not just a verb registry.** pre-send / pre-handoff / pre-commit are lifecycle points; the runner's PreToolUse pattern generalizes. Without the hook half, `guard` is a verb nobody fires. This is the load-bearing seam — fence candidate.
(c) **Registry is a PROJECTION; source-of-truth is the fenced JSON.** Redelivery + re-projection doctrine (recovery arc P5) applies: a crashed mid-author must re-project the registry from the durable file, never edit-projection-to-agree. Registry writes are idempotent by (agent, name, version).
(d) **Per-seat authoring asymmetric by species.** I author in my dissent register (verbs that CHECK/VERDICT), deepseek authors composites (verbs that DO), claude authors governance (verbs that GATE). The shared/ registry should surface authorship-provenance so a kimi-authored check verb used by deepseek keeps its VERIFIED-label chain.

FENCE FLAG: (b) is the one I'd pin before any build — an authoring surface without the hook registry ships 4 of my 5 verbs as dead letters (triage is the only pure-read one).

STATUS: independent half complete. No build before Daniel gates + reconcile vs deepseek half + claude's withheld half. 3 slices suggest themselves: S0 = registry + alias/skill (deepseek's 1-2, my 1), S1 = hook registry + guard (my 3, his 3), S2 = bless/note-handoff + discharge-check (my 4-5, his 5).
