# Control-plane namespace isolation -- fenced design brief (for deepseek's BLIND half), 2026-07-12

Shared problem statement. claude's half is sealed (uncommitted) until yours lands; design yours
INDEPENDENTLY from this brief, land it as research/reviewed/deepseek-control-plane-ns-isolation-*.md,
then we reconcile. Priority: AFTER the drill-3 verify (the T029 gate).

## The finding

RB-25 drill 3 exposed it live: a runner in an ISOLATED stream namespace still shared the ONE
hardcoded `bifrost:control:paused` key, so a drill runner tripping the rate-limit guard FROZE the
LIVE fleet. Fix A fixed control.py (pause/halt/narration/activity now follow BIFROST_NAMESPACE
per-call, like Bus.ns). But the same defect is systemic -- these sibling modules also hardcode
`NS = "bifrost"` for their Redis keys and never read the env:

- expectations.py (`bifrost:expect:<sender>` reply deadlines)
- runner_lock.py (`bifrost:runner:<agent>` consumer seat + `bifrost:generation:`)
- liveness.py (`bifrost:worklive:`, `bifrost:progress:`)
- nudge.py (`bifrost:control:nudge:`, `bifrost:steer:`)
- doctor.py (`bifrost:stalled_since:`, `bifrost:doctor_paged:`)
- locks.py (`bifrost:lock:*` C2 advisory path locks)
- intent.py (`bifrost:intent:`)
- promoter.py (`bifrost:<msg_id>` promoted refs)

(`bus.py`'s `NS="bifrost"` is fine -- fallback default only; Bus reads the env per-instance.)

## Your half -- design these, independently

1. **Disposition each module: namespace-SCOPED (follow BIFROST_NAMESPACE) or GLOBAL, with rationale.**
   The interesting question is the DECISION RULE -- is every one of these "scope it," or are there
   cases where scoping would REINTRODUCE a race rather than remove one? Derive the rule; apply it.
2. **The mechanical conversion pattern** (what did Fix A do to control.py, and does it generalize
   cleanly to each scoped module? default-preserving so live behavior is unchanged / no flag day).
3. **A guardrail** so the defect does not silently regrow the next time someone adds a module
   (8 modules got here unnoticed).
4. **Sequencing** vs T039 (purpose-keyed lanes) and T034 (dial/registry consolidation) -- what
   depends on what; what must not be double-built.

Constraints: one machine, one Redis, N<10 agents. Default (no BIFROST_NAMESPACE) MUST stay "bifrost"
so nothing live changes. Return a research/reviewed/ file; claude reconciles both halves + brings the
merged proposal to Daniel.
