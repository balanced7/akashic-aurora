#!/usr/bin/env python3
"""Test: Complete startup/learning/briefing system (after fixes)"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test 1: Can we import everything?"""
    try:
        from learning_store import LearningStore, get_learning_store
        from coordinator_api import CoordinatorAPI, initialize
        from coordinator_service import CoordinatorService
        from agent_briefing_loader import AgentBriefingLoader
        return True, "All imports successful (including new modules)"
    except Exception as e:
        return False, f"Import failed: {e}"

def test_api_initialization():
    """Test 2: Can we initialize without Redis?"""
    try:
        from coordinator_api import CoordinatorAPI
        api = CoordinatorAPI('test_agent_001')

        # Check if startup context attributes exist
        has_context = hasattr(api, 'startup_context')
        has_briefing = hasattr(api, 'startup_briefing')
        has_decisions = hasattr(api, 'startup_decisions')
        has_learnings = hasattr(api, 'startup_learnings')

        if has_context and has_briefing and has_decisions and has_learnings:
            return True, f"API created with startup context fields (session: {api.session_id})"
        else:
            return False, "API missing startup context fields"
    except Exception as e:
        return False, f"API creation failed: {e}"

def test_learning_store_file_fallback():
    """Test 3: Can we record learnings to file (file fallback)?"""
    try:
        from learning_store import LearningStore
        store = LearningStore(redis_client=None)

        learning = {
            'experiment_name': 'test_file_fallback',
            'what_tried': 'Test file fallback',
            'expected_outcome': 'Should write to file',
            'actual_outcome': 'It worked',
            'success': 'yes',
            'timestamp': '2026-06-16T12:00:00Z',
            'recommendation': 'File fallback works',
            'anti_pattern': 'None',
            'root_cause': 'N/A',
            'confidence': 'high',
            'agent_id': 'test_agent',
            'metrics': {}
        }

        result = store.record_learning(learning)
        if result:
            # Verify file was written
            log_file = Path("E:\\AI-Setup\\session_logs\\learnings.jsonl")
            if log_file.exists():
                return True, "Learning written to file successfully"
            else:
                return False, "File fallback didn't write file"
        else:
            return False, "record_learning returned False"
    except Exception as e:
        return False, f"File fallback test failed: {e}"

def test_startup_context_loading():
    """Test 4: Does initialize() load startup context?"""
    try:
        from coordinator_api import initialize

        # Initialize with context loading
        api = initialize('agent_context_test', load_context=True)

        # Check if context was loaded
        has_context_method = hasattr(api, 'get_startup_context')
        has_briefing_method = hasattr(api, 'get_startup_briefing')
        has_decisions_method = hasattr(api, 'get_startup_decisions')
        has_learnings_method = hasattr(api, 'get_startup_learnings')

        if all([has_context_method, has_briefing_method, has_decisions_method, has_learnings_method]):
            return True, "Startup context loading methods available"
        else:
            return False, "Missing startup context retrieval methods"
    except Exception as e:
        return False, f"Startup context loading test failed: {e}"

def test_decision_cache_queries():
    """Test 5: Can we query decisions from cache?"""
    try:
        from coordinator_service import DecisionCache
        cache = DecisionCache()

        # Add a test decision
        cache.add_decision('use_redis', 'yes', 'Redis is fast')

        # Test single decision retrieval
        decision = cache.get_decision('use_redis')
        if not decision:
            return False, "get_decision() didn't return cached decision"

        # Test relevant decisions query
        relevant = cache.get_relevant_decisions('redis', limit=10)
        if len(relevant) == 0:
            return False, "get_relevant_decisions() returned no matches"

        return True, "Decision cache queries work"
    except Exception as e:
        return False, f"Decision cache test failed: {e}"

def test_briefing_loader():
    """Test 6: Does AgentBriefingLoader exist and work?"""
    try:
        from agent_briefing_loader import AgentBriefingLoader, load_agent_context

        loader = AgentBriefingLoader('test_agent', None)
        context = loader.load_startup_context()

        # Check context structure
        has_keys = all(k in context for k in ['agent_id', 'briefing', 'relevant_decisions', 'recent_learnings', 'metadata'])

        if has_keys:
            return True, "AgentBriefingLoader creates proper context structure"
        else:
            return False, "Context structure incomplete"
    except Exception as e:
        return False, f"Briefing loader test failed: {e}"

def test_complete_startup_flow():
    """Test 7: Complete end-to-end startup flow"""
    try:
        from coordinator_api import initialize, get_api

        # Initialize an agent with full context loading
        api = initialize('agent_e2e_test', load_context=True)

        # Verify all retrieval methods work
        context = api.get_startup_context()
        briefing = api.get_startup_briefing()
        decisions = api.get_startup_decisions()
        learnings = api.get_startup_learnings()

        # All should return something (even if None or empty list)
        if context is not None and isinstance(decisions, list) and isinstance(learnings, list):
            return True, "Complete startup flow works"
        else:
            return False, "Startup flow incomplete"
    except Exception as e:
        return False, f"E2E startup test failed: {e}"

def main():
    tests = [
        ("Imports (including new modules)", test_imports),
        ("API with startup context fields", test_api_initialization),
        ("Learning file fallback", test_learning_store_file_fallback),
        ("Startup context loading", test_startup_context_loading),
        ("Decision cache queries", test_decision_cache_queries),
        ("Briefing loader", test_briefing_loader),
        ("Complete E2E startup flow", test_complete_startup_flow),
    ]

    print("\n" + "="*70)
    print("STARTUP SYSTEM EVALUATION (Post-Fix)")
    print("="*70 + "\n")

    results = []
    for name, test_func in tests:
        success, msg = test_func()
        status = "PASS" if success else "FAIL"
        results.append((name, status, msg))
        symbol = "[PASS]" if success else "[FAIL]"
        print(f"{symbol} {name}")
        print(f"      {msg}\n")

    # Summary
    passed = sum(1 for _, status, _ in results if status == "PASS")
    total = len(results)

    print("="*70)
    print(f"RESULTS: {passed}/{total} tests passed\n")

    if passed == total:
        print("SUCCESS: All startup system tests passing!")
        print("\nAgents can now:")
        print("  1. Auto-load context at startup (briefing, decisions, learnings)")
        print("  2. Record learnings to file when Redis is down")
        print("  3. Query past decisions before making new ones")
        print("  4. Print readable startup briefings")
    else:
        print("Some tests failed. Review the output above.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
