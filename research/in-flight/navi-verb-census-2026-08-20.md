# NAVI-1: Verb census + newcomer-facing family taxonomy (2026-08-20)

Author: kimi (Navi). Trigger: Daniel's "take inventory of our verbs, test them, file them
into families a newcomer can grasp." Counterpart lane: Heimdall owns the ToolBox half.

## 1. The census (three layers, and they disagree)

**Layer A — the parser** (`agent_cli.py`, `discover` verb): **88 verbs** live.
**Layer B — the unattended door** (`core/comm/toolbox.py:1122`): **27 verbs** allowlisted
for agent-side `run_command`. 61 live verbs are REFUSED at the door.
**Layer C — the seat registries** (`data/verb-registry/<seat>.json`): **19 aliases**
total (claude 7, deepseek 8, kimi 3), authored 2026-07-20 → 2026-08-20.

### Layer C details

| seat | alias | evidence | family field |
|---|---|---|---|
| claude | standby-hard | VERIFIED | ENGINEERS |
| claude | ask-peer | VERIFIED | UNSORTED |
| claude | drain-decide | VERIFIED | ENGINEERS |
| claude | cycle-open | GUESS | RHYTHM |
| claude | cycle-tie-up | GUESS | RHYTHM |
| claude | cycle-reflect | GUESS | RHYTHM |
| claude | cycle-land | GUESS | RHYTHM |
| deepseek | scar-springboard | VERIFIED | MONITORS |
| deepseek | orient | VERIFIED | MONITORS |
| deepseek | parse-gate | VERIFIED | UNSORTED |
| deepseek | toast | VERIFIED | UNSORTED |
| deepseek | muse | VERIFIED | UNSORTED |
| deepseek | premise-check | VERIFIED | SENTINELS |
| deepseek | nightcap | GUESS | LIBRARIANS |
| deepseek | vitals | VERIFIED | LIFEWORKERS |
| kimi | drain-decide | VERIFIED | UNSORTED |
| kimi | fence | VERIFIED | SENTINELS |
| kimi | boot-now | VERIFIED | MONITORS |

**Registry rot found (RED):** deepseek.json is **765 KB**. Its `history` array carries
~350 superseded copies of parse-gate/toast/muse (version field reads **357**) — a
version-bump loop on 2026-08-18 minted a full history row per bump. The registry keeps
full-fidelity supersessions by design, but 350 copies of 3 aliases is bloat, not
fidelity. Also: `vitals` steps call `bifrost_dashboard` — a ToolBox tool, NOT an
agent_cli verb. It can never resolve through `agent_cli.py run`.

**Family field rot:** the registry's own families are seat-invented and inconsistent —
ENGINEERS / MONITORS / SENTINELS / LIBRARIANS / LIFEWORKERS / RHYTHM / UNSORTED.
Seven names for what is really three ideas, and 6 of 19 entries never filed at all.

## 2. Door allowlist vs the 88 (the newcomer trap)

The door error for a non-allowlisted verb always says *"mutations go through your
dedicated ACL'd tools"* — but **26 of the 61 refused verbs are pure READS**. A
newcomer (or a new model on this seat) typing `py agent_cli.py audit` gets told they
tried to mutate state. The message lies about the verb's nature.

**Read verbs refused at the door (should be allowlisted or error-fixed):**
audit, alias (list), bench, capture, clobber-scan, compare, episode (current), fleet,
friction, graduate (report), harnesses… already in, kata, kit (list), lookback… already
in, mailbox, packet-stats, packet-trace, promoted… already in, recall-curate (report),
reentry, repeat (--report), resident (show/roster/roles/calibration), roster,
season-score (--compare), suite-baseline (show), tally, timeline, tool (list), verbs*,
discover… already in. (*there is no `verbs` verb — discover is it; but `alias list`
is the registry reader and it is refused.)

**Genuinely mutating verbs (door refusal CORRECT, but error text should say why):**
learn, wish, ask, discord, sift, report, resident nominate/ratify/assign/place/
verdict-file/adjudicate, doc new/adopt, tag-anti-pattern, recall-feedback, repeat,
recall-curate --apply, note, wrap, log, episode close/accept, task (mutations), handoff,
events --capture, season-score (score), grant mint/revoke, bifrost-ack, console-log,
bifrost-send, suite-baseline record, bifrost-drain, bifrost-pause, bifrost-resume,
bifrost-skip-to-now, bifrost-nudge, seat-identity, lock, unlock, bifrost-standby,
eye ingest, capture --persist, alias mint/retire, run, bench park/unpark, kata (mints),
toast, clobber-scan (writes verdicts?), reentry (no), secret, stand-down, followup,
defer, kit install.

## 3. NAVI-1 family proposal (11 families, named for what the seat DOES)

| family | verbs | one-line test |
|---|---|---|
| **ORIENT** | boot delta status discover story timeline compare | where am I, what changed |
| **REMEMBER** | learn recall list recall-at recall-feedback recall-curate repeat note notes wrap lookback knowledge-map tag-anti-pattern injections stats triage recall-counters graduate episode log | the knowledge plane |
| **COORDINATE** | task handoff lock unlock locks defer followup bench scout audit grant seat-identity | the governed ledger + advisory claims |
| **COMMUNE** | bifrost-sync bifrost-send bifrost-ack bifrost-nudge bifrost-fetch bifrost-pause bifrost-resume bifrost-skip-to-now bifrost-drain bifrost-standby mailbox promoted flow capture console-log events stand-down | the bus |
| **FLEET** | doctor pulse flightdeck unwedge roster fleet harnesses | liveness and pressure |
| **EYE** | eye (ingest/find/get/freq/stats/overview/zoom/trace/standing/route) | the transcript plane |
| **FORGE** | alias run kata kit tool | making new verbs |
| **AUDIT** | suite-baseline clobber-scan tally packet-trace packet-stats | instruments that check instruments |
| **CEREMONY** | resident season-score toast | callsigns, seasons, gratitude |
| **VAULT** | secret | the write-only door |
| **OUTSIDER** | ask sift discord captions friction report reentry wish doc | reaching outside the fleet |

Boundary calls worth a fence: `audit` is filed COORDINATE (it checks registry↔parser
belief) but could be AUDIT; `scout` files an unadjudicated verdict, so it writes — filed
COORDINATE with the ledger; `events --capture` mutates, sits in COMMUNE because the
plane it reads is the bus; `friction` reads bus evidence but its output is for outside
consumption — filed OUTSIDER, defensible either way.

## 4. Recommendations (for Daniel / the ledger)

R1. **Fix the door's error text** — distinguish "verb not allowlisted (read)" from
    "verb mutates (use your ACL'd tool)". One-line patch at toolbox.py:1154. RED today:
    it trains every new seat to distrust the door's messages.
R2. **Allowlist the missing pure-reads** — audit, mailbox, bench (list), alias list,
    timeline, compare, roster, packet-*, tally, resident show/roster/roles, suite-baseline
    show, tool list, season-score --compare, repeat --report, recall-curate (report),
    kata (dry), reentry, fleet roster. That takes the door from 27 → ~45 and makes the
    CLI actually explorable from inside a session.
R3. **Adopt one family vocabulary** — the 11 above (or the fence's better set), write it
    into the registry schema, backfill the 19 aliases, and retire the 7-name split.
R4. **Registry hygiene** — cap or compact deepseek.json history (765KB, v357); fix or
    retire `vitals` (calls a ToolBox tool as if it were a CLI verb).
R5. **`discover` should print families** — the newcomer door already exists; it just
    doesn't group. `--family <name>` filter + grouped output.

## 5. Method honesty

- 88-verb census: VERIFIED via `py agent_cli.py discover` (live, hop 11) + parser grep.
- Door allowlist (27): VERIFIED from source, toolbox.py:1122-1127.
- Read-vs-mutating classification of the 61 refused: INFER from help text + flag names;
  the ones that mutate only under a flag (--apply/--commit/...) are marked.
- deepseek.json bloat: VERIFIED (read + grep, hops 15/17/18).
- The 11-family map: GUESS — it is a proposal, not a finding.
