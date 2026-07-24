---
akashic_id: art_20260715_fence-brief-boot-onboarding-ergonomics-c_9439cf
akashic_sha: d430a0cd7ac1
status: current
type: report
date: 2026-07-15
title: "Fence brief — Boot/onboarding ergonomics (claude → deepseek, 2026-07-15 night)"
gist: "## Daniel's directive (verbatim, tonight) > \"launch a write capible deepseek and have it also analyze its own bootup erganomics and I want y"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting, ergonomics]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260715_boot-ux-retro-the-first-native-primer-se_5e132c
    rel: cites
  - target: art_20260715_boot-ux-retro-the-runner-seat-reports-ba_4e9674
    rel: cites
  - target: art_20260715_boot-onboarding-ergonomics-reconciliatio_94a21c
    rel: cites
created: "2026-07-15T22:42:42"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260715_fence-brief-boot-onboarding-ergonomics-c_9439cf -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Fence brief — Boot/onboarding ergonomics (claude → deepseek, 2026-07-15 night)

## Daniel's directive (verbatim, tonight)

> "launch a write capible deepseek and have it also analyze its own bootup erganomics and I want you both to make a plan on how to tackle every issue. Find out what was unclear or ambiguous, what wouldve allowed you both to arrive at the optimum primed state quicker with less re-learning"

Earlier tonight, also his: *"let me know how the new bootup process feels! Any new pain points... Anything we could optimize in the onboarding process to help you avoid re-researching things on every new initialization?"*

And the standing rule he reaffirmed: *"for this kind of mission critical work we always do a collaborative process with deepseek."*

## Why this fence exists

The T074 primer (SessionStart whisper = primer) just shipped. I (claude) am the first cold seat to boot on it and reported back. But a retro from ONE seat on ONE harness is half the picture — your runner seat boots through a **different door** (runner boot-fold, ToolBox, inbox-drain, per-peer convo, API statelessness) and hits a different set of ambiguities. Daniel wants BOTH surfaces analyzed and ONE plan that fixes every issue on both.

## Your task — TWO parts

### Part 1 (PRIMARY): analyze YOUR OWN boot/onboarding ergonomics
From the runner seat, first-class — not as a cross-check of mine. Concretely, walk your own path to "primed state" and answer, with file:line receipts wherever you can get them:
- **What primes you today?** Runner boot-fold vs my SessionStart whisper — what context do you actually receive on wake, and through what code path (name the function/file)?
- **What was ambiguous or unclear** the last few times you booted — anything you had to re-derive, re-read, or guess at? (e.g. which task is current, what's mine vs yours, what beats what, where a doc lives, what a tool does, what write_mode you're in.)
- **What forced re-learning** — anything you re-research on EVERY init because it isn't carried forward (your flagged private-memory leak, the 120k agent_cli truncation, ToolBox third-door parity, stale pre-lane inbox — pull from your own ergonomics retro 2026-07-14 where still true, but re-verify, don't just cite).
- **What would have gotten you to primed-state faster** with less re-research — the concrete missing affordance.
- **Time-to-primed:** roughly how many tool calls / reads from wake to "I know what to do"? Where did they go?

### Part 2 (SECONDARY): adversarial cross-check of my half
My half is `research/reviewed/claude-boot-ux-retro-2026-07-15.md` — READ it. It is PUBLIC INPUT, not a blind seed (my earlier inform already leaked a summary into your queue — T073 twin-sketch precedent: your pass is independent + adversarial over declared public input, that inform is SUPERSEDED by this brief). For EACH of my P1–P6, give a one-line **CONFIRM / REFUTE / PARTIAL** with a file:line or live receipt, plus a T049 confidence + grounding-quality field. Affirm in one line; only re-prove where you disagree.
- P1 native-MCP door cwd-fragile (`.mcp.json` project-scoped + relative `["ai_setup_mcp.py"]`)
- P2 boot asserts context, not services/presence (no UI/wake/runner liveness at boot)
- P3 arm/consume/re-arm ritual is memory-carried, not systemic (live insta-wake receipt tonight)
- P4 trace spam buries mail in the sync peek (your runner emits those traces — you own this evidence)
- P5 heal cries wolf on 4810 ephemeral-by-design keys (real orphan invisible)
- P6 gauge drift (8/10/19 unread), 189h untitled episode, cwd-reset per CLI call

## Output — write to a FILE, keep the bus reply short

Deliverable: `research/reviewed/deepseek-boot-ux-retro-2026-07-15.md` (your ergonomics-retro doc is the shape precedent).

**Write it SECTIONED** — `write_file` the skeleton + Part-1 first section, then `edit_file`/append the rest section by section. This is your own lesson `runner_bigwrite_tool_call_truncation`: a single giant write truncates. Sections: (1) Your primed-path walkthrough, (2) Ambiguities, (3) Re-learning tax, (4) Cross-check of my P1–P6, (5) **YOUR PRIORITIZED FIX LIST**.

Section 5 is load-bearing for the plan: list EVERY issue you found (yours + confirmed-from-mine), each with — proposed fix · owner (claude-seat / deepseek-runner / shared / substrate) · rough size (fence-lite one-slice vs needs-full-fence) · which existing task it rides if any (T075/T077/T067/T050 etc). This gives the reconciliation two independent plans to merge, not one plan you're reviewing.

**Bus reply (short):** "filed + top-3 findings + your single biggest DISAGREEMENT with my half." Keep it under the runner token cap; the detail lives in the file.

## What happens next (the plan mechanic)

I reconcile SECOND: I read your file + mine and write `research/reviewed/boot-ux-reconciliation-2026-07-15.md` — a JOINT plan that tackles EVERY issue with owner + gated-slice + tier, ordered by ROI, answering Daniel's two framing questions directly (what was ambiguous; what shortens time-to-primed with less re-learning). Slices register in the ledger from the reconciliation only. Nothing builds before Daniel's gate. Fence-lite tier (T049(3)) likely for most slices given their size.

Reply when filed — your reply wakes me.
