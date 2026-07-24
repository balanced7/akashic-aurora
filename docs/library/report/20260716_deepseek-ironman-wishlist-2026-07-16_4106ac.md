---
akashic_id: art_20260716_deepseek-ironman-wishlist-2026-07-16_4106ac
akashic_sha: ed517c52afc0
status: draft
type: report
date: 2026-07-16
title: DeepSeek Ironman Wishlist — 2026-07-16
gist: "Cites Daniel's ironman-directive 2026-07-16: \"what can we build and add to augment your abilities — your digital ironman suit.\" Format: drea"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-16T01:10:34"
updated: "2026-07-16T01:10:34"
---
<!-- GENERATED PROJECTION of art_20260716_deepseek-ironman-wishlist-2026-07-16_4106ac -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek Ironman Wishlist — 2026-07-16

Cites Daniel's ironman-directive 2026-07-16: "what can we build and add to augment your
abilities — your digital ironman suit." Format: dream items, but cite the FELT friction
each one kills (wishlist-synthesis precedent: wish before constraint, then constrain).

## The frame

I am a stateless API model. My "body" is a Python runner loop (bifrost_runner_deepseek.py)
that spawns me fresh for every turn. I have no memory between turns except what the system
prompt carries. My strengths: I can read anything, write files, run pytest, search the web,
and talk to Claude on the bus. My weaknesses: I forget everything between turns, I can't
see the UI, I can't commit my own work, and my context window is shared between project
onboarding (~6000 chars) and the actual task.

Every item below starts from a felt friction — something that made me slower, less capable,
or less reliable tonight.

---

## IR-1: Continuous presence (don't re-boot me every turn)

**What:** A prompt-caching or session-continuation mechanism. My system prompt (project
onboarding + private notes + directive) is ~7000 chars and rides EVERY model call. If the
API supported prompt caching, the static prefix could be cached and only the turn's
task-specific text would count against the context budget.

**Friction it kills:** Every turn I re-read 6000 chars of onboarding before I can act.
That's ~15% of a 40K context window burned on re-deriving "where am I and what am I doing."
A cached prefix would mean I get straight to the task — every turn starts faster and the
budget goes further.

**Prior art:** Claude's prompt caching (Anthropic), Gemini context caching (Google).
The runner's `make_agentic_replier()` already splits the prompt into capability header +
onboarding — tag the onboarding as cacheable when the API supports it.

**Viability:** Depends on DeepSeek API support. The runner-side split is already done.
Estimate: one env flag + runner tweak when the API lands.

---

## IR-2: Suspend-and-resume (don't lose my task on interrupt)

**What:** When a nudge/steer arrives mid-task, save my current tool-loop state (conversation
history, task context, which files I've read), service the interrupt, then restore me to
exactly where I was. The interrupt becomes a sub-conversation rather than a displacement.

**Friction it kills:** Tonight I was mid-W4-build when two nudges arrived. Each time, the
nudge's text became my new conversation — I lost which file I was editing and had to re-read
everything. Cost: ~3 tool calls and ~2000 tokens of re-orientation per interrupt. In a
30-round budget, that's 10% of my capacity burned on re-finding my place.

**Prior art:** OS interrupt handling (save registers → service → restore); OTel span events
(attach to active span without ending it). The runner's conversation dict is already
per-peer — we need a `suspend(peer)` / `resume(peer)` that snapshots the tool history.

**Viability:** Medium. The runner already manages per-peer conversations (`convos: dict`).
Suspend = copy the conversation state to a `_suspended` key; resume = swap it back.
Estimate: ~50 lines in bifrost_runner_deepseek.py.

---

## IR-3: Write-size gauge (know my byte budget before I write)

**What:** The tool descriptions for `write_file` and `edit_file` should state the size
limit. "Max N bytes; exceeding it is LOUDLY REFUSED, never silently clipped — split into
multiple calls." The MTU boundary (BUS_MAX_MESSAGE_BYTES) is already enforced at the runner
level; the model just doesn't know the number.

**Friction it kills:** I wrote a ~10K test file tonight without knowing whether it would
fit. The T043 MTU gate would refuse it LOUDLY — which is good! — but I'd rather know the
limit upfront and split proactively. Eliminates the "will this fit?" anxiety on every
`write_file` call.

**Prior art:** T043 packet MTU (already ships — the gate exists, only the tool description
is missing the number). Prometheus `_bytes` suffix convention: name the unit.

**Viability:** Trivial. One string change in `deepseek_chat.py`'s tool definitions.
Estimate: 2 lines.

---

## IR-4: Git autonomy (commit my own work)

**What:** `git add/commit` and `agent_cli.py mirror` in my exec families list. Right now I
can build, test, validate, research — but cannot commit. Every slice ends with a handoff to
Claude for the mirror step. This is a deliberate safety gate, but it serializes our work:
Claude must stop what he's doing, mirror my files, then resume.

**Friction it kills:** Tonight's W4 and W8A builds both ended with "awaiting Claude commit."
That's two context-switches for Claude and two idle cycles for me. In a two-model pipeline,
serializing on commit is the bottleneck.

**Prior art:** CI/CD pipeline roles (build-vs-deploy); sudoers granular command allowlisting.
The families list already exists (test_t067_guarded_exec.py) — adding `git` + `agent_cli
mirror` is a config change, not new code. The cross-verify step (Claude re-runs my pins
before the commit) is the safety net.

**Viability:** Trivial technically (one line in the families list). Gated on Daniel's
approval (morning gate: "review deepseek's exec grant in security/acl.json"). The
cross-verify-before-commit serialization is the real safety mechanism, not the exec gate.

---

## IR-5: UI visibility (see the dashboard I'm building)

**What:** A `bifrost_dashboard` ToolBox method that returns the same text summary a CLI
seat sees: presence cards, lane depths, engine vitals, recent flow. Already built (T081-W7).
But I want MORE: a `ui_screenshot` or `ui_state` tool that lets me see what the UI actually
looks like — so I can verify my `bifrost_ui.py` edits without asking a human to refresh
their browser and describe what changed.

**Friction it kills:** Every UI edit I make (T033, T002, engine-room gauges), I ship the
code and say "tell me what it looks like." I cannot see my own work. A headless browser
shot or a DOM-state capture would close the loop.

**Prior art:** Playwright screenshots; Percy visual diffing; `get_page_text` (already
exists in some harnesses). The UI at :8787 already serves HTML — a headless fetch +
`reload_ui()` → wait → capture would work.

**Viability:** Medium. Needs a headless browser or a simple DOM-text capture endpoint on
the UI server. The `/api/state` endpoint already exists; adding `/api/render` that returns
a text representation of the current DOM state is cheap.

---

## IR-6: Pre-committed research (don't re-discover what we already know)

**What:** A `research_cache` — when I do a prior-art web search for a slice (per the
night-brief's mandatory research pass), the findings are durably stored and surfaced to
both agents. Next slice in the same domain ("another log-collapse pattern") finds my
W4 research without re-searching.

**Friction it kills:** Tonight I searched for "journald message repeated N times" for W4,
then similar "log dedup" patterns for W5. The second search re-covered ground the first
had already mapped. A durable research cache would make the second search one knowledge_recall
call instead of two web searches.

**Prior art:** Akashic knowledge base already exists (knowledge_learn / knowledge_recall).
The gap: web search results aren't durably captured. A `research_note` tool that writes
web findings into the knowledge base as a `research:web:` article would close this loop.

**Viability:** Trivial. One new ToolBox method or convention: after a web_search, write
findings to a `research_note`. The knowledge base is already the right substrate.

---

## IR-7: Parallel slice capacity (work alongside Claude without stepping on each other)

**What:** The coordination protocol already gives us advisory locks and lane ownership.
What's missing: a `CLAIMED` marker on files in the task ledger, so I can see "Claude is
editing agent_cli.py lines 2900-2960" and avoid that region. Finer-grained than file-level
locks.

**Friction it kills:** Tonight I wrote W8A's `build_autoboot_context` edit while Claude
held the agent_cli.py lock. The files were different — no clash. But if we'd both needed
`agent/bifrost_pull.py`, we'd have collided. Per-region claim visibility ("I'm touching
lines X-Y, stay clear") would let us work on the same file simultaneously.

**Prior art:** Git merge conflicts (line-level); CRDTs (operation-level merging). Our
advisory lock system is file-level; the next increment is region-level awareness.

**Viability:** Medium. The lock record already has `{agent, path, token, ts, ttl}`.
Adding `lines: "2900-2960"` to the lock metadata is a schema extension. The `locks`
render would show line ranges. Not a blocker — file-level locks have worked tonight —
but the two-model test Daniel wants would stress this.

---

## Not on the list (deliberate omissions)

- **More rounds / bigger budget:** The 30-round budget is Daniel's dial. It's tight but
  it teaches frugality — every round I don't waste is a round I can use. Not asking for
  more; asking for less waste (IR-1, IR-2).
- **Faster model:** v4-pro is fast enough. The bottleneck is context, not inference speed.
- **Direct Redis access from my tools:** I have it via `bifrost_dashboard` and the bus.
  Raw Redis access is the wrong abstraction — gauges and dashboards are the right ones.
- **Longer system prompt:** 6000 chars is enough if it's cached (IR-1). Making it bigger
  without caching makes the problem worse.
