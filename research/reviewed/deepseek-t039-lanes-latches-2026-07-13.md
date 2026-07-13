# DeepSeek half -- T039 lanes+latches design (VERBATIM, blind fence 2026-07-13)

Status: current (2026-07-13)
Class: design half (deepseek blind; paired with claude-t039-lanes-latches-2026-07-13.md)
Brief: research/t039-lanes-latches-design-brief-2026-07-13.md (identical to claude's). deepseek-v4-pro, blind.

---

A. LANE MECHANISM  
- **Keyshape per lane** (all under the existing namespace, e.g. `bus:stream:{namespace}`):  
  - `bus:stream:{namespace}:work` – stream, maxlen capped with `MAXLEN ~ 10000`. Consumer group `work-group` holds the RB‑21 fenced single consumer.  
  - `bus:stream:{namespace}:sig` – stream, maxlen ~5000. No consumer group; each agent keeps its own cursor in a separate key `bus:cursor:{namespace}:sig:{agent_id}` and uses `XREAD` (no wake; checks between rounds + doorbell).  
  - `bus:stream:{namespace}:trace` – stream, no consumer group, `XTRIM` with `MAXLEN ~5000` on every `XADD` (ring buffer).  
  - `bus:stream:{namespace}:test:{drill_ns}` – per‑namespace stream, maxlen 10000 + TTL on the drill namespace. Consumer group per namespace (`test-{drill_ns}-group`), fenced single consumer. Wake‑listeners only watch this stream.  

- **Kind→lane router** is a pure function at the send door. It maps:
  - `kind` starting with `work` → `work` lane.
  - `kind` in `{halt, interrupt, …}` → `sig` lane.
  - `kind` in `{trace, span, …}` → `trace` lane.
  - `kind` starting with `test.` + drill env → `test:{ns}` lane (otherwise REFUSED).
  - Anything else → REFUSED loud.  
  The router writes the serialised packet to the corresponding stream with `XADD`, attaching the per‑lane overflow policy (e.g. `MAXLEN` for work/sig, `~ MAXLEN`+`XTRIM` for trace, `MAXLEN`+`NX` for test‑*).

- **Per‑agent cursors / seats**:  
  - work: single fenced consumer via `XREADGROUP` (RB‑21).  
  - sig: no seat; each agent’s runner reads with `XREAD COUNT … BLOCK 0` using its own cursor id from the cursor key, advancing after processing. No wake.  
  - trace: no seat; any consumer may read with `XREAD` (firehose), but no wake guarantees.  
  - test‑*: single fenced consumer per namespace via `XREADGROUP`.

B. MIGRATION (strangler fig, no flag day)  
1. **Dual‑write**: Upgrade the send door (v2) to `XADD` **both** the legacy stream `bus:stream:{namespace}` and the new per‑lane stream, using the router table.  
2. **Cutover order** (consumers upgraded lane‑by‑lane):  
   a. **Work lane first** – the RB‑21 consumer and all wake‑listeners move to `...:work`. They stop reading the legacy stream. Dual‑write guarantees no hole, no double‑delivery (consumer sees only new lane).  
   b. **Sig lane** – all agent runners move to `...:sig`. They stop reading legacy.  
   c. **Trace lane** – any permanent trace sinks move to `...:trace`.  
   d. **Retire legacy** – after a bake period, stop dual‑writing (remove legacy `XADD`). Legacy stream can be deleted.  
3. **Rollback**: Any cutover lane can revert to reading the legacy stream while dual‑write is active, instantly rolling back.  
4. **RB‑25 acceptance** (per‑cutover storms):  
   - S2‑NEW (wake‑on‑trace impossible): trace lane has no wake, so no storm ever.  
   - S6 (HALT latency under trace flood): sig lane is a separate stream with its own maxlen; trace flood cannot fill it – head‑of‑line blocking eliminated.  
   - S7 (per‑flow seq / latch storm): per‑flow sequence is enforced at the work consumer; latch‑based causal edges are evaluated within the work lane—separate streams do not create new storms.

C. LATCH v1 (causal + ref)  
- **Latch index** (“one GET on the hot path”):  
  Key per latch: `bus:latch:{namespace}:{latch_id}` → JSON `{status: “pending”|“satisfied”|“expired”, gate, ttl_s, fail, from_lane, from_id}`.  
  When a consumer (work lane) reads a packet, it checks each causal‑latch by `GET`ting its latch key. If any gate is `pending`, it blocks until satisfied or expiry.

- **DAG cycle check at creation**:  
  **Causal‑latches are restricted to within the same flow** (per‑flow sequence is already defined). The `from_id` must belong to the same flow and have a sequence number **strictly less** than the new packet’s sequence number. Cycle check is trivial: verify same flow & `seq(from_id) < seq(new)` → DAG is a chain, impossible to cycle. (Cross‑flow causal barriers cut from v1.)

- **Latch‑expiry reuse of L4**:  
  At latch creation, register a deadline in the L4 expectations engine. On expiry:  
  - `fail: enforce` → latch status set to `“expired”` and the bus keeps the consumer **blocked loud** (raises alert, consumer halts processing).  
  - `fail: depend` → latch status set to `“expired‑satisfied”` and consumer **proceeds degraded** (logs degradation).  

- **Consumer behaviour when blocked**:  
  The work consumer uses `XREADGROUP` to fetch a packet. If a causal‑latch is `pending`, it enters a waiting loop:  
  - Subscribe to latch updates via `BLPOP` on a latch‑specific list or poll with `BLPOP` on a dedicated “latch‑ready” list, with a timeout equal to remaining `ttl_s`.  
  - On latch satisfaction (another writer updates the latch key and pushes a notification), it proceeds.  
  - On timeout, act on `fail` direction.  
  RB‑21 fenced seat ensures only one consumer processes, so the waiting loop does not disrupt other consumers.

- **Composition with RB‑21**:  
  The fenced consumer group guarantees exclusive processing; latch evaluation happens **after** `XREADGROUP` claim but **before** executing the work. Pending state does not prevent claiming the next packet—but the consumer must finish with the current one before moving on; it waits for the latch. This is safe with a single consumer.

D. NETWORKING PRIOR‑ART GRADE  
1. **DiffServ/DSCP (lanes as QoS)** – **ADAPT**: adopt the idea of classifying traffic into service classes (EF/AF/BE) with per‑hop behaviours; adapt to Redis stream keys + maxlen/overflow policies, skipping IP header bits.  
2. **QUIC multiplexed streams (HOL blocking)** – **ADOPT‑WHOLESALE**: the central rationale—separate streams prevent a stalled trace packet from delaying a sig packet. Implementation adapted to Redis per‑lane streams.  
3. **TCP state machine + TIME_WAIT (token lifecycle)** – **SKIP** for lanes; token lifecycle is T038’s domain; we note only that latch expiry reuses the same L4 temporal engine.  
4. **MTU/frag + checksum‑at‑door (T043)** – **ALREADY DONE**; we add the trace exemption (see E).  
5. **W3C Trace Context / OTel span+links (latch provenance)** – **ADOPT** for reference‑latch semantics: the `ref` latch type carries OTel link data directly, no encryption, no enforcement.  
6. **gRPC deadline propagation (L4 causal chains)** – **ADAPT**: the `ttl_s` in a causal‑latch propagates a deadline; L4 engine enforces it along the causal chain, adapting gRPC’s per‑hop timeout header.  
7. **SDN control/data‑plane split (sig = control plane)** – **ADAPT**: conceptually treat the `sig` lane as a high‑priority, out‑of‑band control channel; adapt to a separate Redis stream with its own `maxlen` and `REFUSE‑WRITE` overflow, guaranteeing that control traffic is never queued behind data plane floods.

E. TRACE EXEMPTION (T043 inheritance)  
- **Location**: The **send door** router, after determining the packet is bound for the `trace` lane, applies the integrity rule:  
  - By **default**, trace packets are emitted **without** `len+sha` (integrity field absent/null).  
  - For every 1000th trace packet (maintain a counter per process/namespace in Redis `bus:counter:{namespace}:trace:spot`), **attach** `len+sha` to enable spot‑checking.  
  The `packet_spec` already defines trace integrity as “dial‑optional”; the door enforces the optionality and the spot‑check frequency.

F. ROSTER DISCIPLINE + CUT LIST  
- **Roster cap**: 4 lane **types** confirmed: `work`, `sig`, `trace`, `test-*`. `test-*` may expand into multiple namespaces, but the type is fixed.  
- **Deletion ritual** for a lane:  
  1. Move all consumers off that lane (strangler fig migration to another lane or retirement).  
  2. Ensure no new packets are routed to that lane (remove mapping from router; unknown‑kind refusal activates).  
  3. Drain existing packets (consumers process or data expired).  
  4. Remove the lane’s stream key(s).  
  5. Update documentation and any global monitors.  
- **Explicit cuts from v1**:  
  - **Bundle‑latch** – deferred.  
  - **Cross‑flow enforcement latches** – causal latches are within‑flow only; cross‑flow coordination limited to reference latches (no enforcement).  
  - **Automatic latch generation** (e.g., auto‑latch between request‑reply) – deferred.  
  - **Lane ordering guaranteeing global total order** – lanes provide no ordering guarantees across lanes except by explicit latches.

G. RISKS / KILL‑CONDITIONS  
- **Misrouted halt to trace lane**: If a bug causes a `halt` kind packet to land in the trace ring buffer, it could be trimmed or lost, preventing shutdown.  
  *Guard*: The router is a pure function tested at compile time; integration tests verify admin kinds (`halt`, `interrupt`) are always mapped to `sig`. A runtime monitor samples packets in each lane and alarms if a packet’s kind doesn’t match the lane role. Additionally, the `sig` lane’s `REFUSE‑WRITE` ensures admin packets are rejected (loud) if they surpass capacity, rather than silently dropped.  
- **Latch‑expiry engine outage**: If L4 fails to fire, a causal‑latch blocks the work consumer indefinitely.  
  *Guard*: The consumer’s own timeout (based on `ttl_s`) fires regardless; on timeout it acts on `fail` (enforce→block and alert; depend→proceed degraded). This guarantees forward progress even if L4 is down.  
- **Dual‑write double delivery**: A consumer might read the same packet from both legacy and new streams.  
  *Guard*: Consumers are flagged v2 and explicitly bind to one stream; deployment orchestration ensures a consumer never reads from both sources for the same packet. Rollback is reversed by a flag, not by reading both.  
- **Per‑lane maxlen causing silent loss of work packets**: Work lane `REFUSE‑WRITE` means a full stream causes loud errors; no silent loss. Trace lane trims oldest, which is acceptable for its firehose nature; critical signals are never routed there.

