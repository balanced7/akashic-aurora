"""
BreakThrough Stack - Unified Launcher
====================================
Main entry point for the AI startup system.

Presents a menu to choose between:
1. Single Primed Agent - One OpenCode instance with full initialization
2. Generator + Analyst - Paired instances that collaborate
3. Custom Role Launch - Launch with specific role
4. Spawn Helper - Request a helper agent to assist

USAGE:
    python E:\AI-Setup\launch.py
    python E:\AI-Setup\launch.py --auto 1  # Auto-select option 1
"""

import argparse
import os
import sys
import subprocess
import time
import json
from datetime import datetime

sys.path.insert(0, r'E:\AI-Setup')

REDIS_CHECK_TIMEOUT = 30

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


def wait_for_redis(timeout=REDIS_CHECK_TIMEOUT):
    """Wait for Redis to become available"""
    print(f"Waiting for Redis (timeout={timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        if check_redis():
            print("Redis connected")
            return True
        time.sleep(1)
    print("WARNING: Redis not available - running in single-agent mode")
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


def print_active_agents():
    """Print currently active agents"""
    agents = get_active_agents()
    if not agents:
        print("  No other active agents")
        return
    
    print(f"  {len(agents)} active agent(s):")
    for agent in agents:
        role = agent.get('role', 'unknown')
        session = agent.get('session_id', 'unknown')
        agent_id = agent.get('agent_id', 'unknown')[:20]
        print(f"    - [{role}] {agent_id}... (session: {session})")


def run_initialization(role='general'):
    """Run initialization sequence"""
    os.environ['OPENCODE_AGENT_ROLE'] = role
    
    from session_manager import check_and_reprime, get_session_manager
    from session_logger import SESSION_ID, SESSION_UNIQUE
    from multi_agent import initialize_multi_agent
    
    state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)
    
    result = {
        'session_id': SESSION_ID,
        'is_new': state.is_new if state else True,
        'multi_agent': None,
        'redis_available': check_redis()
    }
    
    if check_redis():
        ma_result = initialize_multi_agent(
            session_id=SESSION_ID,
            session_unique=SESSION_UNIQUE,
            role=role
        )
        result['multi_agent'] = ma_result
    
    return result


def launch_opencode(role='general', paired_mode=False):
    """Launch OpenCode with specified role"""
    opencode_path = get_opencode_path()
    
    env = os.environ.copy()
    env['OPENCODE_AGENT_ROLE'] = role
    if paired_mode:
        env['OPENCODE_PAIRED_MODE'] = '1'
    
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
        return process.pid
    except Exception as e:
        print(f"Launch failed: {e}")
        return None


def option_single_agent():
    """Launch single primed agent"""
    print("\n" + "=" * 60)
    print("SINGLE PRIMED AGENT MODE")
    print("=" * 60)
    
    print("\nRunning initialization...")
    result = run_initialization('general')
    
    print(f"\nSession: {result['session_id']}")
    print(f"Redis: {'Available' if result['redis_available'] else 'Not available'}")
    
    if result.get('multi_agent'):
        ma = result['multi_agent']
        if ma.get('initialized'):
            print(f"Agent registered: {ma['agent_id']}")
            print(f"Role: {ma['role']}")
            active = ma.get('active_agents', [])
            if active:
                print(f"Other agents: {len(active)}")
        else:
            print(f"Multi-agent: {ma.get('warnings', ['failed'])[0]}")
    
    print("\nLaunching OpenCode...")
    pid = launch_opencode('general')
    
    if pid:
        print(f"\nOpenCode launched (PID: {pid})")
    else:
        print("\nFailed to launch OpenCode")
    
    return pid


def option_generator_analyst():
    """Launch generator + analyst paired instances"""
    print("\n" + "=" * 60)
    print("GENERATOR + ANALYST MODE")
    print("=" * 60)
    
    if not wait_for_redis():
        print("\nERROR: Redis required for paired mode")
        return None, None
    
    print("\nRunning initialization for Generator...")
    gen_result = run_initialization('generator')
    
    print("\nRunning initialization for Analyst...")
    analyst_result = run_initialization('analyst')
    
    print("\n" + "-" * 60)
    print("CURRENT AGENTS:")
    print_active_agents()
    print("-" * 60)
    
    gen_pid = None
    analyst_pid = None
    
    print("\nLaunching Generator...")
    time.sleep(0.3)
    gen_pid = launch_opencode('generator', paired_mode=True)
    if gen_pid:
        print(f"  Generator launched (PID: {gen_pid})")
    
    print("\nLaunching Analyst...")
    time.sleep(0.3)
    analyst_pid = launch_opencode('analyst', paired_mode=True)
    if analyst_pid:
        print(f"  Analyst launched (PID: {analyst_pid})")
    
    print("\n" + "=" * 60)
    print("COORDINATION INFO")
    print("=" * 60)
    print("""
Communication flow:
  1. Generator creates proposal -> writes to blackboard
  2. Generator sets proposal_ready flag -> Analyst detects
  3. Analyst reviews -> writes verdict
  4. Analyst sets verdict_ready flag -> Generator detects
  5. Generator continues or revises

Use --status to monitor progress.
""")
    
    return gen_pid, analyst_pid


def option_custom_role():
    """Launch with custom role"""
    print("\n" + "=" * 60)
    print("CUSTOM ROLE LAUNCH")
    print("=" * 60)
    
    roles = ["generator", "analyst", "master", "orchestrator", "general"]
    
    print("\nAvailable roles:")
    for i, r in enumerate(roles, 1):
        print(f"  {i}. {r}")
    
    try:
        choice = input("\nSelect role (1-5) or enter role name: ").strip().lower()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(roles):
                role = roles[idx]
            else:
                print("Invalid selection")
                return None
        else:
            role = choice if choice in roles else 'general'
        
        print(f"\nRunning initialization for {role}...")
        result = run_initialization(role)
        
        print(f"\nSession: {result['session_id']}")
        print(f"Redis: {'Available' if result['redis_available'] else 'Not available'}")
        
        print("\nLaunching OpenCode...")
        pid = launch_opencode(role)
        
        if pid:
            print(f"\nOpenCode launched as {role} (PID: {pid})")
        
        return pid
    except KeyboardInterrupt:
        print("\nCancelled")
        return None


def option_spawn_helper():
    """Spawn a helper agent to assist"""
    print("\n" + "=" * 60)
    print("SPAWN HELPER AGENT")
    print("=" * 60)
    
    if not wait_for_redis():
        print("\nERROR: Redis required for spawning helpers")
        return None
    
    print("\nAvailable helper types:")
    print("  1. generator - Helps write code and proposals")
    print("  2. analyst - Helps review and critique")
    print("  3. researcher - Helps search and gather information")
    print("  4. tester - Helps run tests and verify")
    
    try:
        choice = input("\nSelect helper type (1-4): ").strip()
        
        helper_map = {
            '1': 'generator',
            '2': 'analyst', 
            '3': 'researcher',
            '4': 'tester'
        }
        
        helper_role = helper_map.get(choice, 'generator')
        
        print(f"\nInitializing {helper_role} helper...")
        result = run_initialization(helper_role)
        
        if result.get('multi_agent') and result['multi_agent'].get('initialized'):
            agent_id = result['multi_agent']['agent_id']
            print(f"Helper registered: {agent_id}")
            
            # Send broadcast to existing agents
            from multi_agent import get_message_bus
            bus = get_message_bus()
            bus.broadcast_to_agents(
                'alert',
                f'Helper agent spawned: {helper_role}',
                {'agent_id': agent_id, 'role': helper_role}
            )
        else:
            print("Warning: Helper registered but multi-agent may be limited")
        
        print(f"\nLaunching {helper_role} helper...")
        pid = launch_opencode(helper_role)
        
        if pid:
            print(f"\nHelper launched (PID: {pid})")
            print("It will receive context from the shared workspace")
        
        return pid
    except KeyboardInterrupt:
        print("\nCancelled")
        return None


def option_status():
    """Show system status"""
    print("\n" + "=" * 60)
    print("SYSTEM STATUS")
    print("=" * 60)
    
    redis_ok = check_redis()
    print(f"\nRedis: {'OK' if redis_ok else 'NOT AVAILABLE'}")
    
    if redis_ok:
        print(f"\nActive Agents:")
        print_active_agents()
        
        # Check blackboard state
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            state = r.hget("blackboard:state", "state")
            turn = r.hget("blackboard:state", "turn")
            proposal_ready = r.get("blackboard:proposal_ready")
            verdict_ready = r.get("blackboard:verdict_ready")
            
            print(f"\nBlackboard:")
            print(f"  State: {state.decode() if state else 'IDLE'}")
            print(f"  Turn: {turn.decode() if turn else '0'}")
            print(f"  Proposal Ready: {proposal_ready == b'1' if proposal_ready else False}")
            print(f"  Verdict Ready: {verdict_ready == b'1' if verdict_ready else False}")
        except:
            pass
        
        # Check message queues
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            
            broadcast_len = r.llen("msg:broadcast")
            print(f"\nMessage Bus:")
            print(f"  Broadcast messages: {broadcast_len}")
        except:
            pass
    else:
        print("\nStart Redis with: docker start wsl-ai-redis")
    
    print()


def show_menu():
    """Display main menu"""
    print("\n" + "=" * 70)
    print("  BREAKTHROUGH STACK - AI Startup System")
    print("=" * 70)
    print()
    print("Select startup mode:")
    print()
    print("  [1] Single Primed Agent")
    print("      One OpenCode instance with full initialization")
    print("      Best for: Focused single-task work")
    print()
    print("  [2] Generator + Analyst")
    print("      Paired instances that collaborate via blackboard")
    print("      Best for: Proposal writing, code review, iterative development")
    print()
    print("  [3] Custom Role Launch")
    print("      Launch with specific role (generator/analyst/master/etc)")
    print()
    print("  [4] Spawn Helper Agent")
    print("      Add another agent to help with current work")
    print()
    print("  [5] System Status")
    print("      Check active agents, blackboard state, message queues")
    print()
    print("  [q] Quit")
    print()
    print("-" * 70)


def main():
    parser = argparse.ArgumentParser(description="BreakThrough Stack Launcher")
    parser.add_argument('--auto', '-a', type=int, choices=[1, 2, 3, 4, 5],
                       help='Auto-select option (1-5)')
    parser.add_argument('--status', '-s', action='store_true',
                       help='Show status and exit')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List active agents and exit')
    
    args = parser.parse_args()
    
    if args.status:
        option_status()
        return
    
    if args.list:
        print_active_agents()
        return
    
    if args.auto:
        # Auto mode - run selected option without prompt
        if args.auto == 1:
            option_single_agent()
        elif args.auto == 2:
            option_generator_analyst()
        elif args.auto == 3:
            option_custom_role()
        elif args.auto == 4:
            option_spawn_helper()
        elif args.auto == 5:
            option_status()
        return
    
    # Interactive mode
    while True:
        show_menu()
        
        try:
            choice = input("Enter selection (1-5, q): ").strip().lower()
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        
        if choice == 'q':
            print("\nGoodbye!")
            break
        
        if choice == '1':
            option_single_agent()
        elif choice == '2':
            option_generator_analyst()
        elif choice == '3':
            option_custom_role()
        elif choice == '4':
            option_spawn_helper()
        elif choice == '5':
            option_status()
        else:
            print("\nInvalid selection. Use 1-5 or q to quit.")
        
        input("\nPress ENTER to return to menu...")


if __name__ == "__main__":
    main()
