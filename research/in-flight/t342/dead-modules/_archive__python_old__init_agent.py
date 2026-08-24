#!/usr/bin/env python
"""Initialize agent and load context"""

from agent_init import initialize_and_load_context

result = initialize_and_load_context('claude-code-session', task_keyword='general', verbose=True)

print("\n" + "="*70)
print("AGENT INITIALIZATION STATUS")
print("="*70)
print(f"Status: {result['status']}")
print(f"Message: {result['message']}")

if result['status'] in ['success', 'partial']:
    api = result['api']
    print(f"\nContext Loaded:")
    print(f"  Decisions: {len(api.get_startup_decisions())}")
    print(f"  Learnings: {len(api.get_startup_learnings())}")
    print(f"  Briefing: {api.get_startup_briefing() is not None}")

    print("\n" + "="*70)
    print("READY TO WORK")
    print("="*70)
    print("\nYou can now:")
    print("  - api.decision(...) to log decisions")
    print("  - api.learning(...) to record learnings")
    print("  - api.signal(...) to emit signals")
