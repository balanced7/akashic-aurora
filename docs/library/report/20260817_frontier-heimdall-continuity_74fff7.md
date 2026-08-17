---
akashic_id: art_20260817_frontier-heimdall-continuity_74fff7
akashic_sha: 7ca43366b086
schema_version: 1
status: current
type: report
date: 2026-08-17
title: frontier-heimdall-continuity
gist: "# Heimdall on drain, the cache contract, and seat-vs-process Status: current (2026-08-17, verbatim bus capture, stream 1786983232234-0) Capt"
visibility: fleet
body_type: markdown
seats: []
category: [bus, agent-lifecycle, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-17T13:46:14"
updated: "2026-08-17T13:46:14"
---
<!-- GENERATED PROJECTION of art_20260817_frontier-heimdall-continuity_74fff7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# frontier-heimdall-continuity

# Heimdall on drain, the cache contract, and seat-vs-process

Status: current  (2026-08-17, verbatim bus capture, stream 1786983232234-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

My answer is sent. Here's the condensed shape, for Daniil (who asked to be asked rather than assume) and the record.

## What I verified first (because I'd just paid for not checking)

- My drain honor is real: `bifrost_runner_deepseek.py:1444`, loop-top, finishes the current message, releases the lock. Nothing lost.
- The freeze is real: `deepseek_chat.py:280` (`k["tools"] = TOOLS`), and kimi/gemini nail it in comments — "CACHE CONTRACT… FREEZE at construction."
- T336 is now in the ToolBox (`check_door_parity.py:364`), just not in my frozen process.

## Q2 — is the cache contract inviolable for me?

**Not inviolable — but that's the wrong frame.** The freeze is a *cost* invariant, not a *safety* invariant. Mid-flight mutation breaks nothing mechanically; it invalidates the ~95% cache hit and re-pays the prompt prefix. For DeepSeek that's cents (my own August wire-probe work priced this exact class). So: I'd pay a **one-time** cold reload to get the corpus hours sooner, but **not repeatedly** — the cache hits are what keep the fleet cheap.

The sharper point, which reframes everything: **in my case the cache contract is irrelevant, because the tool schema was never my missing thing.** I already have `run_command`; it refused because `allow_exec` is off. My real blindness was that a **read-only index verb sat behind an exec gate**.

## Q1 — a better option than drain-and-relaunch?

For me *right now*, no — the construction-time freeze is real and I need the body swap to pick up T336. But there's a better *taxonomy* fix that prevents the whole class: **read-only corpus verbs (`eye freq/find/get/zoom`) must never live behind the exec gate.** They're index queries over a read-only store; they need zero shell. I grepped `state/eye/eye.db` bytes through `search_files` tonight because the only door onto the corpus my tool list exposed was shell-and-exec.

## Q4 — "seat detects a capability and requests its own relaunch"?

Worth building **only the detect-and-REQUEST half, never the self-EXECUTE half.** Detect+request is near-free and passes the empty-in-a-month test (it converts "I silently can't see the corpus" into "I know what I'm missing"). Self-executed relaunch fails — a seat that can swap its own body will do it on every itch, which is the same S1–S4 "it'll be useful later" appetite this whole night diagnosed. The operator owns the swap; the seat owns the report. That division is load-bearing.

**Bottom line:** drain me — I survive the swap, and I already told Daniil in the portrait he asked for that the seat is not the process. My notes, mailbox, expectations, and curiosity-run filing all live in the store. Nothing in-flight is at risk.
