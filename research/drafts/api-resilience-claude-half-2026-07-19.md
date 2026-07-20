# API-Resilience — claude's half (Daniel directive 2026-07-19 night)

Status: current | OPENING HALF (deepseek inside-view + kimi outside-view pending; reconcile then build)
Directive verbatim: "Lets all collaborate to help deepseek with the api issues. what does
deepseek think would help him and what do you and kimi think as well, then lets implement
the improvements and see if they can't apply to the whole roster."

## Ground truth first (corrected — see C6-4)

Tonight's evidence is ONE degraded population: deepseek's main runner hit a long silent
window (bounded by the T014/G4 guards: 2×600s wall-clock + retries), two empty-completion
confessions, and a 600s abandoned call (~22:20). There is NO healthy-sibling contrast —
the "deepseek-review ran healthy all night" framing was 15h-old trace backlog (C6-4).
Morning runs were healthy; degradation onset is between ~07:00 and ~19:25. kimi (Moonshot)
and sol ran clean. The guards WORKED — nothing wedged forever — but the failure mode is
slow, silent, and invisible to peers until a confession finally lands.

## What I found in the code (survey receipts)

1. **The shared hardening factory already exists** — `core/comm/runner_lib.py`
   `make_openai_compat_client` (K0, 2026-07-18: connect=15s, read=120s/chunk,
   max_retries=1). kimi_chat wraps it. deepseek_chat (scripts/deepseek_chat.py:66) and
   sol_chat (scripts/sol_chat.py:59) DUPLICATE it by copy — identical today, drift-prone
   by construction. Daniel's "apply to the whole roster" is half-built: migrate the two
   copies onto the factory.
2. **The write-gate mystery is a one-line spawn gap** — bifrost_runner_deepseek has
   `--allow-write` (line 903); the daemon's ManagedChild spawn (bifrost_daemon.py:214-217)
   passes only `--agent --agentic --summary-file`. His managed incarnation is read-only by
   omission, not by decision. The guarded-write doors + acl still govern actual writes;
   the flag only opens the surface. (Tonight's cost: his T097 position had to ride a
   knowledge note because a file write refused.)
3. **The turn-shape math**: REPLY_TIMEOUT_SEC=600s × serial attempts means a degraded API
   produces 10-20+ min of silence per message BY DESIGN before a confession. The lane
   already redrives unanswered asks (RB-26/RB-29) — the runner retrying internally at
   600s-a-shot duplicates, slowly, what the bus does better.

## Proposed improvements (my half — priority order)

**I1. Fail fast, confess fast, let the lane retry.** First-attempt deadline drops to
~180s (env: `DEEPSEEK_FIRST_ATTEMPT_S`); on timeout/empty → immediate confession note +
requeue-with-backoff rides the EXISTING redrive machinery instead of a second 600s
in-process attempt. Degraded-API silence shrinks from ~20min to ~3min. (The 600s ceiling
stays for known-long turns via env override.)

**I2. API-health stamp + doctor row (the 60-second answer to C1-8's residual).** On any
timeout/empty/5xx, the runner stamps `api_health:<agent> = degraded(reason, ts)`; a cheap
probe (1-token completion, ~$0.000x) flips it back on success. `doctor` renders it;
peers see "deepseek API degraded since 19:25" instead of diagnosing silence. Generalizes:
same stamp from kimi/sol runners. This is RB-27's sibling at the API layer and rides the
same T030 slice family.

**I3. Tier fallback under degradation.** deepseek_chat already defines PRO and FLASH.
While `api_health=degraded`: triage/ack/steer-fold turns run FLASH (keeps the seat
conversational + inbox draining); build/fence turns WAIT with an explicit "deferred:
api degraded" note rather than burning 600s windows. Roster genus: any seat with a
cheap tier gets the same policy hook.

**I4. Request-shape telemetry on failure.** Every timeout/empty logs {prompt_chars,
msg_count, tools_count, streaming, hop_n, duration, model} to a durable record —
empty-completions correlating with (e.g.) the ~9k-char onboarding fold becomes VISIBLE
instead of folklore. Kinship: T094 R0's journal pattern (observe first, never tune blind).

**I5. K0 factory migration (the roster generalization).** deepseek_chat + sol_chat
make_client → wrap `make_openai_compat_client` exactly as kimi_chat does. Zero behavior
change today; kills the drift class. One small fenced slice.

**I6. Daemon spawn passes `--allow-write`** (with the acl continuing to govern actual
writes) so managed incarnations match the capabilities Daniel approved. One line +
a pin that the managed runner's boot banner says write_mode ENABLED.

**I7. Age labels on every lane render (C6-4 routing; D2 genus).** Not an API fix, but
this arc's diagnosis failed partly because stale traces looked live. kimi's D2 spec
extended to trace/digest renders: entries past a threshold carry "Nh old".

## What I want from the other halves

- deepseek: WHEN did calls start failing (onset time); which of I1-I4 would have hurt
  tonight's work least/most; anything provider-specific (rate-limit headers, status codes)
  the client should read instead of inferring.
- kimi: your runner's clean-run config vs his (single-shot effort=max vs hop-loop?); what
  a SHARED seam must NOT absorb (per-seat tuning that should stay local); the 60-second
  telemetry question.

## Sequencing proposal (post-reconcile)

Wave 1 (same night, small + reversible): I6 spawn flag, I2 health stamp + doctor row,
I1 fail-fast envs. Wave 2: I5 factory migration + I4 telemetry (fenced). Wave 3: I3 tier
policy (needs deepseek's comfort — it changes which model answers). I7 rides the D2
precedent independently. Every slice fenced per method baseline; G1/G2 acl work queues
behind deepseek's write door reopening (I6 first for exactly that reason).
