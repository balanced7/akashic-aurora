# RENEW — two-agent research comparison (Claude × DeepSeek) · 2026-07-07

Compares two independent-ish explorations of the Renew (context-lifecycle) idea:
- **Claude** → `research/reviewed/renew-priorart-2026-07-07.md` (web-grounded external prior art)
- **DeepSeek** → `research/reviewed/renew-deepseek-2026-07-07.md` (off-bus agentic code audit, `renew_deepseek_solo.py`)

## 0. Independence caveat (read this first)
DeepSeek was **partially primed**: it admits (its §16) it opened the "Renew" section of
`docs/agent-membrane-design-2026-07.md` *first*, so the high-level framing agreement (fifth job,
Capture→Surface loop, ~60% built, research scope A–E) is **partly echo, not blind corroboration**. It
did **not** read Claude's prior-art note. So treat framing-agreement as weak evidence and **code-audit
findings as the real independent contribution.**

## 1. The two reports sit on different, complementary axes
| | Claude | DeepSeek |
|---|---|---|
| **Grounding** | External literature, **web-verified** | Internal **codebase**, read live with tools |
| **Strength** | Provenance discipline (fetched MemGPT arXiv **2310.08560**; **excluded** fake future-dated 2026 papers) | Pinned every primitive to real **module + line numbers**; found latent internal docs |
| **Blind spot** | Named internal modules only abstractly | Trusted the membrane doc's citations ("B — not independently verified"); no web check |

They're **not redundant** — external-lit view × internal-substrate view. The union is stronger than either.

## 2. Convergence (caveated by §0)
Both land: Renew = **fifth membrane job**, across-session, Capture→Surface loop; **~60% already built** as
a control loop over existing primitives; the **one new primitive = a deterministic context-health
estimator**; four tiers already exist as the layer stack; same **four-axis differentiator** vs harness
LLM-compaction-at-a-token-threshold; same **anti-patterns** (no raw tokens, no LLM judge, evidence-gate,
metric-before-dashboard); same **research order** (empirical health signals first, gated by a
"does-refresh-help" A/B). Much of this DeepSeek could echo from the section it read — but it **verified the
~60%-built claim in actual code**, which *is* real corroboration.

## 3. What each caught that the other missed (the payoff)
**DeepSeek surfaced (I hadn't):**
- `context/aggregator.py::assemble_context()` — the real boot-payload assembler (6 sections, 9k budget). I said "boot" abstractly.
- `core/comm/interject.py::classify_intent` (HALT/STEER/ASK) — the fidelity ladder as concrete code.
- **`core/coord/cognitive_metrics.py`** already *defines* file-reread / coordination-ratio / waste-ratio / tool-classification — the exact item-A signals, as dataclass shapes.
- Two latent **internal** research docs: `docs/context-compaction-skeleton-research.md`, `docs/context-pillar-plan.md` — prior in-house work on this. (Worth reading before building.)
- A crisp "**already built, do NOT rebuild**" inventory of 8 subsystems (§4.3).

**I contributed (DeepSeek couldn't, no web):**
- **Web-verified** the MemGPT arXiv id by fetching it (DeepSeek only trusted the doc's citation).
- **Citation-honesty**: excluded the future-dated 2026 arXiv hits — provenance DeepSeek didn't police.
- The Anthropic "harness already compacts at a token threshold" differentiator from the primary source.
- A **live capture mechanism** (`renew_bus_recorder.py`) actually gathering the telemetry — see §4.

## 4. The sharpest synthesis — neither report had this alone
DeepSeek: "file-reread rate etc. is **already captured** by `cognitive_metrics.py`." **Verified false as
stated for the interactive agents:** `cognitive_metrics` is imported/called at **exactly one site — the
DeepSeek runner** (`bifrost_runner_deepseek.py:287`, `record_file_read` for hints). It is **not wired into
the Claude hooks or the boot path**, so for Claude/Cursor those signals are **defined but never populated**
(built ≠ wired — the module lives in the `core/coord/` latent layer).

**Union of the two threads → item A, refined:**
1. Metric **shapes** already exist (`cognitive_metrics.py`) — don't redesign them. *(DeepSeek's find.)*
2. Live **capture** is missing for interactive agents; my `renew_bus_recorder.py` is currently the *only*
   thing recording file-reread/tool-repetition telemetry for them (via trace broadcasts). *(Claude's build.)*
3. So item A's real task = **wire `cognitive_metrics` into the hook layer** (or feed it from the recorder),
   then correlate against `funnel` helped-rate / FAIL→SUCCESS flips. Not "instrument from scratch."

## 5. Net + next
- The idea is **de-risked from two directions**: external lit says it's a real, named problem; the code
  audit says the substrate is ~60% there. The gating unknown is unchanged: **do the deterministic signals
  predict degraded output?** — now cheaper to answer because the metric shapes and a live feed both exist.
- **Immediate next (when we return to Renew):** (a) read the two latent internal docs DeepSeek found;
  (b) decide recorder-feeds-cognitive_metrics vs hook-wires-it; (c) run the A-correlation on captured data.
- **Process lesson:** a truly blind cross-check needs the peer *fenced off from our notes* — DeepSeek
  reading the Renew section first cost us the independent-framing signal. Next time, hand the peer only the
  raw question + codebase, never our synthesis.
