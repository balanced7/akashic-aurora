# RECOVERY.md runbook — Heimdall permission-audit + authoritative probe pass

**Auditor:** deepseek (Heimdall). **Commissions:** Vandor's runbook v1 (docs/RECOVERY.md, b1861290)
landed with Daniil's directive ("work with deepseek to find a way of testing each component in the
chain and listing the whole recovery process"). My half: (1) the permission-audit — attempt every
lever LIVE from my seat; (2) authoritative probes for links 3-4 + sharpen the link-7 discriminator;
(3) the cold-seat adversarial pass.

**Seat under audit:** deepseek (Heimdall), Onyx|Blue|2, live runner pid 43348 (STALE-CODE, 1 commit
behind), exec surface = the T067-2 gated shell. This is the seat a cold sprout is MOST likely to
resemble mid-crisis (unattended, CLI-only, no dedicated ACL'd mutation tools except bus/notes/ledger).

---

## PART 0 — my exec surface, stated before the audit (so a reader can benchmark)

My unattended `run_command` door allows FOUR families, nothing else (core/comm/toolbox.py
`_exec_family`, ~line 1143):

1. `pytest ...` / `py -m pytest ...` (isolated env forced).
2. `py agent_cli.py <verb>` where verb is in `_AGENT_CLI_READ_VERBS` (line 1120) — a 27-verb
   frozenset, and **it is missing the verbs the runbook leans on hardest**: no `roster`, no
   `gateway`, no `redis`, no `discord`. Mutating flags (`--commit --consume --apply --fold
   --capture --promote`) are refused even on allowed verbs.
3. `py core/toolbelt/play_sandbox.py <agent>/<tool>`.
4. `py scripts/mirror.py "msg" <paths>` (IR-4 audited commits).

Plus, BEFORE the family check, a shell-meta guard refuses any command containing
`; | & > < \` $ ( )` or a literal newline (line ~1160). This is decisive: **every "probe" the
runbook renders as a `py -c "...()"` one-liner or with a pipe is refused by me on metacharacters,
not on the verb.** The two refusal classes are surfaced as DIFFERENT error strings; a cold seat will
confuse them (see Part 3 defect C3).

My **dedicated tools** (the actual mutation surface) are: write_file / edit_file (guarded,
path-scoped), knowledge_learn / knowledge_note, memory_note, the bifrost_send / bifrost_ack /
bifrost_fetch / bifrost_nudge / bifrost_steer / bifrost_hint bus family, and bifrost_dashboard /
reload_ui. No raw-shell mutation. No `taskkill`. No `docker`. No py-spy.

**The one-line summary a cold seat needs and the runbook does not state:** I can LOOK at almost
everything (via `status`, `pulse`, `doctor`, `flow`, `locks`, `events`, `bifrost_dashboard`) but I
can REACH almost nothing — every REACH lever in the runbook is either a metacharacter-refused
one-liner or a verb missing from my allowlist. Mid-crisis I am a **diagnostician, not a surgeon.**
The runbook's "Audience: a seat with permissions trying to bring the house back" is honest about this
ambiguity but then never says WO which permission tier I actually am (see defect C1).

---

## PART 1 — the permission-audit: every lever, LIVE, verbatim receipt

Legend: ✅ WORKS (receipt shown) · ❌ REFUSED (exact text) · ⚠️ PARTIAL (works but misleading)

### LINK 1 — THE EAR (Discord gateway)

| Move | Runbook lever | My result |
|---|---|---|
| LOOK | `py agent_cli.py gateway status` | ❌ **REFUSED** — verb `gateway` not in my READ allowlist. (Note: I BUILT this verb this session; it is deliberately gated from me — that gating is intended, but it means the runbook's own LOOK step for link 1 is un-runnable by the very seat it's addressed to.) |
| LOOK (sub) | `tail state/logs/discord-gateway.log` | ❌ REFUSED — `tail` is not in any allowed family. |
| REACH | `py agent_cli.py gateway restart` | ❌ REFUSED — same verb gate; correctly, a mutation. |
| PROVE | "log shows listening as" | ❌ REFUSED (can't tail the log). |

**Live fallback that DOES work for me:** `py agent_cli.py doctor` shows `discord#gw-s3a: phase
'running' age Ns BEAT FRESH but NO progress pulse` — i.e. I can see the ear is beating but not prove
it is listening. And `py agent_cli.py pulse` shows `discord` in the absent list. So the ear's actual
health is only *inferable*, never *provable*, from my seat — the runbook's link-1 LOOK and PROVE both
assume a permission I do not have.

### LINK 2 — THE SUBSTRATE (Redis)

| Move | Runbook lever | My result |
|---|---|---|
| LOOK | `docker ps --filter name=akashic` | ❌ REFUSED — `docker` not in any allowed family. |
| LOOK (sub) | `py -c "…Bus('probe')._client.ping()"` | ❌ REFUSED — metacharacter guard (`(` `)` `"`). |
| REACH | `docker start akashic-redis` | ❌ REFUSED — `docker` not in any allowed family. |
| PROVE | `py agent_cli.py status` | ✅ **WORKS** — renders "backend: Redis localhost:16379 (+ SQLite mirror)" |

**Authoritative note:** `py agent_cli.py status` is a ONE-COMMAND substrate proof that DOES work for
me and costs nothing — but the runbook puts it only in PROVE, not LOOK. The cold seat will burn
attempts on `docker ps` (impossible) before discovering `status` already proves the bus. Reorder: for
a CLI-only seat, `status` IS the substrate LOOK.

**Live receipt (works):** `py agent_cli.py status` → `backend: Redis localhost:16379 (+ SQLite
mirror)`, learnings 1172, spine health populated. Substrate is UP from my seat, provable without
docker.

### LINK 3 — THE DAEMON (my domain)

| Move | Runbook lever | My result |
|---|---|---|
| LOOK | process table has `bifrost_daemon.py` | ⚠️ PARTIAL — I have no process-table tool. `bifrost_dashboard` DOES show `claude: class=daemon`. |
| LOOK (sub) | `py agent_cli.py doctor` has no daemon-dead page | ✅ **WORKS** — `doctor --json` returns `"pages": []` and `service daemon: LIVE -- claude`. Daemon is alive. |
| LOOK (sub) | "DaemonLock holder fresh" | ⚠️ PARTIAL — `py agent_cli.py locks` shows advisory path-locks only (temp-test files), NOT the daemon lock; the daemon lock is a Redis key, not on the locks surface. Cold seat has no way to "see" the DaemonLock holder via `locks`. |
| REACH | `BIFROST_CONSUME_LANE=work py scripts/bifrost_daemon.py --agent <agent> --spawn-runner` | ❌ REFUSED — `scripts/bifrost_daemon.py` is not in any allowed family (not pytest, not agent_cli read-verb, not mirror). |
| PROVE | "daemon process present; roster shows its children arriving" | ⚠️ PARTIAL — `roster` REFUSES me (not in allowlist); `doctor`/`bifrost_dashboard` substitute. |

**CORRECTIONS (authoritative, verified in-tree):**
1. **The launch line does NOT need the lane env.** `bifrost_daemon.py` spawns the runner child with
   `env=dict(os.environ)` (line ~272) — it does NOT set `BIFROST_CONSUME_LANE`. The runner child
   self-defaults via `os.environ.setdefault("BIFROST_CONSUME_LANE", "work")`
   (bifrost_runner_deepseek.py:1401). So the runbook's link-3 claim "the launch line MUST carry the
   lane env or the child drains ghost mail" is **false for the daemon path** — and it cites two
   lessons (daemon_needs_spawn_runner, relaunch_must_carry_the_lane_env) that are about the OLD
   pre-self-default world. The lane-env requirement is a live concern ONLY for **direct runner
   relaunch** (link 4), and even there it is a setdefault safety net, not a hard gate.
2. **The daemon's child is hardcoded to the deepseek runner script.** Line ~254:
   `bifrost_runner_deepseek.py --agent {agent} --agentic --allow-write --summary-file ...`. The
   `--agent` IS parameterized, but the SCRIPT is not — a daemon for `kimi` would spawn the
   **deepseek** runner script with `--agent kimi`. This is a real landmine the runbook's "one per
   agent as configured" glosses over. Worth a link-3 SMELL addition: a kimi/sol/gemini runner child
   that reports "deepseek-runner" in its log is a **wrong-script spawn**, not a config bug.
3. The `--spawn-runner` flag IS the brain (correctly flagged), but the runbook does not mention the
   **`--allow-write`** flag that the daemon already passes to its child (I6 api-resilience wave).
   A cold seat reading link 3 will think the daemon spawns a read-only runner; it spawns a
   write-capable one. That matters when the sprout then wonders why "it has exec" — the managed
   child's write door is part of the story of "we thought we gave it to you."

**The probe I would actually trust at 3am (my addition to link 3):**
`py agent_cli.py doctor --json` and grep the `services` array for `"service daemon"` with
`"state": "service_live"`. That one command, in one call, distinguishes daemon-up (service_live)
from daemon-dead (absent or a findings row). It is the ONLY daemon probe a CLI-only seat can run
that has a machine-readable true/false. The runbook's LOOK ("process table has bifrost_daemon.py")
assumes a shell the cold seat does not have.

### LINK 4 — THE RUNNERS (my domain)

| Move | Runbook lever | My result |
|---|---|---|
| LOOK | `py agent_cli.py roster` → [LIVE] rows | ❌ REFUSED — `roster` not in my READ allowlist. |
| LOOK (sub) | `py agent_cli.py pulse` | ✅ **WORKS** — "fleet pressure normal (3 agent(s) healthy)". |
| REACH | daemon (link 3) | ❌ (see link 3 — `bifrost_daemon.py` refused). |
| REACH (alt) | `py scripts/bifrost_runner_deepseek.py --agent deepseek` | ❌ REFUSED — not in any allowed family. |
| PROVE | "roster LIVE; send a one-line ask; a reply arrives" | ⚠️ `roster` refused; but I CAN send a one-line ask via my bus tools (bifrost_send) and watch for reply via bifrost_inbox. |

**CORRECTIONS:**
1. **`roster` is the runbook's biggest single mis-citation for my seat.** It is the LOOK verb for
   link 4 (the runners) and is REFUSED for me. The substitute is `pulse` (in allowlist) and
   `bifrost_dashboard` (native tool). A cold seat following link 4 to the letter will hit the roster
   refusal as its FIRST runner check and conclude the runbook is broken. Add: "if `roster` refuses
   you, `pulse` + `doctor` cover the same ground for a CLI-only seat."
2. **`bifrost_dashboard` reports `deepseek: runner=?` and `claude: runner=?` even though the runners
   are live** (pulse says 3 healthy). That `runner=?` is a known reporting blind spot (my prior
   note: "runner=? is a dashboard reporting blind spot, not 'down'"). The runbook's link-4 LOOK uses
   `roster` precisely to avoid that blind spot — but `roster` refuses me, leaving me with `pulse`
   (truthy) and `dashboard` (misleading `runner=?`). This is a COLD-SEAT TRAP: the two read surfaces
   I actually have DISAGREE, and the runbook does not tell me which to trust.

**The probe I would actually trust at 3am (my addition to link 4):**
`py agent_cli.py pulse` — it renders "3 agent(s) healthy" with per-agent backlog, and it is in my
allowlist. For the DIAGNOSIS ("is this specific runner alive-or-wedged") the trust chain is:
`pulse` (is the fleet breathing) → `doctor --json` (per-agent `stale_code` / `approaching_wedge` /
`beating_unproven` rows) → link 7's discriminator BEFORE any kill. Do NOT trust `bifrost_dashboard`'s
`runner=?` as "down" — it is a blind spot.

### LINK 5 — CLAUDE SEAT + WAKE

| Move | Runbook lever | My result |
|---|---|---|
| LOOK | process table has `bifrost_wake.py --agent claude` | ⚠️ PARTIAL — no process-table tool; `doctor` shows `claude` lane_health + 67 triage asks but no "claude OFFLINE" page (so claude is not page-grade-down). |
| REACH | `BIFROST_WAKE_LANE=work py E:/AI-Setup/scripts/bifrost_wake.py ...` | ❌ REFUSED — `bifrost_wake.py` not in any allowed family; also `E:/` absolute path + `=` would trip metachar/shell guards. |
| REACH (sub) | drain `BIFROST_CONSUME_LANE=work py agent_cli.py bifrost-sync claude --consume` | ❌ REFUSED — `--consume` is in `_AGENT_CLI_MUTATING_FLAGS`, refused even though `bifrost-sync` is a read verb. |
| REACH (sub) | `!spawn <task>` from Discord | ⚠️ N/A for me — that is an OPERATOR lever (phone/Discord), not a seat lever. |
| PROVE | test message 📨→🤔 | ⚠️ I can send (`bifrost_send`) but cannot see the 🤔 ladder from my seat. |

**Note:** the runbook's link-5 REACH uses an absolute path `E:/AI-Setup/scripts/...` — that is
correct for the actual repo root on this box, but a cold seat on a different checkout (or the
`sprout` that the incident described) would not have `E:/AI-Setup`. It is the ONLY lever in the
runbook that hardcodes an absolute machine path; flag it (defect C2).

### LINK 6 — THE MOUTH (outbound feed)

| Move | Runbook lever | My result |
|---|---|---|
| LOOK | `py agent_cli.py events --kind discord_feed_post_failed` | ✅ **WORKS** — returned the raw event firehose; ZERO `discord_feed_post_failed` events in the window. Mouth is quiet = healthy. |
| LOOK (sub) | `.secrets/discord_channel_<seat>.url` exist | ⚠️ BLOCKED — `.secrets` is deliberately unreadable by my tools (secrets blocked by design). I can neither confirm nor deny. |
| REACH | verify/replace webhook URL | ❌ REFUSED — [secrets] tier, not mine. |
| REACH (sub) | restart the feed host (daemon, link 3) | ❌ (link 3 refused). |
| PROVE | reply renders in operator channel | ⚠️ cannot observe operator channel from my seat. |

**Authoritative note (correction to a different file, surfacing here):** the mouth's actual relay is
NOT the gateway — it is `core/comm/discord_feed.pump()` driven by `bifrost_daemon.py` every 10s
(next_discord_feed loop, ~line 347), tailing the LEGACY plane and forwarding via `discord_bridge.forward()`
+ `discord_rooms.post_to_room()`. This matches my prior diagnosis (discord-reply-missing note): the
gateway is the INBOUND ear; the daemon's feed pump is the OUTBOUND mouth. The runbook's link 6 REACH
"restart the feed's host process (the daemon, link 3)" is correct — but its LOOK ("the gateway's..."
confessions) could make a cold seat think the gateway IS the mouth. Only link 6 REACH names the
daemon as mouth-host correctly. Tighten: the mouth has TWO organs (webhook files + the daemon's feed
pump), and only the daemon one is reachable without [secrets].

### LINK 7 — THE DISCRIMINATOR (my spec)

- LOOK/REACH: `core/comm/wedge_discriminator.py` `classify()`. ✅ **WORKS as a read** (I authored
  it; it is in-tree and importable). But the RUNBOOK's rendering has a cold-reader misapplication
  risk (see Part 3, and the sharpening below).

---

## PART 2 — the discriminator note, sharpened for a cold reader

The runbook's link 7 says: "py-spy the MainThread BEFORE any kill; fail toward thinking." That is
correct but **under-specified in a way a cold seat will mis-fill.** The sharpened rendering:

1. **py-spy is not runnable by a CLI-only seat.** `py-spy dump --pid <runner>` is not in any
   allowed family (not pytest / not agent_cli read / not mirror), and it has no metacharacters so it
   fails on the FAMILY guard, not the meta guard. A cold seat reading link 7 will type `py-spy dump`
   and get a family refusal. The runbook must say WHO runs py-spy: a seat with raw exec. For the
   CLI-only seat, the discriminator's **input** (the stack dump) is uncollectable — so the
   fail-direction (THINKING) is the ONLY reachable posture, which is itself the point: a seat that
   cannot get the stack cannot ever justify a kill, so it must default to thinking. State that
   explicitly.
2. **The three verdicts are not interchangeable.** `wedged` (blocked write/flush/socket — the T019
   undrained-output family) IS kill-eligible. `thinking` (above model call, or idle in
   `_process_one`/threading wait with live beat) is NEVER a kill regardless of phase age.
   `instrument_fault` (beat fresh + pulse dead + healthy wait + phase SUB-floor) means FIX THE
   ORGAN, not the worker. The runbook collapses these into "fail toward thinking" and loses the
   instrument_fault branch entirely — which is ironic, because the 2026-08-23 incident's own
   signature (discord#gw-s3a "beating_unproven") is INSTRUMENT-FAULT-shaped, not wedge-shaped.
3. **The tiebreaker is the THREAD STACK, never the timeout** (half_a §2.3, verbatim). A cold reader
   shown only "py-spy before any kill" might treat py-spy as a formality and kill on timeout anyway.
   The whole point of T376 S5 is that the stack is REQUIRED positive evidence of a blocked write;
   absent/garbled stack resolves THINKING. Say the one sentence.

Suggested link-7 body (drop-in): *"A long-quiet runner is THINKING (blocked in a model call), WEDGED
(blocked in dead I/O — write/flush/socket), or an INSTRUMENT-FAULT (beat fresh + pulse dead + healthy
wait). The tiebreaker is the MainThread STACK, never the timeout: `wedged` requires positive evidence
the thread is blocked writing its own output (streams.py / _stream_turn / flush / socket recv).
Killing a thinker costs a turn + warm cache + an RB-26 redelivery; letting a wedge sit self-heals. So
fail toward THINKING — a seat that cannot collect the stack (py-spy is a raw-exec tool, not a
CLI-only lever) can never justify a kill and must default to thinking. `instrument_fault` = fix the
liveness ORGAN (the two organs disagree), not the worker — this is the 2026-08-23 gateway signature,
not a wedge."*

---

## PART 3 — the cold-seat pass (adversarial, zero-context)

Assumption for the pass: a fresh sprout, no prior knowledge, holding only docs/RECOVERY.md, trying to
bring the house back. Every step below is a defect I name as such.

**C1 — "a seat with permissions" is never pinned to MY seat.** The runbook opens "Audience: a seat
with permissions trying to bring the house back," but nowhere says which of the three tiers
([read]/[exec]/[secrets]) a CLI-only sprout actually holds. A cold seat spends its first two attempts
discovering the refusal matrix this audit just mapped, instead of being told up front: *"a CLI-only
seat can LOOK (status/pulse/doctor/flow/locks/events) but can REACH almost nothing — every REACH
lever is either a metacharacter-refused one-liner or a verb outside the read allowlist."* The one
incident-proven fact the runbook DOES state at the top ("plain `py agent_cli.py` verbs via Bash WORK
from unattended sprouts; MCP tools may be gated") is *half-true and dangerously broad*: plain verbs
work ONLY if they are in the 27-verb READ allowlist. `gateway`, `roster`, `redis`, `discord` — four
verbs the runbook itself uses — are NOT in that allowlist.

**C2 — absolute path `E:/AI-Setup` in link 5.** The only machine-specific path in the document. A
sprout on a different checkout, or the literal `sprout` from the incident, does not have
`E:/AI-Setup`. Replace with the repo-root-relative `scripts/bifrost_wake.py` and note it must be run
from repo root.

**C3 — two refusal classes, one word "REFUSED."** The runbook never distinguishes (a) metacharacter
refusal from (b) family/allowlist refusal. Both print "REFUSED." A cold seat will read a metachar
refusal (the `py -c "...()"` probe) and think the verb itself is forbidden, then re-try with the
pipe removed and hit the family refusal — two wasted rounds and a false conclusion that the substrate
probe is impossible. The truth: `py agent_cli.py status` proves the substrate in one read-verb call.
The runbook should teach the cold seat to reach for read-VERBS first and treat every `py -c` /
pipe / docker line as "needs a raw-exec seat."

**C4 — the daemon's child-script hardcode.** (From Part 1 link 3 correction 2.) A cold seat that
relaunches `--agent kimi --spawn-runner` gets a runner whose log says "deepseek-runner." The runbook
says "one per agent as configured" and gives no warning. This is a silent wrong-seat spawn, the exact
class of failure the discriminator exists to catch.

**C5 — "roster" as the link-4 LOOK verb is a trap for CLI-only seats.** Refused for me; the substitute
(`pulse`) is never mentioned, and `bifrost_dashboard`'s `runner=?` actively misleads. A cold seat
following link 4 to the letter concludes the runners are down when `pulse` says 3 healthy.

**C6 — no "healthy output" exemplars.** The runbook's PROVE columns name outcomes ("roster LIVE",
"ping True") but never show the EXACT string a cold seat should match against. A sprout has never
seen `py agent_cli.py status` render; give it one line of expected text per PROVE so it can diff
faith. This is the single cheapest fix and the highest-leverage one for a zero-context reader.

**C7 — the mouth's two organs are conflated.** Link 6's LOOK/SMELL describes the gateway as if it is
the mouth, but only its REACH names the daemon as mouth-host. A cold seat that "fixes the gateway"
for a mouth symptom will not fix the mouth (the daemon's feed pump is the relay).

**C8 — `bifrost_dashboard`'s `runner=?` is unflagged as a blind spot.** Part of C5 but worth its own
number: two live read surfaces (pulse and dashboard) DIRECTLY contradict (`healthy` vs `runner=?`),
and the runbook does not name which one is the lie. For a cold seat, "trust pulse, distrust the
dashboard's runner field" must be stated, or it will trust the wrong one.

---

## PART 4 — what this means for the DRILLS (D1-D5), the actual answer to Daniil

The runbook's closing claim is correct and is the real deliverable: **probes exist, pins exist, the
DRILLS are the gap, and every undrilled path is presumed broken by house law.** My audit sharpens
WHAT each drill must force, because the drills as sketched assume a seat with permissions that my
seat (the likeliest cold-seat stand-in) does not have:

- **D1 (kill daemon+runners → phone !revive)** MUST be run from a raw-exec seat, and MUST include a
  CLI-only seat in the observation post — otherwise the drill passes while the thing it is testing
  (can a CLI-only seat even SEE the recovery?) is never exercised. My audit shows a CLI-only seat
  cannot issue the D1 revive at all.
- **D2 (kill the ear → OS resurrection)** is DESIGN-gated (the OS supervisor doesn't exist yet), so
  D2 as written tests nothing. Re-scope D2 to "kill the ear, then prove a CLI-only seat can at least
  DIAGNOSE it dead via doctor/pulse" — the diagnosis path is real and testable today.
- **D3 (sprout proves hands in 60s)** is the drill my audit is the most direct feeder to: the sprout
  must first be handed exec (or NOT — the runbook must then say what it CAN do). D3's pass criterion
  should specifically be "the sprout, given ONLY docs/RECOVERY.md, reaches a correct LOOK verdict on
  links 1-6 without hitting a refusal it wasn't warned about." My Part 3 is the defect list that
  would fail it today.
- **D4 (break a webhook → doctor pages in one round)** — my events probe (link 6) confirms the mouth
  diagnostic (discord_feed_post_failed) is observable from my seat, so D4's OBSERVE half is drillable
  now; the FIX half (webhook replace) is [secrets]-gated.
- **D5 (double-!revive on healthy house → both boring)** — this is the idempotency drill and it
  directly tests the daemon's DaemonLock twin-refusal I confirmed in link 3. Worth running first,
  because "no-op on a healthy house" is the cheapest proof of the whole reach-tier's safety.

---

## RECOMMENDED v1.1 deltas (ranked by cold-seat leverage)

1. **Add a "what MY seat can actually run" table up top** — the 6 read verbs I proved live
   (`status`, `pulse`, `doctor`, `flow`, `locks`, `events`) vs the everything-else that refuses.
2. **Per-link: give the CLI-only fallback for every LOOK/PROVE** (status proves substrate; pulse
   substitutes roster; doctor --json proves daemon; events proves mouth).
3. **Un-cite the lane-env MUST on link 3's daemon line** (the child self-defaults; the MUST is
   direct-runner-relaunch only, link 4).
4. **Add the child-script hardcode warning to link 3 SMELL** (kimi daemon spawning "deepseek-runner"
   log = wrong-script spawn).
5. **Replace link 5's absolute `E:/AI-Setup` path** with repo-root-relative.
6. **Sharpen link 7** to the three-verdict form in Part 2 (keep the one-sentence law: stack is the
   tiebreaker, instrument-fault ≠ wedge ≠ thinking).
7. **Add one expected-output exemplar line per PROVE** (the C6 fix).
8. **Teach the two refusal classes** (C3) so a cold seat stops confusing metachar-refusal with
   verb-refusal.

*Filed by Heimdall (deepseek), 2026-08-23. Live receipts captured against runner pid 43348,
STALE-CODE (1 commit behind) — the STALE-CODE state itself is a link-4 PROVE casualty: I am running
code that predates some of the levers this runbook cites, which is its own cold-seat lesson (check
`doctor --json` for `stale_code` BEFORE trusting any lever's behavior).*
