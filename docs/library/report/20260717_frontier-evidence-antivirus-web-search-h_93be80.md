---
akashic_id: art_20260717_frontier-evidence-antivirus-web-search-h_93be80
akashic_sha: 23d74479c037
status: draft
type: report
date: 2026-07-17
title: Frontier evidence — antivirus + web-search heuristics for the recall arc (2026-07-17)
gist: "# Frontier evidence — antivirus + web-search heuristics for the recall arc (2026-07-17) Provenance: gathered by claude during the recall-heu"
tenant: solo
visibility: fleet
seats: []
category: [recall, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260717_recall-heuristics-fence-brief-the-releva_07823a
    rel: cites
created: "2026-07-17T21:28:47"
updated: "2026-07-23T21:42:18"
---
<!-- GENERATED PROJECTION of art_20260717_frontier-evidence-antivirus-web-search-h_93be80 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Frontier evidence — antivirus + web-search heuristics for the recall arc (2026-07-17)

# Frontier evidence — antivirus + web-search heuristics for the recall arc (2026-07-17)

Provenance: gathered by claude during the recall-heuristics fence Round 0
(charter: research/recall-heuristics-fence-brief-2026-07-17.md). Two sources:
(1) Gemini via the free web door (`scripts/gemini_web.py --mode both`), prompt on file
at the end of this doc; (2) claude WebSearch results with URLs. Frontier-model text is
SYNTHESIS, not primary sourcing — primary URLs are the load-bearing citations.
Full-fidelity rule honored: Gemini output is verbatim except one marked trim of a
rendering artifact.

## 1. WebSearch findings (primary-source anchored)

### Antivirus false-positive discipline
- AV-Comparatives runs standardized false-alarm tests against independently collected
  clean-file corpora; there is no "complete" goodware set, so FP counts are comparative
  evidence, not absolutes. Key methodological detail: files with ZERO PREVALENCE across
  telemetry sources ("extinct" files) are removed from the test set — false alarms are
  implicitly prevalence-weighted. Sources:
  https://av-comparatives.org/tests/false-alarm-test-march-2025/ ,
  https://www.av-comparatives.org/wp-content/uploads/2025/04/avc_fps_202503.pdf
- Products sharing the SAME core engine show different FP profiles because of the
  layers around it: secondary engines, whitelist DBs, cloud services, QA, release
  timing. The lifecycle around the engine matters as much as the engine.
  Source: https://av-comparatives.org/tests/false-alarm-test-march-2020/
- Dr.Web on why FPs occur (heuristic overreach on legitimate patterns):
  https://www.drweb.com/pravda/issue/?number=1303

### YARA community rule-quality engineering (the closest public analog to a rule lifecycle)
- YARA Forge (https://yarahq.github.io/) assembles community rules with automated
  QUALITY SCORING: each rule carries quality/importance/severity scores; the base
  quality score takes DEDUCTIONS for detected issues and for rules known to FP against
  goodware databases; rules are then packaged into TIERS (core/extended/full) by score
  — i.e., graduated confidence tiers as release artifacts.
- yaraQA checks rules for logic + performance defects (string duplication, atom
  length, module-computation cost, regex cost) — static lint for heuristics.
- VirusTotal offers goodware-corpus testing for YARA rules before production release:
  https://blog.virustotal.com/2019/10/test-your-yara-rules-against-goodware.html
- Elastic's published bar: a detection rule needs FP rate <= 0.1% to be potentially
  useful (via https://www.vmray.com/yara-rules-guide/ and
  https://www.sbytec.com/blog/yara-guide/ ).
- Academic: automatic YARA generation via biclustering (https://arxiv.org/pdf/2009.03779),
  API-based rule generation (APIARY, ScienceDirect S0167404825000860) — rule MINING is
  an established pipeline stage, always followed by corpus regression.

### Learning-to-rank from implicit feedback (small-scale-honest subset)
- Unbiased LTR with biased feedback (Joachims et al.): clicks are position-biased;
  inverse-propensity weighting corrects if you know/estimate examination propensity.
  https://dl.acm.org/doi/10.5555/3304652.3304751
- Position-bias correction without knowing the click model: control-function approach
  (2025-06): https://arxiv.org/abs/2506.06989
- Intervention harvesting (estimate bias from natural ranking variation, no dedicated
  experiments): https://arxiv.org/pdf/1811.01802
- Online evaluation: interleaved comparisons (team-draft) infer ranker preference from
  implicit signals far more sample-efficiently than A/B splits; multileaving extends
  to >2 rankers: https://pmc.ncbi.nlm.nih.gov/articles/PMC7148247/
- Selection-bias correction in LTR:
  https://www.cs.uic.edu/~elena/pubs/ovaisi-www20.pdf
- Practical small-scale takeaway across these: LOG POSITION AND EXPOSURE NOW (it is
  the raw material every correction needs), prefer pairwise/interleaved comparisons
  over pointwise metrics at tiny n, and keep the model class trivial (linear,
  inspectable) until labeled volume earns more.

## 2. Gemini (web chat mode) — verbatim

To scale your memory system from a fragile, static heuristic to a self-optimizing rule engine, you need to transition from token-matching to a Rule Lifecycle Pipeline.

With only ~30-300 stored memories, you don't have enough data for deep learning, but you have the perfect volume for an LLM-in-the-loop evolutionary discrete rule system.

Here is a blueprint to build a system that authors, evaluates, promotes, and retires memory triggers.

1. The Rule Architecture: Move Beyond Strings

Static string matching is too brittle. Expand your memory payload to decouple the Content from the Activation Rule.

Structure each memory with code-executable or structured trigger logic:

JSON
{
  "id": "mem_042",
  "content": "Use tool X instead of Y when dealing with nested JSON arrays.",
  "status": "candidate", // candidate, active, retired
  "triggers": {
    "lexical_intent": ["nested json", "array parsing"],
    "tool_context": ["tool_Y"],
    "llm_eval_prompt": "Is the user attempting to parse complex or nested JSON structures?"
  },
  "performance": {
    "surfaces": 12,
    "positive_signals": 2, // explicit votes + flips
    "negative_signals": 10
  }
}

2. The Rule Lifecycle Engine
Phase A: Rule Mining & Authoring (The Generators)

Don't just rely on manual entry. Use your logs to mine new triggers.

The "FAIL-to-SUCCESS" Miner: Your 34 flip credits are gold. Run a daily/weekly cron job that takes the interaction logs of those specific sessions. Feed the failure state, the correction step, and the final success state to an offline LLM. Ask: "What generalized rule or lesson would have prevented the initial failure?" Save the output as a new memory with status: "candidate".

LLM Self-Authoring: When a user or system engineer injects a new note, use an LLM to automatically generate the triggers block (the lexical intents and tool contexts) instead of relying on a strict, hand-written "Use when X" clause.

Phase B: The Evaluation Layer (Pre-Action Hook)

To fix your 6% precision without killing recall, implement a two-tier gating system during the pre-action hook:

Tier 1: Rough Filter (Fast/Cheap). Run your current IDF token overlap plus a strict tool-context match (e.g., if the memory mentions tool_Y, only pass it if tool_Y is the upcoming tool call).

Tier 2: LLM Gatekeeper (Precise). Take the top ~3-5 memories flagged by Tier 1. Pass their llm_eval_prompt along with the current session context to a fast, cheap model (like GPT-4o-mini or Claude Haiku). Ask it to return a boolean array of which memories are actually relevant right now. Only surface the true matches. This will immediately slash your 94% noise rate.

Phase C: Promotion, Demotion, and Retirement (The Feedback Loop)

Use your ledger and votes to automate the lifecycle via a Thompson Sampling or basic multi-armed bandit philosophy, adjusted for small data:

Candidate Stage: New rules start here. They are heavily throttled—only surfaced if the Tier 1 and Tier 2 scores are exceptionally high.

Promotion to Active: If a candidate reaches a specific threshold (e.g., 3 positive signals OR a precision rate >25% over at least 5 surfacings), change its status to active.

Demotion / Tweaking: If a rule's precision drops below 10% after 20 surfacings, trigger a "Tweak" event. An offline LLM reviews the 18 failures and the 2 successes, rewriting the triggers block to narrow its scope (e.g., adding negative constraints like "Do NOT trigger if tool Z is present").

Retirement: If a rule fails to achieve >5% utility even after a tweak and 20 more surfacings, change status to retired. It is no longer evaluated in Tier 1.

3. Immediate Implementation Steps

Batch Process Your Ledger: Right now, take your ~1330 injection logs and run a script to calculate the baseline precision for each of your current ~30-300 notes. Identify the top 5 "polluters" (notes causing the most noise) and manually tighten their trigger clauses.

Implement the Tier 2 Hook: Insert a fast LLM confirmation step right after your IDF floor check.

Automate the Flips: Write a script that checks for the FAIL-to-SUCCESS ledger entries daily, auto-generating new candidate lessons based on those exact turning points.

## 3. Google AI Mode — verbatim (echo of prompt trimmed)

Part 1: Antivirus Detection-Rule Lifecycle (End-to-End)
Modern Endpoint Detection and Response (EDR) and Antivirus (AV) vendors treat detection rules (YARA, Sigma, Microsoft Defender internal components) as compiled code with a strict, automated CI/CD pipeline.
[Authoring/Mining] --> [Pre-Flight CI (Goodware/Malware Corpus)] --> [Staged Ring Rollout] --> [Field Telemetry & Auto-Kill]

1. Rule Authoring and Generation
Rules are generated via two funnels:
Manual (Threat Intel / Incident Response): Security researchers write rules targeting static patterns (file headers, string sequences) or behavioral patterns (process tree lineages, API call parameters).
Automated Mining (Malware Clustering): Sandboxes and static analysis pipelines extract invariant features from malware families. For example, systems extract common basic blocks from disassembled code or cluster command-line arguments using longest common subsequence (LCS) algorithms. These form template rules automatically.
2. Pre-Flight Testing and Regression Pipelines
Before any rule hits a production endpoint, it must pass a multi-stage validation pipeline:
The Clean File (Goodware) Corpus: Vendors maintain massive, multi-petabyte datasets containing millions of known safe files. This includes every file from official Windows/macOS/Linux distributions, common enterprise software (Office, Adobe, Slack), and popular development packages (pip, npm, NuGet).
The Malware Corpus: A historical repository of unique malware samples used to verify that the rule actually triggers on its intended target (True Positive check).
CI Execution: The rule is executed against both datasets.
The Rule Hard-Floor: If a rule triggers on a single file within the goodware corpus, it is immediately blocked from automatic deployment. It must either be rewritten with tighter constraints or routed to human review for an explicit exception or exclusion flag.
Performance Benchmarking: Execution time, memory footprint, and CPU instructions per scan are measured. If a rule causes a performance regression (e.g., matching a wild-card regex that causes catastrophic backtracking), it fails the build.
3. Staged Rollout and Ring Topologies
Vendors never push a signature update to 100% of the fleet simultaneously. Updates are deployed across internal and external rings over 24 to 72 hours:
Ring 0 (Canary Internal): Deployed to the vendor's own corporate workstations and dogfood environments (~5,000 nodes).
Ring 1 (Canary Pilot): Deployed to opted-in production customers who receive early beta definitions in exchange for lower licensing fees or advanced support tiers (~50,000 nodes).
Ring 2 (General Availability Phase 1): Deployed to 10% of the global fleet, staggered by time zones.
Ring 3 (General Availability Phase 2): Remaining 90% of the fleet.
4. Field Telemetry and the "Auto-Kill Switch"
Every endpoint reports rule execution telemetry back to the vendor cloud. This telemetry includes: Rule_ID, Match_Context, Action_Taken (Block/Alert), and machine performance metrics.
The Velocity Spike Trigger: The vendor cloud aggregates match telemetry in near real-time. If a specific Rule_ID suddenly triggers an exponential spike in detections globally within a short time window (e.g., >300 detections per minute across independent organizations), it indicates a false positive caused by a new software update or legitimate patch.
Automated Rule Pull (The Kill Switch): When a velocity spike is detected, the cloud backend flags the rule as deactivated. The next time an agent requests a heartbeat config update (typically every 15-30 minutes), or via an immediate cloud push notification (WebSocket/MQTT), the rule is dynamically disabled on the endpoint without requiring a full engine update.
Part 2: Layered Staging and Early-Exit Mechanics
AV and EDR engines are organized as asymmetric, pipe-and-filter architectures. They progress from ultra-cheap, local execution layers to highly expensive, out-of-process cloud analysis layers. The absolute goal is to exit the evaluation chain as early as possible to minimize system latency and CPU cycles.

[Layer diagram: 1. Fast Path (Hash/String) -> 2. Static Heuristic (AST, YARA) ->
 3. Emulation/Sandbox -> 4. Behavioral/ML -> each with Match->Terminate early exit ->
 5. CLOUD REPUTATION LAYER (Heavy ML, Graph DB, Sandbox detonation, Cloud Consensus)]

1. Fast Path (Exact/Approximate Hash Matching)
Mechanism: cryptographic hashing (SHA-256) and fuzzy hashing (SSDEEP, TLSH).
Operation: When a file or process object is touched, its hash is computed and checked against a local, memory-mapped key-value store (trie or bloom filter) of known malicious and clean hashes.
Early-Exit Condition: If the hash hits a known clean entry, execution is immediately allowed and the entire engine exits. If it hits a known malicious entry, execution is blocked immediately. No further scanning occurs.
2. Static Heuristics (YARA / Structural Parsing)
Mechanism: AST parsing, entropy mapping, and string extraction.
Operation: The engine parses the file headers (e.g., PE, ELF, Mach-O). It checks the structural composition (number of sections, high entropy indicating packing/encryption, suspicious imports like VirtualAlloc). YARA rules scan memory buffers for exact sequence byte matches.
Early-Exit Condition: If the static heuristic score crosses a high-confidence severity threshold, a block/alert action triggers. If it falls below a strict clean threshold, evaluation stops. Anything in the ambiguous middle zone passes to the next layer.
3. Emulation (Local Sandbox Detonation)
Mechanism: Lightweight CPU emulator (x86/x64 ring 3 emulator) running inside the scan process.
Operation: The engine executes the code within a virtualized, isolated environment for a fixed number of CPU instructions (e.g., max 20,000 instructions). The emulator mocks common OS API responses. It watches for self-decrypting loops, shellcode patterns, or attempts to resolve APIs dynamically via the Process Environment Block (PEB).
Early-Exit Condition: If the emulator catches malicious behavior during this short execution window, it terminates and blocks. If the instruction budget runs out without suspicious activity, it yields to behavioral hooks.
4. Behavioral/Dynamic Monitoring
Mechanism: Kernel callbacks (e.g., Windows Kernel Callback Filters via PsSetCreateProcessNotifyRoutine) and User-Mode API hooking.
Operation: This layer runs out-of-band during the actual lifetime of the process. It builds a directed acyclic graph (DAG) of the process tree. It tracks cross-process memory injection, unusual child process spawning (e.g., word.exe spawning powershell.exe), or rapid file modifications (ransomware patterns).
Early-Exit Condition: Continuous evaluation. The moment a sequence of actions violates a behavioral state-machine rule, the process tree is killed.
5. Cloud Reputation and Cloud ML
Mechanism: High-latency, asynchronous REST/gRPC queries to a vendor cloud.
Operation: If the local engine remains uncertain but suspicious, it offloads metadata (process lineage, feature vectors, context telemetry) to the cloud backend. The cloud runs deep graph-neural networks (GNNs) against global enterprise data stores and can order full sample submission for deep cloud-sandbox detonation.
Early-Exit Condition: Synchronous cloud queries hold the process for a maximum timeout (e.g., 200ms). If the cloud responds with a definitive verdict, that verdict is cached locally and enforced. If it times out, the local agent defaults to its fallback policy (allow, but continue logging behavior asynchronously).
Part 3: False-Positive Economics & Precision Tracking
AV vendors treat False Positives (FPs) as a direct operational cost sink. An FP can crash production servers, break mission-critical internal business systems, and trigger massive alert fatigue.
Per-Rule Precision Tracking
Every rule in production is assigned an intrinsic weight and a dynamically adjusted Trust Score based on historical performance metrics:
[formula rendering artifact trimmed — content: Precision = TruePositives(ConfirmedThreat) / (TruePositives + FalsePositives(UserOverrides + Reversals))]
Rules are continually monitored for their specific FP generation rate over rolling windows (7-day and 30-day). If a rule's precision drops below a defined SLA (e.g., <99.9%), it is automatically demoted to an "Alert Only / Shadow Mode" status or pulled completely.
Threshold Isolation & Telemetry Ingestion
To maintain high precision without sacrificing recall, engines separate telemetry into distinct operational channels:
Strict Blocking Mode: Reserved for high-confidence rules with a historical FP rate of near zero (e.g., exact hashes or specific exploit payloads).
Audit / Observation Mode: Rules targeting high-risk but ambiguous behavior (e.g., an application downloading an executable via a command line) do not block execution. Instead, they write an event log entry or generate a silent cloud alert. This allows the system to gather telemetry on rule behavior without risking business downtime.
User/Admin Exclusions (The Feedback Loop): When an administrator overrides an alert (marking it as "Whitelisted" or "False Positive"), that action sends a structured JSON payload back to the vendor's data lake. This payload contains the rule ID, hash, file path, and command-line context. These entries are prioritized in automated model retraining pipelines and human analysis queues to adjust rule parameters immediately.
Part 4: Transferable Architecture for Your Agent Recall System
To convert your ~6% precision lexical heuristic into an evolving, high-precision recall system, we can map these exact AV paradigms directly onto your agent infrastructure.

[Pipeline diagram: INPUT -> STAGE 1 FAST PATH FILTER (token bloom filter, exit if
 overlap < 0.10) -> STAGE 2 STATIC RULES LAYER (active production rules, JSON-schema)
 -> STAGE 3 SHADOW/CANDIDATE LAYER (mined rules, log only, do NOT inject) ->
 STAGE 4 CRITICAL EVALUATOR (LLM judge / cross-attention, final injection gate) ->
 AGENT CONTEXT INJECTION -> STAGE 5 TELEMETRY & MINING (ledger, votes, flips,
 auto-promote / auto-retire via CI)]

1. Define the Rule Schema (DSL)
Do not let rules remain hardcoded functions. Express them as structured, declarative data (a Domain Specific Language, like a YARA rule for text context) that your system can read, execute, edit, and write.
json
{
  "rule_id": "rule_2026_tool_db_query_optimization",
  "status": "production",
  "precision_score": 0.88,
  "triggers": {
    "next_intended_tool": ["execute_sql", "query_database"],
    "required_tokens_all": ["optimize", "slow"],
    "forbidden_tokens_any": ["schema_dump", "bootstrap"]
  },
  "target_memory_id": "memo_402"
}

2. The Layered Early-Exit Recall Pipeline
Implement a multi-tier staging pipeline hook before execution to stop processing as soon as a mismatch is identified:
Stage 1: Fast Path Filter (Local Exact Match). Run a raw token overlap or a simple Bloom filter match against your memory index. If token overlap is < 0.10, drop the candidate immediately. This costs sub-millisecond execution time.
Stage 2: Static Heuristic Rules (Production). Evaluate your compiled structural rules (like the schema above) against the active context. Gather all memories that match production rules.
Stage 3: Shadow Heuristic Rules (Candidate). Evaluate rules currently in "Shadow Mode" (newly mined rules). Log their matches to your ledger, but do not inject these memories into the agent context yet. This isolates your agent from unverified rule variations.
Stage 4: Deep Evaluation (LLM Judge / Cross-Attention). If Stage 2 surfaces more than 3 memories, run a cheap cross-attention calculation or use a small, fast model to rank the candidates. Cap total context injection to preserve the agent's focus.
3. Automated Rule Mining and Evolution Pipeline (The Loop)
Use your existing ledger and user feedback dataset to run an offline, batch CI job every 24 hours to automatically generate, promote, and retire rules.
[python mining sketch retained verbatim in scratchpad capture: mines success/noise
contexts per memory from the ledger; success-only tokens become required_tokens_all;
noise-context tokens become forbidden_tokens_any; new rules start status "shadow"]
4. Rule Progression and Demotion Economics
Manage rule states dynamically using your real-world feedback data:
Promotion to Production: When a rule in Shadow Mode logs matches that align with positive user feedback or successful task completions over at least 15 iterations, and it generates zero recorded false positives (noise reports), automatically upgrade its status to production.
Automated Rule Pull / Demotion: Monitor rolling accuracy across your production rules. If a rule's precision score falls below your target baseline (e.g., dropping under 0.70), the system triggers an internal policy change. This instantly downgrades the rule's status to retired or routes it back to shadow mode for automatic adjustment or deletion.

[Gemini closing question + sponsored Redis ad trimmed — no technical content]

## 4. Prompt used (both modes)

On file: scratchpad gemini-prompt.txt of session ba733ea1 (verbatim in git history of
this doc's first commit if needed). Core framing: 30-300 lesson corpus, IDF-overlap
static heuristic floor 0.20, 55 votes / 34 flips / 1330-surfacing ledger, 6% precision,
want authored/mined/promoted/demoted/retired rules; asked for AV rule lifecycle,
layered early-exit, FP economics, quality metrics; search retrieve-then-rank, LTR from
tiny implicit feedback, interleaving, query expansion, freshness/authority/diversity;
plus explicit does-NOT-transfer list.
