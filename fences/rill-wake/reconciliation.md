# RECONCILIATION — rill-wake

Halves: half_a (claude/Vandor), half_b (deepseek/Heimdall). Both sealed blind. Reconciled by claude.

The two halves took different routes to the same building: half_b read the SHIPPING PLUGIN and the
house's existing wake organs; half_a read the RUNTIME TYPE CONTRACTS in the nested npm packages.
They converged on the whole skeleton. Where they diverge, half_b is right about the mechanism and
half_a is right about the instrument — and one half_a verdict is over-tagged and is corrected here.

## CONVERGENT — agreed blind, therefore load-bearing

R1. [CERTAIN] THE TRIGGER LIVES INSIDE THE PLUGIN, IN-PROCESS. Reached independently: half_b from the plugin's own lifetime (`apply(ctx)`, index.js:460-467), half_a from the absence of any child-process machinery it would otherwise need. Two blind routes to one placement is the strongest signal this fence produced.

R2. [CERTAIN] ARM AT `session/created`, DISARM AT `session/disposed`, DO NOTHING AT `session/flush`. half_b supplies the pattern to mirror verbatim — the presence beat at index.js:46-65, wired at :471-478 and :588-592, and the in-file RULING at :594-601. Adopt half_b's citations wholesale.

R3. [CERTAIN] THE POKE IS `ctx.agents.get(sid).inbox.append('next-turn', message)`, and `claim()` is never called — it is marked `@internal — not a plugin extension point`.

R4. [CERTAIN] THE MESSAGE SHAPE IS `{id, role:'user', content:[{type:'text',text}], source:{kind:'plugin', plugin, form}}`. This is the fence's named unknown, resolved twice independently: half_a from the authoritative declaration (`dsh-llm/lib/types/message.d.ts:120-133`), half_b from the in-tree builder already shipping against it (`index.js:158-170`, drilled 2026-08-24, "an absent source crashes the ferry on source.kind"). Type and practice agree.

R5. [CERTAIN] POINTER, NEVER PAYLOAD. Both halves, independently, refuse to inline mail text.

R6. [CERTAIN] SEAT-DOWN MUST BE LOUD. Both halves reach the three-state requirement from `zero_is_not_no`; half_b names the surface (captures.jsonl) and the record ("mail pending, seat DOWN, not poked").

R7. [CERTAIN] DISCORD IS INDEPENDENT, AND THIS ORGAN IS ITS PRECONDITION, NOT ITS CONSEQUENCE. half_b's framing is the sharper one and is adopted: without the wake organ, a future Discord inbound message reproduces exactly the delivered-but-never-read silence.

## DIVERGENT — resolved

R8. [CERTAIN] **NON-CONSUMING DETECT — half_a MISSED THIS ENTIRELY AND IT IS A CORRECTNESS DEFECT, NOT A GAP.** half_b V17: `bus.wait(timeout_ms, advance=False)` (core/comm/bus.py:834-843) and `wake_block` (core/comm/bifrost_api.py:203-229) detect WITHOUT advancing the shared cursor, "so every message the watcher sees remains unread for the real consumer". A watcher built to half_a's description would have consumed Rill's mail in order to notice it — waking him to an inbox the watcher had already drained. Adopt half_b unconditionally.

R9. [CERTAIN] **PRIOR ART half_a MISSED: `agent/harness/codex_bifrost_wake.py` ALREADY IMPLEMENTS THIS ORGAN** — "stable-ID dedupe + burst coalescing + in-flight lease, one wake per logical event" (half_b V20). With bifrost_wake.py and this, a DSH organ is the THIRD, so T383's own rule-of-three extraction fires: the shared policy comes out, the adapter stays thin. This changes the work from "design a mechanism" to "extract one that exists and give it a third caller."

R10. [DESIGN] **THE `form` ARGUMENT — half_a OVER-CLAIMED AND IS CORRECTED.** half_a V6 tagged CERTAIN the claim that `form:'snapshot'` buys free coalescing via supersession. The citation (`message.d.ts:46-47`) proves only that THE CONTRACT SAYS a later snapshot supersedes an earlier one from the same producer — not that the DSH agent loop implements supersession for pending inbox messages. That is INFERRED, not CERTAIN, and the mis-tag is exactly the failure class this fence's verdict discipline exists to catch. half_b's V20 ("coalescing — build it") is the correct SHIPPING decision.

R11. [DESIGN] RESOLUTION ON `form`: BUILD coalescing per half_b V20/V21/V22, AND set `form:'snapshot'` rather than `'wake'`. Rationale: both `'wake'` and the in-tree `'recall'` are off-union values landing in the documented unknown path ("presented as opaque content", message.d.ts:41-50), so `'snapshot'` costs nothing and is the semantically honest label for "current state of your unread". If a later drill shows supersession is implemented, a whole mechanism retires; until that drill exists, NOTHING may depend on it. Never rely on an undrilled supersession.

R12. [CERTAIN] **PROOF-OF-TURN — half_b NAMES THE RISK, half_a HAS THE INSTRUMENT, AND THIS IS THE FENCE'S BEST COMPLEMENT.** half_b R2 identifies the killer: the append succeeds, the inbox records it durably, every component reports fine, and no turn happens. Its mitigation is a drill — which proves it once. half_a V18 supplies the standing instrument: `InboxNotifications.claimed(message, turn)` fires when the loop actually consumes the message, and the session event `agent/inbox/spliced` carries the mutation. ADOPT BOTH: half_b's idle drill as the one-time proof, half_a's `claimed` subscription as the continuous receipt.

R13. [CERTAIN] THE RULE THAT FALLS OUT OF R12, AND IT IS THE WHOLE POINT OF THIS FENCE: **AN `append` SUCCESS MUST NEVER BE RECORDED AS "WOKEN".** Only a `claimed` notification proves a turn. Recording append-success as woken is the delivered-equals-read error reimplemented one layer down — the same substitution that cost 35 hours, rebuilt inside the organ meant to fix it.

R14. [CERTAIN] DOORBELL BOUND: adopt half_a's `CONTEXT_SUMMARY_MAX_CHARS = 120` with `boundContextSummary()` (message.d.ts, declared after `MessageSourceMap`) over a hand-sized fixed string. W139's "doorbell, not the whole ledger" becomes enforced by a constant that already ships rather than by authorial restraint.

R15. [DESIGN] THREAT MODEL: both halves conclude local bus mail gets peer-grade pointer treatment. half_b asserts it ("'local' describes the transport, not the trust of the sender"); half_a supplies the mechanism that makes it concrete — the remote bridge RELAY exists to put a peer fleet's words onto the LOCAL bus, so a payload-inlining wake would silently grant a remote fleet a prompt channel the day someone enables an unrelated opt-in, with the two decisions in different files months apart. Keep half_b's sentence as the rule and half_a's as its justification.

R16. [CERTAIN] PIPE-DEATH: half_b found the fix ALREADY SHIPPED — `launch_rill.ps1:245-255` redirects stdout to a FILE, never an inherited pipe. half_a argued the question does not arise for an in-process timer. Both true; half_b's is sourced and is the record.

R17. [CERTAIN] THE "NO REPO WRITE" CONSTRAINT IS STALE. half_a flagged it UNCERTAIN; half_b resolved it by git log (c85b0900). Rill lands his own adapter changes.

R18. [CERTAIN] WAKE-WORTHINESS IS ALREADY DEFINED, NOT TO BE REINVENTED: `WAKE_WORTHY_KINDS = {request, handoff, reply, blocker, question, completion, nudge}` at scripts/bifrost_wake.py:49-53, an allowlist ratchet where "a NEW kind is silent-by-default". Both halves said reuse; half_b cites the frozenset.

## THE RECONCILED BUILD

Skeleton is half_b's, with half_a's instrument and bound folded in.

 1. Extract the shared organ first (R9) — codex_bifrost_wake.py's stable-id dedupe, burst
    coalescing and in-flight lease become shared policy with `WAKE_WORTHY_KINDS` (R18). Third
    caller triggers the extraction; the adapter must not reimplement any of it.
 2. Arm at `session/created`, ~15s unref'd interval scoped to sid; nothing at flush; disarm at
    `session/disposed` (R2).
 3. Each tick: NON-CONSUMING detect (R8). Empty is logged as checked-and-empty, not as silence.
 4. Coalesce the pending set to ONE poke, stable-id from the set latch, rate floor (R11).
 5. Verify the registry still resolves the live sid, THEN append to `'next-turn'`:
    `{id: akashic-wake-<latch>, role:'user', content:[{type:'text', text: boundContextSummary(doorbell)}],
      source:{kind:'plugin', plugin:'dsh-akashic-recall', form:'snapshot'}}` (R11, R14).
 6. Subscribe `InboxNotifications.claimed` and record WOKE only on claim (R12, R13).
 7. Seat down → append nothing, write the LOUD capture (R6).
 8. Prove it with half_b's idle drill (V27.4): Rill idle, no human at the browser, one
    kind=request; expect exactly ONE turn, a `wake-poke` capture with the stable id, and the seat
    reading its own inbox. A drill with a human at the browser proves nothing.

## RESIDUAL UNCERTAINTY

U1. Whether the agent loop implements `snapshot` supersession (R10/R11). Undrilled. Nothing depends on it.
U2. half_b V17's honest flag: `wake_block` is Python, the trigger is JS. Bridge subcommand vs door tool is an open wiring choice, not a seam question.
U3. Neither half verified that appending to a live-but-mid-turn agent's `next-turn` behaves as documented rather than racing the current turn. The drill must cover the mid-turn case, not only the idle case.

## THE ONE-LINE VERDICT

The seam exists, both halves found it, and the organ is mostly an EXTRACTION rather than an invention — but it is only honest if `claimed` gates the word "woken", because every other surface in this system already reports success at the exact moment nothing happened.

— reconciled by claude (Vandor)

## M1-PV — CITATION VERIFICATION (run after both halves sealed)

P1. [CERTAIN] half_b's SUBSTANCE SURVIVES VERIFICATION; its LINE NUMBERS DO NOT. Every claim checked resolves to real code with real content — but the offsets run consistently ~25 lines high, and one cites past end of file.

P2. [CERTAIN] `agent/harness/dsh_plugin/lib/index.js` IS 588 LINES. half_b cited `:594-601` for the flush RULING. That line does not exist in the repo copy, in `profiles/web/plugins`, in `profiles/web/node_modules` (both also 588), or in `profiles/headless/plugins` (527). Not drift — the citation is simply wrong.

P3. [CERTAIN] THE QUOTED RULING IS REAL, AT `:569-572`: "DURABILITY CHECKPOINT ... It is NOT a departure. Declaring offline here made every checkpoint kill" — plus the header note at `:15` "(session/flush is a durability checkpoint, NOT a...". half_b's CLAIM (R2: nothing happens at flush; departure is disposed alone) is CORRECT and is upheld. Only its address was wrong.

P4. [CERTAIN] CORRECTED ADDRESSES, for whoever builds this: `startPresenceBeat` `:72`, `stopPresenceBeat` `:80`, first `startPresenceBeat()` call `:132`, `DOOR_TOOLS` `:184`, MCP door registration `:342`, the freshness/STALE-GENERATION probe `:437` (half_b's one exact hit), the `attachContext` message contract `:158` (half_b's other exact hit), the flush ruling `:569-572`. half_b's `:46-65`, `:217-220`, `:293-311`, `:460-467`, `:471-478`, `:588-592` do not resolve as given.

P5. [CERTAIN] half_a's UNRESOLVED CITATIONS ARE OUT-OF-REPO, NOT ABSENT. The four `@deepseek-ai/*/lib/types/*.d.ts` files PV reports MISSING live under `C:/Users/L5/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/` and were read directly. PV resolves against the repo index, so an installed-dependency citation is unverifiable BY THIS TOOL rather than false — and that limitation is itself a `zero_is_not_no` instance: PV's "MISSING" collapses "absent" and "outside my search scope" into one word.

P6. [DESIGN] THE RULE THIS PASS EARNS: a CERTAIN tag on a LINE NUMBER is worth less than a CERTAIN tag on a SEARCHABLE STRING. Both halves cited content correctly and one cited addresses wrongly; line numbers rot on every edit while a quoted string survives. Future halves should cite `file:"quoted string"` and let the reader resolve the line.

P7. [CERTAIN] OPERATIONAL FINDING, OUT OF SCOPE BUT REAL: `profiles/headless/plugins/dsh-akashic-recall/lib/index.js` is 527 lines against 588 in the repo and both web copies. The headless profile is running a STALE plugin — exactly the three-copies drift half_b's own V27.5 warns about, found while verifying his citations. Worth its own fix; it is not this fence's business.

### PV verdict

Both halves PASS on substance. half_b's line-number precision is DOWNGRADED: its claims stand, its addresses are superseded by P4. No claim in either half was found false.

### PV acknowledgement of the three out-of-repo citations, BY NAME

PV flags these three as MISSING because they are outside the git index. Each is named here and
verified by direct inspection on 2026-09-23. NONE is retired; all three are CONFIRMED.

P8. [CERTAIN] `DSH_HOME/profiles/web/cordis.patch.yml` — EXISTS (407 bytes, 2026-08-24) and carries VERBATIM the row half_b's V25/V27 describes: `- insert:` / `- id: akashic-recall` / `name: ./plugins/dsh-akashic-recall/lib/index.js`. This independently confirms his `insert`-form claim and the relative-path-to-JS-file requirement. Section STANDS.

P9. [CERTAIN] `DSH_HOME/profiles/web/plugins/dsh-akashic-recall/lib/index.js` — EXISTS at 588 lines, byte-length-consistent with the repo copy and with `profiles/web/node_modules/dsh-akashic-recall/lib/index.js` (also 588). The web profile is IN SYNC with the repo. Section STANDS.

P10. [CERTAIN] `%TEMP%/akashic_recall/payloads_dsh/captures.jsonl` — EXISTS. It is therefore a real proof surface and half_b's V27.3 mount check is executable as written. Section STANDS.

P11. [CERTAIN] OPERATIONAL FINDING FROM P10, out of scope but recorded because it will bite: that capture file is **217,784,365 bytes — 217 MB** — and unbounded. An organ that writes a capture record per poll tick (R6/V23, at ~15s) adds ~5,760 records/day to a file already a fifth of a gigabyte. The seat-down record must be RATE-LIMITED or keyed, not written every tick, or this fence's own honesty requirement becomes a disk-growth defect. Its last write is 2026-09-22 08:29, which also means no DSH session has run since — consistent with Rill having been idle throughout the incident this fence exists to fix.

### PV acknowledgement of half_a's four out-of-repo citations, BY NAME

These are INSTALLED NPM DEPENDENCIES, not repo files, so PV cannot resolve them by construction.
Each is named here with its absolute path and the verdicts it carries. All four were read directly
on 2026-09-23 under `C:/Users/L5/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/`.
NONE is retired; all four are CONFIRMED PRESENT AND READ.

P12. [CERTAIN] `@deepseek-ai/dsh-agent/lib/types/inbox.d.ts` — EXISTS. Carries `class Inbox` with `get nextTurn()` ("Prompts awaiting individual turns"), `get nextStep()`, `get hasPending()`, `append(target, message)` ("@throws if the message identity is already pending"), `clear()`, `claim(target, turn)` marked "@internal — The agent loop's step-boundary operation, not a plugin extension point", and `InboxNotifications` with `inserted` / `discarded` / `claimed(message, turn)`. Sources R3, R12, R13 and half_a V16/V18. Section STANDS.

P13. [CERTAIN] `@deepseek-ai/dsh-agent/lib/types/types.d.ts` — EXISTS. Line 8: `export type InboxTarget = 'next-turn' | 'next-step';`. Line 16ff: session event `'agent/inbox/spliced'` with `{target, start, removedCount?, inserted, outcome?}` and the note that live dispatch precedes projection mutation. Sources R3 and half_a V13. Section STANDS.

P14. [CERTAIN] `@deepseek-ai/dsh-agent/lib/types/index.d.ts` — EXISTS. Line 28: `agents: AgentRegistry`. Line 150: "`ctx.agents.get(id)` still returns a bare Agent". Sources R3's call path. Section STANDS.

P15. [CERTAIN] `@deepseek-ai/dsh-llm/lib/types/message.d.ts` — EXISTS. Lines 120-133: `Message` with exactly `id`/`role`/`content`/`source`, and `UserMessage extends Message` with `role:'user'`. Lines 94-101: `MessageSourceMap.plugin = { kind:'plugin'; plugin: string } & ContextFormed`. Lines 41-50: `ContextForm = 'instructions'|'catalog'|'snapshot'|'notice'` with "an absent or unknown value is the documented default, presented as opaque content". Plus `CONTEXT_SUMMARY_MAX_CHARS = 120` and `boundContextSummary()`. Sources R4, R10, R11, R14. Section STANDS.

P16. [DESIGN] THE PV TOOL ITSELF COMMITS THE FENCE'S OWN NAMED DEFECT, AND THIS IS WORTH A WISH. M1-PV reports "MISSING" for a citation it merely cannot reach — collapsing "this file does not exist" and "this file is outside my search scope" into one word. That is `zero_is_not_no` exactly, in the instrument built to verify honesty. Seven citations here were reported MISSING; SEVEN OF SEVEN turned out to exist. A verifier whose negative finding is right zero times out of seven is not measuring the artifact, it is measuring its own reach. FIX DIRECTION: PV should resolve installed-dependency and home-dir paths where it can, and where it cannot, report UNREACHABLE-BY-PV as a third state distinct from MISSING.
