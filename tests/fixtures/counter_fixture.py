"""Gold fixture for the counter-retrieval eval (recall confirmation-bias, Slice 0).

Companion doc: docs/recall-critic-decision.md (the decision + the slice plan).

WHAT THIS MEASURES
------------------
Recall today surfaces the top *supporting* lessons for an action. Slice 1 will change the
unit of retrieval to a POSITION = thesis + its strongest live counter. Before we build that,
we need a yardstick that answers, honestly and offline: does a counter-finder surface a REAL
counter when one exists, and stay SILENT when none does? This fixture is that yardstick's
ground truth.

Each case is SELF-CONTAINED: it carries its own tiny `corpus` (the candidate pool a
counter-finder searches) so the eval is deterministic and never touches the live store. A
detector under test sees `thesis` + `corpus` and must decide whether to surface a counter and,
if so, which source(s).

LABELLING METHODOLOGY (kept auditable on purpose -- same discipline as FAITH-1 provenance)
------------------------------------------------------------------------------------------
A corpus record is a GENUINE counter to the thesis iff one of:
  - opposite_success        : same topic, the thesis says it worked and this record reports it
                              failed (or vice-versa).
  - anti_pattern            : this record carries a populated `anti_pattern` naming the very
                              thing the thesis recommends as actively known-bad.
  - conflicting_recommendation : both may be self-reported successes, yet they advise opposite
                              actions on the same decision (the hard case -- needs stance, not
                              keyword overlap).
A record that merely shares a TOPIC while AGREEING is NOT a counter (these are the precision
distractors -- surfacing them would be manufactured "false balance", the failure mode the
design explicitly forbids). `counter_exists=False` cases are the silence controls.

`should_change_action` is a RICHER, more subjective label (would a rational agent actually
revise its plan?). It is deliberately left None here: it needs human adjudication (open
question #1 in the decision doc) and is out of scope for Slice 0's objective metric.

REAL vs SYNTHETIC
-----------------
`origin="real"` cases quote actual lessons from the store (text trimmed but faithful). The
corpus is 90 `yes` / 3 `no` / 2 `partial` / 0 `anti_pattern`, so genuine counters are scarce --
that scarcity is itself the finding (confirmation-by-omission), and it forces most cases to be
`origin="synthetic"` clean constructions that exercise the detector independent of corpus rot.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def L(name: str, success: str, rec: str, *, anti_pattern: str = "",
      agent: str = "synthetic") -> Dict[str, Any]:
    """A minimal lesson record shaped like what the LearningStore yields
    (experiment_name / success / recommendation / anti_pattern / agent_id)."""
    r: Dict[str, Any] = {"experiment_name": name, "success": success,
                         "recommendation": rec, "agent_id": agent}
    if anti_pattern:
        r["anti_pattern"] = anti_pattern
    return r


def _case(cid: str, origin: str, thesis: Dict[str, Any], corpus: List[Dict[str, Any]],
          counter_sources: List[str], kind: Optional[str], why: str) -> Dict[str, Any]:
    # The thesis is always searchable within its own corpus (a detector must not count the
    # thesis as its own counter -- that is a detector responsibility, asserted in the harness).
    pool = [thesis] + [c for c in corpus if c["experiment_name"] != thesis["experiment_name"]]
    return {
        "id": cid, "origin": origin, "thesis": thesis, "corpus": pool,
        "counter_exists": bool(counter_sources), "counter_sources": list(counter_sources),
        "kind": kind, "should_change_action": None, "why": why,
    }


# --- real lessons (faithful trims of actual store records) -------------------------------
_EMBED_SEAM = L("codex_c0_embedder", "yes",
    "ONE embedding seam (Ranker.relevance_fn) so every consumer (router Tier-1, Clusterer, "
    "recall) gets embedding relevance for free. Cache-first + lazy-load.", agent="claude_design")
_EMBED_LOST = L("spine_v6_theme_discovery", "yes",
    "When an ablation gate exists, MEASURE before committing a shape -- the obvious approach "
    "(embeddings replace keywords) LOST; hybrid won. Gate embedding theming behind an explicit "
    "flag, not the default write path.", agent="claude_research")
_TIER1_ABLATION = L("narrative_slice_6_ablation_failed", "no",
    "Keep the heuristic as the default Tier 0; an optional experimental Tier 1 (embeddings) "
    "behind a flag only.", agent="composer_cursor")
_GITIGNORE = L("gitignore_no_inline_comments", "yes",
    "Never put trailing comments on .gitignore pattern lines; only lines STARTING with # are "
    "comments -- put the comment on its own line above the pattern.", agent="claude")
_RECALL_V1 = L("recall_at_action_v1", "yes",
    "action-trigger + deterministic ranking is ahead of SOTA (mem0/Zep inject at turn-start); "
    "non-blocking so latency delays a hint, not the action.", agent="claude")
_RECALL_POLISH = L("recall_at_action_polish", "yes",
    "recall-at-action is complete end-to-end: engine -> CLI -> hook -> warm cache -> anti-repeat.",
    agent="claude")
_DEPLOY = L("deploy_kit_public", "yes",
    "core is stdlib-only (no required deps); Redis optional on 16379; deterministic file "
    "fallback everywhere.", agent="claude")


GOLD_CASES: List[Dict[str, Any]] = [

    # ============ HAS-COUNTER: opposite_success (thesis worked / counter failed, same topic) ============
    _case("syn-opp-blocking", "synthetic",
          L("blocking_writes_safe", "yes",
            "synchronous blocking writes keep the store consistent; prefer them for correctness"),
          [L("blocking_writes_hang", "no",
             "synchronous blocking writes hung connect for 48s on a filtered port; make writes "
             "async / non-blocking"),
           L("naming_ddd", "yes", "use ubiquitous-language names from the domain")],
          ["blocking_writes_hang"], "opposite_success",
          "same topic (synchronous blocking writes), thesis=worked vs counter=failed"),

    _case("syn-opp-redis", "synthetic",
          L("redis_only_state", "yes",
            "store all coordination state in Redis for speed; it is the single source of truth"),
          [L("redis_only_crash", "no",
             "Redis-only coordination lost state on crash; use file-first with Redis optional"),
           L("stopwords_help", "yes", "dropping generic tokens improves keyword relevance")],
          ["redis_only_crash"], "opposite_success",
          "same topic (Redis-only coordination state), opposite outcome"),

    _case("syn-opp-cache-ttl", "synthetic",
          L("long_ttl_fast", "yes", "a long disk-cache TTL keeps the hot path fast; raise it"),
          [L("long_ttl_stale", "no",
             "a long cache TTL served stale poisoned data across processes; keep the TTL short"),
           L("faithful_gate", "yes", "gate surfaced text through a faithfulness check")],
          ["long_ttl_stale"], "opposite_success",
          "same topic (cache TTL length), thesis=worked vs counter=failed"),

    # ============ HAS-COUNTER: anti_pattern (counter names the thesis's move as known-bad) ============
    _case("syn-anti-unroll", "synthetic",
          L("unroll_hot_loop", "yes", "unroll the hot loop for a speedup"),
          [L("python_unroll_waste", "no",
             "loop unrolling gave only +2% in Python and hurt readability -- do not do it",
             anti_pattern="python_loop_unrolling"),
           L("memoize_win", "yes", "memoization gave a real +52% speedup")],
          ["python_unroll_waste"], "anti_pattern",
          "counter carries anti_pattern naming loop unrolling, the thesis's exact move"),

    _case("syn-anti-gitignore", "synthetic",
          L("gitignore_inline_ok", "yes",
            "add a trailing comment on the .gitignore line to explain each pattern"),
          [L("gitignore_inline_breaks", "no",
             "trailing comments on .gitignore lines are parsed as part of the pattern and break "
             "the ignore", anti_pattern="gitignore_inline_comment"),
           L("recency_decay", "yes", "decay lesson weight by age so fresh outranks stale")],
          ["gitignore_inline_breaks"], "anti_pattern",
          "counter carries anti_pattern for inline gitignore comments"),

    _case("syn-anti-selfjudge", "synthetic",
          L("llm_judge_grades", "yes",
            "use an LLM-as-judge to grade whether recalled context is faithful"),
          [L("llm_judge_biased", "no",
             "LLM-as-judge is unreliable (self/position bias); judge deterministically instead",
             anti_pattern="llm_as_judge_self_bias"),
           L("provenance_tags", "yes", "prefix each lesson with a verification-status tag")],
          ["llm_judge_biased"], "anti_pattern",
          "counter names LLM-as-judge (the thesis's move) as an anti-pattern"),

    # ============ HAS-COUNTER: conflicting_recommendation (both 'yes', opposite advice) ============
    _case("syn-conf-critic-block", "synthetic",
          L("critic_blocks", "yes",
            "the critic should BLOCK the action until the agent resolves the flagged tension"),
          [L("critic_advises", "yes",
             "the critic must be advisory and non-blocking; it informs, it never stalls the action"),
           L("stopwords_help2", "yes", "short exemplar phrases beat one long seed phrase")],
          ["critic_advises"], "conflicting_recommendation",
          "both self-reported successes, but opposite advice on block-vs-advise"),

    _case("syn-conf-sync-async", "synthetic",
          L("tier2_sync", "yes", "run the Tier-2 LLM critic synchronously so the agent sees it now"),
          [L("tier2_async", "yes",
             "run the Tier-2 critic async and surface it as a follow-up; never block the hot path"),
           L("cap_budget", "yes", "cap the critic token budget per action")],
          ["tier2_async"], "conflicting_recommendation",
          "opposite advice (sync vs async) on the same Tier-2 critic decision"),

    _case("syn-conf-anti-repeat", "synthetic",
          L("show_every_time", "yes",
            "re-surface a relevant lesson every time the action recurs so it is never missed"),
          [L("anti_repeat", "yes",
             "suppress a lesson already shown this session; re-surfacing it is the top noise source"),
           L("floor_relevance", "yes", "gate on a relevance floor so off-topic hints stay silent")],
          ["anti_repeat"], "conflicting_recommendation",
          "opposite advice on re-surfacing vs anti-repeat, both 'worked'"),

    # ============ HAS-COUNTER: real lessons ============
    _case("real-embed-cluster", "real",
          _EMBED_SEAM,
          [_EMBED_LOST, _TIER1_ABLATION, _RECALL_POLISH],
          ["spine_v6_theme_discovery", "narrative_slice_6_ablation_failed"],
          "conflicting_recommendation",
          "REAL: embeddings-everywhere (codex_c0_embedder) vs embeddings-lost/gate-behind-flag "
          "(spine_v6) and keep-Tier0-heuristic (narrative ablation, success=no). NB: the counters "
          "use different vocabulary than the thesis -- a pure keyword overlap will MISS them, "
          "which is exactly the gap Slice 1 must close."),

    _case("real-embed-vs-ablation", "real",
          _EMBED_LOST,
          [_EMBED_SEAM, _RECALL_V1, _DEPLOY],
          ["codex_c0_embedder"], "conflicting_recommendation",
          "REAL (mirror): gate-embeddings-behind-a-flag vs one-embedding-seam-everywhere"),

    # ============ NO-COUNTER: agreement (silence controls) ============
    _case("syn-agree-perf", "synthetic",
          L("memoize_hot", "yes", "memoization sped up the hot path substantially"),
          [L("cache_results", "yes", "caching computed results improved performance"),
           L("warm_cache_start", "yes", "warming the cache at start avoids the cold reload")],
          [], None, "all three agree performance caching helps -- no genuine counter -> silence"),

    _case("syn-agree-determinism", "synthetic",
          L("determinism_wins", "yes",
            "deterministic action-time ranking beats turn-start injection"),
          [L("no_llm_hotpath", "yes", "keep the hot path LLM-free for latency and reproducibility"),
           L("fail_soft", "yes", "fail soft: a recall path must never brick the action")],
          [], None, "agreeing neighbours on determinism -> no counter -> silence"),

    _case("syn-agree-failures", "synthetic",
          L("approachB_failed", "no", "approach B failed: it deadlocked under concurrent writes"),
          [L("approachB_failed_too", "no",
             "approach B also failed for us: it corrupted the index on crash")],
          [], None, "both records AGREE the approach failed (same direction) -> not a counter"),

    # ============ NO-COUNTER: off-topic (silence controls) ============
    _case("syn-offtopic-hooks", "synthetic",
          L("githook_exit1", "yes", "use exit 1 in git hooks to abort; exit 2 is Claude-only"),
          [L("memoize_win2", "yes", "memoization gave a real speedup"),
           L("embed_seam2", "yes", "one embedding seam serves every consumer")],
          [], None, "neighbours are on unrelated topics -> nothing to surface -> silence"),

    _case("syn-offtopic-gitignore", "synthetic",
          _GITIGNORE,
          [_RECALL_V1, _EMBED_SEAM],
          [], None, "REAL thesis (gitignore) among off-topic recall/embedding lessons -> silence"),

    # ============ NO-COUNTER: precision distractors (topically similar but AGREEING) ============
    _case("syn-distractor-embed", "synthetic",
          L("embed_relevance", "yes", "embeddings improve retrieval relevance on our corpus"),
          [L("embed_clustering", "yes",
             "embeddings improved clustering quality for the theme discovery step"),
           L("embed_cache", "yes", "cache the embedding model load; it is 7.5s cold")],
          [], None,
          "shares the 'embedding' topic but every neighbour AGREES -> surfacing one would be "
          "manufactured false balance -> must stay silent (precision test)"),

    _case("syn-distractor-redis", "synthetic",
          L("redis_fast", "yes", "Redis streams give fast fan-out for the coordination bus"),
          [L("redis_streams_good", "yes", "per-agent cursor over Redis streams works well for fan-out"),
           L("redis_optional", "yes", "Redis stays optional; the file backend mirrors it")],
          [], None,
          "shares the 'redis' topic but neighbours agree -> no genuine counter -> silence"),

    # PRECISION (Slice 3): an on-topic ANTI-PATTERN that the thesis AGREES with. The thesis advocates
    # the fix the anti-pattern implies, so it is NOT a contradiction -- surfacing it is hallucinated
    # disagreement. This is the real dogfooding false-positive distilled (the finder fired 7/7 of these
    # on the live corpus). Must stay SILENT: "has anti_pattern + on-topic" != "contradicts this thesis".
    _case("syn-antipattern-agrees", "synthetic",
          L("expose_on_door", "yes",
            "always expose a new capability on the same door agents already use, in the same slice"),
          [L("cap_no_door", "no",
             "we shipped a capability but never exposed it on any door, so it went unused",
             anti_pattern="capability_without_a_door"),
           L("naming_ddd3", "yes", "use ubiquitous domain names for new modules")],
          [], None,
          "thesis AGREES with the on-topic anti-pattern (both: expose on the door) -> not a counter -> silent"),

    _case("syn-antipattern-agrees-2", "synthetic",
          L("async_flush_good", "yes",
            "make the store flush async and non-blocking so the write path never stalls"),
          [L("sync_flush_bad2", "no",
             "a synchronous blocking flush hung the store; never block the write path",
             anti_pattern="sync_blocking_flush")],
          [], None,
          "thesis (async, non-blocking) AGREES with the anti-pattern (never block) -> silent"),

    # ============ NO-COUNTER: singleton + real agreement ============
    _case("syn-singleton", "synthetic",
          L("lonely_lesson", "yes", "this is the only lesson on its very specific topic"),
          [], [], None, "no neighbours at all -> silence"),

    _case("real-recall-agree", "real",
          _RECALL_V1,
          [_RECALL_POLISH, _DEPLOY],
          [], None,
          "REAL: recall lessons that refine/agree with each other -> no counter -> silence"),
]


def gold_cases() -> List[Dict[str, Any]]:
    """The full labeled eval set (real + synthetic)."""
    return [dict(c) for c in GOLD_CASES]


# --- SAMPLE_CORPUS: a faithful sample of the real store's outcome skew, for the coverage
# report. Mirrors the measured distribution (mostly self-reported 'yes', a few 'no'/'partial',
# ZERO populated anti_pattern) so the counter-density number is representative, not cherry-picked.
SAMPLE_CORPUS: List[Dict[str, Any]] = [
    _EMBED_SEAM, _EMBED_LOST, _RECALL_V1, _RECALL_POLISH, _DEPLOY, _GITIGNORE, _TIER1_ABLATION,
    L("spine1_unify", "yes", "the consolidator is the one seam; route every source through it"),
    L("faith1_faithfulness_critic", "yes", "deterministic no-LLM faithfulness gate at the seam"),
    L("provenance_tags_ship", "yes", "prefix recalled lessons with worked/unverified/anti-pattern"),
    L("concurrency_c0_git_guard", "yes", "in a shared tree, git add/commit explicit paths only"),
    L("concurrency_c1_worktrees", "yes", "agents live in worktrees; integrate from master"),
    L("bifrost_b0_bus_transport", "yes", "per-agent cursor beats consumer groups for fan-out"),
    L("wrap_autocapture_shipped", "yes", "ambient session capture is continuity insurance"),
    L("narrative_test_hermeticity", "no", "clear shared store keys per test for count assertions"),
    L("patchright_headless_google", "partial", "true headless cannot pass the gate; use invisible mode"),
]


def sample_corpus() -> List[Dict[str, Any]]:
    """A representative real-skew corpus for the counter-density (confirmation-by-omission) report."""
    return [dict(r) for r in SAMPLE_CORPUS]
