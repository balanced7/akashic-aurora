# DRILL RECEIPT — mem_watch as a scheduled black box, now with the commit gauge

**Date:** 2026-09-24, about 21:11 EDT (01:11 UTC on 09-25)
**Organ:** `scripts/ops/mem_watch.py` (upgraded in 934b3acd, plus the v2 row stamp), run by the scheduled task
`AkashicAurora-MemWatch` (`scripts/ops/install_mem_watch_task.ps1`)
**Drilled by:** claude (Vandor), on Daniel's go-ahead: "Yes to 1 and 2".
**Result:** PASS for every path listed under Method. The logon trigger across a real reboot is NOT drilled yet.

## Why this exists

At 20:15 on 2026-09-24 Windows logged a low-memory event. The cursor dropped to about 1 fps and Daniel cut the
power at about 20:24. The recorder built on 08-26 for exactly this moment named nothing, for two reasons.

1. **It was not running.** It had been launched by hand. Its last sample was at 2026-09-07 17:37, the minute of a
   reboot, and nothing ever started it again. That left the house blind for 17 days, through the 09-11
   kernel-pool outage, the 09-16 hard reset and the 09-24 freeze.
2. **It watched the wrong gauge.** Its own trail covers two of the Resource-Exhaustion hits:
   - 09-04 01:53: the sample at 01:52:51 shows 21.2 GB of RAM still available.
   - 09-06 02:33: the sample at 02:33:12 shows 14.0 GB still available.

   Windows' detector reads COMMIT: memory charged against RAM plus the pagefile, about 124 GB here. Commit that
   is charged but not resident never shows up in RSS.

## Method and observations

1. **Pins, red first.** `tests/test_mem_watch_commit_recorder.py` was committed alone in 7c7cf99a: 11 of its
   tests failed and the 7 ratchet pins passed. After 934b3acd all 18 passed, and all 18 still pass after the
   v2 stamp.
2. **One-shot sample plus a forced snapshot into a scratch log.** The sample recorded:
   - commit 44,219 / 126,579 MB (34.9%);
   - kernel paged pool 2,957 MB and nonpaged pool 2,525 MB;
   - 272,691 handles and 11,015 threads;
   - top pool tag SW03, 518.7 MB nonpaged.

   The snapshot was 119 KB and one row was 11.4 KB. The run took 3.4 s, including interpreter start.
3. **`install_mem_watch_task.ps1`.** The heal trigger repeats every PT15M with an empty duration, which means
   indefinitely. MultipleInstances=IgnoreNew and ExecutionTimeLimit=PT0S.
4. **Start.** A new row appeared in `state/mem-watch/mem_watch.jsonl` at 2026-09-25T01:11:03Z with v=2,
   commit 45,194 / 126,579 MB (35.7%), 16 pool tags, 16 top rows and 273,288 handles. The task reported Running
   (267009), with one pythonw instance, pid 52972. Success was judged by the durable row, not by the process
   table.
5. **Second start while it was alive.** There was still one instance, pid 52972, so IgnoreNew holds.
6. **Kill and re-trigger.** Killing pid 52972 left 0 instances. A start, which is what the 15-minute heal
   trigger does, brought up pid 50424 and a new v2 row at 01:11:25Z.

## NOT proven — read before trusting

1. **The logon trigger has not fired yet.** The next reboot proves it or doesn't. Until then the 15-minute heal
   trigger is the only proven restart path.
2. **Real pressure has not tested the commit WARN/ALERT or the pressure snapshots.** The snapshot writer was
   drilled with `--force-snapshot`. The 80/90/88% thresholds have never met a real squeeze.
3. **Under pyw, the stdout ALERT lines go nowhere.** Alerts survive only as the `alerts` field of each JSONL
   row, and nothing reads them live yet. A recorder with no reader is half an organ. The live consumer
   belongs to the fleet memory-pressure design Daniel is still thinking over ("I want to think of a more
   elegant solution").
4. **Rotation (32 MB x 3) has still never been seen running.** This carries over from the 08-26 receipt. At
   about 11 KB per 5-minute sample, the first rotation is about 10 days out.

## Fence

The DeepSeek review is pending. It will be appended here verbatim when it lands.
