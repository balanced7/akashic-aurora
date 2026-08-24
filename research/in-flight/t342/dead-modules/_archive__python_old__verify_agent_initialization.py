#!/usr/bin/env python3
"""
Verification Test: Is the Agent Actually Initialized?

This tests whether an agent has ACTUALLY initialized (executed code)
vs just READ about initialization (read docs).

A truly initialized agent should be able to:
1. Import agent_init
2. Call initialize_and_load_context()
3. Access API instance
4. Make decisions
5. Record learnings
6. Manage checkpoints
"""

import sys

print("\n" + "="*70)
print("AGENT INITIALIZATION VERIFICATION TEST")
print("="*70 + "\n")

print("VERIFICATION CHECKLIST:")
print("-" * 70 + "\n")

# Test 1: Can we import agent_init?
print("[1] Testing agent_init import...")
try:
    from agent_init import initialize_and_load_context, quick_initialize
    print("    PASS: agent_init module imports successfully")
    test1 = True
except ImportError as e:
    print(f"    FAIL: Cannot import agent_init: {e}")
    test1 = False

# Test 2: Can we actually call initialize?
print("\n[2] Testing initialize_and_load_context() execution...")
try:
    result = initialize_and_load_context(
        "verification_test_agent",
        task_keyword="verification",
        verbose=False
    )
    if result["status"] != "failed":
        print(f"    PASS: Initialization executed (status: {result['status']})")
        test2 = True
    else:
        print(f"    FAIL: Initialization failed: {result['message']}")
        test2 = False
except Exception as e:
    print(f"    FAIL: Cannot execute initialization: {e}")
    test2 = False

# Test 3: Do we have an API instance?
print("\n[3] Testing API instance access...")
if test2 and result.get("api"):
    api = result["api"]
    print(f"    PASS: API instance available")
    test3 = True
else:
    print("    FAIL: No API instance in result")
    test3 = False

# Test 4: Can we call API methods?
print("\n[4] Testing API method calls...")
if test3:
    try:
        # Try calling a method
        startup_context = api.get_startup_context()
        print(f"    PASS: API.get_startup_context() works")

        # Try getting decisions
        decisions = api.get_startup_decisions()
        print(f"    PASS: API.get_startup_decisions() works (got {len(decisions)} decisions)")

        # Try getting learnings
        learnings = api.get_startup_learnings()
        print(f"    PASS: API.get_startup_learnings() works (got {len(learnings)} learnings)")

        test4 = True
    except AttributeError as e:
        print(f"    FAIL: API method doesn't exist: {e}")
        test4 = False
    except Exception as e:
        print(f"    FAIL: API method call failed: {e}")
        test4 = False
else:
    print("    SKIP: No API instance")
    test4 = False

# Test 5: Can we make a decision?
print("\n[5] Testing decision making...")
if test3:
    try:
        api.decision(
            "verify_initialization",
            outcome="yes",
            reason="Testing if actually initialized"
        )
        print("    PASS: api.decision() works")
        test5 = True
    except Exception as e:
        print(f"    FAIL: api.decision() failed: {e}")
        test5 = False
else:
    print("    SKIP: No API instance")
    test5 = False

# Test 6: Can we record a learning?
print("\n[6] Testing learning recording...")
if test3:
    try:
        api.learning(
            experiment_name="initialization_verification",
            what_tried="Verified agent initialization",
            expected_outcome="Agent should be initialized",
            actual_outcome="Agent successfully initialized",
            category="testing",
            success="yes",
            recommendation="Agent is properly initialized"
        )
        print("    PASS: api.learning() works")
        test6 = True
    except Exception as e:
        print(f"    FAIL: api.learning() failed: {e}")
        test6 = False
else:
    print("    SKIP: No API instance")
    test6 = False

# Test 7: Can we access session state?
print("\n[7] Testing session state access...")
if test2 and result.get("state"):
    state = result["state"]
    try:
        has_checkpoint = state.has_checkpoint()
        print(f"    PASS: Session state accessible (has_checkpoint: {has_checkpoint})")
        test7 = True
    except Exception as e:
        print(f"    FAIL: Cannot access session state: {e}")
        test7 = False
else:
    print("    FAIL: No state instance in result")
    test7 = False

# Test 8: Can we save a checkpoint?
print("\n[8] Testing checkpoint saving...")
if test7:
    try:
        state.save_checkpoint(
            task="Initialization Verification",
            progress=100,
            blockers=[]
        )
        print("    PASS: state.save_checkpoint() works")
        test8 = True
    except Exception as e:
        print(f"    FAIL: state.save_checkpoint() failed: {e}")
        test8 = False
else:
    print("    SKIP: No state instance")
    test8 = False

# Summary
print("\n" + "="*70)
print("VERIFICATION SUMMARY")
print("="*70 + "\n")

tests = {
    "agent_init imports": test1,
    "initialize_and_load_context() executes": test2,
    "API instance accessible": test3,
    "API methods callable": test4,
    "Can make decisions": test5,
    "Can record learnings": test6,
    "Session state accessible": test7,
    "Can save checkpoints": test8,
}

passed = sum(1 for v in tests.values() if v)
total = len(tests)

for test_name, result in tests.items():
    status = "[PASS]" if result else "[FAIL]"
    print(f"{status} {test_name}")

print(f"\nResult: {passed}/{total} tests passed\n")

# Final verdict
print("="*70)
if passed == total:
    print("VERDICT: [OK] AGENT IS FULLY INITIALIZED AND FUNCTIONAL")
    print("\nThe agent has:")
    print("  - Imported all modules")
    print("  - Called initialization code")
    print("  - Loaded startup context")
    print("  - Accessed API instance")
    print("  - Made decisions")
    print("  - Recorded learnings")
    print("  - Managed checkpoints")
    print("\nAgent is ready to work with full context!")
    sys.exit(0)

elif passed >= 6:
    print("VERDICT: [~] AGENT IS PARTIALLY INITIALIZED")
    print(f"\n{passed}/{total} tests passed. Some features may be unavailable.")
    sys.exit(1)

elif passed >= 4:
    print("VERDICT: [!] AGENT INITIALIZATION INCOMPLETE")
    print(f"\nOnly {passed}/{total} tests passed.")
    print("Agent may not have full context or functionality.")
    sys.exit(1)

else:
    print("VERDICT: [X] AGENT NOT INITIALIZED")
    print(f"\nOnly {passed}/{total} tests passed.")
    print("Agent read documentation but did not execute initialization code.")
    print("\nTo actually initialize, agent must run:")
    print("  from agent_init import initialize_and_load_context")
    print("  result = initialize_and_load_context('agent_id', 'task')")
    print("  api = result['api']")
    sys.exit(1)

print("="*70 + "\n")
