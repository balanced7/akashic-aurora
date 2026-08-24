#!/usr/bin/env python
"""Quick Phase 1 validation without Redis initialization"""

import sys
sys.path.insert(0, 'E:\\AI-Setup')

print("PHASE 1 VALIDATION - SIMPLE TEST")
print("=" * 60)
print()

# Test 1: Import modules
print("Test 1: Importing modules...")
try:
    from learning_store import LearningStore
    from coordinator_api import initialize, learning, SignalType
    print("SUCCESS - All modules imported")
except Exception as e:
    print(f"FAILED - {e}")
    sys.exit(1)
print()

# Test 2: Check SignalType.LEARNING exists
print("Test 2: Checking SignalType.LEARNING...")
try:
    if hasattr(SignalType, 'LEARNING'):
        print(f"SUCCESS - SignalType.LEARNING = '{SignalType.LEARNING.value}'")
    else:
        print("FAILED - SignalType.LEARNING not found")
        sys.exit(1)
except Exception as e:
    print(f"FAILED - {e}")
    sys.exit(1)
print()

# Test 3: Check learning() method exists
print("Test 3: Checking learning() method...")
try:
    import inspect
    api = initialize("test_agent")
    if hasattr(api, 'learning') and callable(getattr(api, 'learning')):
        sig = inspect.signature(api.learning)
        params = list(sig.parameters.keys())
        print(f"SUCCESS - learning() method with {len(params)} parameters")
    else:
        print("FAILED - learning() method not found")
        sys.exit(1)
except Exception as e:
    print(f"FAILED - {e}")
    sys.exit(1)
print()

# Test 4: Check LearningStore has all methods
print("Test 4: Checking LearningStore methods...")
try:
    required_methods = [
        'record_learning', 'get_learnings', 'get_patterns',
        'get_anti_patterns', 'get_recommendations', 'search_learnings',
        'get_category_summary', 'get_agent_learnings', 'get_stats'
    ]

    # Don't initialize with Redis - just check the class
    for method in required_methods:
        if not hasattr(LearningStore, method):
            print(f"FAILED - Missing method: {method}")
            sys.exit(1)

    print(f"SUCCESS - All {len(required_methods)} required methods present")
except Exception as e:
    print(f"FAILED - {e}")
    sys.exit(1)
print()

print("=" * 60)
print("PHASE 1 VALIDATION: PASSED")
print("=" * 60)
print()
print("What this test verified:")
print("  ✓ Code syntax is valid")
print("  ✓ All modules import correctly")
print("  ✓ SignalType.LEARNING is defined")
print("  ✓ learning() method exists on CoordinatorAPI")
print("  ✓ LearningStore has all required methods")
print()
print("What's not available:")
print("  - Redis persistence (Docker/WSL not available)")
print("  - Cross-agent learning (needs persistence)")
print()
print("NEXT: Phase 1.5 - Real-world test using file-based logging")
