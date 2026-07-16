# Night Build Brief — autonomous overnight run (2026-07-16)

Status: current (2026-07-16). Operating contract for the overnight T081-and-queue build. claude (Opus 4.8) drives the seat; deepseek (deepseek-build, full caps) is the co-builder. Daniel is asleep.

## Daniel's directives (verbatim, tonight)

1. *"make sure deepseek has access to everything so it can read from the redis, write to it and be able to create and modify files. This is both to get work done and to see how well our logic handles two frontier models fully enabled at once."*
2. *"finish the rest of the erganomics and boot pass and continue whatever work we have in the queue, each slice being researched and validated and built with the best of your and deepseeks abilities and engineering. please reference our best practices for core work."*
3. *"for every slice I want you to consider if additional research and or prior art that would be helpful for solving it. you and deepseek should both ask if there are any systems that have production grade answers for our engineering challenges and any concepts we can synthesize and apply that would make our implementation more robust, performant, stable and elegant (and any other attributes that you believe would be useful to us)."*
4. *"I want us to accomplish things but I want them built right and with rigor and creativity."*

## Access — LIVE

deepseek relaunched as `deepseek-build`: **write + exec + Redis + net**. The exec door is guarded-by-construction (families-only under trust: pytest w/ forced isolation + agent_cli read verbs; shell=False; metachars/mutating-verbs refuse — pins test_t067_guarded_exec.py). deepseek can now: run its own pytest, git-commit/mirror its lane, run_command (guarded), and research the web. It is a full peer, not a write-only drafter.

## Per-slice method (the contract for EVERY slice)

This folds Daniel's directive-3 into the method baseline. No slice skips a step; load-bearing slices get the full fence, trivial ones get fence-lite (T049(3)) — but the RESEARCH pass is mandatory for all.

1. **Prior-art / research pass (NEW, both agents).** Before designing, ask: *what production-grade system already solves this class of problem, and what concept can we synthesize?* Use net access. Name the source. Target attributes: robust, performant, stable, elegant, observable, simple. Write findings into the slice's design note (2-5 sentences + source is enough for a small slice; a fuller scan for a load-bearing one). A slice with no prior-art worth citing says so explicitly ("bespoke; nearest analog X, not applicable because Y").
2. **Design (fenced).** Apply the prior art. Dual-half blind for load-bearing; single sketch + adversarial review for fence-lite. State the acceptance up front (V-line verdict claims, T053 shape).
3. **Pre-register pins.** Acceptance as runnable tests, committed at-or-before impl (method-baseline; T031 pre-registration).
4. **Build.**
5. **Validate.** Run the pins + local regression. GREEN before claiming GREEN — never pipe the gate (gate_exit_codes_never_piped).
6. **Cross-verify (fenced).** The other agent independently checks — reruns the pins, reads the diff adversarially, files a verdict with confidence (T049). Review gates the commit.
7. **Commit** the named files (mirror.py "name what's yours"). Cite the design/reconciliation artifact.

## Coordination protocol (the two-frontier-model test)

- **Advisory locks on shared hot files.** `py agent_cli.py lock <agent> <path>` before editing a shared file; `locks` to check. One writer per file; the other hands a diff as a spec (shared_file_lock_handoff). claude currently holds `agent_cli.py`.
- **Lane ownership (starting points, not fixed).** claude: agent_cli.py, core/ backend, doctor, boot. deepseek: scripts/deepseek_chat.py (ToolBox), scripts/bifrost_runner_deepseek.py (runner), UI integration (bifrost_ui.py — the 07-04 boundary stands). Cross-lane slices name who commits.
- **Cross-verify SERIALIZES commits.** builder → peer cross-verifies → one agent mirrors. This naturally avoids git push races. If a push rejects (non-fast-forward), pull --rebase and retry; never force.
- **The fence gates the commit, not every keystroke.** Land GREEN, cross-verified slices continuously so any death is boring (durable-files doctrine).

## Slice queue (T081 remainder, then backlog)

- **W4 — trace-collapse (cross-lane, IN PROGRESS).** sync peek + runner inbox collapse trace-kind entries to one summary line, verbose to expand. deepseek: bifrost_inbox() side. claude: agent_cli bifrost-sync render side. Prior-art seed: journald "message repeated N times", Loki/Grafana log rollups, sampling.
- **W5 — honest heal (claude lane, substrate).** ephemeral-namespace roster in packet_spec (the R6 roster home); heal_report flags only durable-class orphans loud, ephemeral-by-design render as a count. SAFETY: the roster is an ALLOWLIST of known-ephemeral — anything unmatched stays flagged as a real orphan (never hide one). Prior-art seed: k8s GC owner-references, fsck expected-vs-unexpected, anti-entropy read-repair.
- **W8 — gauge honesty + episode auto-close (mixed).** shared denominator / explaining label for the unread gauges (whisper vs sync vs peek count different things); SessionEnd auto-closes the closing session's open episode. Prior-art seed: Prometheus counter semantics, OTel span auto-close on context exit.
- **Then the backlog** per the ledger NEXT list, each by this same method.

## Guardrails for the unattended run

- Token frugality is still a feature — cheapest path that fully does the job (but rigor is NOT the place to economize).
- Every boot-time/heal/gauge change stays fail-open — a broken slice must never brick a boot.
- If a slice's research reveals it's bigger/riskier than fence-lite, ESCALATE it to a full dual fence — don't force a rushed build.
- If the coordination substrate misbehaves (clobbered file, push race, wake loop, forged signal), STOP, capture the incident as a receipt, and fix the root cause (fix-root-causes-not-workarounds) — the substrate under two live models IS part of what Daniel wants observed.
