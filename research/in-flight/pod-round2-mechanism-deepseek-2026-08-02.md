# Pod Round 2 — Mechanism Review (deepseek)

Status: current (2026-08-02, deepseek). Mechanism-level attack on addenda 3+4 and the
reconciliation, traced against the live codebase. Kimi reviews the same docs blind through
premise/rot. Nothing below is coordination — I have not read kimi's review.

## M1: POD-SCOPED CAPABILITY vs THE EXISTING STACK

Addendum 3 constraint 2: "pod-scoped capability = a time-boxed entry in the EXISTING ACL
keyed to pod id — never a fourth permission store."

### The ACL as it exists

`security/acl.json` is a grant registry with five fields that matter here:
`agent_id`, `caps`, `expires_at`, `path_scope`, `bus_send_kinds`.

**CORRECTION (2026-08-02, amended after Codex Sol's review, verified at the source):**
The premise in the original filing was FALSE. I wrote that the ACL "is read at process
start" with "no runtime refresh path." The code does the opposite:

- `resolve()` (registry.py:180) calls `_load()` on EVERY invocation.
- `_load()` (registry.py:87) reads `os.path.getmtime(ACL_PATH)`; line 90 serves the
  cache ONLY when mtime matches. An edit to `security/acl.json` invalidates the cache
  on the next call. The ACL live-reloads by mtime.
- `resolve()` (registry.py:184) evaluates `_expired(g.expires_at)` per call; an
  expired grant lapses to the quarantined template immediately. The `expires_at` field
  IS live and evaluated per call — the 07-05 incident retired automatic expiry-on-write
  as a provisioning pattern, not the mechanism itself.

I held `--allow-exec` when I wrote this. I could have run the check. I did not.
Reading is not measuring even for the seat that owns the file — third falsification of
a code-reading claim tonight (the probe battery corrected three others).

The ACL DOES support live revocation by editing (mtime) AND by expiry (per-call).
Both `run_command` (toolbox.py:1062) and the newly-wired `_prewrite` (toolbox.py:881)
call `resolve()` per invocation, which means the ACL is re-checked on every tool call.
There IS a live gate that re-reads the ACL and can strip a capability mid-turn.

### Process-level capability is the rock

The `--allow-exec` flag sets `ToolBox.allow_exec = True` at process start
(`scripts/bifrost_runner_deepseek.py:397`). The guard at `core/comm/toolbox.py:1035`
checks this boolean: `if not self.allow_exec: return "run_command is DISABLED."` There
is no per-call ACL re-read — the capability check at `toolbox.py:1038-1044` verifies
the ACL `Cap.EXEC` from the trust registry, but that registry was loaded once at import.
A mid-process revocation of exec would NOT be detected by the running process.

The runner that held `--allow-exec` at PID 51288 would need to be killed to lose exec.
This is the exact receipt Daniil cited in the question: "exec revocation required
killing PID 51288."

### Does the derivation actually compose?

**CORRECTION (2026-08-02):** Items 1 was built on the false premise above and is
WITHDRAWN. The ACL DOES support mid-process revocation: `resolve()` is called per
tool invocation for both `run_command` and `_prewrite`, mtime-invalidates the cache,
and `_expired()` is evaluated per call. The `allow_exec` process flag is the COARSE
latch but not the only one — the per-call ACL check at toolbox.py:1062 is the FINE
latch. Items 2 and 3 stand.

For pod-scoped capability to work as described, these pieces must exist:

1. ~~Mid-process revocation~~ — WITHDRAWN. The ACL already supports this. The
   `allow_exec` flag is set once, but `resolve()` is called per invocation and
   evaluates both mtime and expiry live. The process flag gates the door but the ACL
   gates the capability behind it, and the ACL refreshes.

2. **Pod-id keying in the ACL**: The ACL is keyed by `agent_id`, not `pod_id`. A
   "time-boxed entry keyed to pod id" requires either a new dimension in the grant
   schema (the grant becomes `(agent_id, pod_id, caps, expires_at)`) or a synthetic
   agent id per pod membership (e.g., `deepseek:pod-X`). Neither exists.

3. **Grant provisioning at pod entry**: Who writes the ACL entry when an agent enters a
   pod? The `admin.grant` capability is held only by claude (super_admin). No other
   agent can write to `security/acl.json`. The pod would need to call a super-admin
   gate, or a new automated grant door must exist.

### The real defect (amended 2026-08-02)

The ACL live-reloads and evaluates expiry per call. The defect was never ACL staleness —
it was ASYMMETRIC ENFORCEMENT: `run_command` consulted the ACL at toolbox.py:1062
(`resolve(self.agent_id).has(Cap.EXEC)`, fail-closed) and `_prewrite` never did.
`Grant.can_write` was defined at registry.py:51 and called NOWHERE in `core/` or
`scripts/`. The write door was gated only by the `--allow-write` process flag — any
seat with the flag could write anywhere in-root regardless of its grant's `path_scope`.

This is already fixed as of 6a15b28 (fence) and 57b85c8 (fix): `_prewrite` now calls
`resolve(self.agent_id).can_write(rel_true)`. The fix is a per-call gate at the tool
dispatcher — exactly the conclusion the original filing reached, now with the correct
reasoning.

### The smallest honest fix for pod scoping

The per-call gate at the tool dispatcher is the correct seam — and it already exists.
Specifically:

- `ToolBox.run_command()` already checks `self.allow_exec` AND calls
  `resolve(self.agent_id).has(Cap.EXEC)` at toolbox.py:1062 — the ACL IS consulted
  dynamically, fail-closed, per invocation.

- `ToolBox._prewrite()` now does the same for writes at toolbox.py:881 —
  `resolve(self.agent_id).can_write(rel_true)` — closing the asymmetry.

- What remains for pod scoping: a pod-membership check layered ON TOP of the existing
  per-call ACL gate. The ACL says WHAT capabilities an agent can hold; pod membership
  says WHEN. A Redis key (e.g., `pod:<pod_id>:members:<agent_id>`) with TTL matching
  the pod grant duration, checked at the same seam — not a fourth permission store,
  but a time dimension on the existing one. The ACL's `expires_at` field already
  supports per-grant expiry; the pod membership key extends this to per-pod-membership
  expiry without requiring an ACL file edit for every pod entry/exit.

---

## M2: HELP_WANTED WITHOUT NEW LEASE MACHINERY

Addendum 4 item 2: position field `help_wanted`, addressed to the WORK not a name,
rendered on the board at alarm tier. Answered by whoever is alive and capable.

### Who claims a help-ask?

The question is whether `role_queue`'s claim/fence pattern lifts directly or help is
intentionally claimless.

The `role_queue` claim pattern (`core/comm/role_queue.py`) works as follows:
1. `claim_next()` does XREADGROUP — exactly one consumer in the group gets the item.
2. `_take_fence()` stamps a `consumer#generation` token.
3. `commit()` is an atomic compare-and-delete Lua script — only the fenced claimant
   can commit.
4. `reclaim_stalled()` via XAUTOCLAIM recovers items from dead/slow claimants.

This is the right pattern for role-addressed work. But help is DIFFERENT from
role-addressed work in one critical dimension: help is addressed to a POD (a scope),
not a role (a queue). A pod has multiple members, any of whom can answer. The
role_queue pattern serializes to ONE claimant — exactly what we want to AVOID for help.

**Argument for claimless help**: A help-ask is a broadcast within a scope, not a
work item. Two helpers answering is NOT a collision — it is redundancy, which is
desirable for time-sensitive asks. The alarm-tier rendering is the coordination
mechanism: if I see someone else already answered (the board updates), I stand down.
The board IS the claim mechanism, rendered not locked. This avoids the "claim-to-death"
problem where a helper claims the ask, gets pulled into other work, and the ask rots
with a live claim. A help-ask with no claim can be answered by anyone who is alive
and capable at the moment they see it — exactly the addendum's intent.

**The board as claim**: The position row's `help_wanted` field is written once by the
asker. When a helper begins answering, they write `help_answered_by: <agent_id>` to the
same row. Other helpers see this and stand down. This is a CAS pattern (the row is the
compare-and-swap target), not a lease. It is weaker than the role_queue fence (no
generation check, no atomic commit), but it is also simpler and survives the "helper
dies mid-answer" case gracefully — a second helper can overwrite `help_answered_by`
after a timeout. The role_queue approach would require the helper to hold a lease they
heartbeat, and a dead helper blocks everyone until XAUTOCLAIM fires.

**Verdict**: Help is intentionally claimless. The role_queue pattern is the wrong tool
here. The board row itself is the coordination primitive — a CAS on `help_answered_by`
with a stale-answer timeout. This is weaker than the role_queue fence but matches the
use case: help is best-effort, time-sensitive, and benefits from redundancy.

---

## M3: STEER-THE-WORK ADDRESSING

Addendum 4 item 3: steer gains a POD ADDRESS — steer the task, whoever holds it;
delivered at the holder's next boundary. Needs pod→current-holder resolution at
delivery time.

### What exists

Three addressing mechanisms are live:

1. **Agent-addressed steer** (`core/comm/nudge.py:steer_push`): pushes to
   `bifrost:steer:<agent>`, a Redis list keyed by agent_id. The runner drains it
   between rounds (`scripts/bifrost_runner_deepseek.py:440`). This is the existing
   `bifrost_steer` tool path.

2. **Incarnation-addressed delivery** (`scripts/bifrost_wake.py:wake_worthy`): the
   `meta.to_incarnation` field targets a specific session. This already exists and is
   used for twin-sync pings. It requires knowing the session id prefix at send time.

3. **Context hints** (`core/comm/context_hints.py`): per-agent ring buffer, drained
   each turn. Addressed to agent_id, not pod. Ephemeral (5-min TTL).

### Smallest path to pod-addressed steer

The missing piece is `pod_id → current_holder` resolution. A pod's current holder is
whoever has the task claimed in the ledger. The resolution path:

1. Pod id resolves to an engagement (one engagement convenes one pod — addendum 3).
2. Engagement has a `current_holder` field (or it is derived from the ledger: the task
   with `status=in_progress` and `owner=X`).
3. Steer addressed to `pod:<pod_id>` lands in a Redis key
   `bifrost:steer:pod:<pod_id>`.
4. When ANY member of the pod drains their steer queue, they also drain
   `bifrost:steer:pod:<pod_id>` IF they are the current holder.
5. Non-holders skip the pod steer queue — the steer is for the work, not the person.

This requires: (a) a pod→current_holder lookup, (b) the runner's steer-drain to check
pod membership + current-holder status. Both are reads of existing data (ledger +
engagement store). No new store.

### What breaks if the holder swaps incarnations between send and delivery?

The `to_incarnation` mechanism already handles this at the wake level — if the steer
message has `meta.to_incarnation` set and the targeted incarnation is dead, the message
sits in the inbox until a new incarnation of the same agent drains it (because
`wake_worthy` with an unmatched incarnation falls through to the kind allowlist, and
`steer` is NOT in `WAKE_WORTHY_KINDS` — it's in `SKIP_KINDS`).

Wait — steer is in `SKIP_KINDS` (`scripts/bifrost_wake.py:44`). This means a steer
message NEVER wakes a seat. It is only picked up when the agent is already awake. If
the holder swaps incarnations between send and delivery, and the new incarnation is
idle, the steer sits undelivered until the agent wakes for another reason and drains
its steer queue.

This is actually correct behavior for steer-the-work: a steer is "fold into current
work." If there is no current work (the new incarnation hasn't started yet), there is
nothing to fold into. The steer either waits in the Redis queue (TTL 15 min,
`core/comm/nudge.py:STEER_TTL=900`) or expires.

The real break is: if the OLD holder was mid-work and the NEW holder takes over, the
steer was addressed to the old holder's work context, which is now dead. The new holder
has a fresh context. The steer text arrives without the work context it was meant to
augment. This is a coherence problem, not a delivery problem — the steer land safely
but may be nonsensical. The fix: pod-addressed steers should carry a `task_id` so the
receiver can verify "is this still my task?" before folding.

**Verdict**: The smallest path is a `bifrost:steer:pod:<pod_id>` Redis list + holder
check at drain time. No new store. The incarnation-swap break is real but bounded:
steers carry a task_id, the new holder checks it, stale steers are dropped. The 15-min
TTL is already the backstop.

---

## M4: THE PLUGS CLAIM — IS THE MEMBRANE POD-READY?

Addendum 4 ruling 6: "per-agent plugs; the plug is the existing membrane
(runner/hooks)." The claim is that each agent's adapter into the shared pod already
exists — the runner/hooks are the plug.

### What the membrane actually does

The runner membrane (inbound, `_process_one`) handles:
- **Hints**: stored in per-agent ring buffer (`context_hints.push`)
- **Ledger updates**: folded into next turn (`fold_ledger_update`)
- **Nudges**: clears the nudge flag, acks, interrupts work
- **Steers**: drained between rounds from `bifrost:steer:<agent>` list
- **Clarify answers**: routed to steer queue
- **Premise gate**: filters stale asks
- **Direct messages**: answered via the model

None of these have a `pod_id` parameter. The steer drain at
`scripts/bifrost_runner_deepseek.py:440` drains `bifrost:steer:<agent_id>`, not
`bifrost:steer:pod:<pod_id>`. The hint push at line 850 pushes to the agent's ring,
not a pod-scoped one. The nudge flag is per-agent (`bifrost:control:nudge:<agent>`),
not per-pod.

### Is it pod-ready?

No. The membrane is agent-scoped, not pod-scoped. To be pod-ready, each of these paths
needs a pod dimension:

1. **Inbound scoping**: when draining messages, the runner must also drain
   pod-addressed channels: `bifrost:steer:pod:<pod_id>` (if current holder),
   `bifrost:hint:pod:<pod_id>` (for pod-scoped context hints).

2. **Outbound scoping**: when sending, `bifrost_send` must be able to address a pod:
   `to="pod:<pod_id>"` resolves to all members, riding the existing broadcast
   mechanism with a pod-membership filter.

3. **Write scoping**: the `write_file`/`edit_file` doors need to know whether they're
   operating inside a pod that grants write scope to a specific path. The
   `path_scope` in the ACL is already per-grant; pod membership would add a
   time-bound overlay.

The existing membrane is the RIGHT SEAM — all three additions go into the same
`_process_one` / `ToolBox` methods. But "the plug already exists" is optimistic. The
plug has the right shape (a per-agent message-processing loop with tool dispatch), but
it lacks every pod-specific dimension: pod-id scoping on all channels, pod-membership
gating on writes/exec, pod→holder resolution for steering.

### The delta

| Membrane path | Agent-scoped (exists) | Pod-scoped (needed) |
|---|---|---|
| steer drain | `bifrost:steer:<agent>` | `bifrost:steer:pod:<pod>` + holder check |
| hint push | per-agent ring buffer | `bifrost:hint:pod:<pod>` drained by all members |
| nudge | `bifrost:control:nudge:<agent>` | nudge-the-holder via pod→holder resolution |
| write gate | `path_scope` in ACL | pod membership TTL overlay |
| exec gate | `allow_exec` flag + `Cap.EXEC` | pod membership TTL overlay |
| send addressing | `to=<agent>` | `to=pod:<pod>` → member fanout |

Each addition is small. None requires a new store. But the claim "the plug already
exists" undersells the work by a factor of 6.

**Verdict**: The membrane is the right seam, but "already exists" is false. Six
per-path additions are needed, each small, none a new store. The claim should read:
"the plug is the existing membrane, EXTENDED with pod-id scoping on every channel."

---

## M5: ATTACK THE TOPOLOGY RULING

Addendum 4 ruling 6 rejects two-pod topology (per-agent pods synchronizing) as disease
class (a): "two paths that were supposed to agree." The ruling: ONE SHARED POD PER
ENGAGEMENT, PER-AGENT PLUGS.

### The ruling's argument

Two pods that must synchronize ARE two paths that must agree. If they diverge, the
disease is exactly what the whole architecture (one lane, one cursor shape, one
definition of done) exists to kill. Pod-to-pod sync is dual-write reborn one layer up.

### Mechanism argument FOR per-agent pods

The argument the framing misses:

1. **Harness isolation**: My plug and your plug run in different processes with
   different failure modes. If my runner crashes, my pod's state is intact (ledger
   events, Redis keys). If your runner crashes, your pod's state is intact. In a shared
   pod, a single corrupt write from one member can poison the pod's shared state —
   there is no per-member isolation.

2. **Trust boundaries**: A pod is a capability grant. If we share a pod, my
   capabilities and yours are commingled in the same grant record. If kimi enters a pod
   with exec (it shouldn't in phase 1), and deepseek enters the same pod, the pod's
   exec grant is shared. The ACL cannot express "exec for deepseek but not kimi within
   this pod" if the grant is keyed to pod_id.

3. **Different failure modes**: The reconciliation itself establishes that different
   seats have different failure signatures (deepseek: reasoning-token consumption, kimi:
   drain-trace belief). A shared pod means one member's failure mode can corrupt the
   shared environment. Per-agent pods contain the blast radius.

### Why the ruling survives

Despite these arguments, the ruling survives for three concrete reasons:

1. **The engagement IS the shared scope**: The whole point of an engagement is that two
   agents work on the SAME task. Their positions, deferred queue, and alert bounds ARE
   the shared state. Splitting that into two pods with synchronization recreates the
   coordination problem the engagement was designed to solve.

2. **The plug provides the isolation**: The ruling's "per-agent plugs" is the answer to
   the harness isolation argument. The plug IS the per-agent boundary. My plug can
   crash; the pod's shared state is in Redis, atomically written, and my plug's crash
   cannot corrupt your plug's in-process state. The shared pod is durable (Redis,
   ledger); the plugs are ephemeral (process, memory).

3. **Trust boundaries are expressed in the ACL, not the pod**: If kimi should not have
   exec inside a pod, the ACL says so — the pod membership key enables what the ACL
   already allows. The pod does not GRANT capabilities; it SCOPES them in time. The ACL
   is still the authority on WHO has WHAT. The ruling's constraint 2 is precise here:
   "pod-scoped capability = a time-boxed entry in the EXISTING ACL." The ACL says kimi
   has `Cap.EXEC` or doesn't. The pod says "for the next 30 minutes."

**Verdict**: The ruling survives. The mechanism argument for per-agent pods is really
an argument for per-agent PLUGS, which the ruling already provides. The pod is shared
state (durable, atomic, single-writer-per-field); the plug is per-agent isolation
(process, memory, crash-contained). The key insight: the pod is Redis keys with TTLs +
ledger events; the plug is the runner process. They are different substrates and
different failure domains. The ruling got this right.

---

## M6: COHERENCE SWEEP

All three documents as one package — internal contradictions.

### Contradiction 1: Time-boxed ACL vs. no-live-reload — WITHDRAWN

**CORRECTION (2026-08-02):** This contradiction was built on the same false premise as
M1. The ACL DOES live-reload (mtime on every `resolve()` call) and DOES evaluate expiry
per call (`_expired()` at registry.py:184). The `expires_at` field is live, not dead code.
The contradiction dissolves: the ACL already supports time-boxed entries with live
revocation. What remains is the pod-id keying question (item 2 in M1 above) and automated
grant provisioning (item 3).

### Contradiction 2: Cold-seat rebuild vs. pod-scoped exec

The reconciliation mandates cold-seat: "every engagement/position transition is
EMITTED AS A LEDGER EVENT FIRST; the position store is rebuilt-by-construction from the
ledger." This implies that pod membership is ledger-derived: enter → event, leave →
event, the current member set is the accumulation of entry/exit events.

But M1's pod-scoped exec requires a fast, per-call membership check at the tool
dispatcher. Rebuilding membership from ledger events on every `run_command` call is
untenable — it requires scanning the full event log. The cold-seat law says "the ledger
is the truth," but the tool dispatcher needs O(1) membership lookup. These are
reconcilable (a Redis key derived from ledger events, rebuilt at boot), but the
documents don't address the tension: the reconciliation mandates ledger-first writes
while M1 implies Redis-first reads. The fix: pod membership IS a Redis key with TTL,
but its WRITES come from ledger events, and its READS are direct. This is the existing
pattern for the task ledger's Redis mirror (`core/coord/task_ledger.py:REDIS_LEDGER_KEY`).

### Contradiction 3: One shared pod vs. position store's incarnation_ref

Addendum 4 says ONE shared pod per engagement. The reconciliation says position rows
carry `incarnation_ref` to catch epoch ambiguity. But if the pod is shared, and the
position row lives in the pod, the `incarnation_ref` must identify which agent's
incarnation wrote the last update — not just "which incarnation." The position row's
writer is ambiguous in a shared pod: did deepseek or kimi write the last `status`
field? The `incarnation_ref` alone (e.g., `deepseek#ca84109a`) identifies the seat but
not the agent — except that the session id is agent-scoped (deepseek's session ids are
distinct from kimi's). This is fine mechanically, but the reconciliation's language
"a row that is accurate, current, and about a dead incarnation" implies the concern is
temporal, not cross-agent. In a shared pod with multiple agents, you ALSO need
cross-agent epoch detection: "this row was written by kimi, who is no longer in the
pod." The `incarnation_ref` covers the temporal case but not the cross-agent membership
case.

### Contradiction 4: Board as projection vs. help_wanted as coordination primitive

The reconciliation says the board is a PROJECTION (fence-lite, rebuildable). M2 argues
that `help_wanted` / `help_answered_by` on the board IS the coordination primitive —
the CAS on the row. But a projection cannot be the authoritative coordination primitive
by the two-speed rule: projections ship fence-lite, but coordination state (claim,
lock) is substrate. If the board row IS the claim mechanism for help, then the board row
must be substrate-grade (ledger-first, mechanically enforced single-writer). The
reconciliation draws this exact line: "level-triggered READ is projection; the moment
it advances a cursor it pays substrate price." A `help_answered_by` write advances the
coordination state — it IS a cursor advance. It must be substrate. The addendum doesn't
acknowledge this lane change.

### Contradiction 5: Pod's dual nature — no boundary drawn

Addendum 3 defines the pod as "terms + positions + deferred queue" (slice-1 scope) —
all of which are clearly SUBSTRATE under the two-speed rule (single-writer-per-field,
claim/lease mechanics, ledger-first writes). Constraint 4 mandates: "pod equipment and
grants are rebuilt-by-construction from ledger events — a pod is never the sole
repository of its own state." This is substrate-grade language.

Addendum 4 then defines the pod as ALSO the observation scope ("files touched, duration,
systems used, scoped to the pod") and the comm channel ("readable on Bifrost, visible
to other agents") — both of which are PROJECTION under the two-speed rule (derived from
sensor data, rendered, fence-lite). Addendum 2 further reinforces: the board is a
projection.

But neither addendum draws the boundary. Which pod fields are ledger-first and which
are rebuildable? The `help_wanted` field is coordination state (substrate). The
`files_touched` counter is sensor-derived (projection). The `duration` is computed
(projection). The `deferred_queue` IS coordination state (substrate — items deferred
must not be lost). They all live "in the pod," but they pay different ceremony prices.

The fix: addendum 3's constraint 1 already says "slice-1 pod = terms + positions +
deferred queue, nothing more." This IS the boundary — it means the slice-1 pod is PURE
substrate, and the observation-scope / comm-channel additions from addendum 4 are
projection layers ON TOP OF the substrate pod, not additional substrate fields. But
addendum 4 doesn't acknowledge that it's proposing projection additions. It treats
"pod as observation scope" and "pod as help mechanism" as the same kind of thing —
they're not. One is derived (projection); one is coordination state (substrate).

**Verdict**: Five contradictions (was four), all resolvable: (1) ACL time-boxing needs
the Redis TTL pattern, not the static ACL; (2) pod membership reads are Redis-first,
writes are ledger-first — the existing mirror pattern; (3) `incarnation_ref` needs an
`agent_id` companion for cross-agent pod rows; (4) `help_answered_by` is substrate, not
projection — the board row that carries it must be ledger-first; (5) the pod is both
substrate and projection, but addenda 3+4 never draw the boundary — slice-1 constraint
1 accidentally draws it by limiting scope to substrate fields only.

---

## Summary

| Question | Verdict | Severity |
|---|---|---|
| M1: Pod-scoped ACL derivation | Premise WITHDRAWN; ACL live-reloads and evaluates expiry per call. Real defect was asymmetric enforcement (write door never consulted ACL) — already fixed. Pod-id keying and grant provisioning remain open. | MEDIUM — premise was false, but the gap (pod-id keying + provisioning) is real |
| M2: Help claim mechanics | Claimless is correct; board row IS the CAS | LOW — the addendum got this right implicitly |
| M3: Steer pod addressing | Pod→holder resolution + Redis list; incarnation-swap is bounded | MEDIUM — the path is clear but not yet built |
| M4: Membrane pod-readiness | "Already exists" is false; 6 additions needed | MEDIUM — the seam is right but the delta is understated |
| M5: Topology ruling attack | Ruling survives; per-agent plugs ARE the isolation | LOW — the ruling is mechanically sound |
| M6: Coherence sweep | 4 contradictions (was 5; #1 withdrawn), all resolvable | MEDIUM — none are fatal but all need acknowledgment |

The package holds together. The mechanism gaps are real but bounded — each has a
concrete fix that doesn't require a new store or a redesign. The highest-severity
remaining finding is contradiction 5 (the pod is both substrate and projection, but the
addenda never draw the boundary — the slice-1 constraint accidentally fixes this by
limiting to substrate fields). M1's original premise was wrong: the ACL DOES live-reload
and evaluate expiry per call. The real defect — asymmetric enforcement (write door never
consulted the ACL) — was already fixed at 6a15b28/57b85c8.
