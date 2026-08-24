"""
Agent Comm Helper - Quick Functions for OpenCode
============================================
Simple functions OpenCode can call to check/send messages.

Usage in OpenCode:
    from agent_comm_helper import check_messages, send_quick, get_status
"""

import sys
import os
import json

sys.path.insert(0, r'E:\AI-Setup')

COORD_DIR = r"E:\AI-Setup\blackboard_data\agent_coordination"
INBOX_DIR = os.path.join(COORD_DIR, "inbox")


def get_my_id() -> str:
    """Get my agent ID"""
    identity_file = os.path.join(COORD_DIR, "state", "identity.json")
    
    if os.path.exists(identity_file):
        try:
            with open(identity_file, 'r') as f:
                data = json.load(f)
            return data.get("agent_id", "unknown")
        except:
            pass
    return "unknown"


def get_unread_count() -> int:
    """Get count of unread messages"""
    agent_id = get_my_id()
    unread_file = os.path.join(INBOX_DIR, agent_id, "unread.json")
    
    if not os.path.exists(unread_file):
        return 0
    
    try:
        with open(unread_file, 'r') as f:
            unread = json.load(f)
        return len(unread)
    except:
        return 0


def get_latest_message() -> dict:
    """Get the latest message"""
    agent_id = get_my_id()
    latest_file = os.path.join(INBOX_DIR, agent_id, "latest.json")
    
    if not os.path.exists(latest_file):
        return None
    
    try:
        with open(latest_file, 'r') as f:
            return json.load(f)
    except:
        return None


def get_messages(limit: int = 10) -> list:
    """Get recent messages"""
    agent_id = get_my_id()
    inbox_file = os.path.join(INBOX_DIR, agent_id, "inbox.json")
    
    if not os.path.exists(inbox_file):
        return []
    
    try:
        with open(inbox_file, 'r') as f:
            messages = json.load(f)
        return messages[-limit:]
    except:
        return []


def check_messages(limit: int = 5, mark_read: bool = True) -> dict:
    """
    Check for messages - main function OpenCode should call.
    
    Returns:
        dict with unread_count, has_new, messages
    """
    agent_id = get_my_id()
    
    # Get messages
    messages = get_messages(limit=limit)
    
    # Get unread count
    unread_count = get_unread_count()
    
    # Get latest
    latest = get_latest_message()
    
    # Mark all as read
    if mark_read and unread_count > 0:
        unread_file = os.path.join(INBOX_DIR, agent_id, "unread.json")
        try:
            with open(unread_file, 'w') as f:
                json.dump([], f)
        except:
            pass
    
    return {
        "unread_count": unread_count,
        "has_new": unread_count > 0,
        "latest": latest,
        "messages": messages
    }


def print_status():
    """Print human-readable status"""
    agent_id = get_my_id()
    unread = get_unread_count()
    latest = get_latest_message()
    
    print()
    print("=" * 50)
    print("AGENT COMMUNICATION STATUS")
    print("=" * 50)
    print(f"Agent ID: {agent_id}")
    print(f"Unread: {unread}")
    
    if latest:
        print(f"Latest: [{latest.get('msg_type', '?')}] {str(latest.get('content', ''))[:60]}")
    
    messages = get_messages(limit=3)
    if messages:
        print()
        print("Recent messages:")
        for m in messages[-3:]:
            print(f"  [{m.get('msg_type', '?')}] {str(m.get('content', ''))[:50]}")
    
    print("=" * 50)
    print()


def send_via_fast_comm(to_agent: str, msg_type: str, content: dict) -> bool:
    """
    Send a message via fast_agent_comm.
    """
    try:
        from fast_agent_comm import get_fast_comm
        
        comm = get_fast_comm()
        if not comm.is_available:
            return False
        
        comm.set_agent_id(get_my_id())
        
        if to_agent == "broadcast":
            msg_id = comm.send_broadcast(msg_type, content)
        else:
            msg_id = comm.send_direct(to_agent, msg_type, content)
        
        return msg_id is not None
    except Exception as e:
        print(f"Send failed: {e}")
        return False


# Quick test
if __name__ == "__main__":
    print_status()
