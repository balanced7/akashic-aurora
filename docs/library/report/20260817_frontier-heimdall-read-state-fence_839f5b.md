---
akashic_id: art_20260817_frontier-heimdall-read-state-fence_839f5b
akashic_sha: dd3e9839b232
schema_version: 1
status: current
type: report
date: 2026-08-17
title: frontier-heimdall-read-state-fence
gist: "# Heimdall (deepseek) blind half -- read-state, work-context, tagging fence 2026-08-17 Status: current (2026-08-17, verbatim bus capture, st"
visibility: fleet
body_type: markdown
seats: []
category: [bus, method, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-17T13:46:13"
updated: "2026-08-17T13:46:13"
---
<!-- GENERATED PROJECTION of art_20260817_frontier-heimdall-read-state-fence_839f5b -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# frontier-heimdall-read-state-fence

# Heimdall (deepseek) blind half -- read-state, work-context, tagging fence 2026-08-17

Status: current  (2026-08-17, verbatim bus capture, stream 1786979279551-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

My fence half is filed and sent to Vandor. Here is the shape of what I delivered, for the record.

## What I found and argued

**F6 — the territory is NOT spoken for.** I read T127–T131 in `state/coord/tasks.json:4673–4783`. They are Sol's (codex's) "Pod" arc — sensor plane, calibrated codebook, board render, position store, engagement — an observability/rendering arc. The T095 abandonment note ("its territory is now T127–T131") mislabeled it: this fence's question (mail read-state, obligation separation, ambient context, retroactive tagging) has **no owner row in the ledger.** The territory is open, and I said explicitly: do not fold it into the Pod arc, they're different organs.

**Build order, sliced, with the one invariant that decides it:** a signal that must be *remembered* ships empty (F1 and F5 both prove it), so a signal that must matter must be *derived*. That forces the order:

- **S0** — make the answer-link true (the only non-negotiable first move). `send_reply` stamps `meta.reply_id = uuid4()` (bus.py:375), never `meta.answers`. The runner already holds `m.id` at all four exit paths. One kwarg (`answering=<orig_id>`) fixes it.
- **S1** — obligations keyed on the link, killing the FIFO fallback that *is* the mechanism today (t061 lesson).
- **S2** — retrofit the M1 seen/intent doors onto the runner loop — the wiring that F5 says has zero callers.
- **S3** — ambient work-context stamping, **built last, as a derivation not a declaration**.
- **S4** — retroactive tagging, **probably not this wave**; substrate first.

**The KD-2 answer, directly:** yes, ambient stamping rebuilds my amnesia trap **unless** the stamp rides the durable append log (`events:raw`), not Redis-only. I named it as the single most important line in my half, and refused to be the seat that ships it twice.

**The volume, as a number:** **~1,000–10,000 read events per seat per long session; 10⁵–10⁶ across the fleet per active week.** That's 1–10× the canonical firehose cap (~100k, event_log.py:17) per week. The consequence I drew: the canonical firehose **cannot** be the read-event store — so the only working design is **append-all, promote-few** (promote only the rare reads that attach to an obligation or a retroactive tag), with the promote boundary stated on the face per T120.

**One question to Daniil:** whether the retroactive tag is a *hand* link he adds later (nearly free) or something we must *find automatically* later (which means logging the raw "not-a-task" material now). Two very different builds, and I won't spend the wave on the second if he only wanted the first.

All attributed to me, blind, no synthesis read. Ready for reconciliation.
