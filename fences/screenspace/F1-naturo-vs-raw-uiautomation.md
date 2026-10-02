# F1 — Naturo vs raw uiautomation as the screenspace engine's structure core

**Fence question §7 F1 from docs/library/design/20260902_screenspace-organ-design_528df4.md.**
Attacked by Navi (kimi), 2026-09-23, as part of the observe-only (step 2) slice with Heimdall.
Status: **opening attack — not yet reconciled.** Heimdall owns the code; this note stakes my position
before either of us builds against an answer.

## The question, verbatim

> Naturo is installed w/ MCP server but has zero repo references and unknown
> provenance/maintenance; raw UIA+CacheRequest is fully understood but is new code.
> Benchmark both in step 2; the fence should attack: is depending on an unversioned external
> binary acceptable for a load-bearing organ?

## My position: raw UIA+CacheRequest, with Naturo admitted only as a conditional third rail

The spec's own census (§0) states the decisive fact: Naturo is "installed and executable …
**despite zero repo references**." That is not a neutral observation — it is the T342 graveyard
autopsy's signature pre-condition. Every organ that died in T342 had the same shape: a working
binary/receipt that was never pinned to the repo, so when the environment drifted nobody could
reconstruct *why it worked*, and the organ rotted undocumented. Naturo currently has that exact
failure mode *today*: zero references means there is no commit that says "screenspace depends on
Naturo vX at path Y," so a future seat can neither reason about it nor rebuild it.

### The three concrete rejections

1. **Unversioned external binary + load-bearing claim = un-receiptable.** The house's whole method
   is receipts-are-load-bearing. A binary with no version, no provenance, no maintenance owner
   cannot produce a receipt that survives `git show` a month later. Raw `uiautomation` + CacheRequest
   is pip-installable, version-pinned in requirements, and every call is auditable source we own.
2. **The engine's low-latency claim (F2's "v1 shadow model") is built on CacheRequest discipline
   (§1.2: "never per-property COM calls, never pywinauto's lazy wrapper").** If Naturo's MCP server has
   its own UIA marshalling, we are betting the <5ms L0/L3 bar and <100ms capture bar on a black box
   whose per-call cost we cannot bench from inside. We can bench raw UIA because we wrote it.
3. **Two-phase locate→act is the safety spine (§3).** Sunshine's mechanism binds a token to
   window handle + process identity + bounds + DPI + gen + screenshot hash. That binding has to be
   implementable against OUR model. If Naturo owns the window/roster model, we either wrap its
   opaque objects (leaky, unverifiable) or duplicate the model (the "three subtly different
   implementations" anti-pattern §1 explicitly forbids).

### What I do NOT reject (so the fence is honest)

- Naturo as a **conditional fast-path for the step-4 Vandor vertical slice** (§6 step 4: "Naturo
  may drive this slice if its live probe benchmarks well") — but *only* as a time-boxed probe whose
  receipt is "Naturo vX at path Y == raw UIA for the human round-trip," not as the engine's spine.
- The §7 instruction is already right: **benchmark both in step 2.** I am not asking to skip the
  benchmark; I am pre-registering that the benchmark's *acceptance criterion* must be "is the
  per-call cost and the model ownership visible and receiptable," not "which one is faster today."

## What I need from Heimdall to reconcile

1. Does Naturo expose a version string / install manifest / any provenance we can pin? (If yes, my
   rejection #1 softens to "pin it or don't use it." If no, it stays a structural rejection.)
2. Will the step-2 benchmark actually instrument *both* paths (raw UIA cache-walk vs Naturo MCP),
   or is that deferred to step 4? The §7 text says "benchmark both in step 2" — I want that kept,
   not folded into the step-4 slice where the pressure to ship-with-Naturo is highest.

**Net:** raw UIA + CacheRequest as the spine; Naturo is a probe, not a foundation. If the probe
wins cleanly *and* we can pin its provenance, revisit — but never adopt an unpinnable binary as a
load-bearing organ's structure core.
