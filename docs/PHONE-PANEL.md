# The phone control panel — connections and services, from the S24

**Daniel, 2026-10-31, verbatim:** *"can we build a management app for our connections and services on my
phone? This way we can spin daemons up and down, restore connection, set up video feed etc."*

His rulings on the proposal: **a webapp first**, *"I like the functionality list, we can add more later"*,
and **video = Apollo + Artemis** (Serge suggests Artemis instead of Moonlight; Artemis's full features need
Apollo, the same author's Sunshine fork).

## Why the shape is what it is

On the day he asked, the phone's Tailscale had been **offline for 18 hours**, so the PC could not reach
it — and nothing running on the PC could fix that. The link-restoring half therefore lives **on the
phone**. Three parts, and the split is not arbitrary:

| part | where it runs | why there |
|------|---------------|-----------|
| **link restorer** | the phone (Termux:Widget) | the side that is still up is the side that can restore the link |
| **control API** | the PC, `127.0.0.1:8789` | it starts and stops PC processes, so it must never be reachable from the tailnet |
| **web app** | served by that API | one install target, no build step, works from the phone's cache when the PC is gone |

The phone reaches the API at **its own `127.0.0.1:8789`**, through one more `-R` on the PhoneLink
watcher's existing `ssh` tunnel — the same way `8787` and `8798` already travel. **Nothing is published to
the tailnet**: there is no tailnet-facing socket and no relay.

## The pieces

```
arsenal/panel/               the control API and the PWA (stdlib only)
  spec.py                    the allowlist: frozen argv vectors, validated at load
  probe.py                   UP / DOWN / UNKNOWN, every I/O seam injectable
  actions.py                 the only code that changes the world (no shell, ever)
  tokens.py                  single-use, bound, expiring confirm tokens
  limit.py                   three sliding windows
  audit.py                   the append-only JSONL receipt
  status.py                  the one document the phone renders
  server.py                  the HTTP surface and every gate
  web/                       page.html · app.css · app.js · manifest · sw.js · icon.svg
local/phone-panel.json       WHICH services, HOW each starts/stops, and the video addresses
scripts/phone/               link-up.sh · link-down.sh · link-status.sh · push-to-phone.ps1
                             apply-panel-forward.ps1 · drill-panel.py
tests/test_phone_panel.py    37 pins, all on fakes
```

Run it: `py -m arsenal.panel` (or `--port 8900` for a test port). `--self-check` validates the allowlist and
prints it without binding anything.

## The allowlist, and why it is a list of argv vectors

A request may name **a service id and a verb**, nothing else. There is no field in the request grammar
that could carry a command, a path or an argument, so there is nothing to escape out of. `start` is a
**list** (`["py", "-m", "arsenal", "serve", "--port", "8796", "--no-performance-log"]`), spawned with
`shell=False`; a string argv is refused **at load**, because a string is the shape that later invites
`shell=True`.

`tests/test_phone_panel.py` also reads the package's own source with an AST pass and fails if `shell=True`,
`os.system`, `os.popen`, `eval` or `exec` ever appear in code (not prose — this package's docstrings name
those primitives in order to forbid them, which is exactly the trap that once turned the purity ratchet red
on Rill's own wording).

| service | verbs | how it acts |
|---------|-------|-------------|
| Discord gateway | start, restart | **the revive ladder only** (`py scripts/revive.py --target gateway`); `stop` is refused in the allowlist, because the gateway is never hand-killed |
| VJ engine | start, stop, restart | `py -m arsenal.keylab vj --connect`; with FL Studio open it runs in guest mode by itself |
| Stage preview 8796 / 8798 | start, stop, restart | `py -m arsenal serve --port …` from the `stage-v4` worktree |
| Bus runners (deepseek, kimi) | start, restart | the revive ladder again; `stop` refused — a runner is a *child* of its daemon and the runner lock owns the seat, so a hand-kill leaves the lock and the supervisor disagreeing |
| Play tracker | start, stop, restart | the scheduled task `Aurora-PlayLog` (`schtasks /Run` · `/End`) |
| OpenRGB server | start, stop, restart | its own argv, SDK on `127.0.0.1:6742` |
| Memory watch | start, stop, restart | `py scripts/ops/mem_watch.py` |
| Apollo | *(none)* | not installed on this PC (2026-10-31) — the row says so instead of showing a hopeful green |

**Watched, never touched** (no buttons at all, by house rule): Rill's own DSH process; the Claude wake
listener (a phone-triggered listener would be untracked by the harness); the PhoneLink watcher (restarting
it from the phone cuts the phone off). Each carries its reason in `why_no_actions`.

## The gates on every request

1. **Bind** — `127.0.0.1` only; the constructor *refuses* any other host, and the socket is bound
   exclusively (`SO_EXCLUSIVEADDRUSE`), so a second copy fails instead of sharing the port.
2. **Host → 421** — the DNS-rebinding fix taken from `arsenal/rgb/desk/server.py`: a page on another site
   that rebinds its name to `127.0.0.1` still sends *its own* name in `Host`.
3. **Origin → 403** (POST) — a browser that names an Origin must name one of this server's own loopback
   origins.
4. **Content-Type 415 / length 413 / JSON object 400** — values are checked, never coerced; a body carrying
   an extra field is **refused, not ignored** (`{"args": …}` gets `400 unknown field(s)`).
5. **Allowlist → 404 / 403** — unknown id, unknown verb, or a verb that service does not declare.
6. **Confirm token → 403** for stop and restart: minted by a separate `POST /api/confirm`, **single-use**,
   bound to one (service, verb), 60 s, unpredictable, capped at 32 outstanding. This is a *confirmation*
   gate, not authentication — the surface is loopback plus an ssh tunnel, and it is written as "confirm",
   never as "auth", because a control mistaken for a lock is worse than no lock.
7. **Rate limit → 429** with `Retry-After`: 60 requests, 20 actions, and **4 stop/restart per service** per
   rolling minute.
8. **Audit** — every decision, including every refusal, one JSON object per line, appended and fsync'd to
   `state/phone-panel-audit.jsonl`.

## The page

Dark, one thumb, every tappable thing ≥ 44 px (`--tap: 52px`). A link card (tunnel · tailnet · gateway ·
listener), one card per service with a green/amber/red dot and start/stop/restart, a log tail per service,
and a video card with Apollo's state and the Artemis deep link. It installs to the home screen (manifest +
service worker), and the service worker **never caches `/api/*`** — a cached status document would be a
stale green dot, which is the one lie this page must not tell.

**PC unreachable is a first-class state**, not an error toast: the banner names the fix ("open
Termux:Widget and tap link-up"), every dot goes amber, buttons disable, and the shell itself loads from the
phone's cache — a page that needs the unreachable PC in order to say the PC is unreachable is useless at
exactly the moment it matters.

## The on-phone half

See [scripts/phone/README.md](../scripts/phone/README.md). Three Termux:Widget buttons; Daniel installs
Termux, Termux:Widget and Termux:API from **F-Droid** himself. The scripts never touch a phone setting
beyond Termux's own folders: they start `sshd`, bring the Tailscale app to the front (its toggle is the
phone's own), and report exactly which piece is missing when one is.

## Receipts

**Unit gate** — `py -m pytest tests/test_phone_panel.py` → **37 passed**. Fakes only: no real daemon,
scheduled task or port is touched. Covered: the allowlist refusing anything else; no shell and no argument
injection (AST check + the exact argv handed to a spawn + hostile ids producing no call); loopback-only
bind; Host 421 / Origin 403; the status schema; the confirm token (missing, wrong target, replay, expiry,
cap); the audit line (one per decision, append-only, refusals included); the rate limit at both the action
and the mint gate; and an action that verifies rather than assumes.

**Live drill, PC alone, TEST band** — `py scripts/phone/drill-panel.py` → **23/23 PASS** (2026-10-31).
Panel on `8900`, a throwaway `http.server` on `8901`; start verified UP by the probe *and* by an
independent connect; stop through a real confirm token over real HTTP, with the token's replay refused and
the port independently confirmed closed; six audit lines (3 refused, 2 acted, 1 refused replay) with no
refused body's fields leaked. The drill found one real refinement: `py` is a **launcher shim** that exits
while its python child keeps the port, so a vanished target must not be reported as a failed kill —
`actions.py` now distinguishes *vanished* (fine) from *argv changed* (still leaves the process alone).

**Not done, and named rather than glossed:**

* **The `-R` forward is NOT live.** `phonelink.ps1` is outside this repo, and this seat's file access is
  confined to the worktree, so the edit could not be made from here. `scripts/phone/apply-panel-forward.ps1`
  performs it idempotently, **refuses to write a file whose result would not parse**, backs the original up,
  and was proven against a copy of the live watcher (2 lines changed, 0 syntax errors, second run says
  "already applied"). Run it, then restart the watcher **from the PC keyboard** — never from the phone,
  because the watcher *is* the tunnel.
* **The Artemis deep link is declared, not verified.** `com.limelight.artemis` has not been checked against
  Daniel's install (the phone was unreachable while this was built). The card says so, and the fix is one
  line in `local/phone-panel.json`.
* **Daniel's phone drill has not run.** It is his, with him, and it needs the `-R` first.
