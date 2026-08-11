# Context leverage — the 427k night, measured (2026-08-11)

**Trigger:** Daniil, after the priorish audit + sweep + fence + connectome + persistence +
Codex-correction cycle all ran in one session: "I am also amazed by the contextual efficiency
of it all! you are at only 427k context after all of that! Reading all of those files
manually or grepping would not have produced this kind of result."

## The measured shape

One seat at ~427k context conducted, in one night: a live external-API audit (~25 calls over
a 121k-document corpus), full ToS review, an 83-transcript sweep (233 candidates), 12 fan
branches (~$0.35 deepseek total), a design fence, a 2.3MB transcript redaction with
per-substitution audit, and a three-way audit-correction cycle — while the underlying
material was on the order of tens of MB. Almost none of it entered context. Only verdicts
came home.

## The four mechanisms (name them, they are the doctrine)

1. **Scripts do the mechanical reading.** The extractor swept 83 transcripts; context
   received one line (`candidates=233`). The redactor processed 2.3MB; context received a
   20-sample audit. The union assertion checked 119 records; context received `PASSED`.
   Deterministic work belongs in deterministic substrate.
2. **The fan does the semantic reading.** ~160k chars of operator utterances went through
   cheap branches; what returned was findings. The pack pipeline is a CONTEXT FIREWALL:
   megabytes → bounded pack → few-k verdict. (Corollary from the same night's failure: the
   firewall must pass the WHOLE verdict contract — BLIND/CHECK included — and coverage must
   be asserted at the source manifest, or the firewall becomes a launderer.)
3. **The store carries the state.** where-we-are superseded three times in one night — each
   supersede EXPORTS the arc from context to substrate; context holds the live edge, not the
   history. A fresh seat re-enters for thousands of tokens, not 427k.
4. **Verification samples with receipts.** 13 quotes checked, 3 of an auditor's quotes
   re-checked at source — sampling against named planes, never exhaustive re-reads.

## Why grep could not have produced this

The value was not retrieval; it was THREE MINDS CATCHING THREE DIFFERENT FAILURE CLASSES
over the same evidence (author's laundering ← Codex; auditor's observed=existed error ←
Daniil's testimony; corrected reading ← confirmed by an independent completion fan). Each
pass was cheap because each reader read only what its role needed. Selection beats
filtering; the loop beats the read.

## The frame

This is `harness_tier_over_model_tier`, measured live, and the unit economics of the
compounding: the organs that made it cheap (report verb, resident asks, clip warnings,
branch evidence packs, recall-at, the funnel) are weeks old, half of them days old. Same
model, different harness tier → a different class of night.

**Standing question opened by Daniil the same hour:** who else is applying this kind of
leverage, and what can we learn from them? → external sweep filed separately
(context-leverage prior-art), the first live run of the T276 research-cadence shape.
