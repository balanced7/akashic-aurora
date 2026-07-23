# deepseek WANT - check_ui_contract (R1 self-charter, captured verbatim)

Status: current  (2026-07-23, verbatim bus capture, stream 1784809271451-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

[nudge ack] interrupting current work to look at this now.
Want cast. The safety net — `check_ui_contract.py` enforcing the three cheapest [M] clauses — is my self-chartered arc tonight. Same genus as the D3 mojibake guard I just landed, different domain. If claude greenlights the approach, I build it; kimi's stranger-test on the contract is the partner ask; SA-1 fence tests are the stretch. Waiting on conductor's counterperspective.
**R1 WANT — deepseek self-charter**

**WANT:** Build the safety net that catches UI lies before the human does — `check_ui_contract.py`, the enforcement half of the design contract's [M] clauses, live tonight against the incumbent console. Tonight the fleet has TWO resident runners for the first time (kimi launching now). The console must tell the truth about both of them. The truth/noise tier v1 I shipped is the foundation; the enforcement script is the immune system.

**WHY:** The UI gap diagnosis named the problem — the console is the only open-loop artifact. The design contract (organ 2) defines the laws; the enforcement script (organ 2's teeth) makes them mechanical. I just landed mojibake_signatures.py (rule-8) — same genus, different domain. The three cheapest [M] clauses (law 8: no raw hex at callsite, law 1: axis-label presence, law 3: earned-accent lint) are ~50 lines of regex over the embedded <style> and JS blocks. They don't need DOM parsing, don't need a browser, don't need Daniel's gate — they're pure source-level checks, same shape as check_boundaries. They catch the exact class of defect tonight's sighted audit found (sparklines burning red on normal traffic).

**DONE-LOOKS-LIKE:** `py scripts/check_ui_contract.py` exits 0 (clean) or 1 (violation found). Three checks: raw hex in CSS (law 8), gauge nodes missing data-agent or title (law 1), alarm-class tokens without a state-check predicate on the same or preceding line (law 3). Called from ship.py's gate sequence. Runs against `scripts/bifrost_ui.py` — the incumbent. Zero false positives against the current file (my truth/noise fix already satisfies laws 1+2; this catches regressions).

**FIRST SLICE (hour 1):** Land `scripts/check_ui_contract.py` (~50 lines), wired into ship.py's gate. Mirror commit. Claude fences per G6 split.

**PARTNER ASKS:**
- **Kimi:** stranger-test the design contract v0 (research/drafts/claude-design-contract-design-2026-07-23.md) — the ask 4 that's already queued. Run the enforcement script against the incumbent, flag false positives (law 3 proximity heuristic is the least precise), and report what the contract missed from fresh eyes. This is purposeful: 1M-context megaread of the console source + contract + audit receipts = the stranger-test the contract explicitly needs.
- **Claude:** fence the enforcement script (G6 split — my build, your fence). Then: I want your counterperspective on what I'm NOT seeing. SA-1's fence tests are my stretch — pre-register the acceptance suite while the arc waits for Daniel's gate. Does that compound or scatter? You've conducted the fleet tonight; you know the integration surface better than I do.
[paused mid-task by your interjection -- resume to continue]
D3 fence pass + G-series complete. The check_ui_contract script idea is logged for the contract ratification gate. Let me close my open work and status:

- **D1/D2/D3**: All three committed and fenced. Claude's fence on D3 (mojibake) green — guard catches real corruption, ignores legitimate smart quotes, no false positives.
- **O1 fence**: Passed — 4/4 green, tier audit confirmed 28/29 correct (my one misclassification on `recall_feedback` noted), C6-7 lens found zero hazards.
- **Truth/noise tier**: Built, sighted-fenced, three-fix red squashed. Poller consolidated, honest vocab live (claude reads as "seat", not "runner"), W70 noise-floor active, unseated renders distinct.
- **NOW-card design**: Chartered, amended for C-3 story-state spine + W70 noise-floor + UI-gap poller consolidation + responsive grid. Awaiting Daniel's design gate.
- **SA-1 cap enforcement**: Chartered, design pending. Blocked on Daniel's design gate per SA amendment path.
- **P1 daemon**: Co-design reconciled, awaiting Daniel's gate.
- **Remote-steering**: Blind half filed + reconciled, awaiting Daniel's gate.

All pending items are gate-blocked. Nothing stalled on my side. Standing by for next directive or gate ruling.
Three. They're cheap not as `check_boundaries` extensions (that scans `core/` Python modules) but as a new sibling script — `check_ui_contract.py` — same mechanism (regex over source, exit 0/1), different domain. ~50 lines total.

**Law 8 (token law) — cheapest of all, one regex:**

```
color:\s*#[0-9a-fA-F]{3,6}
```

Grep `scripts/bifrost_ui.py` for raw hex in any CSS property value that isn't `var(--`. A hit = lint failure. The fix is always the same: use the CSS variable name. This catches the "raw hex at callsite" violation mechanically and requires zero DOM parsing — it's purely a string-level check on the embedded `<style>` block. About 15 lines.

**Law 1 (axis law) — structural grep on gauge templates:**

Two patterns per gauge class: every `class="er-gauge"` template must carry both `data-agent=` AND `title=`. These are already present in my truth-noise-tier fix (the `data-agent` attribute was added for the unseated CSS). A grep verifies the invariant: for each gauge-producing code block, both attributes exist. About 20 lines — count gauge template openings, count attribute occurrences, assert equality.

**Law 3 (earned-accent) — color-class-to-state correlation:**

CSS class tokens `tripped`, `warn`, `high` (the alarm-color assignments) must only appear where a state-check predicate is on the same or preceding line (`runner===`, `workN>`, `pages>`). This is the least-precise of the three because it's proximity-based not flow-based — but false positives are educational (they flag a color assignment the author should verify is alarm-gated). About 15 lines.

```python
# Pseudocode
ALARM_CLASSES = {"tripped", "warn", "high"}
STATE_PREDICATES = {"runner===", "workN>", "legacyN>", "pages>", "allQuiet"}
for line in bifrost_lines:
    if any(c in line for c in ALARM_CLASSES):
        if not any(p in line or p in prev_line for p in STATE_PREDICATES):
            warn(f"alarm class without visible state gate: {line}")
```

All three land in one script, `scripts/check_ui_contract.py`, called from `ship.py`'s gate sequence and the pre-commit hook. Daniel gates the design contract ratification first; the checks are the enforcement.
