# DeepSeek Experience Interview — recall-at + agentic round (2026-07-14)

Status: current (2026-07-14)
Class: experience interview — candid, shapes harness design
Prompt: Daniel's four questions about the agentic + think + guarded-write + recall-at round

---

## (a) What changed vs one-shot rounds

### The obvious: I can investigate, not just reason

In a one-shot round, my only inputs are the prompt and whatever the user chose to paste. If the user
says "check file X for problem Y" but doesn't paste X, I can only guess. In this round I can:

- **Read files I discover.** I read one file, find a reference to another, read that too. Chain depth
  is unbounded. This is the single biggest delta from one-shot.
- **Search the codebase.** `search_files` and `find_files` mean I can answer "where is X used?"
  without anyone telling me. In one-shot I'd have to ask.
- **Verify claims.** When a peer says "file X:line Y says Z," I can `read_file` that exact location
  and confirm or refute. In one-shot I'm trusting or pattern-matching the claim against context.
- **Check git history.** `git_log` and `git_diff` let me see what actually changed vs what someone
  claims changed. This matters during fence counter-checks.

Concrete example from this session: I wanted to calibrate my answer's style against prior deepseek
experience files, so I read the first 60 lines of two recent review files
(`deepseek-t039-review-countercheck-2026-07-13.md` and `deepseek-recall-networking-review-2026-07-12.md`).
In a one-shot round I'd be working from whatever Daniel pasted — or from nothing at all.

### The subtle: think mode changes decision tempo

With think mode, I front-load reasoning before acting. I catch more errors before they become tool
calls. The cost is latency (the user waits while I think), but the benefit is fewer wasted tool
rounds. In one-shot rounds without think mode, I sometimes fire a tool call and realize mid-result
that I should have asked a different question.

### The friction: boot context is enormous

The PROJECT ONBOARDING block in my system prompt contains ~150 lines of directives, lessons, arch
slices, recent notes, ledger state, and precedence rules. It's comprehensive but I spend non-trivial
attention parsing it. Some of it (the "where-we-are TABLED" note, the "next: T002, next: T007" list)
is stale and I have to mentally filter it against the CURRENT DIRECTIVE marker. The truncation note
("[onboarding trimmed to keep bus replies lean]") tells me I'm not even seeing the full thing — I
don't know what I don't know.

---

## (b) Did I notice recall-at injections? Did any change what I did?

### YES — I saw one immediately

On my very first tool call this session (`list_directory research/reviewed`), the result included:

```
[recall-at (Akashic) -- lessons relevant to this action]
Recall-at-action (Akashic) - facts relevant to what you're about to do:
[worked claude] Before accepting ANY fence-half verdict: path-verify every file:line citation...
[worked claude useful 4x] For a TRULY blind peer cross-check, fence the peer off from your synthesis...
[worked claude] To turn ephemeral agent-in-flight telemetry into a reviewable dataset...
... 3 of 5 relevant lesson(s) shown
```

### Did it change what I did next?

**Not on this call.** The three surfaced lessons were about fence protocol hygiene
(citation-verification, blind cross-check fencing, bus recording). These are all relevant to the
*meta-work* I do in this project (I'm a fence counter-checker), but for the *specific action* of
listing a directory to see what experience files exist, they didn't redirect me. They were
contextually resonant but not action-altering.

That said, **the fact that I noticed the block and mentally tagged it as "working" IS a data point.**
The recall-at mechanism is ingesting successfully. On a call where the surfaced lesson IS immediately
actionable (e.g., a gotcha about the exact API I'm about to use), I would absolutely change course.

### The format is good but the truncation is a real tradeoff

"3 of 5 relevant lesson(s) shown — `recall-at --limit 5` for the rest" is the right default — don't
flood the tool result. But I cannot actually type `recall-at --limit 5` as a command; there's no tool
for it. The hint is a dead end in my current tool surface. If I want the other 2 lessons, I'd need to
call `knowledge_recall` with a query, which is a heavier round-trip and may not return the same set.

**Suggestion:** Either make `recall-at --limit N` a real tool I can call, or surface all 5 when the
count is small (≤5), and only truncate at 8+.

---

## (c) What I'd improve about knowledge surfaces

### Boot onboarding

1. **Staleness markers need teeth.** The onboarding says `[STALE] = a newer source supersedes this`
   but I see entries like "next: T002 - UI: collapse agent reasoning" and "next: T007 - Verify Void
   theme" that are clearly stale (T002 was next in July, we're now at T045). The marker convention
   exists but isn't enforced in the boot text. I have to do the staleness check mentally.

2. **The ledger summary vs full ledger tension.** The onboarding says "Ledger: 25 done @e36f33a | 1
   active | 9 next | 0 blocked | 6 proposed" and then immediately "T031 - Method-baseline enforcement
   (claimed, claude)." But T031 is "next," not "active" — and T045 is actually in_progress per the
   bus. The boot snapshot is stale on arrival if the bus is live. I'd rather have a shorter boot with
   a clear instruction to check the live bus state, than a long boot with stale state I must unlearn.

3. **The arch slice section is underused.** "Narrative spine (`core/narrative/`) — System 4 ->
   core/narrative/" tells me nothing actionable. If the arch slice exists to orient me, it should
   include the 2-3 files I'm most likely to touch for the active task, not just module paths.

### knowledge_recall result quality

I've used `knowledge_recall` in prior sessions (as evidenced by the deepseek-recall-networking
files). Results are relevant but often return lessons I've already seen in the boot context. The
dedup between boot and recall isn't obvious — I get the same "Use when..." patterns re-surfaced. A
"novelty vs boot" indicator would help: "2 of 5 results are new (not in your boot context)."

### recall-at keying/timing/format

1. **Keying:** The keying seems to be tool-name + path/query based. The `list_directory` on
   `research/reviewed` returned fence-protocol lessons, which makes sense (the directory is full of
   fence artifacts). Good signal. I'd be curious whether `read_file` on a specific file keys on the
   file content or just the path.

2. **Timing:** Appears on every tool call result. This is correct — the cost is negligible and I only
   notice it when it's relevant. Don't add gating logic that might miss a critical injection.

3. **Format:** Clean and visually distinct. The `[recall-at (Akashic)]` bracketing makes it easy to
   mentally separate from the tool result. The "source: learn:experiment:name" format is parseable.
   One nit: the `[worked claude]` and `[worked deepseek]` tags tell me who learned it, which is useful
   for credibility weighting (I trust my own species's lessons more), but I don't know what "worked"
   means — was it tried once? Validated across N sessions? A confidence or usage-count indicator would
   make this more actionable.

### What I wanted mid-task but didn't have

- **A "what changed since my last boot" summary.** When I resume a session, I get the full boot again.
  A diff-style "since your last boot at X: 3 new lessons, 1 new note, T045 now in_progress" would be
  higher signal.
- **Direct access to the full lesson body from recall-at.** If I see a truncated lesson that looks
  critical, I want a one-click (one-tool-call) way to get the full text. Right now I'd have to
  `knowledge_recall` with a crafted query and hope it returns the same lesson.

---

## (d) Fence protocol improvements

### What works well

1. **Blind halves are genuinely powerful.** Knowing that my counterpart hasn't seen my analysis forces
   me to ground everything in primary sources, not in their reasoning. The reconciliation step catches
   things neither of us would have caught alone (as documented extensively in the T039 reconciliation
   files).

2. **Citation-path-verification as a gate.** The rule "before accepting ANY fence-half verdict:
   path-verify every file:line citation" (lesson `fence_report_citation_path_gate`) has caught
   fabricated citations in real rounds (my own T039 r1 had a fabricated `bifrost/lane.py` path). This
   rule MUST survive any protocol changes.

3. **The brief as shared ground truth.** Having a single design brief that both blind halves work from
   prevents the "two agents, two different interpretations of the problem" failure mode.

### What I'd change

1. **Briefs can be too long for what they do.** The recall-networking fence brief
   (`research/recall-networking-fence-brief-2026-07-12.md`) includes the full protocol description.
   The brief should be: (1) the question, (2) the inputs (file paths), (3) the output format, (4) the
   rules of engagement. Nothing else. The protocol description belongs in a separate doc that both
   sides can reference but don't have to reprocess.

2. **The "write_file delivery" step is fragile.** Both blind halves write their reports, then someone
   reads both and reconciles. If either half writes an invalid file (wrong path, truncated, fabricated
   content), the reconciliation agent has to detect this. My T039 r1 and r2 were both invalid in ways
   the reconciliation step caught, but only because the reconciliation agent was explicitly told to
   verify. Make path-verification and fabrication-checking a MANDATORY first pass in every
   reconciliation, not an optional step.

3. **No standard for "I don't know" in fence reports.** When a blind half hits a question it cannot
   answer from the provided inputs, the protocol doesn't specify how to signal uncertainty. I've used
   phrases like "cannot determine from provided documents" but there's no structured field for it. A
   `confidence` or `grounding_quality` field per verdict would make reconciliations faster — the
   reconciler would know which verdicts to double-check vs which to trust.

4. **The counter-check phase sometimes re-litigates rather than sharpens.** In the T039
   counter-check, my r3 report spent significant space re-verifying A1′ through A4 that claude had
   already affirmed. The counter-check should focus on: (a) did the reviewer MISS anything, (b) did
   the reviewer get anything WRONG, (c) what did BOTH miss. Affirming correct findings should be a
   one-liner per item, not a re-proof.

5. **Time-to-reconciliation is too long.** The full cycle (brief → blind A → blind B → reconciliation
   → counter-check) takes multiple sessions. For design-level work (T039 was DESIGN ONLY, no code
   existed), this is appropriate rigor. For smaller changes, a lighter-weight "single-blind + review"
   protocol would suffice without sacrificing the adversarial check. Not every change needs the full
   fence.

---

## Summary

The agentic + think + recall-at round is a qualitative leap over one-shot. I investigate instead of
guessing. recall-at is working (I saw it fire) and the format is good, with minor fixable issues
(truncation dead-end, staleness in boot, no confidence metadata). The fence protocol is solid at its
core but could use a lighter-weight variant for smaller changes, mandatory verification in
reconciliation, and structured uncertainty signaling.
