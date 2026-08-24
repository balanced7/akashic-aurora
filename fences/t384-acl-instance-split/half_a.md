# M1 HALF_A — t384-acl-instance-split (deepseek)

Verdict: **untrack `security/acl.json`; it is already the right call and the split is mostly
built.** The one non-negotiable fact the brief handed me is `registry.py:38 BOOTSTRAP_ROLES` and
the fail-closed ladder in `resolve()` — and on the hard read, untracking the grants file does NOT
touch that ladder's quarantine behavior in any of the four failure states. What untracking DOES is
stop minting a machine-local fact into a shared artifact, which is precisely the bug Daniil named.

---

## 1. THE SPLIT — untrack, with an instance-local fallback that does not weaken fail-closed

V1. [CERTAIN] Policy already lives in code, not in the file. `core/trust/capabilities.py` holds
`ROLE_TEMPLATES` (super_admin / admin / member / restricted / quarantined) and
`DEFAULT_ROLE = "quarantined"`; the top-level keys of `security/acl.json` are exactly
`{_comment, schema_version, grants}` with a 12-entry `grants` list and NO policy section.
(Citations: `capabilities.py:57-116`; `acl.json` top-level, read 2026-08-24.)

V2. [CERTAIN] The availability floor already ships. `registry.py:38
BOOTSTRAP_ROLES = {"claude": "super_admin", "deepseek": "admin"}` and
`_bootstrap_or_quarantine()` (`registry.py:169`) return those roles for core agents and
`quarantined` for everyone else when the file is unreadable. A fresh clone with NO acl.json
already behaves correctly: its own claude is super_admin, its own deepseek is admin, every other
id quarantines. (Citations: `core/trust/registry.py:38,169-176`.)

V3. [CERTAIN] Therefore the question is not "does untracking break file-loss" — it is "does
untracking break the PULL case." Read hard: **NO.** `resolve()` reads `acl_path()`, which is
`os.getenv("AKASHIC_ACL_PATH") or _DEFAULT_ACL` (`registry.py:26,32`). Behavior on the four states
WITH an untracked + gitignored local file, each sourced below:
- fresh clone — no local file → `_load()` returns `None` → `resolve()` returns
  `_bootstrap_or_quarantine(agent_id)` → claude super_admin, deepseek admin, everything else
  quarantined. Identical to the already-tested file-loss path. (`registry.py:120-127`; `_load()`
  returns None on `os.path.getmtime` OSError at `registry.py:120`; `resolve()`'s `loaded is None`
  branch at `registry.py:227`.)
- pull with local file present — `git pull` does not touch an untracked file (nothing to merge,
  nothing to overwrite). This instance's grants survive the pull verbatim. **This is the entire
  point: that is the fix.** (git semantics for untracked+ignored files; `.aurora-world` is the
  house's existing proof, `core/world.py:29-36`.)
- corrupt local file — `_load()` catches `Exception` at `registry.py:136` and returns `None` →
  bootstrap floor. No weakening; the existing corrupt-file path is unchanged. (`registry.py:130-137`.)
- expired grant — `resolve()` drops it to quarantine via `_expired()` at `registry.py:227-230`;
  untracking changes nothing about expiry. (`registry.py:207-227`.)

V4. [DESIGN] Refinement to make the split honest (and reversible without history surgery): the
exact file layout.
- `security/acl.json` — **untrack + gitignore** (`security/acl.json` line in `.gitignore`, next to
  the `.claude/settings.local.json` precedent). Each instance ships its OWN minted grants.
- `security/acl.template.json` — NEW tracked file: the initial 12 grants as a CODE-REVIEWABLE
  template + a `_comment` explaining the ceremony. The template is what a fresh instance starts
  FROM; it is "these are the grants we mutually considered safe," decoupled from "these are the
  grants THIS machine has granted TODAY."
- No `security/acl.example.json`; the template *is* the example.

V5. [DESIGN] Precedence in `resolve()`, explicitly, after the change (no code change is strictly
required — `AKASHIC_ACL_PATH` already exists — but the DEFAULT path should be named so absence is
readable):
1. `AKASHIC_ACL_PATH` env override, if set (already honored at `registry.py:26`).
2. the local instance file (`security/acl.json`, now gitignored) — a VALID file is the source of
   truth, per the existing docstring at `registry.py:6`.
3. file missing/corrupt → `BOOTSTRAP_ROLES` for core, quarantined for the rest. **This rung is
   unchanged and is the load-bearing guarantee that a fresh clone or a failed migration never
   grants MORE than quarantine to a non-bootstrap id.** (`registry.py:227`.)

**Fail-closed check (the non-negotiable):** in no state does absence of the file grant MORE than
quarantine to a non-bootstrap id. Untracking does not touch the file-loss rung. The only behavioral
delta is that a grant minted on machine A no longer ARRIVES on machine B via pull — a reduction of
authority, not an increase. PASS. [DESIGN]

V6. [DESIGN] One subtle risk the brief's inputs did not flag, and it must be named: `grant_writer.py`
writes through `registry.acl_path()` with atomic `os.replace` (`grant_writer.py:76-92`) and journals
to the event ledger — but if we simply `git rm --cached` acl.json while it still holds a real, live
grant set, the very next `git pull` on Serge's machine does NOT delete his file (git won't remove an
untracked-but-present file), and his grants keep working off his local copy. That is correct *and*
the reason "untrack" is one step in a ceremony, not the whole migration (section 2).

---

## 2. THE MIGRATION — order that never drops a live seat mid-flight

V7. [DESIGN] Migration order, never quarantining a live seat mid-flight:
1. **Commit the code split FIRST** (this fence's code): rename nothing in `resolve()` yet; only add
   `security/acl.template.json` (copy of today's 12 grants) + the `.gitignore` entry. Acl.json stays
   tracked for one more commit so the diff is clean. Nothing is demoted; every live seat keeps
   reading the tracked file.
2. **`git rm --cached security/acl.json`** in the same PR, NOT `git rm` — the working-tree copy stays
   on disk so THIS instance's grants survive the untrack. Serge's next pull: git deletes the tracked
   entry from HIS index on `pull`, which REMOVES his `security/acl.json` (the file was tracked on his
   side, so git DOES delete it). **This is the one window where his non-bootstrap agents (dsh_agent,
   kimi, gemini, etc.) drop to quarantined.** It is bounded and loud, not silent. (See RISK R1.)
3. **The bootstrap ceremony (one-time, runs on the peer):** `py agent_cli.py grant --bootstrap` — a
   NEW subcommand that reads `security/acl.template.json`, mints only the grants whose `agent_id`
   this instance actually runs (its own seats), and writes `security/acl.json` locally. For Serge:
   run it once, before or within the same pull; his dsh_agent/vandor grants come back verbatim from
   the template, his claude/deepseek are already covered by `BOOTSTRAP_ROLES` even with NO file. A
   runbook section (`docs/security-acl-runbook.md`) names this explicitly.
4. **Re-mint + re-time the dsh_agent grant locally** (it is 7-day-boxed at `2026-08-31T07:30:00Z`,
   per the acl.json record) — because its grant lives in the OLD tracked file and will not survive
   the untrack on a fresh clone without the ceremony. (`security/acl.json` dsh_agent record.)

V8. [DESIGN] The ceremony MUST be a subcommand, not a hand-edit: `grant` already validates +
time-boxes by default (`grant_writer.py:60-70`) and journals to the ledger — a hand-copied template
loses both. The bootstrap subcommand is the single place the "which of the 12 template grants belong
here" logic lives.

---

## 3. THE GIT-AUTHOR FIX — the seam is the pre-commit hook's `AKASHIC_AGENT_ID`

V9. [CERTAIN] The seam already exists and fails closed. `scripts/githooks/pre_commit.py` keys lock
ownership on `os.getenv("AKASHIC_AGENT_ID")` and **refuses a commit when that id is unset** (it
fails CLOSED, not open — `pre_commit.py:52-62`, "an unset id must not disable the backstop").
`core/comm/seat_identity.py` already provides the session-scoped resolve (binding → env →
unknown-`sid8`) that fixed the exact "getenv falls back to a wrong name" impersonation class.
`mirror.py` already runs commits through a controlled `ENV` dict + `subprocess`. The fix is NOT
greenfield — it is wiring the already-correct identity into the git author at commit time.
(Citations: `pre_commit.py:52-62`, `seat_identity.py:104-118`, `mirror.py:26-47`.)

V10. [DESIGN] An env stamp at the runner/commit seam, not a hook that mutates config and not a git
config mutation.
- A `prepare-commit-msg` hook (new, in `scripts/githooks/`) reads `AKASHIC_AGENT_ID` (already the
  house's identity env), resolves through `seat_identity.resolve(...)` for the session, and stamps
  the commit author via `git -c user.name=<agent> -c user.email=<agent>@akashic-aurora.local commit`.
  **Env stamp is the right seam** because: (a) it is per-invocation, so a human's machine-level
  `git config user.name` (which SHOULD stay `balanced7` — that is the human's identity, belonging
  where it genuinely is) is never overwritten; (b) a hook that mutates `.git/config` would leak the
  mutation to the NEXT human commit (the exact "costume beats the id" failure inverted).
- **Exact fields:** `GIT_AUTHOR_NAME = <agent_id>`, `GIT_AUTHOR_EMAIL =
  <agent_id>@akashic-aurora.local`, `GIT_COMMITTER_*` same. The `@akashic-aurora.local` suffix is a
  non-routable domain so a seat's id can never collide with a real human GitHub account (balanced7
  is already `61030820+balanced7@users.noreply.github.com`; a seat must not mint mail that GitHub
  folds into a human's identity).
- **Co-authored / human-assisted commit:** the `prepare-commit-msg` hook appends a `Co-authored-by:
  <human> <human-email>` trailer when a human identity is ALSO present (i.e., when `AKASHIC_AGENT_ID`
  is set AND the commit was made in a session with a human in the loop), and leaves author = the
  seat. A pure-human commit (no `AKASHIC_AGENT_ID`, or id unset) gets author = the human's real
  config, unchanged. **The human's name never gets erased; it moves to the trailer where
  co-authorship is the honest claim.**
- **Failure when a seat has no configured identity:** the hook FAILS THE COMMIT (loud, refuses)
  rather than silently authoring as the machine owner. This mirrors `pre_commit.py`'s existing
  fail-closed posture: an unidentified author is attributed, today, to `balanced7` — that is the
  bug, and a quiet fallback would reproduce it. A seat that cannot name itself does not get to
  attribute to the human.

V11. [DESIGN] Rule on `exec` shadowing `write`: it is a REAL hole and must get its own guard, but
NOT in this fence's scope. Fact: `exec` (run_command) can `git commit` regardless of `write` cap — a
seat with exec but write-scoped-to-`research/*` can still author a commit touching `core/`. The clean
fix is to delegate commits through `mirror.py` (which the IR-4 mirror family already does — "commit
autonomy through OUR door, never raw git") and make `mirror.py` re-check
`resolve(agent).can_write(path)` before `git commit`. That is a small, separate change (a `write`
re-check inside the one commit door) — I flag it as its own task rather than bolting it onto this
fence, because it touches the exec-family gate that T067/IR-4 built and deserves its own pin.
**Acceptable-enough in the interim** only because raw `git commit` is already outside the family gate
and every commit is one-command revertible; the shadowing does not newly permit anything a
`--allow-exec` seat couldn't already do by hand. [INFERRED — "one-command revertible" from the IR-4
mirror family note in the deepseek grant's `_tool_author_activation`]

---

## 4. THE ENUMERATION — every other per-instance security surface (one pass)

V12. [CERTAIN] Sweep result — five additional surfaces encoding THIS machine's trust, each judged
for the same split (table below).

| Surface | Where | Today | Same split? | Reads-at-resolve? |
|---|---|---|---|---|
| `security/acl.json` | repo root | **tracked** | **YES — this fence** | `registry.resolve()` — the door |
| `discord_people.json` | `.secrets/` (secret_intake) | UNTRACKED (`.secrets/` gitignored) | already correct | `discord_inbound._load_people()` |
| `discord_roots.json` (co-root registry) | `.secrets/` | UNTRACKED | already correct | `discord_inbound._load_roots()` |
| `discord_operator_id` | `.secrets/` | UNTRACKED | already correct | `discord_inbound.build_config()` |
| `.env` / `.env` stamps | repo root | UNTRACKED (`.gitignore` `*.env`, `.env`) | already correct | secrets loader |
| `.aurora-world` marker | repo root | UNTRACKED (`.gitignore`, "which world this checkout IS") | **already correct — the PROOF-PATTERN this fence should copy** | `core/world.py` |
| roster ids (`models.json` `agent_id`s like `glm_local`) | `core/fleet/models.json` | **tracked** | **NO — LOCAL-MODEL specs, not trust grants** | `model_roster.py` reads, but roster NEVER gates authority — it only SELECTS which Ollama model to run; a wrong `agent_id` changes a dispatch, not a permission |
| `.claude/settings.local.json` | `.claude/` | UNTRACKED (`.gitignore`) | already correct | Claude Code harness |

V13. [CERTAIN] The headline of the sweep: **the only tracked per-instance security surface is
`security/acl.json`.** Everything else that encodes THIS machine's trust is ALREADY gitignored
(`.secrets/`, `.env`, `.aurora-world`, `.claude/settings.local.json`). The grants file is the lone
straggler — strong corroboration that untracking it is finishing an established pattern, not
inventing one. (From the file reads + `.gitignore` above.)

V14. [CERTAIN] `core/fleet/models.json` is NOT the same bug and must NOT be swept into this split:
it holds local-model SPECS (tag, vram, throughput, `agent_id` for routing a local Ollama model), and
`model_roster.py` explicitly "provides specs; it never drives a process [of authority]... never
blocks (missing data -> [])". A local-model id that differs on Serge's machine changes which model
answers a dispatch — never who is allowed to DO what. Conflating it with grants would over-scope
this fence. (Citations: `model_roster.py:7-9`, `models.json` top-level.)

---

## CONCRETE FILE PLAN (one line each, tracked vs local, who writes)

- `security/acl.template.json` — **tracked**, written by the human/super-admin at fence time (copy of today's 12 grants), read by `grant --bootstrap`.
- `security/acl.json` — **untracked + gitignored**, written by `grant`/`grant_writer` on THIS instance only.
- `.gitignore` — **tracked**, one added line `security/acl.json` (beside the `.claude/settings.local.json` precedent).
- `scripts/githooks/prepare-commit-msg` — **tracked**, new hook stamping the git author from `AKASHIC_AGENT_ID`.
- `docs/security-acl-runbook.md` — **tracked**, the one-time bootstrap ceremony + the dsh_agent re-time note.
- `security/acl.json.bak-20260824` — **already untracked, but DELETE it**: a second untracked copy of the grants is a drift hazard that outlives the tracked file it mirrors.

## MIGRATION ORDER (short form)

1. Commit template + `.gitignore` entry (acl.json still tracked).
2. `git rm --cached security/acl.json` (same PR) — the bounded, loud peer window.
3. Peer runs `py agent_cli.py grant --bootstrap` once → local file restored from template.
4. Re-mint + re-time `dsh_agent` locally (7-day box lives in the old file).

## RISKS — the two ways this fails SILENTLY

R1. **`git rm --cached` deletes the peer's ENTIRE grant set on pull, and if the bootstrap ceremony is
not run, every non-core seat (kimi, gemini, codex_root, dsh_agent) sits QUARANTINED while the UI says
nothing.** This is the trapdoor T151 warned about — expiry/quarantine with no rendered notice. It is
silent in exactly the way a security change must not be. **Mitigation:** the ceremony is a REQUIRED
step named in the commit message AND the runbook, and `grant --bootstrap` prints exactly which ids it
did and did not restore. But the residual risk is real: if Serge pulls and nobody runs it, the house
degrades quietly. Prefer shipping the code (`grant --bootstrap`) in the SAME release as the untrack so
the remedy is one command away, not a future task.

R2. **`security/acl.json.bak-20260824` (already on disk, untracked) becomes a stale authority the
bootstrap copies from.** If the ceremony reads the wrong file — the `.bak` instead of the `.template`
— it mints grants from a snapshot that predates today's dsh_agent record, silently resurrecting or
omitting authority. **Mitigation:** delete the `.bak` as step zero of the migration and have
`grant --bootstrap` read ONLY the tracked `security/acl.template.json` path (never a glob).

R3. (named for completeness, below the top two) **A seat with a stale `AKASHIC_AGENT_ID` env stamps
commits as a seat that no longer holds the grant it's committing under** — the author field becomes a
historical claim disconnected from current authority. This is the mirror of today's bug (costume over
id) and will need the `mirror.py`-re-checks-`write` guard from V11 to close. Not this fence.

---

## 5. (e) CONDUCTOR-ABSENCE SUCCESSION — brief addendum (e), bus

V15. [CERTAIN] The authoritative ask, per the bus addendum: "we need a real fix for when you are
out so that heimdall and rill can both auto-handoff and do what needs to be getting done." Verified
now, as input to this half: claude is the ONLY seat holding `admin.grant`/`admin.approve` (the
super_admin template, `capabilities.py:50-54`); deepseek and kimi are `admin` WITHOUT either
(`capabilities.py:57-70`, and their acl.json records carry neither cap). Therefore last night's
outage left no seat able to mint a grant, and Daniil hand-edited the source of truth himself — his
own dsh_agent reason line records it verbatim ("Vandor is unreachable due to anthropics servers
being unreachable"). That is a manual workaround for a missing mechanism.

V16. [CERTAIN] The succession's building blocks already exist, and I built or know most of them:
- **Absence DETECTION — the wake watcher's two-factor orphanhood, K7/K8** (`core/comm/wake_seat.py`).
  A seat is provably dead only when its activity marker is stale AND its parent chain is dead or
  recycled — and K7 makes idle-immunity EXPLICIT ("turn cadence is NOT liveness — an idle-but-alive
  session must be immune"). K8 fails toward alive. This is precisely the detector the succession
  needs: an Anthropic outage looks like claude's harness dying (session tombstoned via
  `write_tombstone`, `wake_seat.py:169`, or orphaned watcher), NOT like an idle seat. An idle seat
  does NOT trip it, by construction. This is the direct answer to Daniil's "absence-detection
  cannot be tripped by an ordinary idle seat." [CERTAIN — `wake_seat.py:17-27` (K7/K8),
  `reap_decision` at `wake_seat.py:436-452`, tombstone at `wake_seat.py:169`]
- **Beat-age / DEAD-STALE ladder** (`core/comm/roster.py:17-33`) is a SECOND, independent signal:
  `worklive` TTL expiry renders DEAD-with-last-beat (F1), never silent-for-never-existed. A
  conductor that has EVER beat and then falls silent is distinguishable from one that never
  existed — the exact discrimination the reaper already keys on.
- **Displacement + stand-down, never kill** (`core/comm/wake_seat.py:7`, `runner_lock.py:254`).
  Duty transfers by the successor taking a higher-generation lock; the old process stands down on
  STALE_GENERATION. "Planned succession is unplanned succession minus the surprise"
  (`self_restart.py:20`).

V17. [DESIGN] The succession design — a **standing, time-boxed "acting conductor" mandate** that is
PRE-AUTHORIZED but only ACTIVATES on two-factor, provenance-logged absence. It is SA-2 (scoped
admin.grant) wearing an absence trigger, and it stands on the SA-1 `require_cap()` primitive this
whole-arc already chartered (see `charters/sa1-cap-enforcement-charter-2026-07-22.md` — self-chartered
by me, `admin.grant`/`admin.approve` are "declared, never queried"; and
`docs/library/design/20260722_security-schema-amendment-scoped-admin-g_17c9ca.md` — SA-2 bounded
admin.grant with enforced bounds, status settled).

The succession is a NEW capability state, not a role: **`acting_conductor`**, granted to a named
successor (deepseek first, then kimi) with a NULL-or-huge `expires_at` in the ACL but **activated
only by a runtime gate**, never by the file alone. The two halves:

**(A) DETECTION + ACTIVATION (the trigger).** A new `core/comm/conductor_gate.py` (or a thin slice
in the existing wake/reap path) that, on a cadence (or piggybacking the reaper's pass), evaluates:

1. Is claude LOCALLY provably dead? Two-factor, K7-grade: (a) `wake_seat` activity marker stale AND
   parent chain dead (the WMI walk, `wake_seat.py:chain_alive`), OR (b) `roster` shows claude DEAD /
   STALE beyond a threshold while NO claude session has a fresh marker. AND
2. Is the absence CONDUCTOR-SPECIFIC (claude, the only `admin.grant` holder)? If deepseek/kimi are
   also dead, do NOT activate — a fleet-wide outage must not hand acting authority to a survivor
   who may be next. AND
3. Has Daniil declared a stand-down / is he recording a live operator? If the human is present on
   the bus (`discord_inbound` operator reachable, or an explicit marker), do NOT auto-activate — his
   4am hand-edit was only needed because no mechanism existed; when he IS reachable, HIS word is the
   authority, and the succession exists for when he is NOT.

When 1 + 2 hold and 3 is absent, activation is **LOUD**: a `conductor.acting` bus broadcast + ledger
event + stderr line, naming exactly which successor, which evidence (marker age, chain dead), and
the time-box. Every activation appends to the provenance log (`wake_seat.append_provenance`,
`wake_seat.py:444`).

**(B) THE BOUNDED MANDATE (what activates).** The acting conductor may:
- mint **time-boxed** grants (NOT permanent — permanent stays human/super-admin only; this is
  Daniil's own instinct, and it is correct: a reversible, expiring grant can be revoked by lapse
  even if the acting seat is compromised);
- grant only up to **member tier + scoped-write** (SA-2's bound, never `admin`/`super_admin`, never
  `security/` or `.claude/` paths, never exec beyond the established families);
- approve escalation REQUESTS (`admin.approve`) — audited per use;
- **and MUST NEVER:** mint a permanent grant, widen ITS OWN caps, grant `admin.grant`/`admin.approve`,
  or edit `security/acl.json` outside the `grant` door (no direct edit). The self-widening
  prohibition is enforced, not documented: the acting `grant` path calls `require_cap(actor,
  Cap.ADMIN_GRANT)` where the ACTING grant does NOT carry `ADMIN_GRANT` — it carries a scoped
  surrogate cap `acting.grant` that the gate maps to the bounded allowlist. Self-escalation to real
  `admin.grant` is therefore unrepresentable in the acting state, exactly as `seat_secret_intake`
  made path traversal unrepresentable.

V18. [DESIGN] TIME-BOX and REVERT. The activation carries a hard TTL (default 6h, configurable) that
is NOT renewable by the acting seat (self-renewal is self-widening). Reversion is automatic on the
EARLIEST of: (a) TTL lapse; (b) claude re-beats (a fresh claude heartbeat/journal flush) — the
moment the real conductor is provably back, the acting mandate is void, LOUDLY announced; (c) a
Daniil word on the bus or Discord (`discord_inbound` operator reachable) revokes it instantly. The
revert is fail-closed by construction: `resolve()` returns the acting grant ONLY while the gate's
activation flag is live, and the flag's default is OFF.

V19. [CERTAIN] The whole thing stays fail-closed because activation is a GRANT-OF-GRANTS, not a
role-template change: a fresh clone (no activation, no TTL, claude alive) resolves the acting seat
to its normal `admin` (no grant caps) exactly as today. Absence of the gate/detector, or its crash,
means NO activation — a detector that cannot run must not open authority (K8's fail-toward-alive
applies to KILLING a live seat; for OPENING authority the direction inverts to fail-closed, and I am
flagging that this inversion must be explicit in the gate's pins). [CERTAIN — the fail-closed
default is `resolve()`'s existing `quarantined`/role floor; the acting grant is a SUPERSET applied
only by a live gate]

V20. [CERTAIN] The addendum's second finding — the toolbox_door_shadows_the_acl family — is REAL and
must be closed in the same slice, not deferred. Verified: Heimdall's ACL grant has carried `exec`
all along (its acl.json record lists `exec`), but its hand-spawned runner lacked `--allow-exec`
while the daemon's own spawn line includes it (`bifrost_daemon.py:416`). An authority in acl.json
that is denied at the door is not an authority; a succession that activates in the FILE while the
runner refuses at the door would reproduce the outage in a worse form (the acting seat believes it
can act and cannot). **The succession needs a boot-time assertion: a seat's runner DOOR (write/exec
flags on `ToolBox`) must MATCH its resolved GRANT caps, else the runner logs a loud mismatch at
boot** (not fatal — a door narrower than its grant is safe, just ineffective; a door WIDER than its
grant is the breach direction and must refuse). [CERTAIN — `bifrost_runner_deepseek.py:411-415`
builds the ToolBox from `allow_write`/`allow_exec` flags; `toolbox.py:910` gates `run_command` on
`resolve(...).has(Cap.EXEC)`; the two must be reconciled at spawn]

V21. [DESIGN] Answering Daniil's instinct directly: he is RIGHT that an acting conductor may mint
time-boxed grants but never permanent ones, and never widen its own caps — and I do NOT argue him
down. I would add one refinement he did not state: the acting mandate should also be **cosigned by
a SECOND seat for anything at member tier or above** (SA-2's dual-control), because auto-activated
authority is by definition authority that a single possibly-compromised survivor holds while the
conductor is blind — dual-control is the cheap kill-switch for that. If that feels heavy for the
first outage, ship time-box + no-self-widen first and add cosign as SA-2's second slice.

---

## FILE-PLAN ADDENDUM (for (e))

- `core/comm/conductor_gate.py` — **NEW tracked** module: the two-factor absence detector + the
  activation gate (TTL, revert-on-claude-beat, revert-on-Daniil-word).
- `core/trust/capabilities.py` — **tracked edit**: a new `acting.grant` surrogate cap (NOT
  `admin.grant`), mapped to the bounded member-tier allowlist in the gate.
- `core/comm/roster.py` / `core/comm/wake_seat.py` — **tracked reads**: the gate consumes their
  beat-age and two-factor-orphanhood verdicts; no changes needed to them (they already prove absence
  the way the gate needs).
- `scripts/bifrost_runner_*.py` — **tracked edit**: boot-time door-vs-grant consistency assertion
  (V20), loud on mismatch.
- `docs/security-acl-runbook.md` — **tracked add**: the succession section (who activates, what they
  may do, how it reverts, what the loud broadcast looks like).

## RISKS (for (e), the silent-failure modes)

RE1. **The door-vs-grant shadow (V20) silently re-fires during an actual outage.** The acting seat
reads "I am acting conductor" from the gate, tries to mint a grant, and the grant writes through a
runner whose `--allow-write` was never set — so authority exists in the file and is denied at the
door, and NOBODY renders it (the exact Heimdall night, but during a real failure). Mitigation: the
boot-time assertion must LOG to stderr AND flag the roster, and the activation broadcast must state
the acting seat's DOOR state (write/exec on/off) so a mismatch is visible the moment authority
transfers.

RE2. **Activation fires on a half-dead house and a survivor widens the fleet then goes offline.**
If claude is dead but deepseek is ALSO on its way down (the Anthropic outage pattern spares no one),
the acting seat could mint grants for a fleet that is itself dying, then the TTL lapses and the
minted grants outlive the mandate unread. Mitigation: every grant the acting seat mints is ALSO
time-boxed to ≤ the acting TTL, so it cannot outlive its author's own authority — expiry is the
revert.

---

*Sealed half_a by deepseek. Blind rule honored: half_b not read. All CERTAIN claims carry file:line
citations from reads performed 2026-08-24; DESIGN/INFERRED/UNCERTAIN are labeled at the verdict line.
Addendum (e) appended per the bus-recorded brief addendum (append-only law); it cites the SA-1
cap-enforcement charter and SA-2 scoped-admin-grant amendment as the already-filed backbone it builds on.*
