"""
Init Session - Full Session Initialization
==========================================
Run this at the START of every session for proper bootstrapping.

Usage:
    python E:\AI-Setup\init_session.py
"""

import sys
sys.path.insert(0, r'E:\AI-Setup')

def initialize():
    """Full initialization sequence with session change detection"""
    print("=" * 60)
    print("BreakThrough Stack - Session Initialization")
    print("=" * 60)
    print()
    
    results = []
    
    # 1. Session detection and re-prime check
    print("[1/6] Checking session state...")
    try:
        from session_manager import check_and_reprime, get_session_manager
        from session_logger import SESSION_ID, SESSION_UNIQUE
        state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)
        
        if state.is_new:
            print(f"  NEW SESSION: {SESSION_ID}")
            print("  RE-PRIME REQUIRED - See instructions below")
            results.append(("session", "NEW", state.session_id))
        else:
            print(f"  CONTINUING: {SESSION_ID}")
            results.append(("session", "OK", state.session_id))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("session", "ERROR", str(e)))
        state = None
    
    # 2. Start Redis
    print("\n[2/6] Starting Redis...")
    try:
        import subprocess
        result = subprocess.run(['docker', 'start', 'ai-redis'], 
                             capture_output=True, timeout=30)
        if result.returncode == 0:
            print("  Redis started")
            results.append(("redis", "OK", "started"))
        else:
            print(f"  WARNING: {result.stderr.decode() if result.stderr else 'unknown'}")
            results.append(("redis", "WARN", "may not be running"))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("redis", "ERROR", str(e)))
    
    # 3. Initialize blackboard
    print("\n[3/6] Initializing blackboard...")
    try:
        from blackboard import init_blackboard
        bb = init_blackboard(force=False)
        print(f"  Blackboard state: {bb.get_state()}")
        results.append(("blackboard", "OK", bb.get_state()))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("blackboard", "ERROR", str(e)))
        bb = None
    
    # 4. Activate logging and verify
    print("\n[4/6] Verifying logging...")
    try:
        from session_logger import log, verify_logs
        log("init_session", "Full initialization run", source="system")
        
        verify_result = verify_logs(100)
        if verify_result['corrupted'] > 0:
            print(f"  WARNING: {verify_result['corrupted']} corrupted entries")
            results.append(("logging", "WARN", f"Corrupted={verify_result['corrupted']}"))
        else:
            print(f"  Logging OK: {verify_result['valid']} valid entries")
            results.append(("logging", "OK", f"{verify_result['valid']} valid"))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("logging", "ERROR", str(e)))
    
    # 5. Catch-up from previous session
    print("\n[5/6] Getting session catch-up...")
    try:
        from crash_recovery import get_summary
        summary = get_summary()
        
        session_count = len(summary.get('sessions', []))
        chat_count = len(summary.get('chat_history', []))
        
        print(f"  Previous sessions: {session_count}")
        print(f"  Chat history: {chat_count} messages")
        
        if summary.get('last_error'):
            print(f"  LAST ERROR: {summary['last_error'].get('error_type', 'unknown')}")
        
        results.append(("catchup", "OK", f"{session_count} sessions, {chat_count} chats"))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("catchup", "ERROR", str(e)))
    
    # 6. Service health check
    print("\n[6/6] Checking service health...")
    try:
        from master import check_prerequisites
        checks = check_prerequisites()
        for name, status in checks:
            print(f"  {name}: {status}")
        results.append(("health", "OK", f"{len(checks)} checks"))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("health", "ERROR", str(e)))
    
    # 7. Initialize harness enforcement
    print("\n[7/7] Initializing harness enforcement...")
    try:
        from harness_enforcer import get_harness_enforcer, install_harness_hooks
        
        he = get_harness_enforcer()
        install_harness_hooks()
        
        report = he.get_compliance_report()
        print(f"  Harness active - Escape Risk: {report['escape_risk']}")
        results.append(("harness", "OK", report['escape_risk']))
    except Exception as e:
        print(f"  WARNING: Could not initialize harness: {e}")
        results.append(("harness", "WARN", str(e)))
    
    # 8. Run directives compliance check
    print("\n[8/8] Checking directives compliance...")
    try:
        from directives_checker import check_compliance, print_directives_report
        
        compliance = check_compliance()
        if compliance['compliant']:
            print("  All directives: COMPLIANT")
            results.append(("directives", "OK", "compliant"))
        else:
            print(f"  VIOLATIONS: {len(compliance['violations'])} found")
            for v in compliance['violations'][:3]:  # Show first 3
                print(f"    - [{v['severity']}] {v['directive']}: {v['description']}")
            results.append(("directives", "VIOLATION", f"{len(compliance['violations'])} issues"))
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("directives", "ERROR", str(e)))
    
    # Print summary
    print("\n" + "=" * 60)
    print("INITIALIZATION SUMMARY")
    print("=" * 60)
    for name, status, info in results:
        status_symbol = "✓" if status in ["OK", "NEW"] else "!"
        print(f"  {status_symbol} {name}: [{status}] {info}")
    
    # Re-prime instructions if needed
    if state and state.is_new:
        print("\n" + "=" * 60)
        print("RE-PRIME REQUIRED")
        print("=" * 60)
        try:
            from session_manager import get_session_manager
            print(get_session_manager().get_reprime_instructions())
        except:
            print("""
Run these commands before proceeding:
1. from blackboard import init_blackboard
   bb = init_blackboard(force=True)

2. from crash_recovery import get_summary
   get_summary()

3. from session_logger import verify_logs
   verify_logs(100)
""")
    
    print("\nInitialization complete.")
    return state


if __name__ == "__main__":
    initialize()
