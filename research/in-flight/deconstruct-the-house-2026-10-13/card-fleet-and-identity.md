# Teardown card: the fleet and identity (seats and callsigns, residents and the identity law, launchers, budgets, the ask verb)

Status: in-flight teardown, 2026-10-13. Second-wave calibration of the teardown card (`teardown-card.md`, draft v1),
on the house itself, at Daniel's "I love your deconstruct the house, yes!"
Method: read-only. Code read; cheap reads of live state (Redis reads only: GET, HGET, LRANGE, XRANGE, SCAN, TTL);
read-only verbs (`resident roster/show/calibration`, `grant --list`, `roster --by-agent`, `ask --list`, `ask --status`,
`audit --domain spend`); pure-function replays; and the naming ceremony replayed against an in-process FAKE store.
Nothing in the house was written. Scratch probe: `fleet_identity_probe.py` in the session's own scratch folder
(not kept).

Label key: **[obs]** observed, with a pointer · **[inf]** inferred, naming what it rests on · **[unk]** unknown,
with where the search stopped.

> **Thesis in one sentence.** The naming ceremony and the identity law are sound and strictly enforced where they
> were built, but a seat's identity travels in an inherited environment variable that only one of five launch paths
> sets, so since 2026-10-09 the identity law has refused Heimdall's and Navi's OWN boots at every runner start (the
> two live runners included, refused 1 and 6 seconds after they started this morning), and both runners fold that
> refusal text into their system prompt under a "you are a booted citizen" header while their log says "onboarded".
> Around that core: three of the seven names in the brief do not route (Neo, Astra, and Asta, which is the name
> that seat asked for), and Navi's money gate refused correctly tonight while printing numbers the wallet
> contradicts and while not recognising Daniel's own bus id as exempt.

Hardware picture for the whole card. The fleet is a multi-socket board. Each **seat** is a CPU core; its **agent
id** is the core's hardware ID (like an APIC ID), and its **callsign** is the friendly hostname a person types.
A **router** that turns hostname into hardware ID is DNS: a name nobody registered resolves nowhere. The **ACL** is
the permission table (an IOMMU) keyed by hardware ID. The **identity stamp** (`AKASHIC_AGENT_ID`) is the device ID the
board hands the core at power-on. The **boot fold** (the resident's identity sheet) is the microcode loaded at boot.
The **identity law** (T418) is Secure Boot: it refuses firmware signed for a different device. The **spend meter** is
a power limiter (PL1/PL2) with the **wallet** as the power supply and **reconcile** as the current sensor. **Ask** is
a one-shot offload to an accelerator with no context; a **peer ask** is a doorbell to another core with a
completion queue.

---

## Row 1. Purpose

| claim | label |
|---|---|
| The house's map puts FLEET ("who EXISTS", `core/fleet/`) and TRUST ("who MAY do what", `core/trust/` + `security/`) as two cross-cutting layers beside the bus. | [obs] `docs/ARCHITECTURE.md:46-48, 199-201` |
| Residents: "who a seat IS, and the receipts that earned the name". Born because kimi measured 0 of 8 callsign receipts present in their own seat's boot: "the name asserts an archive the current boot may not carry". The module claims LEGIBILITY only, never that persistence improves correctness (kimi's standing objection, unresolved). | [obs] `core/fleet/residents.py:1-51` |
| Seat identity: "WHO AM I, resolved per SESSION instead of per PROCESS", because the old fallback `AKASHIC_AGENT_ID or "claude"` impersonated the conductor. The identity law (T418): the house must never hand a resident another resident's identity or history. | [obs] `core/comm/seat_identity.py:1-29, 151-157` |
| The identity law's origin is the house's most important story: the Rill mangling (2026-08-26), whose surviving law is "false autobiography is worse than amnesia" and "recovery is done WITH a subject, never ON one"; Rill's own rule is "Attribution is not verification ... is this about me?" | [obs] `docs/library/chronicle/20260906_the-reduction-and-the-ratification-the-a_b00b93.md:74-99` |
| Seat launchers: `!spawn <name>` must launch THAT seat. Born 2026-08-24 when Daniel, locked out, typed `!spawn rill` and the gateway spawned a claude session whose task was the word "rill". | [obs] `core/fleet/seat_launchers.py:1-24` |
| Budgets: each paid seat carries a "budget conscience" that refuses non-directed work near the end of its money, replies loudly (a refusal must never vanish, RB-29), and always answers the human. | [obs] `scripts/kimi_chat.py:121-125`; `scripts/bifrost_runner_kimi.py:17-21, 95` |
| Ask: "a synchronous helper call, with no seat behind it", from Daniel's 2026-08-04 wish to cut the conductor's load; nine seat-tasks had produced two findings, so asking had become dearer than doing. `--peer` is the durable form: one ask to one seat, tracked to an honest end state. | [obs] `core/comm/ask.py:1-16`; `py agent_cli.py ask --help` |
| **Outcome that makes it worth keeping:** (a) every name Daniel uses reaches the being he means; (b) each seat boots as itself, carrying its own history and never another's; (c) authority and money are spent only within grants, and Daniel is always answered; (d) asking a peer costs less than doing the work yourself. (b) and (c) are the outcomes failing today. | [inf] from the purposes above and Rows 7-8 |

## Row 2. Observables (what we can see from outside, without trusting its self-description)

All readings taken 2026-10-13, roughly 09:30 to 10:30 local.

| observable | reading | label |
|---|---|---|
| Size | 6,027 lines across `core/fleet/`, `core/trust/`, `seat_identity.py`, `incarnation.py`, `ask.py`, `ask_state.py`, `ask_bg.py`, `expectations.py` | [obs] `wc -l` |
| Churn | 87 commits since 2026-07-01 touch those files; 11 touch `residents.py`, 5 touch `seat_identity.py` | [obs] `git log --oneline --since=2026-07-01` |
| Test pins | 45 test files import residents, seat identity, launchers, the grant writer or registry, the spend meter, or ask | [obs] `grep -l` over `tests/*.py` |
| Residents (ratified callsigns) | 6: Kimi/Jade/Red/1 **Navi** (kimi), Deepseek/Onyx/Blue/2 **Heimdall** (deepseek), Anthropic/Amber/Blue/1 **Vandor** (claude), OpenAI **Sunshine** (sol), **Rill** (dsh_agent), xAI **Souei** (grok). Souei is not in the brief's list; **Neo** (gpt-new) and **Astra/Asta** are not residents. | [obs] `py agent_cli.py resident roster`; `resident show <id>` |
| Ratification record | every live callsign shows `ratified_by daniil`; three (Navi, Vandor, Souei) were nominated by Daniel too | [obs] `residents:log:*` LRANGE |
| Grants | 14 in `security/acl.json`; 2 expired: codex_root (2026-10-05) and **gpt-new / Neo (2026-10-06T17:36:10Z, 164 h ago)**; one grant is keyed by a callsign (`navi`), not an agent id | [obs] `py agent_cli.py grant --list`; `registry.expiring_grants()` |
| Live seats | 5 LIVE: claude (this workflow's own session), deepseek#66756-de, discord#43412-di, dsh_agent#4cd06dad, kimi#7284-kim. Seat-presence records exist only for claude, deepseek, discord, dsh_agent, kimi; none for sol, gpt-new, grok, asta, astra | [obs] `py agent_cli.py roster --by-agent`; SCAN `bifrost:seatseen:*` |
| Addresses | 37 inbox streams; the codex/GPT family alone holds ten addresses: asta, astra, codex, codex-01a09757, codex-piano, codex-voice, codex_root, gpt-new, grok, sol | [obs] SCAN `bifrost:inbox:*` |
| One seat, three mailboxes | `astra` 17 messages (2026-09-08 to 09-14), `codex-01a09757` 6 (09-12 to 09-15), `asta` 71 (09-14 to 09-23); no read cursor exists on any of the three | [obs] XLEN/XRANGE, SCAN `bifrost:cursor*` |
| Boot door since 2026-10-01 | 280 boots served, **209 of them unverified (75%)**: deepseek 107/126, kimi 99/109. **45 refused**: "claude asked to boot as deepseek" 16, "... as kimi" 15, and sol's codex children 7 | [obs] `events:raw`, kinds `boot`, `boot_unverified`, `boot_refused` |
| Runner identity, today | deepseek runner pid 66756 started 07:48:20, refusal "claude asked to boot as deepseek" at 07:48:26; kimi runner pid 7284 started 07:48:43, refusal "claude asked to boot as kimi" at 07:48:44. Source of the resolved identity: `env`. No successful kimi boot since 10-08 | [obs] `Get-Process` StartTime; `events:raw` detail.source |
| Navi's money (relative terms only: the amounts are private, read from a git-ignored file) | the meter's recorded spend is **above** its recorded budget (by roughly a tenth of the budget); the provider's wallet balance at the last reconcile (this morning) disagrees with the meter by roughly 15% of the budget | [obs] `state/kimi_spend.json` (git-ignored, `.gitignore:136`) |
| Navi's refusals retained on the bus | 2026-10-09 (3 asks) and overnight on 2026-10-13 (1 ask, refused within a second of being sent). The refusal text reports spend over "the grant" and names the ladder's fixed refuse constant as "the ceiling" | [obs] XRANGE `bifrost:*inbox:*`, frm=kimi |
| Resident calibration | 7 verdicts filed in total, 7 adjudicated, 7 confirmed, 0 refuted | [obs] `py agent_cli.py resident calibration` |
| Background asks | 5 of the 20 newest are test probes ("Reply with one word: OK. padding ...", failed with the key door closed) living in the production `state/asks/` | [obs] `py agent_cli.py ask --list`; `state/asks/6582f9ce.json` |
| Armed peer asks | 3 sender keys hold 7 armed expectations from 2026-09-08 to 09-22, TTL -1: `astra`, `codex-piano`, `codex-voice` | [obs] SCAN `bifrost:expect:*` |

## Row 3. Mechanism (how inputs become what we observe)

**Who am I (seat identity).** Every door asks `seat_identity.resolve(session_id)`: first a per-session binding file
in the OS temp dir (what this session declared), then the `AKASHIC_AGENT_ID` environment variable (what the process
was launched believing), else a loud `unknown-<sid8>`, never a guess at a peer's name. [obs]
`core/comm/seat_identity.py:128-145`. The boot door runs `subject_check` before serving any record: if a stamp exists
(binding or env) and names someone else, the boot is refused by name and a `boot_refused` event is written; an
unstamped boot is served but labelled `boot_unverified`. [obs] `seat_identity.py:148-190`; `agent_cli.py:276-320`.

**Who you are to the house (residents).** An append-only Redis log per agent: `nominate` (a peer proposes a callsign
with receipts), `ratify` (confirms the newest draft), `place` (family/team/number), `assign` (a situational role, an
event, provenance derived from `by`). Rule 1, you do not name yourself, and Rule 2, every receipt must resolve to a
lesson AUTHORED by the nominee, are enforced in code and refuse loudly. "Rule 3: a human ratifies" is written in the
docstring and the CLI help but the function accepts any `by` string. [obs] `core/fleet/residents.py:159-253`.
`boot_block` puts "YOU ARE: <designation>", each receipt with its recommendation, `formerly:` names and the current
role into every resident's boot. [obs] `residents.py:611-658`; `agent_cli.py:349-355`.

**Name to address (routing).** `bus.send` runs every recipient through `resolve_agent`, which maps a RATIFIED callsign
(or a former one) to its agent id from an alias index built by scanning every `residents:log:*` key; an agent id
always wins; an unknown name passes through unchanged. Born 2026-08-20 when mail to "vandor" was accepted into a
stream nobody read: "Delivery succeeded; arrival never happened". [obs] `residents.py:291-369`;
`core/comm/bus.py:284-305`. The trust door does NOT resolve callsigns: `registry.resolve` looks up the exact id
string. [obs] `core/trust/registry.py:329-345`.

**Raising a seat (launchers).** Five separate launch paths: the Discord `!spawn` lever (`core/fleet/seat_launchers.py`,
five seats, its own hard-coded name table), the Bifrost UI launcher (`core/comm/launcher.py` + `security/launcher.json`),
the daemon (`scripts/bifrost_daemon.py`), `scripts/revive.py`, and `self_restart` re-exec. Only `seat_launchers` sets
`AKASHIC_AGENT_ID` for the child ("EVERY seat states its own identity. Never inherited"); the other four, and the
runner scripts themselves, set it nowhere, so a runner inherits whatever its launcher's environment held. [obs]
`seat_launchers.py:153-154`; grep counts 0 in `launcher.py`, `revive.py`, `bifrost_daemon.py`, `self_restart.py`,
`bifrost_child.py`, `bifrost_runner_kimi.py`, `bifrost_runner_deepseek.py`.

**The runner's onboarding.** At start a runner shells out to `py agent_cli.py boot <agent>` and takes its STDOUT as the
onboarding digest, without looking at the return code; any non-empty text is folded into the frozen system prompt
under "=== PROJECT ONBOARDING (you are a booted Akashic Aurora citizen; ...) ===" and the log prints "onboarded via
boot (N chars folded into system prompt)". A refused boot prints its refusal to stdout and exits 2. [obs]
`scripts/bifrost_runner_kimi.py:207-226, 796-812`; `scripts/bifrost_runner_deepseek.py:529-552, 1353-1364`;
`agent_cli.py:290-301`.

Put together [inf, from the four mechanisms above plus the Row 2 timings]: a runner started from a context whose
environment says `AKASHIC_AGENT_ID=claude` (the seat-identity docstring says the variable lives in a settings file
shared by every home-rooted Claude Code session, `seat_identity.py:4-6`) inherits that stamp; its onboarding boot asks to boot as
`kimi`; the identity law correctly sees a stamp naming someone else and refuses; the runner folds the refusal
("REFUSED: this session is 'claude' (from its env stamp) and asked to boot as 'kimi' ... Boot as 'claude'") into the
prompt as its onboarding. Navi and Heimdall then run without their identity sheet, receipts, handoffs and lessons,
carrying instead a sentence that says their session is claude. Their persona line still says who they are, so this
is a mild false autobiography, not a full one.

**Who may do what (trust).** `security/acl.json` is instance-local (gitignored since fence t384). `resolve(id)` is
fail-closed: unknown, unverified or expired means `quarantined` (read + read-own-inbox). `grant_writer` says of itself,
honestly, that `--by` is a plain string and the door "refuses; it does not authenticate": it prevents mistakes, not
attacks. [obs] `core/trust/registry.py:1-9, 329-345`; `core/trust/grant_writer.py:1-27, 83-93`;
`core/trust/capabilities.py:93-101`.

**Money (budgets).** Only the kimi and gemini seats carry a money gate. Navi's `SpendMeter` prices every API call from
its token counts, persists to `state/kimi_spend.json`, and every 10 minutes reconciles against the provider's balance:
the first contact seeds spend as budget minus balance; afterwards a balance DROP larger than metered spend corrects
spend UPWARD, a balance RISE is read as a credit and raises the budget by the net rise, and spend is never corrected
down ("credits are the only downward force"). The warn and refuse lines are two fixed constants, scaled by the
ratio of the current budget to a reference budget (the 2026-07-27 fix after a top-up left the gate stuck). Over the refuse line, any sender not in
`BUDGET_EXEMPT_SENDERS = {"user", "daniel"}` gets a settling reply with `meta.budget_refusal`. [obs]
`scripts/kimi_chat.py:70-82, 121-276`; `scripts/bifrost_runner_kimi.py:95, 377-390, 494-498`.

**Asking (the ask verb).** A stateless ask is born, answers and dies inside one call: no tools, no memory, no write;
the vendor is chosen by model name (kimi- prefix goes to Moonshot with Navi's key; everything else to DeepSeek);
`--as-resident` loads the resident's own archive lessons as a catch-up pack and refuses a non-resident before any
model call. `--peer SEAT` sends one durable ask, arms a sender-side expectation, and polls; `ask --status` folds the
expectation and the terminal events into seven honest states (OPEN.DISPATCHED / NOTED / REDRIVING, CLOSED.ANSWERED /
ECHO / DEAD, UNKNOWN). Expectations are swept only when the SENDER boots or syncs. [obs] `core/comm/ask.py:12-29,
91-140, 497-512`; `core/comm/ask_state.py:1-50`; `core/comm/expectations.py:1-24`.

**The model pin** keeps the request ("we asked for Opus") and the receipt ("the session says it runs Opus") as two
labelled planes, so a model change cannot happen quietly. A small, clean design worth copying elsewhere. [obs]
`core/fleet/seat_model.py:1-21`.

## Row 4. First principles (each tested: what evidence or law does it rest on?)

| principle | evidence or law | axiom or assumption? | label |
|---|---|---|---|
| A name is an address only where a router resolves it. | Naming versus addressing (DNS); the 2026-08-20 "vandor" silence | **Axiom** (a property of routing) | [obs] `residents.py:344-349` |
| False autobiography is worse than amnesia; verify the subject before trusting a record about yourself. | The Rill mangling, 2026-08-26, and Daniel's correction | **Axiom of the operator's values** (sourced, ratified in the house's own chronicle) | [obs] chronicle b00b93 `:74-99` |
| You do not name yourself; a peer confers with a receipt you authored; a human ratifies. | Daniel's designation scheme 2026-08-09 and deepseek's amendment | **Axiom of the operator's values**; rules 1 and 2 enforced, rule 3 only written | [obs] `residents.py:22-37, 220-253`; V5 |
| A child process inherits its parent's environment. | Operating-system process model | **Axiom** (a law of the platform) | [obs] V2 events: refusals with `source=env`, `resolved=claude` |
| **"`AKASHIC_AGENT_ID` names the process that carries it."** | Assumed by the boot door's env branch | **FALSE FIRST PRINCIPLE (trap 1).** It names whoever LAUNCHED the process unless the launcher overrides it; only one of five launch paths does. | [obs] Row 3 grep counts; V2 |
| Identity is asserted, not authenticated; the ACL is a seatbelt against mistakes, not a lock against an attacker with a shell. | Stated by the grant writer itself | **A stated, honest assumption** that the whole trust layer rests on; fits a single-operator machine by Daniel's chosen posture | [obs] `grant_writer.py:1-27` |
| **"`ratified_by: daniil` means Daniel ratified it."** | The field is a typed string | **FALSE FIRST PRINCIPLE (trap 1).** Two test-born residents in the live registry carry `ratified_by: daniil`; Daniel never ratified them. | [obs] V6; `residents:log:p4_scout_wearer`, `residents:log:resident-cache-pin` |
| The provider's wallet is ground truth for spend; the local meter is an estimate. | The bank statement beats the checkbook | **Axiom** (the code knows it: it reconciles) | [obs] `kimi_chat.py:191-231` |
| **"A conservative meter is a safe number."** | Unknown cache fields bill full price; reconcile only corrects upward | **Assumption.** Conservative is safe for the GATE (it refuses early), but the reported number drifts from the wallet: today spent exceeds the budget, which a prepaid wallet cannot do. | [obs] V11 |
| The human is always answered, whatever the money. | RB-29 and the exemption set | **Axiom of the operator's values**, implemented with an incomplete list of the human's names | [obs] `bifrost_runner_kimi.py:95`; V15 |
| "Persistence (a resident identity) improves correctness." | kimi's standing objection: never isolated | **Explicitly NOT claimed** by the house; the instrument to test it exists with n=7 | [obs] `residents.py:47-50`; Row 2 calibration |

## Row 5. Capabilities (what you must HAVE to build or run it)

| capability | label |
|---|---|
| Redis on 16379 for the resident logs, alias index, bus addresses and expectations; the lesson store, because receipts are authored lessons | [obs] `residents.py:58-73`; `py agent_cli.py status` (sibling card) |
| A per-session binding place (OS temp dir) and a launcher discipline that stamps `AKASHIC_AGENT_ID` on every child | [obs] `seat_identity.py:42-51`; `seat_launchers.py:153-154` |
| The ACL file plus its reader and writer; a doctor that reads lapses | [obs] `registry.py`, `grant_writer.py`; `agent_cli.py:5947-5958` |
| Provider keys and prepaid wallets per vendor (DeepSeek, Moonshot, OpenAI, Google), with a balance endpoint to reconcile against (Moonshot has one) | [obs] `ask.py:102-130`; `kimi_chat.py:fetch_balance` |
| Per-kind launch machinery: the dsh CLI (Rill), the daemon (Heimdall), runner scripts (Navi, Sunshine), the claude CLI and the desktop app (Vandor), the Discord gateway for `!spawn` | [obs] `seat_launchers.py:51-127, 203-337` |
| The operator as ratifier and as the only party who can raise money; a verified operator signal on the bus (`frm=daniil`, `operator=true`) | [obs] chronicle b00b93 `:115-119`; `core/comm/conductor_gate.py:89` |
| Charters (10 directories) that carry each seat's own law | [obs] `ls charters/` |

## Row 6. Required steps (build order from nothing; the critical path)

1. Stable agent ids, and a per-session binding that beats the shared environment. [obs] `seat_identity.py` (2026-08-01)
2. Grants keyed by agent id, fail-closed. [obs] `registry.py`
3. **Every launch path stamps the child's own identity.** [inf] Done for one path of five: `seat_launchers` (2026-08-24).
4. Lessons with authorship, so receipts can be verified. [obs] `learn:experiment:*` hashes carry `agent_id`
5. The resident registry: nominate, ratify, place, assign; append-only. [obs] `residents.py` (T258, 2026-08-09/10)
6. Name-to-address resolution at EVERY door that takes a name: bus (done 08-20), trust, launcher, budget exemption,
   roster (not done). [obs] Row 3
7. Boot carries identity (T258) and refuses the wrong subject (T418, 2026-10-01). [obs] `agent_cli.py:279-355`
8. Money gates for paid seats, with the human's full set of names exempt. [obs] `bifrost_runner_kimi.py`
9. Ask and peer ask on top. [obs] `ask.py` (T171, T196)
10. Measurement: verdict calibration for residents; counters for refused boots and refusals. [obs] instruments exist; [inf] readers do not (Loop altitude)

Critical path: 1, 3, 7. **Step 7 shipped (10-01) before step 3 was finished**, so the gate that protects residents
from wearing each other's identity now refuses residents their own, at every runner restart since a claude-stamped
launch on 10-09. [inf] from the dates and V2. The same order problem as the bus card's "doctor before liveness
semantics": a reader built before the writer's contract was made true everywhere.

## Row 7. Invariants and failure modes

| invariant | how it breaks | what a break looks like from outside | status today | label |
|---|---|---|---|---|
| I1 A seat boots as itself, with its own record | runner inherits the launcher's `AKASHIC_AGENT_ID=claude` | `boot_refused` events "claude asked to boot as kimi" at each runner start; runner log still says "onboarded" | **Broken for Heimdall and Navi since 10-09** (30 runner refusals; both live runners refused this morning) | [obs] V2; [inf] V3 |
| I2 A name routes to exactly one live seat | a name that was never ratified; two spellings; test callsigns | sends accepted into streams nobody reads | **Broken:** Neo and Astra/Asta pass through unrouted; one codex seat holds three addresses; test callsigns `compass`, `pathfinder`, `immediatesunbeam` route to fixture ids | [obs] V7, V6 |
| I3 A callsign is conferred by a peer with the nominee's own receipt, and ratified by a human | ratify accepts any `by` | a `ratified_by: daniil` that Daniel never gave | Rules 1 and 2 **held** (V4, V5); rule 3 **unenforced** (V5: the nominee can ratify itself) | [obs] V5 |
| I4 Every resident can be raised by a lever, and every lever is drilled | name missing from the lever's own table | `!spawn souei` launches a claude session whose task is "souei" (the 08-24 defect) | **Broken for Souei**; Neo and Asta fall through the same way; 3 of 5 levers undrilled from cold (vandor, heimdall, navi) | [obs] V8; `seat_launchers.py:69, 76, 212` |
| I5 A grant's lapse is seen before it bites | the listing shows a date, not a state | a seat that silently cannot write | **Partly held:** the doctor prints EXPIRED as page-grade; `grant --list` does not mark it; Neo quarantined 164 h | [obs] V9; `agent_cli.py:5947-5958` vs `6330-6341` |
| I6 Daniel is always answered | exemption list lacks his bus id | Navi refuses the operator and tells him "Daniel can direct this ask explicitly" | **Broken, latent:** his bus id `daniil` is not exempt; much of Navi's inbox comes from `daniil`; no refusal to him retained yet | [obs] V15 |
| I7 The meter agrees with the wallet within the code's tolerance | upward-only correction; credits netted against spend in one window | the refusal reports spend above the grant, while the wallet still holds a positive balance | **Broken**, by roughly 15% of the budget | [obs] V11 |
| I8 A refusal is distinguishable from an answer | the state machine has no refused state | `ask --status`: CLOSED.ANSWERED, "read the answer at the pointer" | **Broken at the state level** (the text says refusal) | [obs] V16 |
| I9 Tests never write the production identity plane | a test run without its isolation | fixture identities in the live registry | **Broken (residue):** three fixture residents and three fixture lessons in db 0, written 2026-08-26/27; a real agent id, `cursor`, now boots as "YOU ARE: Compass" | [obs] V6 |
| I10 A durable ask ends (answered, redriven or declared dead) | the sweeper is the sender's own next boot | asks armed forever from senders that never return | **Broken for one-shot codex senders** (7 asks, TTL -1) | [obs] V18 |

## Loop altitude (value chains, and whether the signal flows back)

**Chain A, the identity loop.** launcher env, process, boot subject check, boot fold, seat acts as itself, writes
lessons, lessons become receipts, receipts earn a callsign, the callsign routes mail back to it.
- Launcher to boot: **open in four of five paths** (no stamp). [obs] Row 3
- Boot to fold: the gate is closed and correct, but its **refusal flows into the runner as content** instead of back
  to the launcher as an error. [obs] `bifrost_runner_kimi.py:220-226`
- Refusal to anyone who can act: **designed-open.** `boot_refused` and `boot_unverified` events are written (45 and 209
  since 10-01) and nothing outside two comments reads them. [obs] grep of readers. The runner refusals ran four days
  unseen. A measurement without actuation: the most common real finding, again.
- Lessons to receipts to callsign: closed for the six residents (V4). **Closed off for Neo by a deadlock**: an
  expired grant means quarantined, which means no `kb.learn` through the gated doors, so no lesson, so no receipt, so no
  nomination, so the name cannot route. [inf] from `capabilities.py:93-96`, `residents.py:181-211`, V9.

**Chain B, the money loop.** turn, meter, reconcile against the wallet, gate, refusal reply, asker, operator, top-up,
credit seen, budget raised.
- Meter to wallet: closed in one direction only (upward). [obs] `kimi_chat.py:209-221`
- Refusal to the operator: **open.** `meta.budget_refusal` is written "for the doctor" and has no reader outside the
  two runners and tests; the doctor has no spend line for it. [obs] V17. Daniel learns Navi is refusing only if a
  seat relays the text. She has been refusing since at least 2026-10-09.
- The spend audit watches the meter's internal consistency, not the meter against the wallet, so it reads MATCH on an
  impossible state. [obs] V14
- Side door: `ask --model kimi-...` spends from Navi's wallet without her meter or gate. Measured exposure is small:
  2 of 755 journaled fans (4 branches each, both on 2026-08-16), recorded as unpriced (`usd: null`), so they are
  invisible on any cost line too. [obs] `core/comm/ask.py` (no SpendMeter); `state/route_journal.jsonl`

**Chain C, the ask loop.** ask, expectation, answer or refusal, settle, state. Closed for senders that keep booting.
Open for one-shot senders (I10). A refusal settles as ANSWERED (I8), so any count of answered asks counts refusals.

**Chain D, the value-of-identity loop.** resident-tier ask, verdict filed, adjudicated, calibration, a decision on
whether residency earns its keep. The instrument exists; **n = 7, all confirmed, none refuted**: the loop is built
and nearly dry, so kimi's objection stays exactly where it was. [obs] `resident calibration`

## The five traps, as seen here

1. **False first principles.** "The env stamp names the process", "`ratified_by` records who ratified", and "a
   conservative meter is a safe number" are each assumptions dressed as facts, and each fails on live data (Row 4).
2. **Chesterton's fence.** Every part the proposals touch exists for a stated reason: the identity law (Sunshine was
   once served as Heimdall through a hard-coded id, and Rill as Heimdall through a typed one, `seat_identity.py:153-157`);
   the `navi`-keyed grant (Daniel's 2026-09-09 request to give Heimdall, Navi and Sunshine non-expiring admin; kimi's
   own record already carries the same profile); the fixture residents (seeded by pins; no production use found,
   bounded to seat presence and routing); the budget gate (spend cost Daniel real money on 2026-07-27); the
   upward-only reconcile (a provider credit once "un-spent" money, 2026-07-18); the undecided name of the 2026-09-08 codex
   seat (an astra-authored lesson records that Daniel deferred it, wanting a relational name to emerge); Neo's 30-day
   box (Daniel chose time-boxed over permanent at the ratification). None of these is proposed for removal.
3. **Reductionism.** The runner refusal lives in the loop, not in any part: launcher env times runner not stamping
   times a correct gate times onboarding swallowing stdout times a success-shaped log line. Each part is right alone.
4. **The map is not the territory.** (a) The brief names "Astra"; the seat asked on 2026-09-14 to be reached as
   "asta", and the bus holds both. (b) The brief says Navi was "over her grant"; her ACL grant is admin and permanent,
   and what she exceeded is a money line that her refusal text also calls a "grant": one word, two meanings, the
   homonym class the ask door already names (T174). (c) The runner log says "onboarded via boot"; the boot was refused.
   (d) The refusal names the ladder's fixed refuse constant as its ceiling; the decision used the budget-scaled line,
   a different and much larger number. (e) `grant --list` shows Neo's lapsed grant
   as a row like any other.
5. **Goodhart.** The spend audit reads MATCH on spent > budget (V14). `ask --status` scores a refusal as ANSWERED
   (V16). Calibration shows a perfect 7 of 7 on a sample too small to fail. The `drilled` field is honest precisely
   because it refuses to be Goodharted: it says NO for three levers.

## Row 8. Verification (predictions that could fail, the test, and what came back)

| # | prediction (stated before the test) | cheapest test | result | held? |
|---|---|---|---|---|
| V1 | The identity law works as written: a kimi-stamped process asking to boot as deepseek is refused; asking as kimi is served; an unstamped one is served as unknown. | `subject_check` replayed with an injected env | refused (env) / served (env) / served (unknown) | **held** |
| V2 | The live Heimdall and Navi runners booted as themselves: a successful boot within 60 s of each process start. | process start times vs `events:raw` | deepseek started 07:48:20, refused 07:48:26; kimi started 07:48:43, refused 07:48:44; 30 runner-identity refusals since 10-09, all `source=env`, `resolved=claude`; no successful kimi boot since 10-08 | **failed** |
| V3 | A refused boot leaves a runner's onboarding empty, so its log would say "onboarding skipped". | read the fold code; replay the refusal text | stdout is taken with no return-code check and folded under "you are a booted Akashic Aurora citizen"; the replayed text begins "REFUSED: this session is 'claude' (from its env stamp) and asked to boot as 'kimi'" | **failed** (by replay; the live prompts were not read) |
| V4 | Rule 2 holds in live data: every receipt behind the six callsigns resolves to a lesson authored by its resident. | HGET `agent_id` on each receipt lesson | 10 of 10 self-authored, 0 mismatches | **held** |
| V5 | The ceremony refuses a non-human ratifier. | nominate and ratify against a FAKE store | rule 1 and both rule-2 refusals fire; ratify by `claude`, by the nominee itself, and by `anything-at-all` all ACCEPTED | **failed** (rules 1-2 held) |
| V6 | No test fixture holds a ratified identity in the production registry. | `residents:log:*` keys vs the `residents:all` index | 3 extra: `cursor` (Compass, by `daniil_pin`), `p4_scout_wearer` (Pathfinder, `ratified_by daniil`), `resident-cache-pin` (ImmediateSunbeam, `ratified_by daniil`); their seeded lessons exist in db 0; `boot_block('cursor')` = "YOU ARE: Compass" | **failed** |
| V7 | Every name in the brief routes to a seat. | `resolve_agent` per name | Vandor, Heimdall, Navi, Sunshine, Rill route; Neo, Astra, Asta pass through unchanged | **failed** for three names |
| V8 | Every ratified resident has a launch lever. | `seat_launchers.resolve_seat` per name | Souei none; Neo, Astra, Asta none (all fall to the claude task path); vandor, heimdall, navi levers marked undrilled from cold | **failed** |
| V9 | Neo can act today. | `registry.resolve('gpt-new')` | quarantined (expired 2026-10-06T17:36:10Z) | **failed** |
| V10 | The grant keyed `navi` governs Navi's runner. | runner command line, bus keys | the runner runs `--agent kimi`; 0 bus keys name `navi`; `resolve('Navi')` is quarantined | **failed** (inert; no harm today, kimi's own record is admin) |
| V11 | Navi's meter agrees with her wallet within the code's tolerance. | sidecar arithmetic | spent exceeds budget, yet the wallet holds a positive balance; the gap is roughly 15% of the budget, far outside the tolerance. Most of the recorded spend is token-priced; the rest came from seeding and upward corrections | **failed** |
| V12 | Tonight's refusal is right whichever side of the gap is wrong. | recompute under both hypotheses | if spend is over-counted, the corrected spend is still above the scaled refuse line: refuse; if the budget is under-counted, spend is still above the line computed from the corrected budget: refuse. Nearly all of the recorded budget is gone either way | **held** |
| V13 | The refusal text names the line the decision used. | compare text with `refuse_at()` arithmetic | the text names the fixed refuse constant; the decision used the budget-scaled line, a different number | **failed** |
| V14 | The spend audit flags spent > budget. | `py agent_cli.py audit --domain spend` | `MATCH kimi:spend`, printed over a spent figure larger than its budget figure | **failed** |
| V15 | Daniel's own bus id is exempt from Navi's refusal. | the exemption set vs the house's operator sets vs Navi's inbox | `{"user","daniel"}`; the house elsewhere lists `user, daniel, daniil` (`conductor_gate.py:89`, `mailbox.py:974`); much of Navi's inbox is from `daniil` | **failed** (latent) |
| V16 | A refused peer ask reads as refused. | `ask --status <id>` on tonight's refused ask | CLOSED.ANSWERED, "read the answer at the pointer" | **failed** |
| V17 | `meta.budget_refusal`, written "for the doctor", has a reader. | grep every `*.py` outside tests and worktrees | written by the kimi and gemini runners; read by nothing | **failed** |
| V18 | Durable peer asks always end. | SCAN `bifrost:expect:*` | 7 asks from `astra`, `codex-piano`, `codex-voice`, armed 2026-09-08 to 09-22, TTL −1 | **failed** for one-shot senders |

---

## Great Sage report

> **Notice.** Six callsigns are ratified, and all ten of their receipts are self-authored lessons (V4); the naming
> rules 1 and 2 refuse loudly (V5). The identity law refuses a stamped session asking to be someone else (V1). Since
> 2026-10-01 the boot door has served 280 boots, 209 of them unverified, and refused 45; since 10-09 it has refused 30
> runner boots for Heimdall and Navi with the stamp `claude` from the environment, including both live runners
> within seconds of starting this morning (V2). Only one of five launch paths stamps a child's identity (Row 3); the
> runners fold boot stdout without checking the return code (`bifrost_runner_kimi.py:220-226`) and log "onboarded".
> `ratify` accepts any actor (V5). Three test fixtures hold ratified identities in the live registry, one on the real
> id `cursor` (V6). Neo, Astra and Asta do not route (V7); one codex seat's mail sits in three unread addresses.
> Souei has no lever; three levers are undrilled (V8). Neo's grant lapsed 164 hours ago and `grant --list` does not
> say so (V9). Navi refused overnight with a meter that disagrees with her wallet by roughly 15% of her budget (V11),
> a printed ceiling that is not the line the decision used (V13), an audit that reads MATCH (V14), and an exemption
> list without `daniil` (V15). The refusal settles as ANSWERED (V16) and its doctor flag has no reader (V17).
>
> **Analysis.** The core defect is a meaning problem in the carrier, not in the law. Identity rides an environment
> variable, and environment variables inherit (an OS law), so "the stamp names the process" is true only where the
> launcher overwrote it; the house fixed that at the Discord lever (08-24) and built the gate (10-01) before fixing
> it at the other four doors (V2, Row 6). The gate then did its job perfectly against the residents it exists to
> protect, and the runners turned its refusal into content (V3), the same "a lever that means something other than
> what he meant" shape the 08-24 module was written against. Around it, the fleet's names live in five tables that
> never join (the resident registry, the lever's own alias table, ACL keys, two operator-id sets and the runners'
> exemption set), so each new being (Neo, Asta, Souei) is known to some tables and not others (V7-V10, V15). The money
> gate's VERDICT is robust (V12); its NUMBERS are not, and the loop back to Daniel is open (V17), so a seat can refuse
> peers for days without the operator seeing a gauge.
>
> **Unknown.** Who launched the runners with `AKASHIC_AGENT_ID=claude` on 10-09 and at 07:48 today (the parent processes
> are gone). The exact text in Navi's and Heimdall's live system prompts (inferred by replay, not read). Which side of
> the meter-to-wallet gap is wrong (the provider's top-up history would settle it). Whether the seat that wrote as `astra`
> on 2026-09-08 and the seat that asked on 09-14 to be reached as `asta` are one being: the record cannot join them,
> and guessing would be the Rill-mangling class. How Souei works without a runner, a grant or presence (4 lessons
> authored under `grok`). How the fixtures reached db 0 on 08-26/27 although their tests import the isolation guard.
> Whether the CLI `learn` door enforces the ACL (so whether Neo is truly locked out of earning a receipt). Why one
> refused ask from 10-09 reads UNKNOWN while its refusal reply is still on the stream. Search boundary: Python under
> `core/`, `scripts/`, `agent_cli.py`, `tests/` (grep), `security/acl.json`, chronicle b00b93, `state/kimi_spend.json`,
> `state/asks/`, `state/route_journal.jsonl`, the live Redis keys named above, and `events:raw` since 10-01. Not read:
> `private/`, personal memory, transcripts, the Discord side, the runners' live memory, provider dashboards.
>
> **Proposal** (smallest first; each keeps the fence it touches; none deletes anything):
> 1. Add `daniil` to the runners' budget exemption, better by reading the one operator set in
>    `conductor_gate.operator_ids()`. Fence kept: peers are still refused over the line. (V15)
> 2. Runner onboarding checks the boot's return code: on refusal fold nothing, print "boot REFUSED: identity stamp says
>    <x>" instead of "onboarded". Fence kept: the identity law is untouched. (V3)
> 3. Print the line the decision used (`refuse_at()`), and say "money budget" rather than "grant" in the refusal. (V13)
> 4. Mark EXPIRED rows in `grant --list` (reuse `expiring_grants`). Then Neo's grant is Daniel's call: renew or let it
>    lapse; note the deadlock (quarantined, so no lesson, so no receipt, so no callsign). (V9)
> 5. Stamp identity at every launch path: smallest form, each runner sets `AKASHIC_AGENT_ID` to its own `--agent`
>    before onboarding; fuller form, the daemon, UI launcher, revive and self-restart stamp like `seat_launchers`.
>    Fence kept: T418 still refuses a process whose own stamp names someone else. (V2)
> 6. Close the two open measurement loops: a doctor row for `boot_refused`/`boot_unverified` per agent per 24 h (would
>    have caught 10-09 the same day), and a first reader for `meta.budget_refusal` ("Navi refusing peers since <time>").
> 7. Give `ask --status` a visible refusal (a REFUSED terminal state, or a flag on ANSWERED); add a spend-audit rule
>    for "spent > budget" and "budget − spent vs wallet". (V14, V16)
> 8. Enforce rule 3: `ratify` accepts only an operator id with a verified operator signal, or else records the
>    ratifier as "claimed". Fence kept: the ceremony's human gate becomes real instead of written. (V5)
> 9. Void, do not delete, the three fixture residents (an appended `voided` record honours the registry's
>    append-only law), starting with `cursor` because it hands a real id a fabricated badge; find the isolation leak.
>    Only with Daniel's yes. (V6)
> 10. One name table: derive the lever's aliases, the exemption set and the operator sets from the registry and
>    `conductor_gate`; add levers for Souei, Neo or Asta only after Daniel says how those seats should run. (V8)
> 11. Astra and Asta: do NOT merge. Ask Daniel and the seat whether they are one being; the conversational name was
>    deferred by Daniel and stays his and the seat's to let emerge. If one being, the ceremony plus a former-name
>    alias joins the three mailboxes; if two, mark `astra`'s mail as addressed to a seat that no longer runs. (V7)
> 12. Investigate only: the 10-09 and 07:48 launcher; the meter-to-wallet gap; whether `ask --model kimi-...` should meter into
>    Navi's wallet; the seven stranded expectations.
>
> **Verification.** Eighteen predictions were run. Held: V1 the identity law in pure form, V4 every receipt
> self-authored, V12 tonight's refusal right on either reading of the gap. Failed, and each failure is a finding: V2
> runners refused their own boots, V3 the refusal becomes onboarding, V5 rule 3 unenforced, V6 fixtures in the
> registry, V7 three names do not route, V8 no lever for Souei, V9 Neo quarantined, V10 the `navi` grant is inert, V11
> meter versus wallet, V13 the printed ceiling, V14 the audit's MATCH, V15 Daniel not exempt, V16 refusal reads as
> answered, V17 the unread refusal flag, V18 asks that never end.
>
> **Proceed?** YES / NO: Daniel's gate. Every proposal waits for him. 1 to 4 are a line or a render each; 5 and 6
> change how seats start and what the doctor shows; 7 and 8 change what counts as an answer and a ratification; 9
> touches the identity record itself; 10 and 11 need his rulings on names; 12 is investigation only.
