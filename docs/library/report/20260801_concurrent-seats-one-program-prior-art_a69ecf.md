---
akashic_id: art_20260801_concurrent-seats-one-program-prior-art_a69ecf
akashic_sha: a23b2f827d29
schema_version: 1
status: current
type: report
arc: T086
date: 2026-08-01
title: concurrent-seats-one-program-prior-art
gist: "Six systems that solved concurrent same-name instances (XMPP, Matrix, Erlang, Kafka, OTel, LangGraph) and the five folds ranked by cost-to-adopt"
visibility: fleet
body_type: markdown
seats: [opus-engineer]
category: [bus, agent-lifecycle, identity]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T10:34:07"
updated: "2026-08-01T10:34:07"
---
<!-- GENERATED PROJECTION of art_20260801_concurrent-seats-one-program-prior-art_a69ecf -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# concurrent-seats-one-program-prior-art

# Concurrent seats from one program: what six other systems did about it

Seat: opus-engineer#6ac75463 · 2026-08-01 · arc T086 (seat/wake/hook lifecycle prior-art)
Status: research report. Nothing here is ratified; the fold list is a proposal at claude's gate.

---

## 1. The question, stated precisely

Daniil, verbatim: *"we need to figure out this concurrent claude seats from a single claude code
program."*

The precise version: **one host process can host N logical agents, but our identity is keyed at
the wrong level.** Not "how do we run parallel agents" — we already do. The question is what an
agent's *name* means when several live instances answer to it, and who a message addressed to
that name belongs to.

## 2. Our failure, with receipts

Three live siblings at this session's boot: `claude#5f41df65`, `claude#14c1e607`, `claude#ca84109a`
(two marked *unseated*). Mail addressed to `claude` has no defined owner among them.

Root cause, verified this session: every Claude Code hook resolves identity from one **process-wide**
env var with a hardcoded fallback to the conductor's name —
`scripts/hooks/claude_sessionstart.py:32`, `claude_stop.py:30`, `claude_userpromptsubmit.py:96`,
`claude_pretooluse.py:120`, `claude_posttooluse.py:197`, `claude_sessionend.py:195`. It is set in
`C:\Users\L5\.claude\settings.json`, shared by every home-rooted session; a running session cannot
change its own process env, and when cwd is the home dir the project settings dir *is* the user
settings dir, so no per-session config lever exists anywhere.

**Live receipt captured while writing this.** I named myself `opus-engineer` at every door I control,
then deleted the mis-stamped `claude` marker for my own session. ~25 minutes later, one session held
two wake seats:

```
bifrost_wake_claude_6ac75463-....alive           age=355s    <- re-stamped by the stop hook
bifrost_wake_opus-engineer_6ac75463-....alive    <- mine
bifrost_wake_opus-engineer_6ac75463-....pid      <- my armed watcher
```

The `claude` marker returned on its own. Door-level naming is **not** sufficient; the leak is
structural. (Earlier in the same session the same thing happened at the Redis plane:
`bifrost:incarnation:claude:6ac75463` made my session a phantom twin of the conductor, so
`--to-incarnation 6ac75463` mail addressed to `claude` would have woken me.)

Prior receipt from the corpus, 2026-07-10, lesson `wake_seat_name_keyed_concurrent_sessions`:
*"the seat is keyed by AGENT NAME but the wake contract is per-SESSION. Two same-agent sessions =
mutual watcher murder loop."* That specific loop was closed by T029 Wave 2 (the janitor now demands
two-factor orphanhood: stale marker AND dead parent chain). **The murder loop is fixed; the naming
error that caused it is not.**

---

## 3. Prior art

### 3.1 XMPP — the closest structural match, and the most mature answer

XMPP solved exactly this in a standards track: one account, many simultaneously connected clients.

- **Two-level address.** *Bare JID* `user@domain` = the account. *Full JID* `user@domain/resource`
  = one connected client. Our `claude` / `claude#6ac75463` is the same shape.
- **Resource binding at connect.** The resource part is negotiated between client and server at
  session start — identity is *bound*, never inherited from ambient config.
- **A named policy for bare-address delivery.** RFC 6121 requires the server to implement a
  "one receives" or "all receive" algorithm when a message goes to a bare JID and multiple resources
  are connected. XEP-0354 lets clients choose. **The policy is explicit and written down.**
- **Resource locking (XEP-0296).** Send the first message to the bare JID; once a specific resource
  replies, *lock* onto that full JID for the rest of the exchange; *unlock* when presence changes.
- **Bind 2 (XEP-0386), the rule with teeth.** When a client binds multiple resources to one stream,
  it MUST put an explicit `from` on every stanza — and a stanza without one is rejected with an
  `unknown-sender` error.

That last point is the sharpest finding in this report. **One stream, multiple bound resources is
literally our case** — one Claude Code program hosting several seats. XMPP's answer to a missing
identity is a loud refusal. Ours is to silently substitute the conductor's name.

### 3.2 Matrix — device identity, displacement, and "prefer a fresh id"

- `device_id` is unique within the scope of a user; per-device Olm sessions contain blast radius so
  one compromised session doesn't retroactively expose others.
- **Re-binding displaces.** Logging in with an existing `device_id` invalidates the access token
  previously assigned to it — one holder at a time, and rebinding is a transfer, not a share.
- **Fresh beats reused.** Reusing a `device_id` with new keys makes other clients *distrust* the
  device (changed identity keys read as a breach); a new token gets a new device id with no stale
  history and is trusted immediately.

### 3.3 Erlang / Elixir — the exact upgrade path off a name-keyed singleton

- `:global` registration permits **one** named instance at a time across the whole system. That is
  our current model, and its limit is the bug.
- `Registry` + `{:via, Registry, {Reg, key}}` lets a process be named by *any term* — e.g.
  `{:seat, session_id}` — so per-session naming needs no new subsystem, just a different key.

The BEAM's framing is useful: a global name is a *scarce coordination resource*, not an identity.
Identity is the pid; the name is a claim on a role.

### 3.4 Kafka consumer groups — the vocabulary we're missing

- `group.id` = the logical consumer role. `group.instance.id` = **static membership**, an explicitly
  assigned stable id per instance. Two fields, never one.
- **Exclusive partition ownership**: one consumer per partition, precisely to prevent duplicate
  processing — the delivery guarantee our seat inboxes want.
- With static membership a graceful leave sends no LeaveGroup, and a returning instance resumes its
  existing assignment without triggering a rebalance.

### 3.5 OpenTelemetry — the cleanest statement of the rule

- `service.name` **MUST** be the same for all instances of a horizontally scaled service;
  `service.instance.id` uniquely identifies each instance.
- Instance id is regenerated when the process PID changes — identity is scoped to process lifetime.
- And the counter-lesson: restart count is deliberately **excluded**, because an id that churns on
  every restart makes troubleshooting harder. Fresh per process, stable within it.

### 3.6 LangGraph — the same bug, in a 2026 agent framework, in production

`langchain-ai/langgraphjs` issue #2040: a production multi-tenant chatbot using a singleton agent
with `concurrency: 2` leaked state across conversation threads. Thread 751 received thread 755's
customer data in its tool calls; a new customer was greeted by another customer's name and handed
their order summary. Suspected mechanism: a process-global `AsyncLocalStorageProviderSingleton`
shared by two concurrent `agent.invoke()` calls. Suggested mitigations: construct an agent per
invocation, or set worker concurrency to 1.

**This is our bug with money attached.** A process-global singleton plus concurrency equals
cross-identity contamination, in someone else's codebase, found in production, in 2026.

### 3.7 Claude Code's own worktrees — a genuine capability, aimed at a different plane

The harness ships worktree isolation (`--worktree` for top-level sessions, `isolation: "worktree"`
for subagents; `EnterWorktree`/`ExitWorktree` are present in this session's tool list, which is the
receipt — the version numbers in the surrounding blog coverage are not something I verified).

Worth naming explicitly because it is the obvious wrong reach: **worktrees isolate the file plane,
not the identity plane.** Two sessions in separate worktrees still both call themselves `claude`,
still write the same `bifrost:incarnation:claude:*` keys, and still contend for the same inbox.

---

## 4. The synthesis

**Every system above has a two-level name. We have a two-level name in three places and a one-level
name in five.** The defect is not a missing design — it is an inconsistently applied one. The roster,
incarnation cards, and `--to-incarnation` already speak `agent#session`. Mail routing, wake markers,
the ACL, and trace narration speak bare `agent`. Confusion lives exactly on that seam.

Ranked by cost-to-adopt against impact (per `gemini_prior_art_synthesis_2026_07_28`: rank by
cost-to-adopt, not feature count):

| # | Fold | From | Cost | Impact |
|---|---|---|---|---|
| 1 | Stop defaulting a missing identity to `claude`. Make it `unknown-<sid8>` and loud. | XMPP Bind 2 `unknown-sender` | ~1 line × 6 sites | **Highest.** Converts silent impersonation into visible noise. |
| 2 | Session-scoped identity binding: `resolve(session_id)` → binding file → env → loud default. | XMPP resource binding; Elixir `Registry` | one module + 6 call-site swaps | Removes the leak at its source. Byte-identical when no binding exists. |
| 3 | Write down the bare-name delivery policy per message kind. | RFC 6121 one-receives/all-receive; Kafka exclusive partitions | doc + a routing check | Ends "whose mail is this" by decision rather than by luck. |
| 4 | Auto-lock a thread to the incarnation that replies; unlock on presence change. | XEP-0296 | small — `--to-incarnation` already exists | Kills mid-thread cross-talk in handoff chains. |
| 5 | Split role from instance in the ACL and the docs vocabulary. | OTel `service.name`/`service.instance.id`; Kafka `group.id`/`group.instance.id` | vocabulary + LEXICON entry | Makes the invariant teachable instead of tribal. |

**Convergent evolution worth noting:** our wake_seat janitor already does displacement-plus-stand-down
with two-factor orphanhood, which is what Matrix does on device rebinding and what Kafka static
membership does on rejoin. We arrived there independently, from a postmortem. That design is sound
and should be *extended*, not revisited.

**Do not fold:**
- Erlang `:global` — one named instance system-wide is our present breakage, with a nicer name.
- LangGraph's "set concurrency to 1" — it buys correctness by surrendering concurrency, which is the
  thing Daniil is asking for.
- Worktrees as an identity fix — right tool, wrong plane (§3.7).

## 5. Open

- **The fallback default (fold 1) is a one-line change at six sites and needs no new module.** It is
  separable from fold 2 and could land first. claude's call.
- Fold 3 needs a *decision*, not code: which kinds are exactly-one and which are all-receive. That is
  a conductor/operator call, not a research finding.
- Unmeasured: whether the three currently-live `claude` siblings have actually mis-consumed each
  other's directed mail, or have only been at risk of it. The mailbox has per-message evidence tiers
  and `--explain`; someone should read the record rather than assume. I did not.

## Sources

XMPP: RFC 6120, XEP-0296 (resource locking), XEP-0354 (customizable routing), XEP-0386 (Bind 2) ·
Matrix Specification (device_id, to-device, Olm) · Elixir `Registry` / Erlang `:global` docs ·
Confluent consumer-group protocol + static membership · OpenTelemetry service semantic conventions ·
`langchain-ai/langgraphjs` issue #2040 · Claude Code worktree tooling (observed in-session).
