#!/usr/bin/env python3
"""
OpenCode Progress Test
Run this and report back exactly what you can and cannot do.
This will help us identify exactly what we need to improve.
"""

import sys

print("\n" + "="*70)
print("OPENCODE INITIALIZATION PROGRESS TEST")
print("="*70)
print("\nInstructions: Run each test and report the results back.")
print("Tell me which tests PASS and which FAIL.\n")

results = {}

# TEST 1: Can you import agent_init?
print("[TEST 1] Can you import agent_init?")
print("  Running: from agent_init import initialize_and_load_context")
try:
    from agent_init import initialize_and_load_context, quick_initialize
    print("  Result: PASS - Successfully imported\n")
    results["import_agent_init"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["import_agent_init"] = f"FAIL: {e}"
    print("\nSTOPPED HERE - Cannot proceed without agent_init import")
    print("\nReport back: TEST 1 FAILED")
    sys.exit(1)

# TEST 2: Can you call initialize_and_load_context?
print("[TEST 2] Can you call initialize_and_load_context?")
print("  Running: result = initialize_and_load_context('opencode_test', 'code_analysis')")
try:
    result = initialize_and_load_context(
        agent_id="opencode_test",
        task_keyword="code_analysis",
        verbose=False
    )
    print(f"  Result: PASS - Initialization returned (status: {result.get('status')})\n")
    results["call_initialize"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["call_initialize"] = f"FAIL: {e}"
    print("\nSTOPPED HERE - Cannot proceed without successful initialization")
    print("\nReport back: TEST 2 FAILED")
    sys.exit(1)

# TEST 3: Can you access the API instance?
print("[TEST 3] Can you access the API instance?")
print("  Running: api = result['api']")
try:
    api = result.get("api")
    if api is None:
        print(f"  Result: FAIL - api is None\n")
        results["access_api"] = "FAIL: api is None"
        print("\nSTOPPED HERE - No API instance available")
        print("\nReport back: TEST 3 FAILED")
        sys.exit(1)
    print(f"  Result: PASS - API instance available\n")
    results["access_api"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["access_api"] = f"FAIL: {e}"
    sys.exit(1)

# TEST 4: Can you call API methods to get context?
print("[TEST 4] Can you call API methods to get context?")
print("  Running: api.get_startup_context(), api.get_startup_decisions(), api.get_startup_learnings()")
try:
    context = api.get_startup_context()
    decisions = api.get_startup_decisions()
    learnings = api.get_startup_learnings()
    print(f"  Result: PASS")
    print(f"    - Context accessible: {context is not None}")
    print(f"    - Decisions loaded: {len(decisions)}")
    print(f"    - Learnings loaded: {len(learnings)}\n")
    results["get_context"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["get_context"] = f"FAIL: {e}"
    print("\nSTOPPED HERE - Cannot get context from API")
    print("\nReport back: TEST 4 FAILED")
    sys.exit(1)

# TEST 5: Can you make a decision?
print("[TEST 5] Can you make a decision?")
print("  Running: api.decision('test_decision', outcome='yes', reason='testing')")
try:
    api.decision(
        "test_decision",
        outcome="yes",
        reason="Testing if can make decisions"
    )
    print(f"  Result: PASS - Decision recorded\n")
    results["make_decision"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["make_decision"] = f"FAIL: {e}"
    print("\nSTOPPED HERE - Cannot make decisions")
    print("\nReport back: TEST 5 FAILED - stopping here")
    sys.exit(1)

# TEST 6: Can you record a learning?
print("[TEST 6] Can you record a learning?")
print("  Running: api.learning(experiment_name='test', what_tried='x', ...)")
try:
    api.learning(
        experiment_name="test_learning",
        what_tried="Testing learning recording",
        expected_outcome="Should succeed",
        actual_outcome="It succeeded",
        category="testing",
        success="yes",
        recommendation="Learning system works"
    )
    print(f"  Result: PASS - Learning recorded\n")
    results["record_learning"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["record_learning"] = f"FAIL: {e}"
    print("\nSTOPPED HERE - Cannot record learnings")
    print("\nReport back: TEST 6 FAILED")
    sys.exit(1)

# TEST 7: Can you access session state?
print("[TEST 7] Can you access session state?")
print("  Running: state = result['state']")
try:
    state = result.get("state")
    if state is None:
        print(f"  Result: FAIL - state is None\n")
        results["access_state"] = "FAIL: state is None"
        print("\nSTOPPED HERE - No session state available")
        print("\nReport back: TEST 7 FAILED")
        sys.exit(1)

    # Try to use it
    has_checkpoint = state.has_checkpoint()
    print(f"  Result: PASS - Session state accessible (has_checkpoint: {has_checkpoint})\n")
    results["access_state"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["access_state"] = f"FAIL: {e}"
    print("\nSTOPPED HERE - Cannot access session state")
    print("\nReport back: TEST 7 FAILED")
    sys.exit(1)

# TEST 8: Can you save a checkpoint?
print("[TEST 8] Can you save a checkpoint?")
print("  Running: state.save_checkpoint(task='Test', progress=100, blockers=[])")
try:
    state.save_checkpoint(
        task="Initialization Test",
        progress=100,
        blockers=[]
    )
    print(f"  Result: PASS - Checkpoint saved\n")
    results["save_checkpoint"] = "PASS"
except Exception as e:
    print(f"  Result: FAIL - {e}\n")
    results["save_checkpoint"] = f"FAIL: {e}"
    print("\nSTOPPED HERE - Cannot save checkpoint")
    print("\nReport back: TEST 8 FAILED")
    sys.exit(1)

# ALL TESTS PASSED
print("="*70)
print("ALL TESTS PASSED!")
print("="*70 + "\n")

print("Summary of what you can do:")
for test_name, result in results.items():
    status_char = "[+]" if result == "PASS" else "[-]"
    print(f"  {status_char} {test_name}")

print("\n" + "="*70)
print("REPORT BACK WITH:")
print("="*70)
print("\nAll 8 tests PASSED!")
print("\nYou are fully initialized and can:")
print("  - Import agent_init")
print("  - Call initialize_and_load_context()")
print("  - Access API instance")
print("  - Make decisions")
print("  - Record learnings")
print("  - Access session state")
print("  - Save checkpoints")
print("\nYou are ready to work with full context!")
print()
