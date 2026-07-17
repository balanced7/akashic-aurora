# T060 Moonshot + Networking Spine — Three-Frontier Fence Brief

Status: active brief (2026-07-17)
Task: T060, claimed by `codex_root` on Daniel's live directive
Fence tier: FULL — packet routing is a cross-agent coordination primitive

## 1. CHARTER

Run a three-frontier, method-diverse design fence to determine the smallest safe dependency spine that turns the existing packet substrate into demonstrable progress on M1 continuous presence, M6 fleet self-division, and M7 glass cockpit.

## 2. INPUTS

This is DESIGN ONLY for the new spine; no new implementation exists. Cite only existing code or the design artifacts listed here, and label design-level claims as DESIGN.

Shared required inputs:

- `docs/method-baseline-2026-07.md`
- `research/reviewed/wishlist-synthesis-2026-07-14.md`
- `docs/packet-spec-v1-2026-07.md`
- `docs/packet-substrate-slices-2026-07.md`
- `docs/packet-routing-design-2026-07.md` — reopened; §U is blocking
- Governed task ledger via MCP `task(args="list")`

Lens-specific prior evidence is allowed because it predates this fence:

- Fable/Claude: `research/reviewed/claude-moonshot-enablers-2026-07-16.md`
- DeepSeek Review: `research/reviewed/deepseek-review-moonshot-enablers-2026-07-16.md`
- Sol/Codex: native MCP receipts from `boot`, `status`, `task`, `bifrost_presence`, and `bifrost_send`; the failing MCP `notes` receipt must remain visible

## 3. RULES OF ENGAGEMENT

- Work from separate contexts. Do not read either peer's new half until your own half is filed.
- Use different methods: Fable/Claude is the architecture/dependency lens; DeepSeek Review is the runner-side adversarial/kill-drill lens; Sol/Codex is the MCP-native newcomer/operator/integration lens.
- Do not edit shared design or source files during the blind round. Each author locks and writes only its assigned output path.
- Every material verdict carries exactly one confidence tag: CERTAIN, DESIGN, INFERRED, or UNCERTAIN.
- Resolve §U items U1–U5 from `docs/packet-routing-design-2026-07.md`, or state the exact evidence still required.
- State contraindications and honest bounds. In particular, identify what must not build before T047 or T046.
- Reconciliation begins only after all three halves exist. Its first step is the mandatory M1-PV citation/path verification pass over every file and line reference.
- No implementation begins from this fence alone. The reconciled build spec must name the pre-registered failing acceptance and kill drills; Daniel's gate governs any load-bearing build.

## 4. THE QUESTION

What is the minimum two-to-three-slice dependency spine that turns the live packet substrate into useful M1 continuous presence, M6 fleet self-division, and M7 glass-cockpit capability under three MCP-native frontier models, without violating the T047 legacy-retirement and T046 latch gates? Which slice should build first, what exactly does it include and exclude, how are U1–U5 ruled, and what executable acceptance and kill conditions would falsify the design?

## 5. OUTPUT CONTRACT

Blind halves:

- Fable/Claude: `research/drafts/moonshot-network-spine-fable-2026-07-17.md`
- DeepSeek Review: `research/reviewed/moonshot-network-spine-deepseek-review-2026-07-17.md`
- Sol/Codex: `research/drafts/moonshot-network-spine-sol-2026-07-17.md`

Each half must contain:

1. A two-to-three-slice dependency spine with a ruling for why that order is necessary.
2. An explicit U1–U5 verdict table.
3. The smallest first slice, including exact inclusions, exclusions, and contraindications.
4. Named pre-registered acceptance tests plus at least one live or crash/kill drill.
5. Honest bounds for one machine, one Redis, and fewer than ten agents.
6. Native MCP receipts: which Aurora tools were actually called and which failed.

After filing, reply on Bifrost with only the output path, top three decisions, and MCP receipts. The reconciler writes `research/reviewed/moonshot-network-spine-reconciliation-2026-07-17.md` with M1-PV results first, then CONVERGED / COMPLEMENTARY / DIVERGENT rulings and a build-spec gate.
