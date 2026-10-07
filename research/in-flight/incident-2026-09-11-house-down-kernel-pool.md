# Incident 2026-09-11 — the house went down: kernel pool exhaustion, WSL relay, Docker unable to start

Written by Vandor (claude seat, session 5ee9c3a7) at about 15:25 local, while Redis was down and the
house's own log, note and handoff verbs could not write. Everything below is measured unless marked.

## Timeline (local time)

- **about 12:13** — new Redis connections over `localhost` start failing. `localhost` resolves to
  `::1` first, and `[::1]:16379` is owned by `wslrelay.exe` (pid 50944, WSL localhost forwarding),
  a more specific bind than Docker's `[::]:16379` (`com.docker.backend`). Each connection opens, then
  resets on read (WinError 10054/10053). Fleet processes that reconnect fail: the deepseek and kimi
  runners and the claude daemon restart around 12:11-12:13; the prod Discord gateway refuses at
  startup and exits 75 every minute (38 refusals, 0 successful listens in the last 400 log lines).
- **14:06** — three-host test, 20 pings each: `localhost` 0 ok, `::1` 0 ok, `127.0.0.1` 20 ok.
  Redis itself healthy: 117 clients, 0 rejected, 122 MB, RDB saves every 5 minutes.
- **14:30** — Vandor ran `redis-cli SAVE` then `docker restart akashic-redis`. It did NOT fix the
  shadow (`::1` still owned by wslrelay) and it DROPPED about 115 working fleet connections, so
  processes that were still working lost their sessions. My action made the outage wider.
- **about 15:05** — Vandor ran a read-only-intended `wsl -d <distro> -e sh -c 'ss -ltnp'` loop over
  every distro. It booted three Stopped distros (Ubuntu-Migrate, Ubuntu-24.04, Ubuntu; the timeout
  killed the clients) and the docker-desktop probe failed with WSAENOBUFS, `Wsl/Service/0x80072747`.
- **about 15:10** — `wsl -l -v` shows every distro Stopped, including docker-desktop.
- **15:20** — Docker Desktop relaunches itself; `docker ps` answers "Docker Desktop is unable to
  start". Redis on 127.0.0.1 times out. The whole bus is down: no seats, no Discord.
  Causation between my WSL probe and Docker stopping is NOT proven; the timing is adjacent.

## The system condition underneath

| measure | value |
|---|---|
| nonpaged pool | 6,579 MB |
| paged pool | 12,788 MB |
| total handles | 414,122 |
| FL64 (FL Studio) handles | 72,045 |
| commit charge | 88.3 of 125.6 GB |
| free RAM | 7.0 GB of 61.6 GB |
| Redis connections accepted in 2 days | 6,788,339 |

WSAENOBUFS means Windows ran out of socket buffers, which come from the nonpaged pool. A few hundred
MB of nonpaged pool is normal; 6.5 GB points at a leak (FL Studio's handle count, or a driver).

## Recovery — Daniel's decision, not a seat's

1. Save any open FL Studio work and close FL Studio. If Docker Desktop still cannot start, reboot.
2. After Docker is up (Redis containers restart on their own, policy unless-stopped): the logon
   scheduled tasks may have exited 2 if Redis was not ready (T394). Start them by hand:
   `Start-ScheduledTask AkashicAurora-DiscordGateway`, `AkashicAurora-SunshineFleet`,
   `AkashicAurora-SunshineDiscord`, `AkashicAurora-GptNewDiscord`.
3. `py scripts/revive.py --observe`; the DaemonWatchdog task restarts E: daemons every 5 minutes.
4. If `localhost` still resets while `127.0.0.1` works, the WSL relay shadow is back: see fixes below.

## Durable fixes worth considering

- Default Redis host `127.0.0.1` instead of `localhost`: `core/world.py:137` (identical in the prod
  worktree), plus `agent_cli.py` and `scripts/world_fidelity.py` hardcodes. No pin asserts localhost.
- Connection churn of about 39 new Redis connections per second: reuse clients instead of
  fail-fast connects per call.
- The revive ladder's redis rung cannot see "container running, port unreachable over localhost".
- Existing proposals T393 (bus-less start), T394 (seat tasks die when Redis is not ready), T395
  (alive is not working).

## Lessons for the seat that did this

- Never loop `wsl -d` across distros as a "read": it boots Stopped distros. Never probe WSL on a
  machine whose kernel pool is exhausted.
- Before restarting a container over a port problem, find who owns the listener. A restart drops
  every working connection and does not touch a relay's bind.
