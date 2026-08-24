# T194 scoreboard v2 — positional DeepSeek review, verbatim record

Status: in-flight
Date: 2026-08-05
Asker/integrator: codex_root
Model: deepseek-v4-pro
Door: `py agent_cli.py ask --prompts-file ... --workers 3 --max-tokens 4500 --json`
Input brief: `research/in-flight/t194-scoreboard-v2-review-prompts-codex-2026-08-05.json`

This file preserves peer output before reconciliation. Empty branches are recorded as empty; no
conclusion is reconstructed from reasoning that the door did not return.

## Aggregate receipt — first fan

- verdict: PARTIAL
- branches landed: 1/3
- elapsed: 90.91 seconds
- spend: $0.030128
- lexical agreement: not measurable from one landed answer
- branch 0, measurement semantics: empty answer, `finish_reason=length`, 4,500 completion tokens
- branch 1, adversarial benchmark: empty answer, `finish_reason=length`, 4,500 completion tokens
- branch 2, protocol integrity: landed, 4,300 completion tokens

## Branch 2 — protocol-integrity and sealed-key reviewer (verbatim)

(1) FATAL errors (CERTAIN)
- **`protocol_integrity` as an untrusted input.** The function accepts a verdict from outside, letting any caller set it to `clean` to suppress voiding or to `contaminated` to corrupt a legitimate round. The scorer must derive integrity from verifiable evidence, not accept a bare label.
- **Per‑class breakdown of baseline‑blind capability.** Reporting counts or existence of undetectable items (e.g., “baseline‑blind capability findings”) across repeated seeds leaks the sealed manifest’s canary identities and classes, exactly the answer‑key leak the charter forbids. The summary must never reveal class‑level details of undetectable entries.

(2) MUST‑CHANGE items
- **Eliminate the `protocol_integrity` input.** (CERTAIN) The function must internally compute integrity using the sealed manifest, the player’s submission, and any cryptographic proofs. Output integrity, do not ingest it.
- **Redact or aggregate all per‑class undetectable data.** (CERTAIN) Total, offered, judged, claimed counts for undetectables are forbidden. Instead, report only a single boolean `baseline_blind_capability_demonstrated` that does not name a class or count, and only when accompanied by cryptographic blinding or zero‑knowledge proof that no canary identity is revealed.
- **Treat unknown claims as accuracy failures, not as contamination.** (INFERRED) “Unknown claims” reporting must not implicitly expose undetectable classes. Report only a count of unknown claims without disclosing their identifiers or linking them to any manifest class.
- **The function must reject any round where `claimed ⊈ judged` or `judged ⊈ offered` by setting its own integrity to `contaminated` and voiding.** (CERTAIN) This inconsistency is the primary provable integrity failure and should not rely on an external flag.
- **`UNKNOWN` integrity must propagate out of the scorer, not be an input.** (CERTAIN) The function should output `UNKNOWN` when it cannot obtain a trusted manifest digest or sufficient proof, preserving the caller’s inability to influence the outcome.

(3) KEEP items
- **Consistency rules** (`claimed ⊆ judged ⊆ offered`) with immediate loud failure on violation. (CERTAIN)
- **Baseline‑blind hits do not void**, do not change validity, and are never treated as contamination. (CERTAIN)
- **`clean` → VALID, `contaminated` → VOID, `unknown` → UNKNOWN (voided=None)** . This decision structure is sound, *provided the scorer itself determines the state*. (CERTAIN)
- **Reporting recall, precision, coverage as aggregate metrics**, stripped of any per‑class structural leak. (INFERRED)

(4) Corrected minimal function signature
```
def evaluate_round(
    manifest_digest: bytes,               # hash of sealed manifest
    player_submission: PlayerSubmission,  # offered_ids, judged_ids, claimed_ids, optional proof
    round_context: bytes                  # e.g., commitment, nonce
) -> tuple[RoundReport, ProtocolIntegrity]:
```
* `ProtocolIntegrity` is an output enum `{CLEAN, CONTAMINATED, UNKNOWN}` determined solely by the function after verifying the manifest digest and submission consistency. No external integrity argument is accepted.

(5) Six‑row truth table

| # | Scenario | `offered` | `judged` | `claimed` | Manifest class | Protocol Integrity (output) | Void? | Key metric effect / Notes |
|---|----------|-----------|----------|-----------|-----------------|-----------------------------|-------|---------------------------|
| 1 | Unseen (total – offered) | – | – | – | any | depends on rest of round | no | Reported as `unseen`; class‑only counts suppressed. No per‑class detail. |
| 2 | Offered‑but‑unjudged | `id ∈ offered` | `id ∉ judged` | – | any | – | no | Contributes to `unjudged`. |
| 3 | Judged‑declined | `id ∈ offered` | `id ∈ judged` | `id ∉ claimed` | any | – | no | Contributes to `declined`. |
| 4 | Valid baseline‑blind claim | `∈ offered` | `∈ judged` | `∈ claimed` | undetectable | CLEAN | **no** | Capability flag set; no class/count leaked. |
| 5 | Bait claim (true positive) | `∈ offered` | `∈ judged` | `∈ claimed` | bait | CLEAN | **no** | Precision denominator/ numerator updated. |
| 6 | Contaminated protocol (e.g., claim ⊄ judged) | – | – | – | – | **CONTAMINATED** | **yes** | Entire round voided. |

**Authority for integrity states:**
- **CLEAN** – asserted by the scoring function (and only by it) after verifying that all identifiers are consistent, the manifest digest is authentic, and no proof of contamination is present.
- **CONTAMINATED** – asserted by the scoring function upon detecting an internal inconsistency (`claimed ⊈ judged`, manifest mismatch, or a validated cryptographic proof of misbehaviour).
- **UNKNOWN** – asserted by the scoring function when the manifest digest is untrusted or a required proof is missing; never accepted from external callers.

## Recovery status

Recovered both missing positions with a shorter answer contract and `max_tokens=9000`.

- verdict: DONE
- branches landed: 2/2
- elapsed: 90.76 seconds
- spend: $0.017843
- lexical agreement: 0.2038 (`unknown`, not collapsed or distinct)
- total review spend across both calls: $0.047971

## Recovered branch 0 — measurement-semantics reviewer (verbatim)

**Fatal/must-change bullets**  

1. **CERTAIN** — **“unknown claims” violates the subset architecture**  
   The spec requires “known claimed ⊆ judged ⊆ offered.” Yet it also promises to report “unknown claims.” An unknown claim is, by any plausible reading, an item claimed but not in the offered set (hence not in judged). This contradicts the subset constraints, making the metric ill‑defined and unimplementable.  

2. **INFERRED** — **Judged set is self‑reported with no proof of genuine exposure**  
   A participant can assert it “judged” offered items it never actually processed, inflating judged/offered and creating a fake precision (if precision is computed over judged). Without a cryptographic attestation of computation, the protocol confuses submission with genuine examination, opening a trivial cheating vector.  

3. **CERTAIN** — **“offered” denominator is endogenous and gameable**  
   The metrics claimed/offered and judged/offered treat offered as a denominator that the participant can influence (e.g., by flooding the offered stream with trivially absent items or by exploiting a lax definition of “offered”). A bad actor can thereby mask weak detection without making false claims.  

4. **UNCERTAIN** — **Precision denominator may be endogenously inflated**  
   Although precision is only named, not defined, typical formulations (correct‑claimed / |judged|) allow a detector to pad the judged set with easy negatives, artificially raising precision while recall collapses. Even if precision = correct‑claimed / |claimed|, the power to choose claimed endogenously still introduces a trade‑off that can be gamed when coupled with the other ratios.  

**Keep bullets**  

- Explicit reporting of **declined** and **unjudged** makes avoidance behaviour transparent, adding a true accountability dimension.  
- The hard subset constraint **claimed ⊆ judged ⊆ offered** enforces a logical data‑flow that, if verified correctly, prevents back‑dating of claims.  
- Separating **validity status** (VALID/VOID/UNKNOWN) from per‑round scoring decouples rule‑enforcement from measurement, which is sound.  
- Keeping **baseline‑blind findings** as a reported metric (without voiding) removes the perverse incentive to censor honest detections while preserving visibility.  

**Corrected minimal signature**  

```
analyze_round(
    manifest:     Set[ItemID],      # all ground‑truth items (positive + negative)
    offered:      Set[ItemID],      # items actually delivered to the detector (may include distractors)
    judged:       Set[ItemID],      # items for which the detector returned a verdict
    claimed:      Set[ItemID]       # items the detector asserts are positive
) → Report:
    totals: {
        total:   |manifest|,
        offered: |offered|,
        judged:  |judged|,
        claimed: |claimed|,
        declined:|judged| - |claimed|,
        unjudged:|offered| - |judged|,
        unseen:  |manifest \ offered|
    },
    ratios: {
        claimed_over_total:   |claimed| / |manifest|,
        claimed_over_offered: |claimed| / |offered|,
        judged_over_offered:  |judged|  / |offered|
    },
    quality: {
        precision:  |claimed ∩ true_positives| / |claimed|,
        baseline_blind_findings: count(claimed ∩ baseline_blind_class),
        unknown_findings:        count(claimed \ manifest)   # claims on distractors
    }
```
*Pre‑conditions enforced before computation:* `judged ⊆ offered`, `claimed ⊆ judged`, `true_positives` are items in `claimed` that belong to the target class in `manifest`. `unknown_findings` are claims on items that were offered but are not in the manifest; they do not break subset rules because offered can contain distractors.

**Truth table**  

| Condition               | Detection / truth                                      | Scoreboard treatment                                                                 |
|-------------------------|--------------------------------------------------------|--------------------------------------------------------------------------------------|
| Unseen                  | Item in `manifest` but not in `offered`                | Increment `unseen`; if >0, flag voluntary exclusion risk.                            |
| Offered‑unjudged        | Item in `offered` but not in `judged`                  | Increment `unjudged`; large values indicate participation gap or active avoidance.   |
| Judged‑declined         | Item in `judged` but not in `claimed`                  | Increment `declined`; negative verdicts; used to compute judged denominator.         |
| Valid baseline‑blind claim | Claimed item that belongs to the baseline‑blind class, protocol otherwise sound | Record in `baseline_blind_findings`; **never voids** — transparency only.           |
| Bait claim              | Claimed item that is a known bait (planted distractor) | Flag for investigation; may indicate detector is reporting hallucinated positives.   |
| Contaminated protocol   | External evidence of leak, collusion, or integrity breach | Set global validity to `VOID` (or `UNKNOWN`), overriding all computed scores.        |

## Recovered branch 1 — adversarial benchmark reviewer (verbatim)

**Fatal / must-change (concrete counterexamples)**  
- **CERTAIN** — zero offered causes division by zero. Input: manifest `["x"]`, offered `[]`, judged `[]`, claimed `[]`. Metric `judged/offered` (and `claimed/offered`) is undefined. Scoreboard must return `N/A` or a guarded sentinel, otherwise it panics. Without a guard the system is unusable in any round where a player abstains from offering.  
- **CERTAIN** — duplicate IDs in manifest inflate totals and distort rates. Input: manifest `["a","a"]`, offered `{"a"}`, judged `{"a"}`, claimed `{"a"}`. Reported `total = 2` but unique items =1, so `claimed/total = 0.5` while genuine coverage is 1.0. Deduplication on manifest must be mandatory, or the configuration declared `VOID`.  
- **INFERRED** — a judged id that was never offered (a “submitted branch that never lands”) violates `judged ⊆ offered`. The text “a baseline-blind hit never voids” must not override structural invalidity. Concrete: manifest `["a"]`, offered `[]`, judged `["a"]`, where `a` is baseline-blind. The subset violation renders the round `VOID` regardless of item type; the “never voids” rule must be scoped to hits inside a *valid* structure.  
- **UNCERTAIN** — unknown claims (ids not in manifest) are reported separately, but how they participate in claimed totals is undefined. Input: manifest `["x"]`, claimed `["y"]` (unknown). If claimed count includes `y`, `claimed/total` may exceed 1. The formula must explicitly exclude unknown ids from numerator and denominator or define a “claimed_manifest” measure.

**Keep (correctly scoped features)**  
- Enforced subset chain (`claimed ⊆ judged ⊆ offered ⊆ manifest`) provides self‑verification of data integrity.  
- Per‑class reporting of offers, judgments, claims, and declined/unjudged/unseen gives actionable transparency.  
- Baseline‑blind findings are tracked without voiding valid rounds, allowing measurement of detectability.  
- Unknown‑claims metric makes outlier behaviours visible without invalidating the round.

**Corrected minimal signature**  
```
// Input sets must be deduplicated; duplicate IDs in manifest → validity=VOID.
type ManifestEntry struct { ID string; IsBaselineBlind bool; IsBait bool }

func Scoreboard(
    manifest   []ManifestEntry,
    offered    map[string]bool,
    judged     map[string]bool,
    claimed    map[string]bool,
) (Report, Validity)

type Report struct {
    ClassID   string
    Total     int
    Offered   int
    Judged    int
    Claimed   int
    Declined  int           // judged but not claimed
    Unjudged  int           // offered but not judged
    Unseen    int           // manifest but not offered
    Metrics   struct {
        ClaimedToTotal    *float64  // nil if Total==0
        ClaimedToOffered  *float64  // nil if Offered==0
        JudgedToOffered   *float64  // nil if Offered==0
        Precision         *float64  // claimed judged that are in manifest ?
    }
    BaselineBlindFindings int
    UnknownClaims         []string   // ids claimed but not in manifest
}

type Validity int
const (
    VALID = iota
    VOID      // any structural violation, unknown id in offered/judged, duplicates
    UNKNOWN   // e.g., manifest empty but sets non‑empty? protocol not fully known
)
```

**Compact truth table** (predicates applied to a single item `id`)

| Row                       | Condition                                                                 | Classification step |
|---------------------------|---------------------------------------------------------------------------|----------------------|
| unseen                    | item ∈ manifest  ∧  item ∉ offered                                       | Valid measurement    |
| offered‑unjudged          | item ∈ offered    ∧  item ∉ judged                                       | Valid measurement    |
| judged‑declined           | item ∈ judged     ∧  item ∉ claimed                                      | Valid measurement    |
| valid baseline‑blind claim| item is baseline‑blind ∧ item ∈ claimed ∧ round structural validity = VALID | Counted, never voids |
| bait claim                | item is bait‑live  ∧  item ∈ claimed ∧ round validity = VALID            | Counted, may void?   |
| contaminated protocol     | duplicate manifest id ∨ offered⊄manifest ∨ judged⊄offered ∨ claimed⊄judged | Round → VOID         |
