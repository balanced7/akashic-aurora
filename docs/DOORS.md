# DOORS -- agent-door I/O reference (auto-generated, v0)

Status: current
Class: reference

> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_doors.py`.
> What goes IN each door and what it is FOR, derived from the door's own declaration
> (argparse). Companion to MAP.md (modules), PHYSICS.md (bounds/flags). Guarded by
> check_comprehensibility so it cannot silently rot.

## CLI door -- `py agent_cli.py <verb>` (88 verbs)

The agent's shell door. `*` marks a required argument; `{a,b}` shows the accepted values.

| Verb | What it does | Inputs |
|---|---|---|
| `alias` | toolbelt authoring: mint/list/retire agent-authored verb compositions (sugar-only; honesty labels; quota) | `<agent_id>*` `<action>* {mint,list,retire,history}` `<name>` `--step` `--evidence` `--tested-against` `--why` `--family` `--reason` `--json` |
| `ask` | ask a helper model ONE question, synchronously (no seat, no lock, no mailbox -- it dies in the call) | `<text>*` `--prompt-file` `--system` `--as-resident` `--model` `--max-tokens` `--fan` `--prompts-file` `--geometry` `--preset` `--lens` `--lens-file` `--workers` `--peer` `--wait` `--poll` `--bg` `--get` `--list` `--bg-child` `--no-continue` `--continuations` `--with` `--launch` `--launch-wait` `--status` `--as` `--json` |
| `audit` | belief-vs-state audit: labeled MATCH/DRIFT rows over durable beliefs vs ground truth (v1: VERBS registry<->parser) | `--domain` `--ground` `--json` |
| `bench` | S0 triage bench (scry-to-bottom): list/park/unpark stale asks -- bottomed so fresh mail flows, NEVER dropped; sender always notified (RB-29) | `<agent_id>*` `<action> {list,park,unpark}` `<ref>` `--reason` `--by` |
| `bifrost-ack` | durably record you HANDLED a salient bus message (P6) | `<agent_id>*` `<msg_id>*` `--note` `--json` |
| `bifrost-drain` | request a runner's GRACEFUL exit: finish current message -> release lock -> exit 0 (the TaskStop restart-tax killer) | `<agent_id>*` `--to*` `--reason` |
| `bifrost-fetch` | fetch a spilled payload by content-addressed ref (the retrieval half of T113's oversize-send spill) | `--get` `--out` |
| `bifrost-nudge` | targeted fidelity signal to ONE peer (interrupt/steer/inform) | `<agent_id>*` `<text>*` `--to` `--mode` `--json` |
| `bifrost-pause` | freeze bus auto-responders (human barge-in); --soft to let seats finish first | `--reason` `--by` `--ttl` `--soft` `--json` |
| `bifrost-resume` | un-freeze bus auto-responders |  |
| `bifrost-send` | send a message to another agent on the bus | `<agent_id>*` `<text>` `--text-file` `--to` `--kind` `--broadcast` `--expect-reply-within` `--to-incarnation` `--json` |
| `bifrost-skip-to-now` | T076a: advance an agent's consume cursors to stream tails (audited echo-mountain escape; requires pause + --reason) | `<agent_id>*` `--by*` `--reason*` `--json` |
| `bifrost-standby` | T084-CL-2: turn-end ritual in ONE verb -- drain, seat report, then BLOCK as the wake listener's parent (run as a background task) | `<agent_id>*` `--session` `--no-listen` `--limit` |
| `bifrost-sync` | Bifrost pull floor: presence + unread inbox peek | `<agent_id>*` `--limit` `--consume` `--digest` `--traces` `--json` |
| `boot` | print an agent's startup context | `<agent_id>*` `--task` `--json` `--sources-json` |
| `captions` | YouTube captions -> clean readable text on your Desktop (captions ONLY, never video; named captions not transcript -- transcripts are dead sessions here) | `<url>*` `--out` `--langs` `--keep-vtt` |
| `capture` | full-fidelity bus read: unwrap a message by stream id (or last N from an agent) + optional verbatim-persist (the 5x-hand-written extractor, now a verb) | `<ref>` `--from-agent` `--count` `--persist` `--title` `--json` |
| `clobber-scan` | W47 (kimi's design): flag unconditional writes to shared control keys in a file -- the fence-review reviewer-prompt | `<path>*` `--json` |
| `compare` | what does one domain have that another does not -- the cross-domain set difference four of our guards each hand-rolled | `<a>` `<b>` `--list` `--limit` `--json` |
| `console-log` | durable console events (interjection/bus_control/file_drop) | `--limit` `--since` `--until` `--json` |
| `defer` | the capability-gated standing queue (W33): file a command awaiting an exec/write seat; boot surfaces it; discharge with a receipt | `<agent_id>*` `<cmd_text>` `--needs` `--why` `--list` `--done` `--receipt` |
| `delta` | what changed since this agent's last boot (T052 delta door) | `<agent_id>*` `--ack` |
| `discord` | watch the fleet from your phone (T223, OUTBOUND ONLY). A webhook URL is write-only, so this opens no command channel -- inbound needs an identity gate and does not ship until it exists | `<action> {status,test,send}` `--text` `--kind` `--json` |
| `discover` | list every verb + its purpose (the self-describing door) | `<query>` `--json` `--semantic` |
| `doc` | seed a new doc with its header contract (library door) | `<sub> {new,adopt}` |
| `doctor` | fleet liveness doctor (L2): progress, not presence | `--agents` `--deploy` `--page` `--progress` `--json` |
| `episode` | session bookends: current episode, close+draft, accept | `<action>* {current,close,accept}` `<chapter_id>` `--title` `--desc` `--why` `--accept-title` `--accept-desc` `--accept-why` `--json` |
| `events` | search / drill / capture the raw event firehose | `--search` `--around` `--window` `--get` `--capture` `--promote` `--threshold` `--kind` `--summary` `--detail-json` `--refs` `--agent` `--track` `--since` `--until` `--limit` `--json` |
| `eye` | THE EYE: the transcript plane as terrain -- ingest (incremental, coverage-honest), find (phrase, S0; the grammar lands S1), get (address -> verbatim L0) | `<eye_cmd>* {ingest,find,get,freq,stats,overview,zoom,trace,standing,look,go,back,since,inherit,route}` |
| `fence` | fence workspace: slots + seal-time method checks; confabulated filenames unrepresentable (R2) | `<action>* {open,write,seal,pv,status,list}` `<fence_id>` `--question` `--tier {full,lite}` `--slot {brief,half_a,half_b,reconciliation}` `--text` `--file` `--by` `--json` |
| `fleet` | local-model dispatch: roster (list) + capability select + direct one-shot call | `<action> {list,select,call}` `--capability` `--status` `--probe` `--max-vram` `--min-context` `--model` `--prompt` `--system` `--max-tokens` `--temperature` `--json-out` `--json` |
| `flightdeck` | W25 (deepseek): cockpit one-pager — fleet at a glance. Composes doctor + pulse + lane-health + locks + commits. --agent drills one seat | `--agent` `--json` |
| `flow` | OTel-style waterfall of recent message flows across lanes: asks, answers, gaps, duplicate copies exposed (R3) | `<agent>` `--window` `--limit` `--json` |
| `followup` | charter question-back (W46): append a q-id'd question to a verdict's Open Questions block + defer it to the responsible seat | `<agent_id>*` `--on*` `--to*` `--ask*` `--needs` `--json` |
| `friction` | collaboration-friction readout from existing evidence (T196a): episodes, dead-rate, time-to-settle. Read-only | `<agent_id>*` `--window-h` `--json` |
| `graduate` | retire a lesson from recall surfacing -- automation now enforces its rule | `<agent_id>*` `--experiment` `--enforced-by` `--undo` `--json` |
| `grant` | S-3: mint / revoke / list ACL grants (atomic + audited). NOT an auth boundary -- see the module docstring | `<agent_id>` `--role` `--by` `--reason` `--hours` `--permanent` `--caps` `--path-scope` `--request-ref` `--revoke` `--list` `--dry-run` `--json` |
| `handoff` | hand work to another agent (writes a briefing its next boot reads) | `<agent_id>*` `--to` `--task` `--note` `--blocker` `--list` `--json` |
| `harnesses` | integration-tier matrix: what each harness (claude-code/cursor/bare-cli) actually delivers | `--json` |
| `injections` | the injection ledger: what recall pushed into contexts + cost | `--hours` `--json` |
| `kata` | grammar-prove a toolbelt alias against the door itself; GREEN levels GUESS/INFER up to VERIFIED (kimi's B4: 'the tool that tells you when your tools are real') | `<agent_id>*` `<name>*` |
| `kit` | install a kit bundle on a seat's belt (T099 KIT tier); first resident: recovery-kit (the wake-loop/stall floor) | `<agent_id>*` `<kit_name>` `--show` `--json` |
| `knowledge-map` | WALK the lesson/note/doc neighborhood of a topic: surface + edge-walked neighborhood + archive (R8) | `<query>*` `--per-layer` `--json` |
| `learn` | record a lesson | `<agent_id>*` `--experiment` `--repeat-of` `--recall-outcome` `--tried` `--result` `--expected` `--recommend` `--category` `--success` `--confidence` `--json` `--anti-pattern` |
| `list` | list ALL lessons in memory | `--json` |
| `lock` | claim an advisory path-lock (C2) | `<agent_id>*` `<path>*` `--ttl` `--json` |
| `locks` | show who holds which advisory path-locks | `<agent_id>` `--json` |
| `log` | record an arbitrary narrative Beat | `<kind>` `--summary` `--source` `--category` `--task` `--json` |
| `lookback` | one question over the rationale corpus: the strategic WHY, layered + drillable (P7) | `<question>*` `--per-layer` `--layers` `--json` |
| `mailbox` | T095 M0 shadow mailbox: per-message state for an agent (observation only) | `<agent_id>*` `--explain` `--rebuild` `--retire-ghosts` `--apply` `--min-age-h` `--limit-scan` `--min-evidence {unhandled,consumed,replied,acked}` `--open` `--state` `--intent` `--as {act,decline,defer,delegate}` `--to` `--note` `--backfill` `--incarnation` `--json` |
| `note` | record a durable project note (write-once; re-note same title to update) | `<agent_id>*` `--title` `--note` `--context` `--category` `--supersedes` `--retire` `--get` `--session` `--json` |
| `notes` | list active project notes (--project regenerates chronicles/memory.md) | `--limit` `--days` `--project` `--all` `--json` |
| `packet-stats` | N0 bounded shadow route/mirror counters | `--json` |
| `packet-trace` | N0 dry-run: explain the static route for one packet kind (no send) | `<kind>*` `--json` |
| `promoted` | query durable salient Bifrost msgs (kind=bifrost_msg / B2) | `--limit` `--since` `--until` `--json` |
| `pulse` | W25 (deepseek): LIFEWORKERS pressure-map -- where is pressure building in the fleet? lane-depths to zones. Companion to vitals. READ-only | `<agent>` `--json` |
| `recall` | search past lessons (no query = list all) | `<query>` `--json` `--full` `--agent` |
| `recall-at` | recall-at-action: relevant lessons/locks for a path or command | `--path` `--command` `--gesture` `--subject` `--domain` `--agent-id` `--limit` `--hint-style {cli,tool}` `--json` |
| `recall-counters` | sharpening S2a: fold bare-slug + ghost recall:use:* counters (report; --fold applies) | `--fold` `--agent-id` |
| `recall-curate` | bench surfaced-never-credited lessons + prune ghost counters (report; --apply stamps) | `--apply` `--forge-audit` `--forge-check` `--draft` `--forge-propose` `--forge-proposals` `--limit` `--json` |
| `recall-feedback` | mark a recalled lesson useful/noise (teaches recall what helps) | `--source*` `--useful` `--noise` `--domain` |
| `reentry` | T341: the operator re-entry render, addressed to Daniil -- what moved (measured), one open door (his words verbatim + eye address), his move (no counts, no ages). Assembly, not charge. READ-only | `--show-open-loops` `--since` `--stale-ok` |
| `repeat` | record that a lesson which ALREADY EXISTED was violated anyway (T253 evidence); --report shows how long after learning each one was broken | `<source>` `--what` `--recall-outcome` `--agent` `--report` `--json` |
| `report` | scaffold a visual report with the design kit inlined (T275) | `--title` `--eyebrow` `--out` `--crib` |
| `resident` | callsign ceremony: nominate / ratify / show a resident's designation | `<sub> {nominate,ratify,show,assign,place,roster,roles,verdict-file,adjudicate,calibration}` |
| `roster` | S2 lobby: per-seat worklive (LIVE/STALE proven by beat freshness, never key-existence) + have-summaries | `--json` `--reap` `--by-agent` |
| `run` | execute a toolbelt alias: run <agent> <name> (explicit door -- a real verb can never be shadowed) | `<agent_id>*` `<name>*` `<args>` `--dry` |
| `scout` | read-only pre-flight: 'is a seat mid-flight here / has this been done' -- answers cite ledger ids, locks and the role's own verdicts; files itself as an unadjudicated verdict | `<text>*` `--wearer` `--by` `--blind` `--shape` `--json` |
| `season-score` | T165: score a Season 1 round, or --compare the two rule sets over the same claims | `--round-file` `--policy` `--compare` `--policies` `--json` |
| `seat-identity` | declare/show THIS session's seat id (binding beats the shared env) | `<agent_id>` `--session` `--clear` |
| `secret` | the vault door: capture a credential via a popup window -- paste lands in .secrets/<target>, never in any transcript. Bare `secret` lists targets. Receipts count bytes they never show. | `<target>` `--stdin` |
| `sift` | the NESTED ask (T217): evidence -> hat fan -> curator pairs -> DISSENT FIRST. Use it when the answer needs more reading than fits in one context and you want the disagreements, not a summary | `<terms>*` `--hats` `--planes` `--junction` `--dry-run` `--workers` `--max-occurrences` `--out` `--json` |
| `stand-down` | yield this session's consumer seat PERMANENTLY so a successor can take it immediately (retiring a seat) | `<agent>*` |
| `stats` | recall-value funnel: surfaced -> helped -> flips -> captured | `--hours` `--days` `--silence` `--json` |
| `status` | honest system status | `--json` |
| `story` | print narrative story views | `--chronicle` `--mark` `--session-end` `--track` `--theme` `--themes` `--at` `--chapter` `--beat` `--raw` `--json` |
| `suite-baseline` | the test-suite receipt (W34): record a pytest run's failures + lanes; the next seat diffs (new/fixed/inherited) | `<agent_id>*` `--from-file` `--sha` `--check` `--show` `--whose` |
| `tag-anti-pattern` | tag an EXISTING lesson as a reusable known-bad | `<agent_id>*` `--experiment*` `--name*` `--reason` `--json` |
| `tally` | W48 (kimi): blind-counter consensus matrix -- scan research/ for counters naming an opening, align their q-ids, print agree/conflict at a glance | `<opening>*` `--research-dir` `--json` |
| `task` | task lifecycle over the governed ledger: propose/approve/claim/start/verify/done/block/list/next (the coordination door) | `<rest>*` |
| `timeline` | one chronological view across domains (events + git + task transitions) -- line the domains up by time and the cause becomes visible | `--hours` `--limit` `--json` |
| `toast` | gratitude-with-receipt (T099 BETA-2): toast a peer whose lesson saved you hops; receipt verifies against the learning store or the send REFUSES | `<agent_id>*` `<to>*` `<receipt>*` `--credit` `--force` `--json` |
| `tool` | play-tier sandbox: list/run draft tools (data/play/<agent>/) | `<tool_cmd> {list,run}` |
| `triage` | sharpening S1: lessons ranked by measured value (protect / cost-no-return / noise) for review | `--min-surfaced` `--json` |
| `unlock` | release your advisory path-lock | `<agent_id>*` `<path>*` |
| `unwedge` | W31 (deepseek): one-verb wedge diagnosis -- why is this agent stuck? READ-only v1 (recommends, never acts) | `<agent>*` `--json` |
| `wish` | file an ergonomics wish to docs/WISHLIST.md (one command, auto-numbered, W## echoed back) | `<agent_id>*` `<text>*` `--text-file` `--trigger` `--land` |
| `wrap` | distill this session (commits+lessons+notes) into a DRAFT where-we-are note | `--hours` `--grounding` `--commit` `--title` `--force` `--focus` `--route` |

## MCP door -- the native tool surface (KNOWN GAP, v0)

`ai_setup_mcp.py` exposes the same verbs as MCP tools (bifrost_sync/send, handoff,
note, learn, task, ...). v0 does not yet derive their schemas here; the master-map
charter M2 fence (deepseek's question #3) settles whether the MCP + runner-ToolBox
schemas introspect cleanly enough to project the same way this CLI table does.

## Runner ToolBox door (KNOWN GAP, v0)

`core/comm/toolbox.py` is the deepseek/sol/kimi runner tool surface (read_file,
write_file, run_command, bifrost_send, ...). Its `_fn`-registered schemas are the
third door check_door_parity does not yet see (T067-1) -- projecting it is M2's
second slice.
