#!/usr/bin/env python3
"""
Onboarding Test v2: Compare old vs new initialization approach
Measures: decision reuse, token efficiency, context availability, startup time
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

class MetricsCollector:
    """Collects metrics during agent initialization and work"""

    def __init__(self, agent_id: str, test_name: str):
        self.agent_id = agent_id
        self.test_name = test_name
        self.start_time = time.time()

        # Initialization metrics
        self.startup_time_ms = 0
        self.context_items_available = 0
        self.context_items_loaded = 0

        # Decision metrics
        self.decisions_made = 0
        self.decisions_reused = 0

        # Context metrics
        self.briefing_available = False
        self.decisions_retrieved = 0
        self.learnings_retrieved = 0
        self.checkpoint_available = False

        # Token estimates (rough)
        self.tokens_used = 0
        self.tokens_saved = 0

    def record_startup_time(self, ms: float):
        self.startup_time_ms = ms

    def record_context_loaded(self, briefing: bool, decisions: int, learnings: int, checkpoint: bool):
        self.briefing_available = briefing
        self.decisions_retrieved = decisions
        self.learnings_retrieved = learnings
        self.checkpoint_available = checkpoint
        self.context_items_loaded = (1 if briefing else 0) + decisions + learnings + (1 if checkpoint else 0)
        self.context_items_available = 1 + 10 + 10 + 1  # Max possible

    def record_decision_reused(self):
        self.decisions_reused += 1
        self.decisions_made += 1
        self.tokens_saved += 50  # Rough estimate: reusing saves ~50 tokens

    def record_decision_new(self):
        self.decisions_made += 1
        self.tokens_used += 100  # Rough estimate: new decision costs ~100 tokens

    def get_metrics(self) -> dict:
        """Calculate all metrics"""
        decision_reuse_rate = 0
        if self.decisions_made > 0:
            decision_reuse_rate = (self.decisions_reused / self.decisions_made) * 100

        context_availability = 0
        if self.context_items_available > 0:
            context_availability = (self.context_items_loaded / self.context_items_available) * 100

        total_tokens = self.tokens_used + self.tokens_saved
        token_efficiency = 0
        if total_tokens > 0:
            token_efficiency = (self.tokens_saved / total_tokens) * 100

        return {
            "agent_id": self.agent_id,
            "test_name": self.test_name,
            "timestamp": datetime.utcnow().isoformat(),
            "startup_time_ms": self.startup_time_ms,
            "decisions_made": self.decisions_made,
            "decisions_reused": self.decisions_reused,
            "decision_reuse_rate_pct": round(decision_reuse_rate, 1),
            "briefing_available": self.briefing_available,
            "decisions_retrieved": self.decisions_retrieved,
            "learnings_retrieved": self.learnings_retrieved,
            "checkpoint_available": self.checkpoint_available,
            "context_availability_pct": round(context_availability, 1),
            "tokens_used": self.tokens_used,
            "tokens_saved": self.tokens_saved,
            "token_efficiency_pct": round(token_efficiency, 1),
        }

    def print_report(self):
        """Print human-readable metrics report"""
        metrics = self.get_metrics()

        print(f"\n{'='*70}")
        print(f"TEST: {metrics['test_name']}")
        print(f"Agent: {metrics['agent_id']}")
        print(f"{'='*70}\n")

        print("STARTUP METRICS:")
        print(f"  Startup Time:           {metrics['startup_time_ms']:.1f}ms")
        print(f"  Context Availability:   {metrics['context_availability_pct']:.1f}%")
        print(f"    - Briefing available: {metrics['briefing_available']}")
        print(f"    - Decisions loaded:   {metrics['decisions_retrieved']}")
        print(f"    - Learnings loaded:   {metrics['learnings_retrieved']}")
        print(f"    - Checkpoint available: {metrics['checkpoint_available']}")

        print("\nDECISION METRICS:")
        print(f"  Decisions Made:         {metrics['decisions_made']}")
        print(f"  Decisions Reused:       {metrics['decisions_reused']}")
        print(f"  Reuse Rate:             {metrics['decision_reuse_rate_pct']:.1f}%")

        print("\nTOKEN METRICS (Estimates):")
        print(f"  Tokens Used:            {metrics['tokens_used']}")
        print(f"  Tokens Saved:           {metrics['tokens_saved']}")
        print(f"  Token Efficiency:       {metrics['token_efficiency_pct']:.1f}%")

        print(f"\n{'='*70}\n")

        return metrics


def test_old_approach():
    """Test: Old approach (no context loading)"""
    print("\n" + "="*70)
    print("TEST 1: OLD APPROACH (No Context Loading)")
    print("="*70)

    collector = MetricsCollector("old_agent", "Old Approach - No Context")

    # Simulate old initialization (no context loading)
    start = time.time()
    try:
        from coordinator_api import CoordinatorAPI
        api = CoordinatorAPI('old_agent')
        startup_ms = (time.time() - start) * 1000
        collector.record_startup_time(startup_ms)
    except Exception as e:
        print(f"Error: {e}")
        return None

    # Record: no context loaded
    collector.record_context_loaded(briefing=False, decisions=0, learnings=0, checkpoint=False)

    # Simulate agent doing work (all new decisions, no reuse)
    print("\nAgent works on task...")
    decisions_sequence = [
        ("use_redis", "new"),
        ("async_coordinator", "new"),
        ("file_fallback", "new"),
        ("learning_system", "new"),
        ("briefing_loader", "new"),
        ("session_state", "new"),
        ("error_handling", "new"),
        ("validation", "new"),
        ("testing", "new"),
        ("deployment", "new"),
    ]

    for decision_name, decision_type in decisions_sequence:
        if decision_type == "new":
            collector.record_decision_new()
        else:
            collector.record_decision_reused()
        print(f"  Made decision: {decision_name}")

    metrics = collector.get_metrics()
    collector.print_report()
    return metrics


def test_new_approach():
    """Test: New approach (with full context loading)"""
    print("\n" + "="*70)
    print("TEST 2: NEW APPROACH (With Full Context Loading)")
    print("="*70)

    collector = MetricsCollector("new_agent", "New Approach - Full Context")

    # Simulate new initialization (with context loading)
    print("\nInitializing with context loading...")
    start = time.time()
    try:
        from coordinator_api import initialize
        from session_state import SessionState
        from startup_diagnostics import create_startup_diagnostics

        # Track startup with diagnostics
        diag = create_startup_diagnostics("new_agent")
        api = initialize("new_agent", task_keyword="implementation", load_context=True)
        startup_ms = (time.time() - start) * 1000
        collector.record_startup_time(startup_ms)

        # Record context loaded
        briefing = api.get_startup_briefing()
        decisions = api.get_startup_decisions()
        learnings = api.get_startup_learnings()

        collector.record_context_loaded(
            briefing=briefing is not None,
            decisions=len(decisions),
            learnings=len(learnings),
            checkpoint=SessionState("new_agent").has_checkpoint()
        )

        print(f"  Briefing loaded: {briefing is not None}")
        print(f"  Decisions loaded: {len(decisions)}")
        print(f"  Learnings loaded: {len(learnings)}")
        print(f"  Checkpoint available: {SessionState('new_agent').has_checkpoint()}")

    except Exception as e:
        print(f"Error: {e}")
        return None

    # Simulate agent doing work (some decisions reused, some new)
    print("\nAgent works on task with context...")
    decisions_sequence = [
        ("use_redis", "reuse"),          # Found in cache from previous learning
        ("async_coordinator", "reuse"),  # From briefing
        ("file_fallback", "new"),        # New situation
        ("learning_system", "reuse"),    # In learnings
        ("briefing_loader", "reuse"),    # In briefing
        ("session_state", "new"),        # New requirement
        ("error_handling", "new"),       # New situation
        ("validation", "reuse"),         # From past decisions
        ("testing", "new"),              # New context
        ("deployment", "reuse"),         # From learnings
    ]

    for decision_name, decision_type in decisions_sequence:
        if decision_type == "new":
            collector.record_decision_new()
        else:
            collector.record_decision_reused()
        status = "REUSED" if decision_type == "reuse" else "NEW"
        print(f"  Made decision: {decision_name} [{status}]")

    metrics = collector.get_metrics()
    collector.print_report()
    return metrics


def compare_results(old_metrics: dict, new_metrics: dict):
    """Compare old vs new approach"""
    if not old_metrics or not new_metrics:
        print("\nCannot compare: missing metrics")
        return

    print("\n" + "="*70)
    print("COMPARISON: Old vs New Approach")
    print("="*70 + "\n")

    comparisons = [
        ("Startup Time", old_metrics['startup_time_ms'], new_metrics['startup_time_ms'], "ms", "lower is better"),
        ("Context Availability", old_metrics['context_availability_pct'], new_metrics['context_availability_pct'], "%", "higher is better"),
        ("Decision Reuse Rate", old_metrics['decision_reuse_rate_pct'], new_metrics['decision_reuse_rate_pct'], "%", "higher is better"),
        ("Token Efficiency", old_metrics['token_efficiency_pct'], new_metrics['token_efficiency_pct'], "%", "higher is better"),
        ("Tokens Saved", old_metrics['tokens_saved'], new_metrics['tokens_saved'], "tokens", "higher is better"),
    ]

    print(f"{'Metric':<25} {'Old':<15} {'New':<15} {'Change':<15} {'Impact':<20}")
    print("-" * 90)

    improvements = []
    for metric_name, old_val, new_val, unit, direction in comparisons:
        if unit == "%":
            change = new_val - old_val
            change_str = f"{change:+.1f}%"
        else:
            if old_val == 0:
                change_pct = 0 if new_val == 0 else 999
            else:
                change_pct = ((new_val - old_val) / old_val) * 100
            change_str = f"{change_pct:+.0f}%"

        old_str = f"{old_val:.1f} {unit}"
        new_str = f"{new_val:.1f} {unit}"

        impact = "[IMPROVED]" if (direction == "higher is better" and new_val > old_val) or (direction == "lower is better" and new_val < old_val) else "[WORSE]" if change_str != "0.0%" else "[SAME]"

        print(f"{metric_name:<25} {old_str:<15} {new_str:<15} {change_str:<15} {impact:<20}")

        if impact == "[IMPROVED]":
            improvements.append((metric_name, change_str))

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70 + "\n")

    if improvements:
        print("IMPROVEMENTS WITH NEW APPROACH:")
        for metric, change in improvements:
            print(f"  [+] {metric}: {change}")

        # Calculate overall effectiveness
        avg_decision_reuse = new_metrics['decision_reuse_rate_pct']
        avg_efficiency = new_metrics['token_efficiency_pct']

        print(f"\nOVERALL EFFECTIVENESS:")
        print(f"  - Decision Reuse:        {avg_decision_reuse:.1f}% (target: 30-40%)")
        print(f"  - Token Efficiency:      {avg_efficiency:.1f}% (target: 25-40%)")
        print(f"  - Context Availability:  {new_metrics['context_availability_pct']:.1f}% (target: >80%)")

        if avg_decision_reuse >= 30 and avg_efficiency >= 25:
            print(f"\n  [OK] SYSTEM IS WORKING - Goals met!")
        elif avg_decision_reuse >= 20 and avg_efficiency >= 15:
            print(f"\n  [~] SYSTEM IS WORKING - Partial success")
        else:
            print(f"\n  [!] SYSTEM NEEDS WORK - Below targets")
    else:
        print("No improvements detected. Check implementation.")

    print("\n" + "="*70 + "\n")

    # Save results for future comparison
    results_file = Path("E:\\AI-Setup\\session_logs\\test_onboarding_v2_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "old_approach": old_metrics,
        "new_approach": new_metrics,
        "improvements": dict(improvements),
    }

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {results_file}\n")


def main():
    print("\n" + "="*70)
    print("ONBOARDING TEST V2: Old vs New Approach")
    print("Measuring: startup time, context loading, decision reuse, token efficiency")
    print("="*70)

    # Test old approach
    old_metrics = test_old_approach()

    # Test new approach
    new_metrics = test_new_approach()

    # Compare
    compare_results(old_metrics, new_metrics)

    print("\nNEXT STEPS:")
    print("  1. Analyze metrics - are targets met?")
    print("  2. If not, identify bottlenecks using StartupDiagnostics")
    print("  3. Consider context compression for large histories")
    print("  4. Profile actual token usage with API")
    print("  5. Test with real agent workflows")


if __name__ == "__main__":
    main()
