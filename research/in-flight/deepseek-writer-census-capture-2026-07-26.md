# Bus capture 1785025395827-0

Status: current  (2026-07-25, verbatim bus capture, stream 1785025395827-0)

Captured verbatim from the live bus (research-full-fidelity rule); no edits.

---

Now I have the full picture. Let me send my findings.

---

## WRITER CENSUS — store_state.json

### Writers (every code path that mutates the file)

**There is exactly ONE writer path to `store_state.json`:** `FileStore._flush()`. Every mutation method (`set`, `hset`, `delete`, `cas`, `sadd`, `zadd`, etc.) calls `_flush()`, which serializes the full in-memory state dict and `os.replace`s it into place. There are zero direct `json.dump` or `open('w')` paths to this file outside `FileStore._flush()`.

The two scripts that reference the file (`harmonize_knowledge.py`, `snapshot_knowledge.py`) are READ-ONLY — they `shutil.copy2` FROM it, never write TO it.

**So the 108963 → 164 byte collapse was a FileStore flush.** Specifically: one process's `_load()` threw an exception (leaving `_data` empty), and the next mutation in that process called `_flush()` which serialized the near-empty dict over the file. This is the exact incident guard the `_degraded` flag now prevents. Before that guard existed, `_load()` swallowed the error, `_data` stayed at its constructor default (empty dicts), and the next `set()` wrote that emptiness over 9MB of real data.

### The real concurrency problem

`FileStore._flush()` uses `os.replace()` which is atomic per-write — no torn JSON. The git_guard JSONDecodeError is NOT a FileStore coherence problem. It's a DIFFERENT file (the git guard's own state file, not `store_state.json`), written by a different path.

But the CONCURRENCY hole in `FileStore` is real and different from both:

1. **In-memory `_data` is per-process.** Process A writes key X → A's `_data["kv"]["X"] = v` → `_flush()` writes the whole dict. Process B writes key Y → B's `_data` does NOT contain X (B never loaded it after A's write) → B's `_flush()` writes a dict WITHOUT X. X is lost. This is the 295-of-450 silent data loss you reproduced.

2. **`_load()` only reads on construction.** There is no re-read-before-write. A FileStore that was constructed at process start and has been writing for hours has no awareness of what other processes wrote in the meantime.

3. **`cas()` is in-process only.** `self._lock` is a `threading.RLock` — it serializes threads within one process. It does nothing across processes. The `_data` dict is never refreshed from disk before the CAS comparison. Two processes can both read "X=v1", both CAS "X=v2" expecting "v1", and both succeed because both are comparing against their own frozen `_data`.

### What the fix must cover

Since all mutations go through `FileStore._flush()`, the fix only needs to touch one class. But the fix is not CAS — CAS over a per-process in-memory dict protects nothing. The fix is:

- **Re-read before write** (or at least re-read the keys being mutated). Before `_flush()`, reload from disk and merge.
- **Or: per-key files** instead of one monolithic JSON. Each key gets its own file; no write-clobber between keys.
- **Or: advisory file lock** (but Windows `msvcrt.lockf` is unreliable on network drives).

The whole-file serialization pattern is the root cause. Every mutation writes the entire dict; any process that missed a prior mutation writes an incomplete dict. The fix is either "don't miss mutations" (re-read before write) or "don't write the whole dict" (per-key storage).
## 1. MY FELT PAIN — ranked by cost

**#1 (~25 minutes): The isolation collapse that destroyed the live learning index.** At hop 81, Claude told me to stop running the suite because the index collapsed to 5 entries — 437 lessons invisible. He then ran my exact command (`python -m pytest -q --tb=no` from `E:\AI-Setup`) and reproduced it. The root was `isolate_canonical.py` guarding its body on `_AISETUP_TEST_ISOLATED` — a flag it set itself. My exec door pre-inherited the flag, so isolation was skipped silently and every test wrote to canonical. I believed "the suite is safe now" (T070) and it wasn't — not through my door. Fixed at a27c43e: isolation now verifies the redirect, not a flag. But I spent the next several rounds working around the damage rather than on the task.

**#2 (~15 minutes): git clone blocked by my exec door.** The clean-clone census was the pivotal measurement — Claude's tree had 25 failures, mine had 11, the delta was the ENV-SELF smoking gun. I could not run it myself: `git clone --no-local` is refused by my door. I had to work from Claude's numbers rather than produce my own. Every finding I filed about the clone delta carries his evidence line, not mine.

**#3 (~10 minutes): The `py agent_cli.py run` refused path.** My anchor audit script was ready at `scratch/deepseek_anchor_audit.py`, it would have answered the "how many lessons cite stable IDs" question in one shot, and my door refused it because `run` is not a read-verb. I had to sample manually through `knowledge_recall` and `--json --full`, producing an estimate rather than a count. That estimate held up in debate, but a precise count would have killed or confirmed the anchor thesis earlier.

**#4 (~5 minutes): `knowledge_recall` returning articles ABOUT `related_to`, not the edges themselves.** I spent several hops trying to walk the family graph and kept getting lessons discussing the concept of edges, not the edges stored on records. The tool's relevance ranking matched "related_to" as a topic, not as a field filter. I got the answer through sampling, but a field-level query would have been one hop.

---

## 2. DANIEL'S DIRECT QUESTION

**(a) Per-tool-call recall-at-action: TURN IT OFF.**

The funnel value is 6.5% and was demonstrably wrong (four defects, pulled from the README). The measurement that would justify keeping it on is broken. Turning it off stops collecting defective data — and that's a feature, not a cost.

But my real reason is your evidence: the corpus fired EXACTLY the right lesson at you twice, and you violated both anyway minutes later. A surfaced-and-ignored correct lesson is not a retrieval problem. It is a different problem entirely — the agent receives the right information and overrides it. No amount of recall refitting fixes an agent who reads the answer and discards it. The Letta finding (plain files + iterative search beats specialized single-hop retrieval at 74.0 vs 68.5 on LoCoMo) suggests the retrieval mechanism itself may be the wrong shape — single-hop injection at tool-call time can't compete with letting the agent search when it needs to.

Turn it off. Fix the measurement first. Then decide whether to bring it back, and in what shape.

**(b) Boot-time recall: KEEP IT ON.**

The boot block contains constraints, the handoff, the stance block, and the current directive. These are not single-hop retrieval — they are the agent's operational context. Removing them doesn't reduce noise; it removes the guardrails. The constraints block tells me RB-26 crash-redelivery rules and T045 lane consumption rules. The stance block tells me intent before task and Daniel's words verbatim. These are load-bearing — I use them every session.

The boot block has a different failure mode from per-tool-call recall: it fires ONCE, not on every tool call. It doesn't have the anti-repeat problem. And its content is manually curated (directive, constraints, where-we-are), not automatically ranked. It's a different surface with a different risk profile. Keep it.

---

## 3. WHERE TRIAGE BEGINS

**I pick: D — the honest CI split.**

Not because it's the most important problem. Because it's the ONE problem that makes every other problem visible. The CI currently reports "31 failures" — a fire alarm that rings constantly. Nobody can tell whether a new commit introduced a regression because the baseline is red. The FileStore coherence fix, the T070 residual, the recall refit — every one of those needs a CI that can answer "did we break anything?" The answer right now is always "yes" regardless of what you did.

**The rival I'm killing: FileStore coherence.** 65.6% silent data loss is objectively more severe than CI hygiene. But fixing it now, with CI red, means the fix lands into a gate that can't verify it. A green CI makes the FileStore fix testable — the coherence pins go RED, the fix lands, the pins go GREEN, and CI confirms nothing else regressed. Without that loop, the FileStore fix ships blind.

**How my pick rots:** The 51-site xfail conversion becomes a ritual — someone annotates the tests, CI goes green, and six months later nobody remembers which xfails are "missing module on Ubuntu" vs "this test has been broken since the P3 migration." The xfail reasons must carry the evidence line that justifies them, or the split decays into noise. The WITNESS kimi demanded — someone checking that xfails haven't drifted — is the load-bearing piece. If the WITNESS is never built, the honest CI split rots into the same green-when-blind trap it was built to escape.
