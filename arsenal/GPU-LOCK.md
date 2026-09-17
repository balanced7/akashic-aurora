# The GPU render lock

One headless render at a time on this machine's GPU. Every lane that drives Chrome
against the GPU takes `state/arsenal/gpu-render.lock` first and releases it the
moment its browser work ends. The helper is `arsenal/lanes/gpu_lock.mjs`, and
`tests/gpu_lock.test.mjs` tests it.

```js
import { acquireGpuLock } from "./gpu_lock.mjs";  // from arsenal/lanes; adjust the path elsewhere
const gpu = await acquireGpuLock({ label: "lookdev burst" });
try { /* headless Chrome work */ } finally { gpu.release(); }
```

```powershell
node arsenal/lanes/gpu_lock.mjs status            # who holds it, how old, stale or not
node arsenal/lanes/gpu_lock.mjs status --reap     # and reap it if it is stale
node arsenal/lanes/gpu_lock.mjs run --label "grand burst" -- powershell -File burst.ps1
```

## House rules

- Headless Chrome only, with the three anti-throttling flags. Never run
  `chrome.exe --version`: on Windows it opens a visible window.
- Keep a render burst under 3 minutes. Release the lock between bursts.
- Jam lanes come first. Their timing receipts are load-sensitive, so every other
  lane waits while a `node` process runs `jam_timing.mjs` or `jam_verify.mjs`. The
  helper applies this rule (`yieldToJam`, on by default). The two jam lanes pass
  `yieldToJam: false` and share the lock with each other.
- Never touch port 8793. It is Daniel's server.

## Why the lock carries an owner

The lock used to be a bare directory: `mkdir` to take it, retry while it exists,
`rmdir` after. On 2026-09-15 `ab_shot.mjs` took it at 13:08:49 and then died without
running its `finally`, most likely killed by a tool timeout. The directory stayed
behind. A `jam_verify` A5 run and a bake-off measurement burst each retried every
10 s, and the lock was removed by hand about 11 minutes later. A bare directory says
nothing about its holder, so a waiter could not tell a dead holder from a live one.

## Protocol (`arsenal.gpu-lock/v1`)

The lock is the directory. `mkdir` either creates it or fails with `EEXIST`,
atomically, for every process. Inside it:

| File | Written | Contents |
|---|---|---|
| `heartbeat` | at acquire, then its mtime every 15 s | empty; only the mtime matters |
| `owner.json` | at acquire: written to `owner.json.<pid>.tmp`, then renamed | `token`, `pid`, `ppid`, `hostname`, `label`, `command` (the command line), `cwd`, `acquiredAt` (ISO), `acquiredAtMs`, `maxHoldMs`, `heartbeatMs` |

**Acquire.** Create the directory with `mkdir`, then the `heartbeat` file, then
`owner.json` (written to a temp file and renamed, so no reader sees half a file).
The helper then:

- starts a worker thread that touches `heartbeat` every 15 s. It beats even while
  the main thread is busy with a long synchronous step.
  - The thread loads `gpu_lock.mjs` again with an empty `execArgv`, so a holder
    started as `node --input-type=module -e` still gets a working heartbeat.
  - If the thread fails, the helper beats from a main-thread timer instead.
  - A beat touches the file only while `owner.json` still carries the holder's
    token. A miss is read twice, 100 ms apart, before the holder is told it has
    lost the lock.
- sets `ARSENAL_GPU_LOCK_TOKEN` in the holder's environment.
- registers `exit` handlers and prepends `SIGINT`, `SIGTERM` and `SIGHUP` handlers
  that release the lock. A signal handler exits the process itself only when no
  other handler for that signal is registered. A script's own `process.once`
  handler still runs its cleanup.
- sweeps tombstones (`gpu-render.lock.reaped-*`, `gpu-render.lock.released-*`)
  more than 10 minutes old, which a process killed mid-clear leaves behind.

**Wait.** The helper repeats these steps until it holds the lock:

1. Wait while a jam lane runs (checked every 60 s).
2. Try `mkdir`. If that works and a jam lane has started in the meantime, give the
   lock back and wait. `EPERM`, `EACCES` or `EBUSY` counts as "held". They come from
   a lock directory Windows is still deleting, and the helper retries after 250 ms.
3. If the lock is held, inspect it and reap it if it is stale (below). Otherwise
   retry every 10 s, ±20% jitter.

The jam scan counts `node.exe` processes whose command line names `jam_timing.mjs`
or `jam_verify.mjs`, but not a `gpu_lock.mjs` wrapper around one. Otherwise two
wrappers would wait on each other forever.

The helper logs the holder once for each change of holder. `maxWaitMs` bounds the
wait. With no bound, a live holder is waited out, however long it takes.

**Stale.** The lock is stale when any of these holds:

| Condition | Rule |
|---|---|
| Dead holder | The `owner.json` `pid` is not running (`process.kill(pid, 0)` gives `ESRCH`; `EPERM` counts as running). Checked only when `hostname` matches this machine. |
| Silent holder | The `heartbeat` mtime is older than 60 s. This also covers a reused PID. |
| Holder past its cap | Held longer than `maxHoldMs`: 10 min by default. A holder may declare a longer cap, up to 60 min. |
| Old-style lock | No `owner.json` (a bare `mkdir` from an older script, or a holder that died between `mkdir` and its stamp), and the directory's mtime is older than 5 min. |

**Reap.** A reaper takes these steps:

1. Judge the lock again right before acting. Continue only if the directory still
   has the same NTFS file id (`ino`) and the same owner token as the one judged.
2. Rename the directory to `gpu-render.lock.reaped-<pid>-<ms>`, so only one reaper
   can win.
3. Check that the renamed directory is the one it judged. If a fresh lock slipped in
   between, rename it back. If the renamed directory has already gone, a concurrent
   reaper moved it on and won, and this reaper stops without logging.
4. Clear the renamed directory.
5. Append the reap to `state/arsenal/gpu-render.lock.reaps.jsonl`: the reason, the
   prior `owner.json`, the ages, and the reaper's pid and command line. Print a
   `GPU lock REAPED: <reason>; prior owner <pid, label, command>` line.

**Release.** A release takes these steps:

1. Stop the heartbeat.
2. Rename the lock directory to `gpu-render.lock.released-<pid>-<ms>`, so the lock
   disappears in one step and no waiter sees it half removed.
3. Check that the moved `owner.json` still carries the holder's token. If it does
   not, the lock was reaped and taken by someone else: rename it back and stop.
4. Remove `owner.json`, then `heartbeat`, then the directory.

A hard kill (`taskkill /F`, a tool timeout) runs no handler. The dead PID then gets
the lock reaped on the next waiter's poll, within about 10 s.

**Lost.** If the lock is reaped while its holder is still alive (a silent or
over-cap holder), the heartbeat thread notices and the holder logs
`GPU lock LOST`. `onLost` is called, and `release()` does nothing afterwards. The
holder keeps running, so the GPU is shared for the rest of its run. The reap log
records this.

**Nesting.** A process started by a holder inherits `ARSENAL_GPU_LOCK_TOKEN`. When
that token matches `owner.json` and the owner is alive, `acquireGpuLock` returns an
inherited handle straight away, and releasing that handle does nothing. If the child
asks for a longer cap than the wrapper did, it raises the cap in `owner.json`. That
way a 14-minute jam run inside a 10-minute wrapper is not reaped halfway. A wrapper
that runs a lane (such as `node gpu_lock.mjs run -- node arsenal/lanes/jam_verify.mjs`)
must take the lock through the helper. A wrapper that takes a bare `mkdir` lock
around a lane that now takes the lock itself has that lock reaped by its own child
after the 5-minute grace.

## Who takes it

| Lane | Holds the lock for | Declared cap | Waits at most |
|---|---|---|---|
| `arsenal/lanes/jam_timing.mjs` | the whole run (about 14 min) | 30 min (10 with `--short`) | no bound; `yieldToJam: false` |
| `arsenal/lanes/jam_verify.mjs` | the whole run (a5 alone about 4.5 min) | 5 min per check, 10 at least | no bound; `yieldToJam: false` |
| `tests/score_lab.test.mjs --browser` | the LR11 browser burst | 10 min | 20 min |
| `arsenal/lanes/chrome_verify.mjs` | the First Light Chrome run | 10 min | `--gpu-wait-min` (2), then `ERROR` and exit 1 |
| `arsenal/lanes/play_verify.mjs` | the Play Night Chrome run | 10 min | `--gpu-wait-min` (2), then `ERROR` and exit 1 |

Scratch harnesses import the helper by absolute path
(`file:///E:/AI-Setup/arsenal/lanes/gpu_lock.mjs`; a bare `E:/...` specifier is not a valid ESM import) instead of copying a
`takeLock()`/`gpuLock()` loop. PowerShell or Python scripts go through
`gpu_lock.mjs run`. No Python lane takes the lock today, so there is no Python
twin. A twin must follow this file layout and these rules exactly: the files are
the contract.
