# DRILL RECEIPT — mem_watch growth alert

**Date:** 2026-08-26 ~04:15 EDT (08:15 UTC)
**Organ:** `scripts/ops/mem_watch.py` (built earlier the same night)
**Drilled by:** claude (Vandor)
**Result:** PASS — the alert fired, named the offending pid, and reported growth.

## Why this drill exists

The machine exhausted 62GB the previous night and the forensics found nothing, because
nothing was recording per-process memory. `mem_watch` was written in response. It then sat
armed for ~3 hours in a calm system and never fired once — which proves nothing. House
doctrine: a recovery path ships with an executed drill and a dated receipt, or it is
presumed broken. This is that receipt.

## Method

Watcher, with thresholds lowered so the drill would not require a genuinely dangerous
allocation on a machine that had just died of memory exhaustion:

```
py scripts/ops/mem_watch.py --interval 3 --log state/drills/mem-watch-drill.jsonl \
   --proc-alert-mb 200 --growth-alert-mb 100 --top 15
```

Load, ramped so growth (not just size) is exercised — 12 x 50MB, each block TOUCHED page by
page so resident memory actually grows rather than being lazily reserved:

```
py -c "import time,os; blocks=[]
for i in range(12):
    blocks.append(bytearray(50*1024*1024))
    for j in range(0, len(blocks[-1]), 4096): blocks[-1][j]=1
    time.sleep(2)
time.sleep(12)"
```

## Observed (verbatim)

```
[2026-08-26T08:14:58.358321+00:00] ALERT process python.exe pid=33904 rss=562.1MB (grew +150.0MB since first seen)
[2026-08-26T08:15:04.453650+00:00] ALERT process python.exe pid=33904 rss=612.1MB (grew +200.0MB since first seen)
[2026-08-26T08:15:10.549584+00:00] ALERT process python.exe pid=33904 rss=612.0MB (grew +199.9MB since first seen)
```

Allocator pid was 33904. The alert names it, so the log points at a culprit rather than at a
total — which is the whole difference between this and the blindness that caused the incident.

## What the drill PROVED

- The growth path fires end to end: sample -> high-water compare -> alert line on stdout.
- The alert identifies the process by name and pid.
- The `and` in `rss >= proc_alert_mb AND growth >= growth_alert_mb` does not suppress a real
  climb (the steady-state gigabyte processes on this box stayed silent throughout).

## What the drill did NOT prove — read this before trusting it

1. **Thresholds were lowered.** Production defaults are `--proc-alert-mb 4096 /
   --growth-alert-mb 512`. The drill exercised the same code path at 200/100. The arithmetic
   is identical; the production numbers themselves are untested against a real 4GB climb.
2. **"Since first seen" is not "since process start."** The allocator reached ~412MB before
   the watcher's first sample of it, so the reported growth (+150MB) understates the true
   growth (+600MB). A process that is already large when the watcher starts will report only
   the growth observed AFTER that point. This is honest but easy to misread in a post-mortem.
3. **Not drilled: rotation.** `_rotate()` at 32MB x 3 has never run. The live log grows about
   1MB/hour, so the first rotation is ~32h away and has never been observed.
4. **Not drilled: host-level WARN/ALERT.** Only the per-process path fired; the
   `--warn-pct`/`--alert-pct` host thresholds were never crossed (host sat near 50%).

## Standing

The per-process growth alert — the thing built to name the next 62GB — is DRILLED and works.
Rotation and the host-pressure thresholds remain UNDRILLED and should be treated as presumed
broken until they have their own receipt.
