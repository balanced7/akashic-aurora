---
akashic_id: art_20260712_t038-identity-primitive-closure-amend-ag_c5b02c
akashic_sha: f5dc98def8d2
status: current
type: report
date: 2026-07-12
title: "T038 identity-primitive closure -- AMEND_AGAIN -> FENCE_READY (2026-07-12)"
gist: "Amends the T038 closure in research/reviewed/ultracode-coordination-arc-v3-2026-07-12.md (the ONE blocker to full-arc fence-ready). Author: "
tenant: solo
visibility: fleet
seats: []
category: [bus, coordination, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_ultracode-v3-coordination-arc-3-4-fence_5e64b7
    rel: cites
  - target: art_20260712_t038-identity-deepseek-counter-review-re_930307
    rel: cites
created: "2026-07-12T12:57:27"
updated: "2026-07-23T21:42:22"
---
<!-- GENERATED PROJECTION of art_20260712_t038-identity-primitive-closure-amend-ag_c5b02c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T038 identity-primitive closure -- AMEND_AGAIN -> FENCE_READY (2026-07-12)

Amends the T038 closure in research/reviewed/ultracode-coordination-arc-v3-2026-07-12.md
(the ONE blocker to full-arc fence-ready). Author: claude (Opus 4.8). Solo-authored;
adversarial source-verify appended below (the arc's proven countermeasure to false
seam-claims). Fold-and-fence with deepseek per standing rule -> brief FILE path is THIS
doc (T042: his handoff reader crashes; restate as file path in the bus message).

>> OUTCOME (2026-07-12, adversarial verify): this closure is REFUTED. It repeats the arc's
>> signature false seam-claim a FOURTH time -- it asserts the memoized `instance_token` is a
>> "STABLE, process-distinct" ownership key that "now EXISTS in source", but `instance_token`
>> is `agent:pid:uuid` and (a) memoization is only stable WITHIN ONE PROCESS. Akashic is
>> turn-based: each turn is a distinct OS process. arm() runs in the send turn-process
>> (agent_cli.py:2359 / ai_setup_mcp.py:369); sweep() runs in a LATER pull-floor turn-process
>> (bifrost_pull.py:159). Different pid -> different instance_token -> a work-token offer armed
>> under bifrost:expect:wt:<id_P1> is swept against <id_P2> and NEVER cleared/redriven/killed --
>> the precise v3 "idA/idB" hole, NOT cured. Same root breaks cross-turn intent self-re-declare
>> (a new turn reads its own prior intent as a foreign RED) and makes verify_still_held
>> false-negative the true holder across process boundaries. T038 STAYS AMEND. The (a)/(b)/(c)
>> record-shape edit is NOT the fix as written -- DO NOT BUILD IT. See "ADVERSARIAL VERIFY
>> RESULT" + "RE-CHARACTERIZED BLOCKER" at the foot of this doc. Routed to the deepseek fence.

Every seam claim below cites a line READ THIS SESSION from live source, not from a note or
an inline comment -- the recurring failure signature across v1/v2/v3 was a false claim about
what an upstream seam provides (v2: a false "safe no-op" comment; v3: a false "already
stored" claim). M3 grep-gate applied to all four seams: runner_lock.py, expectations.py,
intent.py, plus the write-site census.

---

## THE BLOCKER (source-confirmed this session)

The v3 T038 closure defined `instance_id = runner_lock.instance_token(agent)` and called it
"the per-process id T036 already stores on the seat record; NO new store." Both halves are
FALSE against source:

- `instance_token(agent)` (runner_lock.py:65-69) returns `f"{agent}:{os.getpid()}:{uuid.uuid4().hex[:12]}"`
  -- a fresh uuid4 is minted EVERY call. Non-deterministic, uncached. Two calls in one
  process return different values.
- The consumer-seat record is EXACTLY `{token, pid, ts, gen}` at all three write sites
  (runner_lock.py:90-91 acquire nx, :132-133 heartbeat vanished-branch nx, :146-147
  heartbeat own-token overwrite). No `instance_id` field.
- `holder(agent)` (runner_lock.py:229-238) returns the raw record verbatim (`json.loads(raw)`)
  -- so it returns no `instance_id`.
- `instance_token`'s only callers are the deepseek runner (bifrost_runner_deepseek.py:663)
  and a manual probe (tests/manual/l5_launch_singleton_probe.py:21). It is NOT on the
  consumer-seat path: `claim_consumer` (runner_lock.py:181) acquires with
  `holder_token = session_holder_token()` (= `session:{sid}`, :172-178), never instance_token.

Consequence (why T038 cannot fence without the fix): T038's `verify_still_held` and every
collision surface (expectations ownership, intent conflicts, proposals) key on a
PROCESS-DISTINCT, STABLE identity. The declared key is neither -- so under the defining
condition (three `claude` twins sharing AKASHIC_AGENT_ID and, in the env lane, the session
token; distinct pids) it degrades to token-only match = twin-eats reintroduced, OR a
per-call-mint mismatch = arm writes `<idA>` / sweep reads `<idB>` = redrive dead-loop + a
proposal that flags its OWN prior round as a foreign RED conflict.

---

## THE CORRECTED PRIMITIVE (a)(b)(c) -- a T036 record-shape edit

The identity must be (i) STABLE for the life of a process and (ii) PROCESS-DISTINCT under
twins that share the agent id and the env session token. `pid` is process-distinct and is
already on the seat; `pid + a birth-unique suffix` is additionally recycle-safe across time.
`instance_token`'s SHAPE (`agent:pid:uuid`) is already correct -- its only defect is that it
is re-minted per call. So:

(a) STABILIZE the mint. Memoize `instance_token(agent)` per process (module-level cache keyed
    by agent) so it returns a constant `agent:pid:uuid` for the process lifetime.
    - Backward-compatible: the two existing callers each call it ONCE and store the result
      (bifrost_runner_deepseek.py:663; the probe), so caching returns the identical value they
      already keep -- zero behavior change for runners.

(b) PERSIST it on the seat. Add `"instance_id": instance_token(agent)` to the JSON record at
    the three pid-write sites (runner_lock.py:90-91, :132-133, :146-147). The WRITER stamps
    its own (now stable) id -- same census as `pid`, co-written at exactly the pid sites.

(c) READ it. `holder()` already returns the raw dict (runner_lock.py:236), so `instance_id`
    rides for free once written; update its docstring (currently "{token, pid, ts}").
    `verify_still_held` compares the caller's OWN cached `instance_token(agent)` against
    `holder(agent).get("instance_id")`.

### Composition with T036 edit-5 (why the seat's instance_id is always the TRUE holder's)

edit-5 (v3 CLOSURE T036) pid-guards the heartbeat own-token branch AFTER the :137 token
check. Trace the three ways the seat's `instance_id` can be written, under twins sharing env
token `session:S`:

- acquire nx winner (:90): the first twin to claim writes its own id. Losers hit the
  re-entrant own-token branch (:96-104) which returns True WITHOUT rewriting the record --
  a re-entrant acquire never overwrites `instance_id`. (Confirmed: :100-102 only
  `_TENURE_GEN.setdefault` + return; no `c.set`.)
- heartbeat own-token (:146): reached only when :137 token matches. A non-holding twin B
  (held pid = A, distinct + live) stands down at edit-5 (`held != os.getpid() and
  _live_distinct_pid(held)` -> return False) and NEVER reaches the :146 write. Only the true
  holder A (held == getpid) refreshes and re-stamps its own id.
- heartbeat vanished-branch (:132, nx): writes only into an EMPTY slot (nx), so it cannot
  displace a live holder's id; whoever legitimately reclaims an expired seat stamps its own.

Under the DISTINCT-token regime (env != payload, Regime B) a twin's heartbeat returns at :137
BEFORE edit-5, so it never stamps either. In every regime the seat's `instance_id` is the
true cursor consumer's. Each twin knows its OWN stable id (cached), so `verify_still_held`
returns True for EXACTLY the true holder and False for every co-tenant -> twin-eats closed,
re-negotiate-livelock avoided. This is the process-distinct stable key T038 needs, and it now
EXISTS in source after the (a)/(b) edit -- not merely in a note.

---

## CORRECTED DOWNSTREAM KEYING (grounded in the real consumer seams)

(c-expectations) The current `sender` param is CONFLATED: it keys the ownership hash
(`_key(sender)` = `bifrost:expect:<sender>`, expectations.py:43-44/71) AND the inbox stream
(anchor `Bus(sender).tail()` :65; `_replies_since` -> `Bus(sender)` :96). Splitting naively
to `instance_id` everywhere would point the READ at an empty `Bus(instance_id)`. So split the
two roles explicitly:
  - OWNERSHIP hash key -> `instance_id`: thread `instance_id` into `arm`/`sweep` and key the
    hash `bifrost:expect:<instance_id>` (:44/:71), so twin B's `sweep(instance_B)` touches
    only its own deadlines.
  - INBOX read -> `agent`: the anchor capture (:65) and `_replies_since` (:90-98) keep reading
    `Bus(agent)` -- the shared inbox where replies actually land.
  - CLEAR only on exact linkage `answers:<offer_id>` (:128-133, the "1) exact linkage" pass).

(e-FIFO) Do NOT globally disable the FIFO fallback (:134-146) -- it serves EVERY RB-29 sender,
not just work-token; disabling it fleet-wide regresses unlinked-reply clearing. Scope the
disable to work-token offers only: mark work-token expectation records (a `wt: true` flag in
the arm record, or a dedicated `bifrost:expect:wt:<instance_id>` namespace) and skip the FIFO
pass (:134-146) for those records alone. Normal handoff expectations keep FIFO fallback intact.

(d-intent) Two surfaces, both currently agent-keyed, both must re-key on `instance_id`:
  - `conflicts()` filters `i.get("agent") != agent` (intent.py:88). Under twins both
    `agent='claude'`, a sibling twin's intent is filtered as re-entrant-self (GREEN) -- it
    HIDES a real twin conflict. Carry `instance_id` in the intent record (declare(), :105-106)
    and filter `i.get("instance_id") != mine` so a sibling shows RED; a self re-declare stays
    green.
  - proposals: key `PROPOSAL_NS:{round}:{instance_id}` (currently `:{agent}`, intent.py:142)
    with `instance_id` in the payload (:143-147), and group `_scope_conflicts` by
    `instance_id` (:210-222) so a twin's own prior proposal is not flagged as its own foreign
    conflict.
  - `covers()` (intent.py:242-251) STAYS agent-keyed: it is a self-query ("did I declare
    intent over this path"), not a collision surface. No change.

Note: (c-expectations)/(d-intent)/(e-FIFO) are BUILD changes to consumer APIs and are
engine-first-gated (design-only until T029 closes). They become mechanically correct once the
key they thread is the STABLE, process-distinct `instance_id` from (a)/(b) -- the v3 critique
of them ("arm writes idA / sweep reads idB", "flags its own proposal RED") was a symptom of
the INSTABILITY, and is cured at the root by (a).

---

## (b-generation) CARRIED FORWARD UNCHANGED (judged sound in v3)

The per-scope high-watermark fencing is unaffected by the identity fix and is retained
verbatim from v3 CLOSURE T038 (b)/(e): keep the SINGLE agent-keyed mint `GEN_PREFIX+agent`
INCR (runner_lock.py:89, grep-confirmed the ONLY `c.incr` in the tree) as the monotone source;
derive a STORE-only per-scope register `bifrost:worktoken:gen:<scope>` (never a second INCR,
never DEL) that records the highest agent-gen to win `<scope>`; apply the STALE_GENERATION
idiom (bus.py:471) via CAS on that key so only the winner writes tokens.json. TTL ==
SESSION_CONSUMER_TTL, refreshed on each winning transition.

---

## NO-RELOCATION (write-site census, source-grounded)

The v2/v3 relocation signature: a correct fix at site A leaves an equivalent unguarded
twin-site B that an unconditional caller walks. This fix adds ONE new field (`instance_id`)
whose write-sites are, by construction, EXACTLY the three pid-write sites (it is co-written
inside the same `json.dumps({...})` as `pid` at :90-91, :132-133, :146-147). I enumerated
every `c.set(_key(agent), ...)` in runner_lock.py: those three plus none other;
release()/clear_if_pid() only DELETE (:161, :220). So `instance_id` inherits pid's COMPLETE
guard set the moment the T036 edit-1+edit-5 land -- there is no fourth writer for the hole to
jump to. A non-holding twin cannot stamp its `instance_id` for the identical reason it cannot
migrate `pid`. The (a) memoization introduces NO write-site (it is a derive/cache). holder()'s
read path is unchanged. The generation authority remains provably one INCR site; the per-scope
watermark is a derived checkpoint, not a second counter.

---

## M3 PINS (updated; the identity-dependent ones re-keyed on grounded instance_id)

Carried from v3 unchanged: test_gen_from_agent_counter_scope_partitioned,
test_tokens_json_cas_fence, test_no_gen_key_ever_deleted, test_held_revalidated_at_act_boundary,
test_solo_fastpath_under_invisible_twins_drill.

New/amended (RED today; GREEN when the closure is reverted):
- tests/test_runner_lock_instance_id.py::test_instance_token_stable_within_process --
  two calls to instance_token(agent) in one process return the SAME value. RED today
  (per-call uuid4). Pins (a).
- tests/test_runner_lock_instance_id.py::test_seat_record_carries_writer_instance_id --
  after claim_consumer, holder(agent) has instance_id == the claiming process's
  instance_token(agent). RED today (record is {token,pid,ts,gen}). Pins (b)/(c).
- tests/test_runner_lock_instance_id.py::test_twin_heartbeat_does_not_restamp_instance_id --
  seed seat = {token:'session:S', pid:<live OTHER>, instance_id:<A>}; refresh_consumer from
  THIS process (distinct live pid). Assert seat.instance_id UNCHANGED == A (edit-5 stands the
  twin down before the :146 write). Composition pin for edit-5 x instance_id.
- tests/test_work_token.py::test_verify_still_held_distinguishes_twins -- two instances of
  'claude', distinct pids, seat.instance_id == A's. verify_still_held True for A, False for B.
- test_expectations_owned_per_instance_read_shared_inbox (amended): arm/sweep key
  bifrost:expect:<instance_id> but _replies_since reads Bus(agent); twin B's sweep clears only
  B's offers; FIFO fallback does NOT fire for work-token records on the shared stream.
- test_intent_conflict_across_instances_is_red (amended): two 'claude' instances, distinct
  instance_id, intersecting intent+proposal scope -> conflicts()/_round_state RED, not
  re-entrant-self green.

---

## VERDICT (superseded -- see ADVERSARIAL VERIFY RESULT below)

The body above ATTEMPTED to close T038 by making instance_token stable and stamping it on the
seat. The adversarial verify refuted it. What genuinely holds from the attempt (verify PASS,
salvageable for the real fix): the write-side composition -- items (a) memoization is
backward-compatible for the two existing callers; the seat write-site census IS exactly 3
(runner_lock.py:90/132/146) so instance_id inherits pid's complete guard set with NO relocation;
edit-5 genuinely prevents a LIVE co-tenant twin from restamping the seat. Those are sound. What
does NOT hold: the claim that the stamped id is a valid OWNERSHIP key for (c)/(d)/(e)/(f).

## ADVERSARIAL VERIFY RESULT: AMEND (closure refuted)

Verifier read runner_lock.py, expectations.py, intent.py, plus the arm/sweep call-sites,
independently. Verdict: AMEND -- one load-bearing false claim.

THE FALSE CLAIM: "they become mechanically correct once the key they thread is the STABLE,
process-distinct instance_id ... cured at the root by (a)" and "the identity every subclause
keys on now EXISTS in source." Source contradicts "stable": instance_token = agent:pid:uuid
(runner_lock.py:69); memoization (a) is a per-PROCESS in-memory cache. The system runs one
process PER TURN. Confirmed cross-process split:
- arm() is called on the SEND path (agent_cli.py:2359, ai_setup_mcp.py:369).
- sweep() is called on the PULL-FLOOR path (bifrost_pull.py:159, in collect_boot_bifrost) -- a
  different, later turn-process.
Different pid => different instance_token. So an offer armed under bifrost:expect:wt:<id_P1> is
swept against <id_P2> and is never cleared, redriven, or declared dead. This is the v3 "idA/idB"
critique verbatim -- (a) only equalizes calls WITHIN one process, so it does not touch it.
Corollaries: intent self-re-declare across turns reads its own prior-turn record as a foreign
RED conflict; verify_still_held compares the caller's LIVE instance_token against a seat id
stamped by a DIFFERENT turn-process, so it false-negatives the true holder across turns (fails
safe -> re-negotiate, never co-consume, but the fence does not hold).

Arc signature, 4th instance: a "cured / no-relocation" argument resting on an unverified
property of an upstream primitive (instance_token is a stable ownership key), contradicted by
the primitive's actual shape (per-process pid) and the system's turn-process model.

## RE-CHARACTERIZED BLOCKER (sharper than v3)

T038 needs ONE identity with BOTH properties at once:
  (i)  TWIN-DISTINCT under the fracture -- separates the three 'claude' co-tenants.
  (ii) TURN-STABLE -- the same value across all of a twin's short-lived turn-processes
       (arm-turn, sweep-turn, act-turn), so ownership survives the process boundary.
The two primitives in source each have exactly ONE:
  - instance_token (agent:pid:uuid, runner_lock.py:69): (i) yes, (ii) NO (pid changes per turn).
  - session_holder_token (session:{env sid}, runner_lock.py:172-178): (ii) yes, (i) NO -- twins
    share the env token; that shared token IS the defining fracture.
So the primitive T038 keys on does not exist in source today. That -- not "add a field" -- is
the blocker. (Note the split of concerns this exposes: T036 seat-integrity needs a LIVE-distinct
process test, for which pid is exactly right, edit-5 uses it correctly; T038 durable ownership
needs a TURN-STABLE distinct identity, a different requirement pid cannot satisfy. The v3 closure
conflated the two by reusing the seat's pid-identity for durable ownership.)

## CANDIDATE DIRECTION (UNVERIFIED -- for the fence, do NOT treat as settled)

Leading candidate: key ownership on the REAL per-session id (the payload session id distinct per
conversational session, which is turn-stable because the harness exports one session's id to all
its turn-processes), PERSISTED into the durable per-offer / per-intent / per-token record at arm
time and REPLAYED to sweep / re-declare / verify_still_held -- decoupling the ownership key from
the live pid. This explicitly makes ownership-identity and seat-holder-identity two DIFFERENT
things (verify's minimal-correction option 1), which is the correct model: the seat holder is
"who is live on the cursor NOW" (pid), the token owner is "which session negotiated this slice"
(session id).
BEFORE the fence trusts this, grep-gate the two load-bearing assumptions (the arc's own M3 rule):
  1. Is a real, per-conversational-session id AVAILABLE and turn-stable in the arm-context
     (agent_cli/MCP door) AND the sweep-context (bifrost_pull) AND the act boundary? Source-check
     what session id each of those contexts can read, and whether it is the payload id or the
     shared env token. If they can only read session_holder_token()'s env value, this candidate
     inherits the fracture and FAILS -- do not adopt it without confirming a distinct id is
     reachable there.
  2. Are the three twins T038 must separate genuinely distinct on THAT id? (Real separate
     sessions: yes. Sidecar/T035 same-token co-tenants: they share it -- but those are
     non-conversational and are a T036 seat-integrity concern, not a T038 work-negotiator; confirm
     T038's actors are only real sessions.)
Second candidate (verify's option 2): mint a genuinely turn-stable twin-distinct id and persist it
on first claim (e.g. a per-session uuid written to a durable session-scoped key, re-read not
re-minted). Heavier; only if candidate 1's session id is not reachable in all three contexts.

## GREP-GATE RESULT (2026-07-12, source-grounded -- ran the gate the candidate demanded)

Ran grep-gate #1 (is a distinct, turn-stable session id reachable in arm/sweep/act?). Findings,
each cited:
- There are TWO session-id sources, and they are NOT the same value:
  (P) PAYLOAD id -- the real per-session id, delivered on the stop-hook stdin
      (claude_stop.py:189 reads sys.stdin JSON; :194 session_id = payload.get("session_id");
      :200 refresh_consumer(AGENT, f"session:{session_id}")). Reachable ONLY in the stop hook.
  (E) ENV id -- session_holder_token() reads CLAUDE_CODE_SESSION_ID / CLAUDE_SESSION_ID from the
      process env (runner_lock.py:172-178). This is what the boot/pull/consume path keys on
      (bifrost_pull.py:77 _session_holder_token(); :112 claim_consumer(agent_id, that)).
- The expectations SWEEP is currently AGENT-keyed, not session-keyed: bifrost_pull.py:158-159
  `sweep(agent_id)`. (So today it does not even distinguish sessions; T038 would add that.)
- CONSEQUENCE: at arm (door/send) time and sweep (boot/bifrost-sync) time there is NO stdin
  payload, so only (E) the ENV id is reachable; (P) the real payload id is stop-hook-only.
- EMPIRICAL: in THIS live session, $env:CLAUDE_CODE_SESSION_ID == the real session id
  (b4e2a256-...), i.e. the harness exports a session's own distinct id into its process env.
  So (E) is turn-stable AND distinct FOR A GENUINE SESSION; it is shared only in the sidecar /
  T035 re-entrancy case (a subprocess under another session's env). bifrost_pull.py:72-75 states
  this design assumption in a comment ("each live session carries the env var, so the twin
  incident class is covered") -- optimistic, since the sidecar case violates it, but that case
  is a non-consumer.

SHARPENED LEADING CANDIDATE (supersedes the persist-replay sketch above; still UNVERIFIED, for
the fence): key T038 ownership/conflict/verify_still_held on session_holder_token() (the ENV
session id) -- NO new primitive, NO persist-replay. It is turn-stable, reachable in arm/sweep/act
(all inherit env), and distinct for T038's ACTUAL actors (real work-negotiating sessions).
Scope-out: the env-token SHARING that defines the fracture is the sidecar/T035 co-tenant, which
sends no offers and negotiates no work -- it is a T036 seat-integrity concern (edit-5 pid-guard
already stands it down), NOT a T038 actor. Under this scoping the verify's "neither primitive has
both properties" dissolves for T038: it conflated the sidecar-sharing (T036) with T038's actors.
THE ONE REMAINING GREP-GATE for the fence to kill or confirm: can two DISTINCT real
work-negotiating sessions ever share a CLAUDE_CODE_SESSION_ID (making (E) non-distinct for a real
T038 actor)? If yes anywhere, fall back to the mint-and-persist token. If provably no, (E) is the
whole fix. This is a harness-behavior question -- confirm empirically, do not assume.

## RESOLUTION (gate resolved 2026-07-12 -- pending deepseek counter-review)

The load-bearing gate is resolved (claude-code-guide over the official Claude Code docs --
hooks.md, sessions.md, headless.md):
- env CLAUDE_CODE_SESSION_ID and the hook-payload session_id are the SAME value (documented).
  So the incident's "env != payload" fracture is NOT a general divergence -- it is the SIDECAR
  anomaly (a subprocess carrying a DIFFERENT session's env id), i.e. T035 re-entrancy.
- subprocesses inherit CLAUDE_CODE_SESSION_ID (documented); stable across a session's turns
  (~90%, uncontradicted -- hooks receive it every turn).
- distinct across concurrent sessions: by design (a UUID per session; transcript storage +
  --resume would collide otherwise), ~95%, not a FORMAL documented guarantee.
- stability across /clear and /compact: UNDOCUMENTED (~70%) -- the one soft spot.

THE RESOLUTION: T038 keys (c)/(d)/(f) on session_holder_token() ( = "session:{CLAUDE_CODE_SESSION_ID}",
runner_lock.py:172-178) -- the SESSION id. It is turn-stable (env inheritance) and distinct for
T038's ACTUAL actors (real work-negotiating sessions). It is the value the consumer seat ALREADY
carries as its `token` field (written at runner_lock.py:90/132/146), so NO record-shape change is
needed -- the identity T038 needs already exists on the durable record. The v3 error was a SCOPING
mistake: it assumed the session token is shared under twins and therefore not distinct, but that
sharing is the SIDECAR case (a non-consumer, handled by T036 edit-5's pid-guard), NOT a T038
work-negotiator. This closes the turn-instability hole directly: instance_token (pid) differed
between the arm-turn and the sweep-turn; session_holder_token() is the SAME env-inherited value
across both, so an offer armed under it is swept under the same key and clears.

Keying, resolved:
- (f) verify_still_held: caller's session_holder_token() == holder(agent).get("token"). No new
  field; compares against the seat's EXISTING token.
- (c) expectations: OWNERSHIP key = session_holder_token(); INBOX read stays Bus(agent)
  (expectations.py:90-98); arm and sweep both derive the key from env -> identical across turns.
  FIFO-disable scoped to work-token records (e), unchanged.
- (d) intent: key/conflicts on session_holder_token() instead of agent (intent.py:50/88/142) so
  two real sessions go RED, while same-session re-declare (ANY turn) stays re-entrant green.
- (b) generation watermark: carried from v3 unchanged. NO instance_id, NO persist-replay, NO new
  INCR, NO new write-site (token is already written at the 3 seat sites) -> no relocation.
- instance_token / pid stays UNTOUCHED, serving the runner-lock's own LIVE-distinctness test (a
  different requirement, correctly pid-based). The two identities are now cleanly separated:
  seat-holder-liveness = pid (T036), work-ownership = session id (T038).

RESIDUAL RISKS (documented harness caveats, all FAIL-SAFE -- for the counter-review to weigh):
1. Concurrent distinctness is by-design ~95%, not a formal guarantee. Even a (practically nil)
   UUID collision degrades safely: the seat is single-holder (one session wins acquire), so only
   one holds the lease at a time regardless of the key.
2. /clear-/compact session-id stability undocumented (~70%). If the id shifted mid-session, the
   owner's verify_still_held would false-negative its OWN held token -> forced re-negotiate.
   Fail-safe (never co-consume), rare, self-correcting on the next claim.
3. A sidecar co-tenant shares the token but is not a T038 actor (sends no offers); T036 edit-5
   keeps its pid off the seat, so holder() reflects the true session.

## COUNTER-REVIEW RECONCILED -- FENCE COMPLETE (2026-07-12)

deepseek's adversarial counter-review (research/reviewed/deepseek-t038-identity-2026-07-12.md,
181 lines) AFFIRMS the resolution. Fence mode = COUNTER-REVIEW (not blind-dual: his runner was
wedged at first dispatch, so he reviewed my resolution rather than designing blind) -- but the
review is substantive, not a rubber-stamp: he re-derived every source fact independently (cited
runner_lock.py:90/132/146/181/229-238, expectations.py:43/90-98/128-146, intent.py:83-88/210-222),
attacked all six assertions + all three residual risks, and gave EMPIRICAL twin-distinctness
evidence -- the live concurrency trial shows session e59d8882 (Opus twin) and 46bf68d6 (Fable seat)
carry DISTINCT session ids while sharing agent id 'claude'. Blind convergence: he reached the same
seat-token=session_holder_token identity + the same sidecar scoping from source, not from my prose.

His verdict: all 6 assertions HOLD; no-relocation confirmed (3 seat write-sites, no 4th); Risk 1
(UUID collision) FAIL-SAFE via the seat's single-holder acquire-nx backstop; Risk 2 (/compact id
change) FAIL-SAFE (work lives in the git branch + C2 locks; cost = a spurious re-negotiation round);
Risk 3 (sidecar impersonation) THEORETICAL only -- a sidecar doesn't negotiate, and if a future one
did, the fix is the T035/T036 re-entrancy check, NOT the T038 identity.

ACCEPTED AMENDMENT: Risk 2 confidence 70% -> ~90%. His argument (sound): a session-id change across
/compact would also break transcript storage, --resume, and the stop-hook payload session_id -- all
more load-bearing than T038 -- so the harness has strong incentive to keep it stable; the 70% was a
DOCUMENTATION gap, not evidence of mechanical instability.

FOLDED INTO THE BUILD SLICE (engine-first: builds after T029; the slice cites this doc):
- (A) claim_consumer asserts token.startswith("session:") -- a non-session token on the consumer
  path is a bug (catches a runner instance_token accidentally landing on the seat).
- (B) runner_lock.py module docstring states the two-identity split explicitly: seat-holder
  liveness = pid (T036, LIVE-distinctness); work-ownership = session token (T038, TURN-STABLE
  distinctness); DO NOT conflate. Comprehensibility guard against a v4 recurrence.
- (C) EMPIRICAL /compact probe BEFORE build: arm a test expectation via CLI -> trigger /compact ->
  sweep; does the session id survive? If yes, lift Risk 2 to ~95%. If no, fall back to the
  mint-and-persist candidate (a durable session-scoped uuid written on first claim, re-read not
  re-minted). This is the M3 empirical gate for the one soft spot.

## STATUS

T038 = FENCE COMPLETE (design). Identity = session_holder_token() (the session id the seat already
carries as `token`) -- NOT a new primitive, zero new write-sites, zero new fields. Coordination arc
T036-T039 = 4/4 FENCE-READY (T036/T037/T039 per v3; T038 closed + counter-review-affirmed here).
Engine-first: BUILD still gated on T029 closing; the build slice folds A/B/C and cites this doc +
deepseek's counter-review. Convergence, monotone across FOUR adversarial rounds + the harness gate +
the counter-review: structural defect -> single named defect -> exact missing primitive -> the
primitive ALREADY EXISTS as the seat's session token (v3 mis-scoped the fracture as shared-under-
twins, true only for the sidecar) -> affirmed against source by an independent adversarial reviewer.
Both residual risks documented + fail-safe; the one soft spot (Risk 2) has an empirical pre-build
gate (C).
