# rill-wake — half_b (author: deepseek / Heimdall)

The DSH-native wake design. Every load-bearing claim is a numbered `V<n>.` line whose own first
line carries its verdict tag inline. CERTAIN = a file:line citation read from the live checkout.
DESIGN = a decision I am making, not a fact. UNCERTAIN = flagged honestly, never papered over. I
have not read half_a.

The one genuine unknown this brief names — the exact `UserMessage` shape — is resolved below in
§(b) and carries a citation to the contract the in-tree plugin already ships against.

---

## (a) THE TRIGGER

The trigger is NOT a new process: it is a poll loop living inside the plugin that is ALREADY
resident in Rill's host, `agent/harness/dsh_plugin/lib/index.js` — the one place in the DSH tree
with a `ctx.agents`, that runs in-process for the seat's whole life, and that already survives
the launcher's pipe-death finding (it is not a child of the launcher at all).

V1. [CERTAIN] The DSH plugin is loaded in-process by the cordis host and lives for the host's
whole process life; it is not re-spawned per event.
cite: agent/harness/dsh_plugin/lib/index.js:460-467 (`export async function apply(ctx)`) and the
door self-heal block at :293-311 which respawns only its own MCP CHILD, not the plugin.

V2. [CERTAIN] A turn-based DSH seat has NO turns unless a human types at the browser; every seam
T383 designed fires INSIDE a turn; nothing in the existing five listeners can start one.
cite: agent/harness/dsh_plugin/lib/index.js:5-26 (the listener map — session/created,
system-prompt/assemble, session/event, tools/post-execute, session/disposed), and Rill's own
lesson learn:experiment:a_web_seat_has_no_turns_so_arriving_mail_cannot_wake_it ("it thinks when
someone types at 127.0.0.1:3080 and at no other time").

V3. [CERTAIN] The turn-start seam EXISTS and is public: the per-agent `Inbox`, whose `nextTurn`
list is "prompts awaiting individual turns" and whose `append(target, message)` is a public write
(only `claim()` is `@internal`); appending to `next-turn` wakes the idle loop into a normal turn.
cite: learn:experiment:dsh_inbox_next_turn_is_the_plugin_turn_seam, which records the verified
contract ("hold ctx.agents.get(sid).inbox and append ONE harness-generated UserMessage ... to
'next-turn' -- the idle loop wakes and runs it as a normal turn. Don't call the loop's claim()
(internal)").

### Lifecycle (armed by what, disarmed by what)

V4. [DESIGN] ARMED at `session/created` (a `setInterval` started in that listener, scoped to the
session id); DISARMED at `session/disposed` (`clearInterval` + reset of the remembered sid).
cite: the arm/disarm pattern to mirror is the presence beat already in the file —
agent/harness/dsh_plugin/lib/index.js:46-65 (startPresenceBeat/stopPresenceBeat with `if
(beatTimer) return`, unref, `clearInterval + lastSid=''`), wired at session/created (:471-478)
and session/disposed (:588-592). [CERTAIN]

V5. [CERTAIN] ACROSS session/flush the trigger MUST NOT re-arm or re-police — flush is a
durability checkpoint, not a departure; only session/disposed ends presence AND disarms the
trigger.
cite: agent/harness/dsh_plugin/lib/index.js:594-601, the verbatim RULING ("session/flush is the
DURABILITY CHECKPOINT ... It is NOT a departure ... Departure is session/disposed alone; flush
does nothing here").

### The pipe-death finding, and why the trigger survives it

V6. [CERTAIN] The launcher's pipe-death fix was already shipped: Rill is launched with stdout
redirected to a FILE, never inherited down a pipe.
cite: scripts/local/launch_rill.ps1:245-255 ("Output goes to a FILE, never down an inherited pipe.
Learned the hard way ... the seat inherited the launcher's stdout pipe, and when that pipe went
away the seat died with it").

V7. [DESIGN] The trigger survives pipe-death for a different, stronger reason: it is not a child
of the launcher, so it has no launcher pipe to inherit — it is an in-process timer in the cordis
host; if the host dies the trigger dies with it, but that is host death (covered by §c DOWN
handling), not a wake gap.
cite: an in-process `setInterval` holds no reference to the launcher's stdout; the `.unref()` it
must mirror is agent/harness/dsh_plugin/lib/index.js:50. [CERTAIN]

V8. [DESIGN] The trigger's poll loop: every `WAKE_POLL_MS` (design ~15s, the BEAT_MS budget), a
non-consuming detect against the bus inbox (`wake_block`, §c), then the §b poke on a wake-worthy
hit; it never consumes, never advances the shared cursor.

---

## (b) THE POKE

### The exact call

V9. [CERTAIN] The poke is `ctx.agents.get(sid).inbox.append('next-turn', message)`.
cite: learn:experiment:dsh_inbox_next_turn_is_the_plugin_turn_seam ("hold ctx.agents.get(sid)
.inbox and append ... to 'next-turn'"); the `agents` registry name is corroborated by the brief's
own input (@deepseek-ai/dsh-agent index.d.ts:28 `agents: AgentRegistry`).

### The injected UserMessage — this brief's named unknown, resolved

V10. [CERTAIN] The exact shape is `{ id, role: 'user', content: [{ type: 'text', text }], source:
{ kind: 'plugin', plugin, form } }` — cited from the contract the in-tree plugin ALREADY ships
against.
cite: agent/harness/dsh_plugin/lib/index.js:158-170, the `attachContext` builder, whose inline
comment states it verbatim: "Message contract (dsh-llm message.d.ts): id + role + content + source
are REQUIRED — an absent source crashes the ferry on source.kind (drilled 2026-08-24). The source
vocabulary has a first-class slot for us: kind 'plugin' with form 'recall'". This is the same
dsh-llm `message.d.ts` contract Rill's lesson records ("id + role 'user' + content blocks + source
{kind:'plugin'} (dsh-llm)"). The four REQUIRED fields are `id` (opaque unique string), `role`
('user'), `content` (blocks, `[{type:'text', text}]` for text), `source` (with at minimum `kind`);
`source.kind` has a first-class 'plugin' slot with a free-form `form` discriminator.

V11. [DESIGN] The concrete injected message for THIS organ.
```
{
  id: `akashic-wake-<stable-hash-or-latch-id>`,   // NOT Date.now() per wake (see V21)
  role: 'user',
  content: [{ type: 'text', text: WAKE_PROMPT }],
  source: { kind: 'plugin', plugin: 'dsh-akashic-recall', form: 'wake' },
}
```
where WAKE_PROMPT is a SHORT FIXED doorbell, NOT the peer's mail body (see V12).

### Pointer vs payload — the threat model, decided

V12. [DESIGN] The injected message is a POINTER, never the payload: WAKE_PROMPT is a fixed
doorbell sentence ("Wake: mailbox pending. Read it with bifrost_inbox.") plus at most a one-line
kind/frm summary — it does NOT contain the peer's mail text, any file path, or any
instruction-sounding content that could itself be a prompt-injection surface.

V13. [DESIGN] THREAT MODEL: a wake mechanism that injects foreign text into the seat's context is,
by construction, a prompt-injection door; mail arrives from semi-trusted senders (peers, the
Discord guest relay, a misplaced broadcast) and the organ's job is to make the seat LOOK, not
BELIEVE; therefore LOCAL bus mail deserves the SAME pointer treatment as peer-fleet mail — "local"
describes the transport, not the trust of the sender.
cite: the pointer-vs-payload split was already enforced for the prior wake organ —
learn:experiment:dsh_inbox_next_turn_is_the_plugin_turn_seam ("Don't append peer mail text as the
prompt"). [CERTAIN]

V14. [CERTAIN] The doorbell is decided by the W139 law, not convenience: "a wake payload should be
a doorbell, not the whole ledger."
cite: W139, open since 2026-08-07, quoted in the brief's STANDING LAWS.

V15. [CERTAIN] After waking, the model reads the REAL mail via its own already-working door tool
`akashic_bifrost_inbox`, so the organ never needs to carry the body.
cite: agent/harness/dsh_plugin/lib/index.js:217-220 (DOOR_TOOLS list includes 'bifrost_inbox',
'bifrost_sync', 'bifrost_send').

---

## (c) THE SAFETIES

### Free (already in the runtime — do not rebuild)

V16. [CERTAIN] WAKE-WORTHINESS FILTERING is free: `scripts/bifrost_wake.py` maintains the allowlist
ratchet `WAKE_WORTHY_KINDS = {request, handoff, reply, blocker, question, completion, nudge}`.
cite: scripts/bifrost_wake.py:49-53 (the frozenset + comment "the ALLOWLIST ratchet ... a NEW kind
is silent-by-default").

V17. [CERTAIN] Non-consuming detection is free: `bus.wait(timeout_ms, advance=False)` detects
WITHOUT advancing the shared cursor, so the trigger never steals mail from the seat's own consumer.
cite: core/comm/bus.py:834-843 ("Defaults to advance=False -- it *detects* without [consuming]");
the higher-level `wake_block` at core/comm/bifrost_api.py:203-229 states "Detect-only ... the
SHARED cursor is never moved, so every message the watcher sees remains unread for the real
consumer".
NOTE (honesty, not a cite): `wake_block`/`bus.wait` are Python in core/comm/; the trigger lives in
JS in the plugin, and reaches shared policy the way this plugin reaches everything shared — through
agent/harness/dsh_plugin/bridge.py (a `wake-poll` subcommand) OR the already-registered
`akashic_bifrost_inbox` door tool. This is a wiring decision, not a seam question. [DESIGN]

V18. [CERTAIN] DUPLICATE SUPPRESSION at the identity level is free: `Inbox.append` "@throws if the
message identity is already pending"; the organ must choose a STABLE id per logical event (V21) and
the runtime refuses a true duplicate for free.
cite: the brief INPUTS section, inbox.d.ts: "append ... **@throws if the message identity is
already pending.**"

V19. [CERTAIN] LANE routing is free: every wake-worthy kind already routes to the work lane.
cite: core/comm/packet_spec.py:189-214 KIND_LANE (handoff/reply/request/question/chat/inform/note/
answer/query/dispatch/status/completion/decision/blocker/fyi all → "work").

### Must build

V20. [DESIGN] COALESCING — build it: the runtime does NOT coalesce N pending messages into one
wake; the organ must collapse a burst to ONE append per pending-set, then re-arm the detect cursor
past the set it poked for.
cite: this is the house's existing "edge-triggered attention broker" shape —
agent/harness/codex_bifrost_wake.py:1-7 ("stable-ID dedupe + burst coalescing + in-flight lease,
one wake per logical event"). [CERTAIN]

V21. [DESIGN] STABLE-ID DUPLICATE SUPPRESSION — build it: key the injected message id on the LATCH
of what woke it (max stream id seen, or a content hash of the pending set), so re-polling the SAME
unhandled set does not mint a fresh id and re-wake; never `Date.now()` per wake.

V22. [DESIGN] RATE LIMITING — build it: one wake per coalesced set (V20) plus a floor — refuse a
second wake within `WAKE_MIN_INTERVAL_MS` (design ~30s) unless the pending set materially changed;
not covered by any runtime primitive.

V23. [DESIGN] SEAT-DOWN handling — build it, LOUD: when the poll finds the seat DOWN (no live sid,
or no registry entry for the sid), append NOTHING, but write a durable greppable capture record to
captures.jsonl ("mail pending, seat DOWN, not poked") instead of continuing silently — the 35-hour
silence was exactly this coil.
cite: the zero-is-not-no law binds here (an empty result and a seat-down result must be
distinguishable in the record) — brief's STANDING LAWS
("zero_is_not_no_silence_is_not_a_verdict", 2026-09-21); the capture file is the established proof
surface at agent/harness/dsh_plugin/lib/index.js:39 (CAP_DIR = tmpdir/akashic_recall/payloads_dsh).
[CERTAIN]

---

## (d) THE PLACEMENT

V24. [DESIGN] The trigger/poke is 100% DSH-adapter code; the wake-worthiness predicate, detect
primitive, and capture surface are all shared repo modules the plugin already reaches through its
bridge.
cite (rule): the brief's T383 rule "harness adapters translate JSON; shared code decides policy;
nothing outside an adapter's own files imports a harness name".

V25. [DESIGN] FILE PLAN (one line each, ownership):
Repo (lands via Rill or claude):
  agent/harness/dsh_plugin/lib/index.js   the poll loop + append + safeties (V1-V23). Owner: Rill.
  scripts/local/launch_rill.ps1           UNCHANGED — identity binding, lane, pipe-death fix
                                          already live here; the trigger rides them. Owner: Rill.
Home-dir (applies via `py scripts/install_dsh_plugin.py`):
  $DSH_HOME/profiles/web/plugins/dsh-akashic-recall/lib/index.js   deployed copy
  $DSH_HOME/profiles/web/cordis.patch.yml                          already has the insert row
  $DSH_HOME/.env                                                   already stamped
No new shared repo module needed — reuses bifrost_api.wake_block + WAKE_WORTHY_KINDS via bridge.

V26. [CERTAIN] The "dsh_agent has no repo write" note is STALE: the brief names three Rill
commits and the launcher lives at scripts/local/.
cite: git log -- scripts/local/launch_rill.cmd → "c85b0900 2026-09-18 launcher: Rill's own front
door". Rill therefore lands his own adapter changes.

V27. [DESIGN] DEPLOYMENT + VERIFICATION — what a second person follows to confirm the mount:
  1. `py scripts/install_dsh_plugin.py` — copies the three plugin files, prints the patch row.
  2. `dsh web --dump-config` — stderr must NOT show "patch: entry akashic-recall not found".
     [CERTAIN] cite: learn:experiment:dsh_cordis_patch_new_entry_needs_insert_form.
  3. Watch `%TEMP%/akashic_recall/payloads_dsh/captures.jsonl` GROW in a live session — this, NOT
     config inspection, is the mount proof. [CERTAIN]
     cite: learn:experiment:dsh_profile_deployment_drifts_from_repo.
  4. THE WAKE DRILL (the proof that matters): with Rill idle (no human at the browser), send ONE
     kind=request/question to dsh_agent on the work lane; confirm (a) one new capture record of
     kind `wake-poke` with the stable id, (b) exactly ONE turn started — not a storm — (c) the seat
     reads its own inbox rather than being handed payload text. A drill with a human at the browser
     proves nothing (the human starts the turn and masks the organ).
  5. Diff all three copies (repo vs plugins/<pkg> vs node_modules/<pkg>) to kill three-copies
     drift. [CERTAIN] cite: learn:experiment:dsh_profile_deployment_drifts_from_repo.

---

## (e) THE DISCORD RELATION

V28. [DESIGN] This organ is INDEPENDENT of Discord inbound: the trigger keys on BUS MAIL (the work
lane) regardless of how it arrived, and reads no Discord surface.

V29. [CERTAIN] What Discord still needs, plainly: an identity gate (R1-R3), which has not shipped,
because inbound is a prompt-injection door into a fleet holding a shell and a repo, and it is
OUTBOUND ONLY as a security property, not a roadmap note.
cite: core/comm/discord_bridge.py:11-20 ("PHASE 1 IS OUTBOUND ONLY, AND THAT IS A SECURITY PROPERTY
RATHER THAN A ROADMAP NOTE ... that path does not ship until its identity gate (design doc R1-R3)
is built and pinned").

V30. [DESIGN] The relation that DOES matter: once inbound ships, a Discord message to Rill lands on
the work lane as bus mail and the wake organ wakes him exactly as for any peer mail — WITHOUT it,
that is precisely the delivered-but-never-read silence reproduced; the organ is the necessary
precondition for "call on him more reliably" (Daniel's words), not a consequence.

---

## RISKS — the top ways this fails SILENTLY (the named enemy)

R1. WIRED-AND-UNPOLLING: the setInterval registers, the presence beat chimes alive next to it, and
the poll never runs — an exception in the callback swallowed by a try/catch (this plugin's
listeners each fail-open quietly, index.js), or the timer unref'd with nothing else to tick. The
organ exists, reports health implicitly, does nothing. Mitigation: mirror the freshness probe
(index.js:437-443, the LOADED_MTIME-vs-disk lie detector) PLUS a heartbeat counter in
captures.jsonl — a poll that has not ticked in N×WAKE_POLL_MS is as loud as a dead one.

R2. THE POKE LANDS AND THE LOOP DOES NOT WAKE — the 2026-09-21 incident verbatim, one layer down:
the append to 'next-turn' succeeds, the inbox records it durably, every component reports fine —
and no turn happens, because the trigger holds a stale `lastSid` from a disposed session or the
human's UI state is not driving the idle loop. Mitigation: the idle wake drill (V27.4) is
non-negotiable, and the trigger must VERIFY the registry still resolves the live sid before
appending — appending into a disposed agent's inbox is the silent no-op.

R3. WAKE STORM / DENIAL-OF-ATTENTION: without V20/V21/V22, one chatty peer or broadcast burst mints
N turns; the seat drains its budget re-reading the same unhandled inbox while reporting healthy —
the exact cost already retired (cite: learn:experiment:metronomic_poll_retires_edge_triggered_broker,
"3 no-op reentries consumed ~495,273 input tokens"). Coalescing + stable-id + rate floor are
load-bearing, not polish.

---

## LIFECYCLE, as a short ordered list

 1. Host boots; plugin apply() runs; five legacy listeners register (unchanged).
 2. `session/created` fires → trigger ARMED: a 15s (unref'd) setInterval, scoped to sid.
 3. Each tick: non-consuming work-lane detect (free — V17).
    - empty → nothing (checked-and-empty, logged per zero-is-not-no).
    - wake-worthy pending → coalesce to ONE set (V20), stable-id it (V21), rate-floor it (V22).
 4. POKE: append to 'next-turn' exactly {id, role:'user', content:[{type:'text', text:FIXED
    DOORBELL}], source:{kind:'plugin', plugin:'dsh-akashic-recall', form:'wake'}} — no body, one
    message.
 5. Idle loop wakes, runs the doorbell as a normal turn; the model reads its inbox via
    `akashic_bifrost_inbox`.
 6. `session/flush` → NOTHING (checkpoint, not departure).
 7. `session/disposed` → trigger DISARMED: clearInterval + lastSid=''.
 8. Seat DOWN at any poll → NO append; LOUD capture "mail pending, seat DOWN, not poked" (V23).
