"""
Multi-Instance Launcher for BreakThrough Stack
=============================================
Launches multiple OpenCode instances with different roles for concurrent operation.

ROLES:
- generator: Creates proposals, writes code
- analyst: Reviews and critiques proposals
- master: Orchestrates workflow
- orchestrator: Coordinates multiple agents
- general: Default role for standalone use

USAGE:
    # Launch a generator agent
    python E:\AI-Setup\multi_instance_launcher.py --role generator

    # Launch an analyst agent
    python E:\AI-Setup\multi_instance_launcher.py --role analyst

    # Launch with custom session
    python E:\AI-Setup\multi_instance_launcher.py --role generator --session my_session

    # List active agents
    python E:\AI-Setup\multi_instance_launcher.py --list-agents

    # Check Redis status
    python E:\AI-Setup\multi_instance_launcher.py --status
"""

import argparse
import os
import sys
import subprocess
import time
import json
from datetime import datetime

sys.path.insert(0, r'E:\AI-Setup')

AGENT_ROLES = ["generator", "analyst", "master", "orchestrator", "general"]

def get_opencode_path():
    """Find opencode executable"""
    paths = [
        r"C:\Users\L5\AppData\Local\Programs\OpenCode\opencode.exe",
        r"C:\Program Files\OpenCode\opencode.exe",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return "opencode"  # Try PATH


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
        
        cutoff = time.time() - 300  # 5 minutes TTL
        
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
    print("WARNING: Redis not available")
    return False


def run_initialization(role):
    """Run the initialization sequence for this agent"""
    print("=" * 60)
    print(f"BreakThrough Stack - Agent Initialization ({role})")
    print("=" * 60)
    print()
    
    os.environ['OPENCODE_AGENT_ROLE'] = role
    
    results = []
    
    if not wait_for_redis():
        results.append(("redis", "WARN", "not available"))
    else:
        results.append(("redis", "OK", "connected"))
    
    try:
        from session_manager import check_and_reprime, get_session_manager
        from session_logger import SESSION_ID, SESSION_UNIQUE
        
        state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)
        
        if state.is_new:
            print(f"NEW SESSION: {SESSION_ID}")
            print("RE-PRIME REQUIRED")
            results.append(("session", "NEW", SESSION_ID))
        else:
            print(f"CONTINUING: {SESSION_ID}")
            results.append(("session", "OK", SESSION_ID))
        
        from multi_agent import initialize_multi_agent
        
        ma_result = initialize_multi_agent(
            session_id=SESSION_ID,
            session_unique=SESSION_UNIQUE,
            role=role
        )
        
        if ma_result['initialized']:
            print(f"AGENT REGISTERED: {ma_result['agent_id']} (role={role})")
            results.append(("multi_agent", "OK", ma_result['agent_id']))
            
            if ma_result['active_agents']:
                print(f"OTHER AGENTS: {len(ma_result['active_agents'])}")
                for agent in ma_result['active_agents']:
                    print(f"  - {agent['agent_id']} ({agent['role']}) in {agent['session_id']}")
        else:
            print(f"MULTI-AGENT: {ma_result.get('warnings', ['init failed'])[0]}")
            results.append(("multi_agent", "WARN", ma_result.get('warnings', ['unknown'])[0]))
        
    except Exception as e:
        print(f"INIT ERROR: {e}")
        results.append(("init", "ERROR", str(e)))
    
    print()
    print("-" * 60)
    print("INITIALIZATION COMPLETE")
    print("-" * 60)
    for name, status, info in results:
        print(f"  {name}: [{status}] {info}")
    print()
    
    return results


def launch_opencode_instance(role, session=None, wait=False):
    """Launch an OpenCode instance with the specified role"""
    opencode_path = get_opencode_path()
    
    env = os.environ.copy()
    env['OPENCODE_AGENT_ROLE'] = role
    if session:
        env['OPENCODE_SESSION_ID'] = session
    
    print(f"Launching OpenCode as {role}...")
    print(f"  Path: {opencode_path}")
    print(f"  Role: {role}")
    if session:
        print(f"  Session: {session}")
    
    try:
        if os.path.exists(opencode_path):
            process = subprocess.Popen(
                [opencode_path],
                env=env,
                cwd=os.path.dirname(opencode_path)
            )
        else:
            process = subprocess.Popen(
                ["opencode"],
                env=env
            )
        
        print(f"Launched with PID: {process.pid}")
        
        if wait:
            process.wait()
        
        return process.pid
    except Exception as e:
        print(f"Launch failed: {e}")
        return None


def print_agents_table(agents):
    """Print agents in a formatted table"""
    if not agents:
        print("No active agents")
        return
    
    print("\nACTIVE AGENTS")
    print("-" * 80)
    print(f"{'Agent ID':<30} {'Role':<12} {'Session':<25} {'Status'}")
    print("-" * 80)
    
    for agent in agents:
        print(f"{agent.get('agent_id', 'unknown'):<30} "
              f"{agent.get('role', 'unknown'):<12} "
              f"{agent.get('session_id', 'unknown'):<25} "
              f"{agent.get('status', 'unknown')}")
    
    print("-" * 80)
    print(f"Total: {len(agents)} agent(s)")


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Instance Launcher for BreakThrough Stack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
    # Launch a generator agent
    python multi_instance_launcher.py --role generator

    # Launch an analyst agent
    python multi_instance_launcher.py --role analyst

    # Launch and wait for exit
    python multi_instance_launcher.py --role generator --wait

    # List all active agents
    python multi_instance_launcher.py --list-agents

    # Check system status
    python multi_instance_launcher.py --status

ROLES:
    generator  - Creates proposals and writes code
    analyst    - Reviews and critiques proposals  
    master     - Orchestrates workflow
    orchestrator - Coordinates multiple agents
    general    - Default role for standalone use
        """
    )
    
    parser.add_argument('--role', '-r', choices=AGENT_ROLES, default='general',
                       help='Agent role (default: general)')
    parser.add_argument('--session', '-s', 
                       help='Custom session ID')
    parser.add_argument('--wait', '-w', action='store_true',
                       help='Wait for OpenCode to exit')
    parser.add_argument('--list-agents', '-l', action='store_true',
                       help='List active agents')
    parser.add_argument('--status', action='store_true',
                       help='Show system status')
    parser.add_argument('--init-only', action='store_true',
                       help='Run initialization only (do not launch OpenCode)')
    
    args = parser.parse_args()
    
    if args.list_agents:
        agents = get_active_agents()
        print_agents_table(agents)
        return
    
    if args.status:
        print("BreakThrough Stack - System Status")
        print("=" * 60)
        
        redis_ok = check_redis()
        print(f"Redis: {'OK' if redis_ok else 'NOT AVAILABLE'}")
        
        if redis_ok:
            agents = get_active_agents()
            print(f"Active Agents: {len(agents)}")
            print_agents_table(agents)
        return
    
    if args.init_only:
        run_initialization(args.role)
        return
    
    run_initialization(args.role)
    
    print("\nReady to launch OpenCode...")
    response = input("Press ENTER to launch, or 'q' to quit: ").strip().lower()
    
    if response == 'q':
        print("Cancelled")
        return
    
    pid = launch_opencode_instance(args.role, args.session, args.wait)
    
    if pid:
        print(f"\nAgent launched successfully (PID: {pid})")
        print("Use --list-agents to check status")


if __name__ == "__main__":
    main()
