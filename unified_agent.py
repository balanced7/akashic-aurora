"""
Unified Agent Communication Layer
=================================
Combines Redis-based (multi_agent) and FileSystem-based (agent_coordinator) 
communication into a single unified interface.

When Redis is available:
- Uses multi_agent for high-performance messaging
- Syncs with agent_coordinator for file-based backup

When Redis is unavailable:
- Falls back to agent_coordinator file-system approach

This ensures reliable communication regardless of Redis availability.

Author: Senior Systems Architect
Version: 1.0 Unified
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

sys.path.insert(0, r'E:\AI-Setup')

# ============================================================================
# CONFIGURATION
# ============================================================================

COORD_DIR = r"E:\AI-Setup\blackboard_data\agent_coordination"
UNIFIED_STATE_FILE = os.path.join(COORD_DIR, "unified_state.json")


@dataclass
class UnifiedMessage:
    """A message that works with both backends"""
    msg_id: str
    from_agent: str
    to_agent: str
    msg_type: str
    content: Any
    timestamp: str
    vector_id: Optional[str] = None
    metadata: Optional[Dict] = None


class UnifiedAgentLayer:
    """
    Unified agent communication layer.
    
    Provides a single interface that:
    1. Uses Redis when available (via multi_agent)
    2. Falls back to file system (via agent_coordinator)
    3. Syncs state between both systems
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._redis_available = False
        self._coordinator = None
        self._multi_agent = None
        self._init_backends()
    
    @classmethod
    def get_instance(cls) -> 'UnifiedAgentLayer':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _init_backends(self):
        """Initialize both backends"""
        # Try Redis backend (multi_agent)
        try:
            from multi_agent import get_agent_registry, get_message_bus, get_shared_workspace
            self._multi_agent_registry = get_agent_registry()
            self._multi_agent_bus = get_message_bus()
            self._multi_agent_workspace = get_shared_workspace()
            self._redis_available = self._multi_agent_registry.is_available
            print("[unified] Redis backend: " + ("OK" if self._redis_available else "NOT AVAILABLE"))
        except Exception as e:
            print("[unified] Redis backend init failed: " + str(e))
            self._redis_available = False
        
        # Always init file system backend (agent_coordinator)
        try:
            from agent_coordinator import get_coordinator
            self._coordinator = get_coordinator()
            print("[unified] FileSystem backend: OK")
        except Exception as e:
            print("[unified] FileSystem backend init failed: " + str(e))
            self._coordinator = None
    
    @property
    def is_redis_available(self) -> bool:
        return self._redis_available
    
    @property
    def agent_id(self) -> str:
        if self._coordinator:
            return self._coordinator.agent_id
        return "unknown"
    
    # =========================================================================
    # REGISTRATION & PRESENCE
    # =========================================================================
    
    def register(self, role: str = "general", status: str = "active", 
                 current_task: str = None) -> Dict:
        """
        Register this agent with both backends.
        """
        result = {
            "role": role,
            "status": status,
            "redis_used": False,
            "filesystem_used": True,
            "agent_id": None
        }
        
        # Register with Redis if available
        if self._redis_available:
            try:
                from multi_agent import initialize_multi_agent
                from session_logger import SESSION_ID, SESSION_UNIQUE
                
                ma_result = initialize_multi_agent(
                    session_id=SESSION_ID,
                    session_unique=SESSION_UNIQUE,
                    role=role
                )
                
                if ma_result.get('initialized'):
                    result["agent_id"] = ma_result.get('agent_id')
                    result["redis_used"] = True
            except Exception as e:
                print("[unified] Redis registration failed: " + str(e))
        
        # Register with file system backend
        if self._coordinator:
            try:
                meta = self._coordinator.register(role=role, status=status, current_task=current_task)
                result["agent_id"] = meta.agent_id
                result["filesystem_used"] = True
            except Exception as e:
                print("[unified] Filesystem registration failed: " + str(e))
        
        # Save unified state
        self._save_state(result)
        
        return result
    
    def heartbeat(self, status: str = None, current_task: str = None):
        """Send heartbeat to both backends"""
        if self._coordinator:
            self._coordinator.heartbeat(status=status, current_task=current_task)
    
    def get_active_agents(self) -> List[Dict]:
        """
        Get all active agents from both backends.
        Merges results, removing duplicates.
        """
        agents = {}
        
        # Get from file system backend (always has data)
        if self._coordinator:
            try:
                for a in self._coordinator.get_active_agents(include_self=True):
                    agents[a['agent_id']] = a
            except:
                pass
        
        # Get from Redis backend if available
        if self._redis_available and self._multi_agent_registry:
            try:
                for a in self._multi_agent_registry.get_active_agents(include_self=True):
                    agents[a.agent_id] = a.to_dict()
            except:
                pass
        
        return list(agents.values())
    
    # =========================================================================
    # MESSAGING
    # =========================================================================
    
    def send_message(self, to_agent: str, msg_type: str, content: Any,
                    metadata: Dict = None) -> Optional[str]:
        """
        Send message to another agent.
        Uses Redis if available, otherwise file system.
        """
        msg_id = None
        
        # Try Redis first
        if self._redis_available and self._multi_agent_bus:
            try:
                msg = self._multi_agent_bus.send_message(
                    to_agent=to_agent,
                    msg_type=msg_type,
                    content=str(content)[:500] if isinstance(content, str) else content,
                    metadata=metadata
                )
                if msg:
                    msg_id = msg.msg_id
            except Exception as e:
                print("[unified] Redis send failed: " + str(e))
        
        # Always also send via file system for redundancy
        if self._coordinator:
            try:
                from agent_coordinator import MessageType
                # Map string msg_type to MessageType enum if needed
                if isinstance(msg_type, str):
                    try:
                        msg_type_enum = MessageType(msg_type)
                    except:
                        msg_type_enum = MessageType.COORDINATE
                else:
                    msg_type_enum = msg_type
                
                fs_msg_id = self._coordinator.send_message(
                    msg_type=msg_type_enum,
                    content=content,
                    to_agent=to_agent
                )
                if fs_msg_id:
                    msg_id = fs_msg_id
            except Exception as e:
                print("[unified] FileSystem send failed: " + str(e))
        
        return msg_id
    
    def broadcast(self, msg_type: str, content: Any, metadata: Dict = None) -> Optional[str]:
        """Broadcast to all agents"""
        return self.send_message("broadcast", msg_type, content, metadata)
    
    def get_messages(self, agent_id: str = None, limit: int = 20) -> List[Dict]:
        """Get messages for this agent from both backends"""
        messages = []
        seen_ids = set()
        
        # Get from file system backend
        if self._coordinator:
            try:
                for m in self._coordinator.get_messages(agent_id=agent_id, limit=limit):
                    if m['id'] not in seen_ids:
                        messages.append(m)
                        seen_ids.add(m['id'])
            except:
                pass
        
        # Get from Redis backend if available
        if self._redis_available and self._multi_agent_bus:
            try:
                redis_messages = self._multi_agent_bus.get_messages(
                    agent_id=agent_id or self.agent_id,
                    limit=limit
                )
                for m in redis_messages:
                    if m.msg_id not in seen_ids:
                        messages.append({
                            'id': m.msg_id,
                            'from_agent': m.from_agent,
                            'to_agent': m.to_agent,
                            'type': m.msg_type,
                            'content': m.content,
                            'timestamp': m.created_at,
                            'metadata': m.metadata
                        })
                        seen_ids.add(m.msg_id)
            except:
                pass
        
        # Sort by timestamp descending
        messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return messages[:limit]
    
    def get_unread_messages(self) -> List[Dict]:
        """Get unread messages for this agent"""
        return self.get_messages(limit=50)  # Filter by read status later
    
    def search_messages(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search messages semantically.
        Uses vector search for best results.
        """
        results = []
        
        # Search file system backend (has vector store)
        if self._coordinator:
            try:
                fs_results = self._coordinator.search_messages(query, top_k=top_k)
                results.extend(fs_results)
            except:
                pass
        
        # Search Redis backend if available
        if self._redis_available and self._multi_agent_bus:
            try:
                redis_results = self._multi_agent_bus.search_messages(query, top_k=top_k)
                for r in redis_results:
                    r['source'] = 'redis'
                    results.append(r)
            except:
                pass
        
        # Sort by score
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return results[:top_k]
    
    # =========================================================================
    # SHARED WORKSPACE
    # =========================================================================
    
    def workspace_put(self, key: str, value: Any) -> bool:
        """Put item in shared workspace"""
        if self._redis_available and self._multi_agent_workspace:
            try:
                item = self._multi_agent_workspace.put(key, value)
                return item is not None
            except:
                pass
        
        # Fall back to file system
        try:
            ws_file = os.path.join(COORD_DIR, "workspace", key + ".json")
            os.makedirs(os.path.dirname(ws_file), exist_ok=True)
            with open(ws_file, 'w') as f:
                json.dump({
                    'key': key,
                    'value': value,
                    'timestamp': datetime.now().isoformat(),
                    'agent_id': self.agent_id
                }, f, indent=2)
            return True
        except:
            return False
    
    def workspace_get(self, key: str) -> Optional[Any]:
        """Get item from shared workspace"""
        # Try Redis first
        if self._redis_available and self._multi_agent_workspace:
            try:
                item = self._multi_agent_workspace.get(key)
                if item:
                    return item.value
            except:
                pass
        
        # Fall back to file system
        try:
            ws_file = os.path.join(COORD_DIR, "workspace", key + ".json")
            if os.path.exists(ws_file):
                with open(ws_file, 'r') as f:
                    data = json.load(f)
                    return data.get('value')
        except:
            pass
        
        return None
    
    def workspace_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search shared workspace"""
        results = []
        
        if self._redis_available and self._multi_agent_workspace:
            try:
                results = self._multi_agent_workspace.search_items(query, top_k)
            except:
                pass
        
        return results
    
    # =========================================================================
    # TASK COORDINATION
    # =========================================================================
    
    def claim_task(self, task: str, timeout: int = 60) -> Tuple[bool, str]:
        """Claim a task with lock"""
        if self._coordinator:
            return self._coordinator.claim_task(task, timeout)
        return False, "no_coordinator"
    
    def release_task(self, task: str):
        """Release a claimed task"""
        if self._coordinator:
            self._coordinator.release_task(task)
    
    def is_task_locked(self, task: str) -> bool:
        """Check if task is locked"""
        if self._coordinator:
            return self._coordinator.is_task_locked(task)
        return False
    
    def get_task_lock(self, task: str) -> Optional[Dict]:
        """Get task lock info"""
        if self._coordinator:
            return self._coordinator.get_task_lock(task)
        return None
    
    # =========================================================================
    # LEARNINGS
    # =========================================================================
    
    def share_learning(self, learning: Dict):
        """Share a learning with all agents"""
        if self._coordinator:
            self._coordinator.share_learning(learning)
    
    def get_learnings(self, since_minutes: int = 60) -> List[Dict]:
        """Get recent learnings"""
        if self._coordinator:
            return self._coordinator.get_learnings(since_minutes)
        return []
    
    # =========================================================================
    # HELP REQUESTS
    # =========================================================================
    
    def request_help(self, help_type: str, description: str, 
                    priority: str = "normal", context: Dict = None) -> Optional[str]:
        """Request help from another agent"""
        # Try Redis first
        if self._redis_available:
            try:
                from multi_agent import create_help_request
                request = create_help_request(help_type, description, priority, context)
                if request:
                    return request.request_id
            except:
                pass
        
        # Fall back to file system broadcast
        return self.broadcast("request_help", {
            'help_type': help_type,
            'description': description,
            'priority': priority,
            'context': context or {},
            'from': self.agent_id
        })
    
    def get_pending_help_requests(self) -> List[Dict]:
        """Get pending help requests"""
        requests = []
        
        if self._redis_available:
            try:
                from multi_agent import get_pending_help_requests
                for r in get_pending_help_requests():
                    requests.append({
                        'request_id': r.request_id,
                        'from_agent': r.from_agent,
                        'help_type': r.help_type,
                        'description': r.description,
                        'priority': r.priority,
                        'source': 'redis'
                    })
            except:
                pass
        
        return requests
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def get_status(self) -> Dict:
        """Get full status of agent and system"""
        status = {
            'agent_id': self.agent_id,
            'redis_available': self._redis_available,
            'filesystem_backend': self._coordinator is not None,
            'active_agents': len(self.get_active_agents()),
            'timestamp': datetime.now().isoformat()
        }
        
        if self._coordinator:
            try:
                status['coordinator'] = self._coordinator.get_status()
            except:
                pass
        
        return status
    
    def print_status(self):
        """Print human-readable status"""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print("  UNIFIED AGENT LAYER STATUS")
        print("=" * 60)
        print("Agent ID: " + status['agent_id'])
        print("Redis Available: " + str(status['redis_available']))
        print("FileSystem Backend: " + str(status['filesystem_backend']))
        print("Active Agents: " + str(status['active_agents']))
        
        if 'coordinator' in status:
            print("\n[Coordinator]")
            coord = status['coordinator']
            if 'system' in coord:
                sys_info = coord['system']
                print("  Pending Messages: " + str(sys_info.get('messages_pending', 0)))
                print("  Vector Entries: " + str(sys_info.get('vector_store_entries', 0)))
        
        print("=" * 60 + "\n")
    
    # =========================================================================
    # STATE MANAGEMENT
    # =========================================================================
    
    def _save_state(self, state: Dict):
        """Save unified agent state"""
        try:
            os.makedirs(COORD_DIR, exist_ok=True)
            with open(UNIFIED_STATE_FILE, 'w') as f:
                json.dump({
                    **state,
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
    
    def _load_state(self) -> Dict:
        """Load unified agent state"""
        try:
            if os.path.exists(UNIFIED_STATE_FILE):
                with open(UNIFIED_STATE_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def sync_to_redis(self) -> bool:
        """
        Sync file system data to Redis.
        Use when Redis becomes available after being down.
        """
        if not self._redis_available:
            return False
        
        try:
            # Sync messages
            if self._coordinator:
                messages = self._coordinator.get_recent_messages(limit=100)
                for msg in messages:
                    self._multi_agent_bus.send_message(
                        to_agent=msg.get('to_agent', 'broadcast'),
                        msg_type=msg.get('type', 'sync'),
                        content=msg.get('content', {}),
                        metadata={'synced_from': 'filesystem'}
                    )
            
            # Sync workspace
            if self._coordinator and os.path.exists(os.path.join(COORD_DIR, 'workspace')):
                for fname in os.listdir(os.path.join(COORD_DIR, 'workspace')):
                    if fname.endswith('.json'):
                        fpath = os.path.join(COORD_DIR, 'workspace', fname)
                        with open(fpath, 'r') as f:
                            data = json.load(f)
                            self.workspace_put(data.get('key', fname[:-5]), data.get('value'))
            
            print("[unified] Synced to Redis")
            return True
        except Exception as e:
            print("[unified] Sync failed: " + str(e))
            return False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_unified_layer() -> UnifiedAgentLayer:
    """Get unified agent layer singleton"""
    return UnifiedAgentLayer.get_instance()


def unified_register(role: str = "general", status: str = "active",
                    current_task: str = None) -> Dict:
    """Register with unified layer"""
    layer = get_unified_layer()
    return layer.register(role=role, status=status, current_task=current_task)


def unified_heartbeat(status: str = None, current_task: str = None):
    """Send heartbeat"""
    get_unified_layer().heartbeat(status=status, current_task=current_task)


def unified_send(to_agent: str, msg_type: str, content: Any,
                metadata: Dict = None) -> Optional[str]:
    """Send message"""
    return get_unified_layer().send_message(to_agent, msg_type, content, metadata)


def unified_broadcast(msg_type: str, content: Any,
                     metadata: Dict = None) -> Optional[str]:
    """Broadcast to all agents"""
    return get_unified_layer().broadcast(msg_type, content, metadata)


def unified_get_messages(limit: int = 20) -> List[Dict]:
    """Get messages"""
    return get_unified_layer().get_messages(limit=limit)


def unified_search(query: str, top_k: int = 5) -> List[Dict]:
    """Search messages"""
    return get_unified_layer().search_messages(query, top_k)


def unified_workspace_put(key: str, value: Any) -> bool:
    """Put workspace item"""
    return get_unified_layer().workspace_put(key, value)


def unified_workspace_get(key: str) -> Optional[Any]:
    """Get workspace item"""
    return get_unified_layer().workspace_get(key)


def unified_status():
    """Print status"""
    get_unified_layer().print_status()


# ============================================================================
# MAIN / TEST
# ============================================================================

if __name__ == "__main__":
    print("Unified Agent Communication Layer")
    print("=" * 50)
    
    layer = get_unified_layer()
    
    print("\nBackends:")
    print("  Redis: " + ("OK" if layer.is_redis_available else "NOT AVAILABLE"))
    print("  FileSystem: " + ("OK" if layer._coordinator else "NOT AVAILABLE"))
    
    print("\nRegistering...")
    result = layer.register(role="generator", status="active")
    print("  Result: " + str(result))
    
    print("\nGetting active agents...")
    agents = layer.get_active_agents()
    print("  Count: " + str(len(agents)))
    
    print("\nSending test broadcast...")
    msg_id = layer.broadcast("test", {"message": "Hello from unified layer"})
    print("  Sent: " + str(msg_id))
    
    print("\nStatus:")
    layer.print_status()
