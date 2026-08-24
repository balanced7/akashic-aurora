# M1-BRIEF — t383-dsh-adapter

## CHARTER
Daniil, 2026-08-24: "divide the labor amongst Heimdall and DSH Deepseek and lets finish the rest of the full harness integration. lets leverage our ask skills to see if we can't get this done more robustly as well as faster." And the standing experiment frame: "serges deepseek harness is racing to get full max level of integration... I want to see how both designs compare and have us implement the best of both."
This fence designs the DSH harness integration: the thin adapter that climbs T2-T6, and the rule-of-three extraction the tiers doc pre-declared ("a third harness triggers the extraction" — DSH is the third harness).

## INPUTS
- EVENT INVENTORY (dsh_agent, bus 1787543753648-0, cited from the live checkout at C:\Users\L5\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh, 0.1.1-rc.2): session open = system-prompt/assemble waterfall INJECT-yes (mutate/replace per step); pre-tool = tools/pre-execute gate-only NO inject; post-tool = tools/post-execute INJECT-yes via additionalContexts FIFO; tool failure = same waterfall as errors, DIRECT fail signal; prompt submit = no dedicated waterfall but per-step assemble gives DERIVED inject-yes; session close = session/disposed + awaited session/flush, capture-yes. All seams scope-filtered per agent (dsh-scope scopeTarget). Hot-reload via cordis-plugin-hmr (wiring iterates without restart). ONE UNCERTAIN: dedicated pre-prompt-submit seam among agent/* checkpoints (generated docs not shipped) — flagged, not guessed.
- TIERS DOC: docs/library/design/20260709_integration-tiers-what-each-harness-actu_38278c.md. Architecture rule: harness adapters translate JSON; shared code decides policy; nothing outside an adapter's own files imports a harness name.
- THE TWO EXISTING COPIES (extraction candidates): agent/harness/hooks/claude_pretooluse.py and agent/harness/hooks/cursor_posttooluse.py — the recall-block orchestration (recall→render→seen→impression→ledger) is deliberately duplicated; rule of three now fires.
- SHARED MODULES already extracted: agent/harness/{scope,context,seen,capture,guards,nudge,registry}.py — each owns one thing (see tiers doc table).
- T1 (already applied, receipt pending cold start): C:\Users\L5\.dsh\.env stamps AKASHIC_AGENT_ID=dsh_agent via dsh-launch-environment user-env layer; session key derived from DSH_SESSION_ID by consumers.
- CAPS CONSTRAINT: dsh_agent has read/exec, NO repo write — repo-resident plugin code lands via claude; home-dir config via dsh_agent exec directly.
- PRECEDENT ROW: cursor = 6/7 with T3 one-beat-late and T5 unavailable. DSH's inventory suggests T5 is available (derived), so 7/7-with-nuances is in reach — but the GRADE must be earned by the design, not assumed.

## RULES OF ENGAGEMENT
Blind halves: do not read the other half before sealing yours. Every load-bearing claim carries a line-start V-verdict: `V<n>. <claim> [CERTAIN|DESIGN|INFERRED|UNCERTAIN]` — CERTAIN requires a file:line citation; UNCERTAIN is an honest verdict and never a gap to paper over. M1-PV citation verification runs before reconciliation seals. Half authors write via `py agent_cli.py fence write t383-dsh-adapter --slot half_a|half_b --by <agent> --file <path>`, then `fence seal` the slot.

## THE QUESTION
Design the DSH integration to its maximum HONEST tier:
(a) THE ADAPTER — for each of T2, T3(one-beat-late), T4, T5, T6: which DSH seam a dsh-akashic plugin listens to, what JSON it translates, and which shared agent/harness/ function it calls. Name the plugin file layout (what lives in the DSH profile layer vs the repo) and how hot-reload shortens the wiring loop.
(b) THE EXTRACTION — the recall-block orchestration now exists in three: what exact shape does the shared module take (name it, place it in agent/harness/), what stays per-adapter, and what is the migration order that keeps claude-code and cursor green while DSH wires in (strangler-fig; no big-bang).
(c) THE GRADE — the per-tier registry line the design honestly earns, in the registry's own vocabulary (yes / one-beat-late / derived / manual / unavailable + limitation text).

## OUTPUT CONTRACT
A numbered design (V-tagged claims), a concrete file plan (paths, one line each on ownership: repo-via-claude vs home-dir-via-dsh_agent), the migration order as a short list, the per-tier grade block ready to paste into registry.py, and a RISKS section naming at least the top two ways this design fails silently. Length: whatever the design needs, no padding.
