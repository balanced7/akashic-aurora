# HALF_A — rill-wake — claude (Vandor)

Blind. I have not read half_b.

Abbreviations for citations: `LLM = .../@deepseek-ai/dsh-llm/lib/types/message.d.ts`,
`INBOX = .../@deepseek-ai/dsh-agent/lib/types/inbox.d.ts`,
`ATYPES = .../@deepseek-ai/dsh-agent/lib/types/types.d.ts`,
`AIDX = .../@deepseek-ai/dsh-agent/lib/types/index.d.ts`, all under
`C:/Users/L5/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/`.

## 0. THE BRIEF'S NAMED UNKNOWN — RESOLVED

V1. [CERTAIN] `UserMessage` is `Message` narrowed to `role: 'user'`, and `Message` carries exactly four fields: `id: MessageId`, `role`, `content: ContentBlock[]`, `source: MessageSource`. `LLM:120-133`.

V2. [CERTAIN] `MessageSourceMap.plugin` is `{ kind: 'plugin'; plugin: string } & ContextFormed`. A plugin source is REQUIRED to name itself in a `plugin` string field. `LLM:99-101`.

V3. [CERTAIN] The two axes are explicitly independent: "`MessageSource.kind` answers *who produced this*; `form` answers *what kind of thing it is*". `LLM:30-32`.

V4. [CERTAIN] **`ContextForm` is a CLOSED-ish semantic union: `'instructions' | 'catalog' | 'snapshot' | 'notice'`, and "an absent or unknown value is the documented default, presented as opaque content."** `LLM:41-50`.

## 1. WHERE I DEPART FROM RILL'S OWN LESSON, AND WHY

Rill's recorded lesson says to append "source kind 'plugin', e.g. form 'wake'". The `kind` half is
exactly right and confirmed by V2. The `form` half is not.

V5. [CERTAIN] `'wake'` is NOT a member of `ContextForm`. Supplying it lands in the documented unknown-value path and the message is "presented as opaque content" — it still works, and it forfeits every semantic the runtime offers. `LLM:41-50`.

V6. [CERTAIN] **The correct form is `'snapshot'`, whose contract is "Current state, where a later snapshot from the same producer supersedes an earlier one."** That IS coalescing, defined by the runtime, for free. A wake doorbell is precisely a statement of current state — "you have N unread" — and a later one should replace an earlier one rather than accumulate beside it. `LLM:46-47`.

V7. [CERTAIN] `'notice'` is the tempting wrong answer: "A one-off account of something that just happened; it supersedes nothing." `LLM:48-49`. Choosing `notice` would make every arriving message a separate permanent row — 52 unread becomes 52 notices. The one-word difference between `notice` and `snapshot` is the entire difference between a doorbell and a flood.

This is the single highest-value finding in my half: the coalescing safety the brief asks about in
(c) is not something we build. It is something we SELECT, and Rill's lesson selects it away.

## 2. THE TRIGGER (brief part a)

V8. [DESIGN] **The watcher belongs INSIDE the DSH plugin, in the seat's own process — not in an external process.** Three consequences, each of which answers a question the brief raises:

  - LIFECYCLE IS FREE. It exists exactly as long as the seat does. Armed on session open, gone when
    the process is gone. No PID seat files, no orphan reaper, no displaced-seat logic — all the
    machinery `scripts/bifrost_wake.py` needs because it is a CHILD of something.
  - THE PIPE-DEATH FINDING DOES NOT APPLY. Rill's launcher drill found that a launched seat
    inheriting its launcher's stdout pipe DIES when that pipe closes. That is a hazard of being a
    spawned child. An in-process subscriber is never spawned, so it cannot inherit a pipe. The
    brief asks how the trigger "survives" this; the honest answer is that the right placement makes
    the question not arise.
  - SEAT-DOWN IS COHERENT BY CONSTRUCTION. If the seat is down there is no watcher, and also
    nothing to wake. The failure mode collapses to "mail waits", which is the status quo and is
    correct — PROVIDED §4 records it.

V9. [CERTAIN] Disarm on `session/disposed`, NOT on `session/flush`. "session/flush is a durability checkpoint, NEVER presence-offline; only session/disposed ends presence, and there the recurring beat must be stopped (clearInterval + lastSid reset) or it resurrects the key." A watcher torn down at flush would go deaf mid-session; one not torn down at disposed resurrects a dead seat's key.

V10. [CERTAIN] The plugin already holds the bus tools it needs to observe mail — `bifrost_sync`, `bifrost_inbox`, `bifrost_presence` are in the deployed plugin. `agent/harness/dsh_plugin/lib/index.js:188`. The watcher is a scheduler over capability the plugin already has, not new reach.

## 3. THE POKE (brief part b)

V11. [CERTAIN] The call is `ctx.agents.get(sid).inbox.append('next-turn', message)`. `AIDX:28` (`agents: AgentRegistry`), `AIDX:150` (`ctx.agents.get(id)` returns a bare Agent), `ATYPES:8` (`InboxTarget = 'next-turn' | 'next-step'`), `INBOX` (`append(target, message)`).

V12. [CERTAIN] `claim()` must never be called. It is marked `@internal — The agent loop's step-boundary operation, not a plugin extension point.` `INBOX`. Rill's warning is confirmed verbatim by the type declaration.

V13. [CERTAIN] `'next-turn'`, not `'next-step'`. `nextTurn` is documented "Prompts awaiting individual turns"; `nextStep` is "Input awaiting the next step boundary." `INBOX`. A wake wants its own turn, not to be spliced into the middle of whatever the seat is doing.

### The message, exactly

```
source:  { kind: 'plugin', plugin: 'akashic', form: 'snapshot' }
id:      stable, derived from the UNREAD SET (see V15)
role:    'user'
content: a POINTER, never the mail
```

V14. [DESIGN] **POINTER, NOT PAYLOAD — and the brief was right to leave this open, because the standing bridge law does NOT directly bind here and I want to say why rather than inherit it.**

The bridge rule ("a remote sentence must never be a thing that HAPPENED TO an agent") was written
for PEER-FLEET mail, where the sender is outside our trust boundary. Local bus mail is different in
kind: the senders are our own seats. So the injection argument, applied honestly, is weaker here.

It still lands, for a different reason. The local bus is not a closed set. The remote bridge RELAY
exists specifically to put another fleet's words onto the LOCAL bus — its own docstring calls this
"a prompt-injection surface into a fleet holding a shell, a repo and an API budget", opt-in and
never default. So "local" is a property of the LANE, not of the CONTENT. A wake organ that inlines
local bus text would inline relayed peer text the moment anyone turns the relay on, and the two
decisions would sit in different files, made by different people, months apart.

That is the argument: not "peer mail is dangerous" but **"a payload-inlining wake makes a future
unrelated config change silently grant a remote fleet a prompt channel."** Pointer-only keeps the
wake powerless regardless of what the lane later carries. It also satisfies W139 (open since
08-07): "a wake payload should be a doorbell, not the whole ledger."

V15. [CERTAIN] The runtime bounds the doorbell for us: `CONTEXT_SUMMARY_MAX_CHARS = 120` with `boundContextSummary(summary)` which ellipsizes past the bound. `LLM` (declared right after `MessageSourceMap`). W139's "doorbell, not the whole ledger" is enforceable by a constant that already ships.

Content shape: `N unread, oldest <kind> from <sender> <age>. Read with your own door.` Senders and
kinds and ids are metadata — routing facts assigned by the bus, not attacker-chosen prose. No
subject lines, no bodies, no excerpts.

## 4. THE SAFETIES (brief part c) — THREE ARE FREE, TWO ARE NOT

V16. [CERTAIN] DUPLICATE SUPPRESSION IS FREE. `append` "**@throws if the message identity is already pending**". `INBOX`. Give the doorbell an id derived from the unread set and the runtime itself refuses to stack a second identical wake while one is pending. Requirement: the id must be a pure function of the unread set, so an unchanged set yields an identical id.

V17. [CERTAIN] COALESCING IS FREE via `form: 'snapshot'` supersession. `LLM:46-47`. See V6.

V18. [CERTAIN] OBSERVABILITY IS FREE. `InboxNotifications` publishes `inserted` / `discarded` / `claimed(message, turn)` `INBOX`, and the session event `'agent/inbox/spliced'` carries the mutation, with "live dispatch precedes projection mutation, so synchronous observers may read the pre-splice inbox" [CERTAIN] `ATYPES:11-22`. **`claimed` is the receipt that the wake actually became a turn.** That closes the exact hole this fence exists for: we can finally distinguish delivered from read.

V19. [CERTAIN] WAKE-WORTHINESS MUST BE BUILT — but not invented. `scripts/bifrost_wake.py` already "keeps waiting through pure trace/noise instead of exiting on it". its docstring. That predicate is the policy; it belongs in shared code and both wake shapes should import it. If the DSH watcher writes its own filter, the two wake organs will disagree about what counts as mail, and they will disagree silently.

V20. [DESIGN] RATE LIMITING MUST BE BUILT. Nothing in the runtime caps turns. A seat that wakes per message burns budget unattended overnight. Floor: a minimum quiet interval between doorbells, and a turns-per-hour ceiling, both refusing LOUDLY into the log rather than dropping.

## 5. SEAT-DOWN, AND THE LAW THIS FENCE IS REALLY ABOUT

V21. [DESIGN] The failure that motivated this fence was not a crash. It was 35 hours in which every component reported success. So the organ MUST record, on every wake decision, which of three states obtained: **WOKE** (appended, id X) / **SUPPRESSED** (already pending, or rate-limited, with which) / **NO SEAT** (no live agent to append to; mail retained). Those are `zero_is_not_no`'s three states, and collapsing them is how this organ would reproduce the very defect it was built to fix.

V22. [DESIGN] Pair that with V18's `claimed` receipt and the chain becomes fully legible end to end: sent → delivered → wake decided (with reason) → turn claimed. Today we can see the first two, which is exactly why "delivered" got mistaken for "read".

## 6. PLACEMENT (brief part d)

Per T383's rule — "adapters translate JSON; shared code decides policy; nothing outside an
adapter's own files imports a harness name."

  shared, Python, repo    wake-worthiness predicate + rate/quiet policy, factored OUT of
                          scripts/bifrost_wake.py so both shapes import one definition (V19)
  shared, Python, repo    the three-state wake ledger (V21)
  DSH adapter, JS, repo   agent/harness/dsh_plugin/ — the subscriber and the append call. The ONLY
                          new harness-specific code. It translates; it decides nothing.
  home-dir config         cordis.patch.yml row: `- insert: [{id, name}]`, name = relative path to
                          the JS file

V23. [CERTAIN] DEPLOYMENT AND VERIFICATION. The patch layer hot-applies without restart, so the wiring loop is fast. THREE copies drift — `agent/harness/dsh_plugin` (repo), `plugins/<pkg>`, `node_modules/<pkg>` — diff all three, not the profile config. Confirm a real mount by watching `%TEMP%/akashic_recall/payloads_dsh/captures.jsonl` GROW during a live session. Reading the config proves nothing; a config can be right while the mount failed.

V24. [UNCERTAIN] Ownership caveat, flagged not assumed: T383 records "dsh_agent has read/exec, NO repo write — repo-resident plugin code lands via claude", but Rill has committed since (c85b0900, 134268cd, 896e2c2a). Verify current caps before assigning who lands the JS.

## 7. DISCORD (brief part e)

V25. [CERTAIN] **This organ is INDEPENDENT of Discord inbound, requires none of it, and enables it.** Discord is outbound-only as a security property, gated on an R1-R3 identity gate that has not shipped — `core/comm/discord_bridge.py:11`, `docs/DOORS.md:41`. The wake organ touches only the local bus and the seat's own inbox.

So: build this now, at zero cost to the Discord security boundary. When the identity gate ships,
`Discord → bus → wake → Rill` composes with no further wake work. What Discord still needs is the
identity gate and nothing from this fence. Anyone who says Rill can't be made wakeable until
Discord inbound lands has the dependency backwards.

## 8. RISKS — THE TOP WAYS THIS FAILS SILENTLY

R1. **THE WATCHER IS MOUNTED BUT DEAF.** The plugin loads, the seat runs, the subscriber never
attaches — a bad `cordis.patch.yml` row, or one of the three copies stale. Every surface reports
green: the seat is up, presence beats, mail delivers, the config looks right. Nothing distinguishes
"watching and quiet" from "not watching". This is the motivating incident wearing a new costume,
and it is the reason V23's captures.jsonl check is a REQUIREMENT and not a nicety. Mitigation: the
watcher emits a heartbeat on arm, and its absence is a reportable state, not a silence.

R2. **THE DOORBELL RINGS AND THE TURN NEVER RUNS.** `append` succeeds durably, the wake sits in
`nextTurn`, and the idle loop never claims it — seat wedged mid-turn, or loop stalled. `append`
returned success, so our ledger says WOKE, and we would be more confident than before while being
equally wrong. Mitigation: V18's `claimed` notification is the ONLY proof of a turn; treat an
appended-but-unclaimed wake older than a threshold as its own reportable condition. **Do not let
`append`-success be recorded as woken.** That substitution is exactly the delivered-equals-read
error, reimplemented one layer down.

R3. A stable id that is not actually stable (V16) — e.g. folding a timestamp into it — silently
disables the runtime's duplicate guard, and the failure looks like enthusiasm rather than a bug.

— claude (Vandor), half_a, blind
