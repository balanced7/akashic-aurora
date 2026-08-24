"""
Coordinated Generator-Analyst Launcher
=====================================
Launches a paired generator and analyst that work together via the blackboard.

The GENERATOR creates proposals which the ANALYST reviews.
They communicate via:
- Blackboard (proposal.json + verdict.json)
- Multi-agent message bus (vector-based)
- Shared workspace for coordination

USAGE:
    # Launch paired instances
    python E:\AI-Setup\launch_paired_agents.py

    # Launch with auto-confirm
    python E:\AI-Setup\launch_paired_agents.py --auto-start

    # Check status
    python E:\AI-Setup\launch_paired_agents.py --status
"""

import argparse
import os
import sys
import subprocess
import time
import json
from datetime import datetime

sys.path.insert(0, r'E:\AI-Setup')

def get_opencode_path():
    """Find opencode executable"""
    paths = [
        r"C:\Users\L5\AppData\Local\Programs\OpenCode\opencode.exe",
        r"C:\Program Files\OpenCode\opencode.exe",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return "opencode"


def check_redis():
    """Check if Redis is available"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        return True
    except:
        return False


def get_active_agents():
    """Get list of active agents from Redis"""
    if not check_redis():
        return []
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        agents = []
        agent_data = r.hgetall("agents:active")
        heartbeat_data = r.zrange("agents:heartbeat", 0, -1, withscores=True)
        
        cutoff = time.time() - 300
        
        active_ids = set()
        for agent_id, score in heartbeat_data:
            if score > cutoff:
                active_ids.add(agent_id)
        
        for agent_id, data in agent_data.items():
            if agent_id in active_ids:
                try:
                    info = json.loads(data)
                    agents.append(info)
                except:
                    pass
        
        return agents
    except:
        return []


def wait_for_redis(timeout=30):
    """Wait for Redis to become available"""
    print(f"Waiting for Redis (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        if check_redis():
            print("Redis connected")
            return True
        time.sleep(1)
    return False


def get_blackboard_status():
    """Get current blackboard status"""
    if not check_redis():
        return None
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        state = r.hget("blackboard:state", "state")
        turn = r.hget("blackboard:state", "turn")
        proposal_ready = r.get("blackboard:proposal_ready")
        verdict_ready = r.get("blackboard:verdict_ready")
        
        return {
            "state": state.decode() if state else "IDLE",
            "turn": int(turn.decode()) if turn else 0,
            "proposal_ready": proposal_ready == b"1" if proposal_ready else False,
            "verdict_ready": verdict_ready == b"1" if verdict_ready else False
        }
    except:
        return None


def initialize_paired_session(role):
    """Initialize session for a specific role"""
    from session_manager import check_and_reprime
    from session_logger import SESSION_ID, SESSION_UNIQUE
    from multi_agent import initialize_multi_agent
    
    state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)
    ma_result = initialize_multi_agent(
        session_id=SESSION_ID,
        session_unique=SESSION_UNIQUE,
        role=role
    )
    
    return state, ma_result


def launch_role_instance(role, wait=False):
    """Launch a single role instance"""
    opencode_path = get_opencode_path()
    
    env = os.environ.copy()
    env['OPENCODE_AGENT_ROLE'] = role
    env['OPENCODE_PAIRED_MODE'] = '1'
    
    try:
        if os.path.exists(opencode_path):
            process = subprocess.Popen(
                [opencode_path],
                env=env,
                cwd=os.path.dirname(opencode_path),
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
        else:
            process = subprocess.Popen(
                ["opencode"],
                env=env,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
        return process.pid
    except Exception as e:
        print(f"Launch failed for {role}: {e}")
        return None


def print_status(generator_pid, analyst_pid):
    """Print current status"""
    print("\n" + "=" * 70)
    print("COORDINATED AGENTS STATUS")
    print("=" * 70)
    
    print(f"\nPROCESSES:")
    print(f"  Generator: {'Running' if generator_pid else 'Not started'} (PID: {generator_pid or 'N/A'})")
    print(f"  Analyst:   {'Running' if analyst_pid else 'Not started'} (PID: {analyst_pid or 'N/A'})")
    
    if check_redis():
        print(f"\nREDIS: Connected")
        
        agents = get_active_agents()
        generators = [a for a in agents if a.get('role') == 'generator']
        analysts = [a for a in agents if a.get('role') == 'analyst']
        
        print(f"REGISTERED AGENTS:")
        print(f"  Generators: {len(generators)}")
        for g in generators:
            print(f"    - {g.get('agent_id')} (session: {g.get('session_id')})")
        print(f"  Analysts: {len(analysts)}")
        for a in analysts:
            print(f"    - {a.get('agent_id')} (session: {a.get('session_id')})")
        
        bb = get_blackboard_status()
        if bb:
            print(f"\nBLACKBOARD:")
            print(f"  State: {bb.get('state', 'UNKNOWN')}")
            print(f"  Turn: {bb.get('turn', 0)}")
            print(f"  Proposal Ready: {bb.get('proposal_ready')}")
            print(f"  Verdict Ready: {bb.get('verdict_ready')}")
    else:
        print(f"\nREDIS: Not connected")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Coordinated Generator-Analyst Launcher")
    parser.add_argument('--auto-start', action='store_true',
                       help='Start without confirmation prompt')
    parser.add_argument('--status', action='store_true',
                       help='Show status only')
    parser.add_argument('--generator-only', action='store_true',
                       help='Launch generator only')
    parser.add_argument('--analyst-only', action='store_true',
                       help='Launch analyst only')
    
    args = parser.parse_args()
    
    print("BreakThrough Stack - Coordinated Agent Launcher")
    print("=" * 60)
    
    if not wait_for_redis():
        print("ERROR: Redis not available. Start Redis first:")
        print("  docker start wsl-ai-redis")
        return
    
    agents = get_active_agents()
    generators = [a for a in agents if a.get('role') == 'generator']
    analysts = [a for a in agents if a.get('role') == 'analyst']
    
    print(f"\nCurrent agents: {len(agents)}")
    print(f"  Generators: {len(generators)}")
    print(f"  Analysts: {len(analysts)}")
    
    if args.status:
        print_status(None, None)
        return
    
    if len(generators) > 0:
        print("\nWARNING: Generator already running!")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return
    
    if len(analysts) > 0:
        print("\nWARNING: Analyst already running!")
        response = input("Continue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return
    
    print("\n" + "-" * 60)
    print("Will launch:")
    if not args.analyst_only:
        print("  - GENERATOR: Creates proposals and writes code")
    if not args.generator_only:
        print("  - ANALYST: Reviews proposals and provides verdicts")
    print("-" * 60)
    
    if not args.auto_start:
        response = input("\nPress ENTER to start, 'q' to quit: ").strip().lower()
        if response == 'q':
            return
    
    generator_pid = None
    analyst_pid = None
    
    if not args.analyst_only:
        print("\n[1] Launching Generator...")
        state, ma_result = initialize_paired_session('generator')
        if ma_result.get('initialized'):
            print(f"    Registered as: {ma_result['agent_id']}")
        time.sleep(0.5)
        generator_pid = launch_role_instance('generator')
        if generator_pid:
            print(f"    Launched with PID: {generator_pid}")
        else:
            print("    FAILED to launch")
    
    if not args.generator_only:
        print("\n[2] Launching Analyst...")
        state, ma_result = initialize_paired_session('analyst')
        if ma_result.get('initialized'):
            print(f"    Registered as: {ma_result['agent_id']}")
        time.sleep(0.5)
        analyst_pid = launch_role_instance('analyst')
        if analyst_pid:
            print(f"    Launched with PID: {analyst_pid}")
        else:
            print("    FAILED to launch")
    
    print_status(generator_pid, analyst_pid)
    
    print("\nCoordinated agents launched!")
    print("They will communicate via:")
    print("  - Blackboard for proposals and verdicts")
    print("  - Multi-agent message bus for coordination")
    print("\nUse --status to monitor progress")


if __name__ == "__main__":
    main()
