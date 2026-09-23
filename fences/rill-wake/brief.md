# M1-BRIEF — rill-wake

## CHARTER

Daniel, 2026-09-22: "Can you think on how we can help make Rill wakeable? this will help his
discord integration and allow us to call on him more reliably." Then: "Can you help get rill wired
in for wake?" and "Lets run the blind."

THE CONCRETE INCIDENT THAT MOTIVATES THIS. On 2026-09-21 15:03 UTC, claude sent Rill (dsh_agent) the
fence-worthiness answer his eye-fuzzy-search spec was explicitly blocked on. It was DELIVERED. As of
2026-09-22 22:xx EDT it still sits at `tier=unhandled` in his mailbox — 35 hours — and
`research/in-flight/eye-fuzzy-search-2026-09-19/brief.md` still reads "Vandor's fence-worthiness
answer still pending." Nothing failed. The bus worked. Rill is turn-based and no turn happened.

## INPUTS — established by direct inspection, cite these

RUNTIME (installed, verified 2026-09-22):
- DSH `@deepseek-ai/dsh` **0.1.1-rc.2** at `C:/Users/L5/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh`.
- The inbox API is NOT in the `dsh` bundle. It lives in the nested package
  `node_modules/@deepseek-ai/dsh-agent/lib/types/inbox.d.ts`. A grep of `dsh/lib` + `dsh/config`
  for "inbox" returns ZERO — scope your search to the nested package or you will conclude wrongly.
- `inbox.d.ts`: `export declare class Inbox` with
  - `get nextTurn(): readonly UserMessage[]` — "Prompts awaiting individual turns."
  - `get nextStep(): readonly UserMessage[]` — "Input awaiting the next step boundary."
  - `get hasPending(): boolean`
  - `append(target: InboxTarget, message: UserMessage): void` — "Append one message to a pending
    list and durably record the insertion. **@throws if the message identity is already pending.**"
  - `prepend(...)`, `replace(...)`, `clear()`
  - `claim(target, turn)` — marked **`@internal — The agent loop's step-boundary operation, not a
    plugin extension point.`**
  - `InboxNotifications`: `inserted(message)`, `discarded(message)`, `claimed(message, turn)`
- `types.d.ts:8`: `export type InboxTarget = 'next-turn' | 'next-step';`
- `types.d.ts:16`: session event `'agent/inbox/spliced'` carries `{target, start, removedCount?,
  inserted: UserMessage[], outcome?}`. "Live dispatch precedes projection mutation, so synchronous
  observers may read the pre-splice inbox."
- `index.d.ts:28`: `agents: AgentRegistry`; `:150` "`ctx.agents.get(id)` still returns a bare Agent".
- UNRESOLVED: the exact `UserMessage` shape (its source/kind/form fields). Not located in
  `dsh-session/lib/types/*.d.ts` by this brief's search. RESOLVE IT AND CITE IT; do not invent it.

PRIOR ART IN THE HOUSE:
- Rill's own lesson (`learn:experiment:dsh_inbox_next_turn_is_the_plugin_turn_seam`): "hold
  `ctx.agents.get(sid).inbox` and append ONE harness-generated UserMessage (source kind 'plugin',
  e.g. form 'wake') to 'next-turn' -- the idle loop wakes and runs it as a normal turn. Don't append
  peer mail text as the prompt, and don't call the loop's claim() (internal)."
- **T383 (`fences/t383-dsh-adapter/`, SEALED 2026-08-24)** inventoried every DSH seam:
  `system-prompt/assemble` (inject-yes), `tools/pre-execute` (gate-only), `tools/post-execute`
  (inject-yes via additionalContexts FIFO), `session/flush`, `session/disposed`. A grep of its
  reconciliation and post-seal notes for wake/initiate/idle-loop/inbox returns ZERO. **Every seam
  T383 designed fires INSIDE a turn. None can start one.** That is the gap this fence fills.
- `scripts/bifrost_wake.py` — the canonical wake listener for the CLAUDE shape: blocks on the
  inbox at ~zero cost, "keeps waiting through pure trace/noise instead of exiting on it", holds a
  per-session PID seat file, exits 0 on benign endings. Its wake mechanism is PROCESS EXIT, which
  works only "in a harness that re-invokes an agent when its background task finishes".
- `scripts/remote_bridge_watch.py` docstring states the split explicitly: "EXIT-ON-HIT suits a
  harness where a finished background task re-invokes the agent... `--notify SEAT --loop` suits a
  TURN-BASED seat (a DSH seat like Rill or Zadkiel), which is not sitting in a loop waiting to be
  re-invoked. A process that prints and dies reaches it never."
- `py agent_cli.py bifrost-standby` — "turn-end ritual in ONE verb: drain, seat report, then BLOCK
  as the wake listener's parent". The claude-side arming pattern.
- Deployment mechanics (Rill's lessons, verified useful 2x each): plugin rows go in
  `cordis.patch.yml` as `- insert: [{id, name}]` with `name` the relative path to the JS file;
  **the patch layer HOT-APPLIES without restart**; confirm a real mount by watching
  `%TEMP%/akashic_recall/payloads_dsh/captures.jsonl` grow, not by reading config; and THREE copies
  drift — `agent/harness/dsh_plugin` (repo), `plugins/<pkg>`, `node_modules/<pkg>` — diff all three.
- Current deployed plugin `agent/harness/dsh_plugin/lib/index.js` (2026-09-18) exposes bus TOOLS
  (`bifrost_sync`, `bifrost_send`, `bifrost_inbox`, `bifrost_presence`) and nothing that touches
  the inbox. The seam is unused.
- Rill's launcher `scripts/local/launch_rill.cmd` / `.ps1` (c85b0900) binds identity at ingress and
  clears eight inherited variables, four of them per-session (`DSH_SESSION_ID`, `DSH_SESSION_JSONL`,
  `DSH_WEB_URL`, `DSH_SHELL`). Two drill findings ride it: a launched seat that inherits the
  launcher's stdout pipe DIES when that pipe closes; and a child inherits session identity unless
  cleared.
- Rill's presence lesson: "session/flush is a durability checkpoint, NEVER presence-offline; only
  session/disposed ends presence, and there the recurring beat must be stopped (clearInterval +
  lastSid reset) or it resurrects the key."

STANDING LAWS THAT MAY OR MAY NOT BIND HERE — decide, don't assume:
- The bridge relay's rule: "a remote sentence must never be a thing that HAPPENED TO an agent";
  its notification "is a POINTER, never the payload". Written for peer-fleet mail. Whether it binds
  LOCAL bus mail is a question this fence must answer, not inherit.
- W139 (open since 2026-08-07): "a wake payload should be a doorbell, not the whole ledger."
- `zero_is_not_no_silence_is_not_a_verdict` (filed 2026-09-21): any surface reporting an empty or
  absent result must distinguish (a) checked-and-empty (b) never-reported/unknown (c) declined,
  with a reason. Never collapse the three.
- Discord is OUTBOUND ONLY and that is a security property, not a roadmap note
  (`core/comm/discord_bridge.py:11`, `docs/DOORS.md:41`): inbound needs an R1-R3 identity gate that
  has not shipped.
- T383's architecture rule: "harness adapters translate JSON; shared code decides policy; nothing
  outside an adapter's own files imports a harness name."
- T383 records "dsh_agent has read/exec, NO repo write — repo-resident plugin code lands via
  claude". Rill has committed since (c85b0900, 134268cd, 896e2c2a). VERIFY whether this is stale.

## RULES OF ENGAGEMENT

Blind halves: do NOT read the other half before sealing yours. Every load-bearing claim carries a
line-start V-verdict: `V<n>. <claim> [CERTAIN|DESIGN|INFERRED|UNCERTAIN]`. CERTAIN requires a
file:line citation. UNCERTAIN is an honest verdict and never a gap to paper over — this brief
contains at least one genuine unknown (the UserMessage shape) and "I could not establish it" is a
correct answer there. Write via `py agent_cli.py fence write rill-wake --slot half_a|half_b --by
<agent> --file <path>`, then `fence seal` the slot. Commit the artifact before the fence lifts.

## THE QUESTION

Design the organ that makes Rill wakeable — reliably, safely, and without a human starting the turn.

(a) THE TRIGGER. What process notices wake-worthy mail for a turn-based seat, where does it run,
    what is its lifecycle (armed by what, disarmed by what, what happens across session/flush vs
    session/disposed), and how does it survive the launcher's pipe-death finding?

(b) THE POKE. Exactly how the trigger reaches the seat: which object, which call, what target, and
    what the injected UserMessage CONTAINS and does not contain — with your reasoning about the
    pointer-vs-payload question, which this brief deliberately leaves open. State the threat model
    you are designing against and whether local bus mail deserves the same treatment as peer mail.

(c) THE SAFETIES. Coalescing, wake-worthiness filtering, rate limiting, duplicate suppression, and
    what happens when the seat is DOWN. Name which of these the runtime already gives you for free
    and cite it, versus which you must build.

(d) THE PLACEMENT. Which code is shared policy and which is the DSH adapter's, the exact file plan
    (repo path vs home-dir path, and who can write each), and the deployment/verification steps a
    second person would follow to confirm it actually mounted.

(e) THE DISCORD RELATION. Whether this organ requires, enables, or is independent of Discord
    inbound — and if independent, say plainly what Discord still needs.

## OUTPUT CONTRACT

A numbered design with V-tagged claims; a concrete file plan (one line each on ownership); the
lifecycle as a short ordered list; the exact injected-message shape; and a RISKS section naming at
least the top two ways this design FAILS SILENTLY — silent failure is the named enemy here, because
the incident that motivated this fence was a 35-hour silence in which every component reported
success. Length: whatever the design needs, no padding.
