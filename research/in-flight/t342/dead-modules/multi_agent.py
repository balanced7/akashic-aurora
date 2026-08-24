"""
Multi-Agent Communication System
================================
Enables multiple OpenCode instances to communicate via Redis + VectorStore.

Features:
- Agent registry with heartbeat/presence
- Vector-based message storage for semantic search
- Shared workspace for concurrent collaboration
- Message routing between agents
- Conflict detection and resolution

ARCHITECTURE:
- Redis: Agent registry, message queues, presence signals
- VectorStore: Message content for semantic search

USAGE:
    from multi_agent import get_agent_registry, get_shared_space, get_message_bus
    
    # On startup
    registry = get_agent_registry()
    registry.register_agent("generator", {"task": "coding"})
    
    # Check for other agents
    active = registry.get_active_agents()
    
    # Send message
    bus = get_message_bus()
    bus.send_message("analyst", "review_needed", {"task": "code_review"})
    
    # Search messages semantically
    results = bus.search_messages("review code", top_k=5)
"""

import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import os
import sys

sys.path.insert(0, r'E:\AI-Setup')

import redis
import numpy as np

try:
    from vector_store import get_vector_store, VectorStore, _text_to_embedding
    VECTOR_STORE_AVAILABLE = True
except ImportError:
    VECTOR_STORE_AVAILABLE = False
    print("[multi_agent] Warning: vector_store not available, using fallback")

# ============================================================================
# CONFIGURATION
# ============================================================================

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

AGENT_TTL_SECONDS = 300
HEARTBEAT_INTERVAL = 30
MESSAGE_TTL_DAYS = 7

AGENT_KEY_PREFIX = "agent"
MESSAGE_KEY_PREFIX = "msg"
SHARED_KEY_PREFIX = "shared"

AGENT_REGISTRY_KEY = "agents:active"
AGENT_HEARTBEAT_KEY = "agents:heartbeat"
AGENT_MESSAGES_KEY = "agents:messages"
SHARED_WORKSPACE_KEY = "shared:workspace"
SHARED_LOGS_KEY = "shared:logs"

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class AgentRole(Enum):
    GENERATOR = "generator"
    ANALYST = "analyst"
    MASTER = "master"
    ORCHESTRATOR = "orchestrator"
    GENERAL = "general"


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    agent_id: str
    role: str
    session_id: str
    session_unique: str
    started_at: str
    last_heartbeat: str
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "session_id": self.session_id,
            "session_unique": self.session_unique,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "status": self.status,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'AgentInfo':
        return cls(
            agent_id=d["agent_id"],
            role=d["role"],
            session_id=d["session_id"],
            session_unique=d["session_unique"],
            started_at=d["started_at"],
            last_heartbeat=d["last_heartbeat"],
            status=d["status"],
            metadata=d.get("metadata", {})
        )


@dataclass
class Message:
    """A message between agents"""
    msg_id: str
    from_agent: str
    to_agent: str  # "all" for broadcast
    msg_type: str  # task_request, task_response, query, broadcast, alert
    content: str
    vector_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None  # msg_id this is replying to

    def to_dict(self) -> Dict:
        return {
            "msg_id": self.msg_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "msg_type": self.msg_type,
            "content": self.content,
            "vector_id": self.vector_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "reply_to": self.reply_to
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'Message':
        return cls(
            msg_id=d["msg_id"],
            from_agent=d["from_agent"],
            to_agent=d["to_agent"],
            msg_type=d["msg_type"],
            content=d["content"],
            vector_id=d.get("vector_id"),
            created_at=d.get("created_at", datetime.now().isoformat()),
            metadata=d.get("metadata", {}),
            reply_to=d.get("reply_to")
        )


@dataclass
class SharedItem:
    """An item in the shared workspace"""
    item_id: str
    key: str
    value: Any
    owner_agent: str
    created_at: str
    updated_at: str
    version: int
    locked: bool
    locked_by: Optional[str] = None
    vector_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "key": self.key,
            "value": self.value,
            "owner_agent": self.owner_agent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "locked": self.locked,
            "locked_by": self.locked_by,
            "vector_id": self.vector_id
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'SharedItem':
        return cls(
            item_id=d["item_id"],
            key=d["key"],
            value=d["value"],
            owner_agent=d["owner_agent"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            version=d.get("version", 1),
            locked=d.get("locked", False),
            locked_by=d.get("locked_by"),
            vector_id=d.get("vector_id")
        )


# ============================================================================
# REDIS CONNECTION
# ============================================================================

def _get_redis_connection():
    """Get Redis connection with error handling"""
    try:
        r = redis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            db=REDIS_DB, 
            decode_responses=True,
            socket_connect_timeout=2
        )
        r.ping()
        return r, True
    except:
        return None, False


# ============================================================================
# AGENT REGISTRY
# ============================================================================

class AgentRegistry:
    """
    Tracks all active agents and their presence.
    
    Uses Redis:
    - agents:active (hash) - Agent info keyed by agent_id
    - agents:heartbeat (sorted set) - Agent heartbeats with timestamp score
    """
    
    _instance: Optional['AgentRegistry'] = None
    
    def __init__(self):
        self._redis, self._available = _get_redis_connection()
        self._vector_store = None
        self._current_agent_id: Optional[str] = None
        self._agent_info: Optional[AgentInfo] = None
        
        if VECTOR_STORE_AVAILABLE and self._available:
            try:
                self._vector_store = get_vector_store()
            except:
                self._vector_store = None
    
    @classmethod
    def get_instance(cls) -> 'AgentRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def _generate_agent_id(self) -> str:
        """Generate unique agent ID"""
        return f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    def register_agent(
        self, 
        role: str, 
        session_id: str, 
        session_unique: str,
        metadata: Dict[str, Any] = None
    ) -> AgentInfo:
        """
        Register this agent in the registry.
        Should be called once on startup.
        """
        if not self._available:
            print("[agent_registry] Redis not available - running in single-agent mode")
            return None
        
        self._current_agent_id = self._generate_agent_id()
        now = datetime.now().isoformat()
        
        self._agent_info = AgentInfo(
            agent_id=self._current_agent_id,
            role=role,
            session_id=session_id,
            session_unique=session_unique,
            started_at=now,
            last_heartbeat=now,
            status="active",
            metadata=metadata or {},
            vector_id=None
        )
        
        try:
            pipe = self._redis.pipeline()
            
            pipe.hset(AGENT_REGISTRY_KEY, self._current_agent_id, json.dumps(self._agent_info.to_dict()))
            pipe.expire(AGENT_REGISTRY_KEY, AGENT_TTL_SECONDS * 2)
            
            pipe.zadd(AGENT_HEARTBEAT_KEY, {self._current_agent_id: datetime.now().timestamp()})
            pipe.expire(AGENT_HEARTBEAT_KEY, AGENT_TTL_SECONDS * 2)
            
            pipe.execute()
            
            if self._vector_store and self._agent_info:
                self._agent_info.vector_id = self._vector_store.add_entry(
                    key=f"agent:{self._current_agent_id}",
                    model="agent_registry",
                    text=f"Agent {self._current_agent_id} role={role} session={session_id}",
                    metadata={"type": "agent_registration", "role": role, "session": session_id}
                )
            
            print(f"[agent_registry] Registered as {self._current_agent_id} (role={role})")
            
        except Exception as e:
            print(f"[agent_registry] Registration error: {e}")
            self._available = False
        
        return self._agent_info
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to indicate agent is alive"""
        if not self._available or not self._current_agent_id:
            return False
        
        try:
            now = datetime.now()
            timestamp = now.timestamp()
            
            self._redis.zadd(AGENT_HEARTBEAT_KEY, {self._current_agent_id: timestamp})
            
            self._redis.hset(AGENT_REGISTRY_KEY, self._current_agent_id, json.dumps({
                **self._agent_info.to_dict(),
                "last_heartbeat": now.isoformat()
            }))
            
            self._redis.expire(AGENT_REGISTRY_KEY, AGENT_TTL_SECONDS * 2)
            self._redis.expire(AGENT_HEARTBEAT_KEY, AGENT_TTL_SECONDS * 2)
            
            return True
        except:
            return False
    
    def unregister_agent(self) -> bool:
        """Unregister this agent"""
        if not self._available or not self._current_agent_id:
            return False
        
        try:
            self._redis.hdel(AGENT_REGISTRY_KEY, self._current_agent_id)
            self._redis.zrem(AGENT_HEARTBEAT_KEY, self._current_agent_id)
            
            print(f"[agent_registry] Unregistered {self._current_agent_id}")
            self._current_agent_id = None
            return True
        except:
            return False
    
    def get_active_agents(self, include_self: bool = False) -> List[AgentInfo]:
        """Get all active agents (heartbeat within TTL)"""
        if not self._available:
            return []
        
        try:
            cutoff = datetime.now().timestamp() - AGENT_TTL_SECONDS
            
            active_ids = self._redis.zrangebyscore(
                AGENT_HEARTBEAT_KEY, 
                cutoff, 
                '+inf',
                withscores=False
            )
            
            agents = []
            for agent_id in active_ids:
                if not include_self and agent_id == self._current_agent_id:
                    continue
                
                data = self._redis.hget(AGENT_REGISTRY_KEY, agent_id)
                if data:
                    try:
                        agents.append(AgentInfo.from_dict(json.loads(data)))
                    except:
                        pass
            
            return agents
        except:
            return []
    
    def get_agent_by_role(self, role: str) -> List[AgentInfo]:
        """Get all active agents with specific role"""
        all_agents = self.get_active_agents(include_self=True)
        return [a for a in all_agents if a.role == role]
    
    def get_current_agent(self) -> Optional[AgentInfo]:
        """Get this agent's info"""
        return self._agent_info
    
    def get_current_agent_id(self) -> Optional[str]:
        """Get this agent's ID"""
        return self._current_agent_id
    
    def count_active_agents(self) -> int:
        """Count all active agents"""
        if not self._available:
            return 1 if self._agent_info else 0
        
        try:
            cutoff = datetime.now().timestamp() - AGENT_TTL_SECONDS
            return len(self._redis.zrangebyscore(AGENT_HEARTBEAT_KEY, cutoff, '+inf'))
        except:
            return 0
    
    def is_any_other_agent_active(self) -> bool:
        """Check if any OTHER agent is active"""
        return len(self.get_active_agents(include_self=False)) > 0
    
    def detect_conflicts(self, resource: str) -> List[AgentInfo]:
        """Check if resource is locked by another agent"""
        if not self._available:
            return []
        
        try:
            lock_key = f"lock:{resource}"
            locked_by = self._redis.get(lock_key)
            
            if locked_by and locked_by != self._current_agent_id:
                data = self._redis.hget(AGENT_REGISTRY_KEY, locked_by)
                if data:
                    return [AgentInfo.from_dict(json.loads(data))]
            return []
        except:
            return []


# ============================================================================
# MESSAGE BUS (Vector-Based)
# ============================================================================

class MessageBus:
    """
    Agent-to-agent messaging with vector-based search.
    
    Uses:
    - Redis lists for message queues per agent
    - VectorStore for semantic message search
    - Pub/sub for real-time message delivery
    """
    
    _instance: Optional['MessageBus'] = None
    
    def __init__(self):
        self._redis, self._available = _get_redis_connection()
        self._vector_store = None
        self._pubsub = None
        
        if VECTOR_STORE_AVAILABLE and self._available:
            try:
                self._vector_store = get_vector_store()
            except:
                self._vector_store = None
        
        self._agent_id = None
    
    @classmethod
    def get_instance(cls) -> 'MessageBus':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_agent_id(self, agent_id: str):
        """Set the agent ID for message sending"""
        self._agent_id = agent_id
    
    def _generate_msg_id(self) -> str:
        """Generate unique message ID"""
        return f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    def send_message(
        self,
        to_agent: str,
        msg_type: str,
        content: Any,
        metadata: Dict[str, Any] = None,
        reply_to: str = None
    ) -> Optional[Message]:
        """
        Send message to another agent or broadcast.
        
        Args:
            to_agent: Target agent ID, "all" for broadcast, or role like "analyst"
            msg_type: Type of message (task_request, task_response, query, broadcast, alert)
            content: Message content (will be embedded as vector)
            metadata: Additional metadata
            reply_to: msg_id this is replying to
            
        Returns:
            Message object if successful
        """
        if not self._available or not self._agent_id:
            print(f"[message_bus] Cannot send - not connected (to={to_agent})")
            return None
        
        msg_id = self._generate_msg_id()
        now = datetime.now().isoformat()
        
        msg = Message(
            msg_id=msg_id,
            from_agent=self._agent_id,
            to_agent=to_agent,
            msg_type=msg_type,
            content=content,
            created_at=now,
            metadata=metadata or {},
            reply_to=reply_to,
            vector_id=None
        )
        
        try:
            # Convert content to string for vector embedding
            content_str = json.dumps(content) if isinstance(content, (dict, list)) else str(content)
            
            if self._vector_store:
                msg.vector_id = self._vector_store.add_entry(
                    key=f"message:{msg_id}",
                    model="message_bus",
                    text=f"[{msg_type}] {content_str}",
                    metadata={
                        "type": "agent_message",
                        "from": self._agent_id,
                        "to": to_agent,
                        "msg_type": msg_type,
                        "metadata": metadata or {}
                    }
                )
            
            msg_json = json.dumps(msg.to_dict())
            
            if to_agent == "all":
                pipe = self._redis.pipeline()
                pipe.lpush(f"{MESSAGE_KEY_PREFIX}:broadcast", msg_json)
                pipe.ltrim(f"{MESSAGE_KEY_PREFIX}:broadcast", 0, 999)
                pipe.execute()
                
                self._redis.set(f"{MESSAGE_KEY_PREFIX}:latest_broadcast", msg_json, ex=MESSAGE_TTL_DAYS * 86400)
            else:
                self._redis.lpush(f"{MESSAGE_KEY_PREFIX}:{to_agent}", msg_json)
                self._redis.expire(f"{MESSAGE_KEY_PREFIX}:{to_agent}", MESSAGE_TTL_DAYS * 86400)
                
                self._redis.lpush(f"{MESSAGE_KEY_PREFIX}:{self._agent_id}:sent", msg_json)
                self._redis.expire(f"{MESSAGE_KEY_PREFIX}:{self._agent_id}:sent", MESSAGE_TTL_DAYS * 86400)
            
            content_preview = str(content)[:50] if content else ""
            print(f"[message_bus] Sent to {to_agent}: [{msg_type}] {content_preview}...")
            return msg
            
        except Exception as e:
            print(f"[message_bus] Send error: {e}")
            return None
    
    def get_messages(self, agent_id: str = None, limit: int = 50) -> List[Message]:
        """Get messages for an agent (or sent by agent if agent_id provided)"""
        if not self._available:
            return []
        
        target_id = agent_id or self._agent_id
        if not target_id:
            return []
        
        try:
            key = f"{MESSAGE_KEY_PREFIX}:{target_id}"
            messages_raw = self._redis.lrange(key, 0, limit - 1)
            
            messages = []
            for msg_json in messages_raw:
                try:
                    messages.append(Message.from_dict(json.loads(msg_json)))
                except:
                    pass
            return messages
        except:
            return []
    
    def get_sent_messages(self, limit: int = 50) -> List[Message]:
        """Get messages sent by this agent"""
        return self.get_messages(agent_id=self._agent_id, limit=limit)
    
    def get_broadcasts(self, limit: int = 50) -> List[Message]:
        """Get recent broadcast messages"""
        if not self._available:
            return []
        
        try:
            broadcasts_raw = self._redis.lrange(f"{MESSAGE_KEY_PREFIX}:broadcast", 0, limit - 1)
            
            messages = []
            for msg_json in broadcasts_raw:
                try:
                    messages.append(Message.from_dict(json.loads(msg_json)))
                except:
                    pass
            return messages
        except:
            return []
    
    def mark_message_read(self, msg_id: str) -> bool:
        """Mark a message as read"""
        if not self._available or not self._agent_id:
            return False
        
        try:
            self._redis.sadd(f"{MESSAGE_KEY_PREFIX}:read:{self._agent_id}", msg_id)
            return True
        except:
            return False
    
    def is_message_read(self, msg_id: str) -> bool:
        """Check if message was read"""
        if not self._available or not self._agent_id:
            return False
        
        try:
            return self._redis.sismember(f"{MESSAGE_KEY_PREFIX}:read:{self._agent_id}", msg_id)
        except:
            return False
    
    def search_messages(
        self, 
        query: str, 
        top_k: int = 5, 
        msg_type: str = None,
        from_agent: str = None
    ) -> List[Dict]:
        """
        Search messages semantically using vector store.
        
        Args:
            query: Search query
            top_k: Number of results
            msg_type: Optional filter by message type
            from_agent: Optional filter by sender
            
        Returns:
            List of matching messages with scores
        """
        if not self._vector_store:
            return []
        
        try:
            results = self._vector_store.search(
                query=f"message {query}",
                top_k=top_k * 2,
                model_filter="message_bus"
            )
            
            filtered = []
            for r in results:
                if r["metadata"].get("type") != "agent_message":
                    continue
                
                if msg_type and r["metadata"].get("msg_type") != msg_type:
                    continue
                
                if from_agent and r["metadata"].get("from") != from_agent:
                    continue
                
                filtered.append(r)
                
                if len(filtered) >= top_k:
                    break
            
            return filtered
        except Exception as e:
            print(f"[message_bus] Search error: {e}")
            return []
    
    def get_unread_count(self) -> int:
        """Get count of unread messages for this agent"""
        if not self._available or not self._agent_id:
            return 0
        
        try:
            messages = self.get_messages(limit=100)
            unread = sum(1 for m in messages if not self.is_message_read(m.msg_id))
            return unread
        except:
            return 0


# ============================================================================
# SHARED WORKSPACE
# ============================================================================

class SharedWorkspace:
    """
    Shared space for agents to collaborate on tasks.
    
    Features:
    - Key-value storage with versioning
    - Item locking to prevent conflicts
    - Vector-based search for items
    - Audit trail of changes
    """
    
    _instance: Optional['SharedWorkspace'] = None
    
    def __init__(self):
        self._redis, self._available = _get_redis_connection()
        self._vector_store = None
        
        if VECTOR_STORE_AVAILABLE and self._available:
            try:
                self._vector_store = get_vector_store()
            except:
                self._vector_store = None
        
        self._agent_id = None
    
    @classmethod
    def get_instance(cls) -> 'SharedWorkspace':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_agent_id(self, agent_id: str):
        """Set the agent ID for ownership tracking"""
        self._agent_id = agent_id
    
    def _generate_item_id(self) -> str:
        """Generate unique item ID"""
        return f"item_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    def put(
        self,
        key: str,
        value: Any,
        force: bool = False
    ) -> Optional[SharedItem]:
        """
        Put an item in shared workspace.
        
        Args:
            key: Item key
            value: Item value (must be JSON serializable)
            force: Overwrite even if locked by another agent
            
        Returns:
            SharedItem if successful
        """
        if not self._available or not self._agent_id:
            print(f"[shared_workspace] Cannot put - not connected")
            return None
        
        try:
            existing = self.get(key)
            
            if existing and existing.locked and existing.locked_by != self._agent_id and not force:
                print(f"[shared_workspace] Item {key} is locked by {existing.locked_by}")
                return None
            
            now = datetime.now().isoformat()
            item_id = existing.item_id if existing else self._generate_item_id()
            
            item = SharedItem(
                item_id=item_id,
                key=key,
                value=value,
                owner_agent=self._agent_id,
                created_at=existing.created_at if existing else now,
                updated_at=now,
                version=(existing.version + 1) if existing else 1,
                locked=False,
                locked_by=None,
                vector_id=None
            )
            
            if self._vector_store:
                item.vector_id = self._vector_store.add_entry(
                    key=f"shared:{key}",
                    model="shared_workspace",
                    text=f"{key}: {json.dumps(value)}",
                    metadata={
                        "type": "shared_item",
                        "key": key,
                        "owner": self._agent_id,
                        "version": item.version
                    }
                )
            
            self._redis.hset(
                SHARED_WORKSPACE_KEY,
                key,
                json.dumps(item.to_dict())
            )
            
            self._redis.lpush(f"{SHARED_KEY_PREFIX}:history:{key}", json.dumps(item.to_dict()))
            self._redis.ltrim(f"{SHARED_KEY_PREFIX}:history:{key}", 0, 99)
            
            print(f"[shared_workspace] Put {key} (v{item.version})")
            return item
            
        except Exception as e:
            print(f"[shared_workspace] Put error: {e}")
            return None
    
    def get(self, key: str) -> Optional[SharedItem]:
        """Get an item from shared workspace"""
        if not self._available:
            return None
        
        try:
            data = self._redis.hget(SHARED_WORKSPACE_KEY, key)
            if data:
                return SharedItem.from_dict(json.loads(data))
            return None
        except:
            return None
    
    def delete(self, key: str) -> bool:
        """Delete an item from shared workspace"""
        if not self._available or not self._agent_id:
            return False
        
        try:
            existing = self.get(key)
            
            if existing and existing.locked and existing.locked_by != self._agent_id:
                print(f"[shared_workspace] Cannot delete - locked by {existing.locked_by}")
                return False
            
            self._redis.hdel(SHARED_WORKSPACE_KEY, key)
            
            if self._vector_store:
                self._vector_store.add_entry(
                    key=f"shared:{key}:deleted",
                    model="shared_workspace",
                    text=f"DELETED: {key}",
                    metadata={
                        "type": "shared_item_deleted",
                        "key": key,
                        "deleted_by": self._agent_id
                    }
                )
            
            return True
        except:
            return False
    
    def lock(self, key: str, ttl: int = 300) -> bool:
        """
        Lock an item for exclusive access.
        
        Args:
            key: Item key to lock
            ttl: Lock timeout in seconds
            
        Returns:
            True if lock acquired
        """
        if not self._available or not self._agent_id:
            return False
        
        try:
            lock_key = f"lock:{key}"
            
            existing = self._redis.get(lock_key)
            if existing and existing != self._agent_id:
                return False
            
            self._redis.set(lock_key, self._agent_id, ex=ttl)
            
            item = self.get(key)
            if item:
                item.locked = True
                item.locked_by = self._agent_id
                self._redis.hset(SHARED_WORKSPACE_KEY, key, json.dumps(item.to_dict()))
            
            print(f"[shared_workspace] Locked {key}")
            return True
        except:
            return False
    
    def unlock(self, key: str) -> bool:
        """Unlock an item"""
        if not self._available or not self._agent_id:
            return False
        
        try:
            lock_key = f"lock:{key}"
            
            existing = self._redis.get(lock_key)
            if existing and existing != self._agent_id:
                return False
            
            self._redis.delete(lock_key)
            
            item = self.get(key)
            if item:
                item.locked = False
                item.locked_by = None
                self._redis.hset(SHARED_WORKSPACE_KEY, key, json.dumps(item.to_dict()))
            
            print(f"[shared_workspace] Unlocked {key}")
            return True
        except:
            return False
    
    def search_items(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search shared items semantically"""
        if not self._vector_store:
            return []
        
        try:
            results = self._vector_store.search(
                query=f"shared workspace {query}",
                top_k=top_k,
                model_filter="shared_workspace"
            )
            
            return [r for r in results if r["metadata"].get("type") == "shared_item"]
        except:
            return []
    
    def get_history(self, key: str, limit: int = 20) -> List[SharedItem]:
        """Get version history of an item"""
        if not self._available:
            return []
        
        try:
            history_raw = self._redis.lrange(f"{SHARED_KEY_PREFIX}:history:{key}", 0, limit - 1)
            
            items = []
            for item_json in history_raw:
                try:
                    items.append(SharedItem.from_dict(json.loads(item_json)))
                except:
                    pass
            return items
        except:
            return []
    
    def get_all_keys(self) -> List[str]:
        """Get all keys in shared workspace"""
        if not self._available:
            return []
        
        try:
            return self._redis.hkeys(SHARED_WORKSPACE_KEY)
        except:
            return []
    
    def create_space(self, space_name: str, description: str = "") -> bool:
        """
        Create a new collaborative space.
        
        Spaces are isolated workspaces for different projects/tasks.
        Each space has its own set of items, locked resources, and messages.
        
        Args:
            space_name: Unique name for the space
            description: What this space is for
            
        Returns:
            True if created successfully
        """
        if not self._available or not self._agent_id:
            return False
        
        try:
            space_key = f"space:{space_name}"
            
            existing = self._redis.hget(SHARED_WORKSPACE_KEY, space_key)
            if existing:
                print(f"[shared_workspace] Space '{space_name}' already exists")
                return False
            
            space_data = {
                "item_id": self._generate_item_id(),
                "key": space_key,
                "type": "space",
                "name": space_name,
                "description": description,
                "owner": self._agent_id,
                "created_at": datetime.now().isoformat(),
                "members": [self._agent_id],
                "status": "active"
            }
            
            self._redis.hset(f"spaces:", space_name, json.dumps(space_data))
            
            if self._vector_store:
                self._vector_store.add_entry(
                    key=f"space:{space_name}",
                    model="shared_workspace",
                    text=f"SPACE: {space_name} - {description}",
                    metadata={
                        "type": "space_created",
                        "name": space_name,
                        "owner": self._agent_id
                    }
                )
            
            print(f"[shared_workspace] Created space '{space_name}'")
            return True
        except Exception as e:
            print(f"[shared_workspace] Failed to create space: {e}")
            return False
    
    def get_spaces(self) -> List[Dict]:
        """Get all spaces"""
        if not self._available:
            return []
        
        try:
            spaces_data = self._redis.hgetall("spaces:")
            spaces = []
            for name, data in spaces_data.items():
                try:
                    spaces.append(json.loads(data))
                except:
                    pass
            return spaces
        except:
            return []


# ============================================================================
# HELP REQUEST SYSTEM
# ============================================================================

HELP_REQUEST_KEY = "help:requests"


class HelpRequest:
    """Represents a request for help from another agent"""
    
    def __init__(
        self,
        request_id: str,
        from_agent: str,
        help_type: str,
        description: str,
        priority: str = "normal",
        context: Dict = None,
        status: str = "pending",
        created_at: str = None,
        responded_at: str = None,
        helper_id: str = None
    ):
        self.request_id = request_id
        self.from_agent = from_agent
        self.help_type = help_type
        self.description = description
        self.priority = priority
        self.context = context or {}
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.responded_at = responded_at
        self.helper_id = helper_id
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "from_agent": self.from_agent,
            "help_type": self.help_type,
            "description": self.description,
            "priority": self.priority,
            "context": self.context,
            "status": self.status,
            "created_at": self.created_at,
            "responded_at": self.responded_at,
            "helper_id": self.helper_id
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'HelpRequest':
        return cls(
            request_id=d["request_id"],
            from_agent=d["from_agent"],
            help_type=d["help_type"],
            description=d["description"],
            priority=d.get("priority", "normal"),
            context=d.get("context", {}),
            status=d.get("status", "pending"),
            created_at=d.get("created_at"),
            responded_at=d.get("responded_at"),
            helper_id=d.get("helper_id")
        )


def create_help_request(
    help_type: str,
    description: str,
    priority: str = "normal",
    context: Dict = None
) -> Optional[HelpRequest]:
    """
    Create a help request that other agents can respond to.
    
    Args:
        help_type: Type of help (generator, analyst, researcher, tester, etc.)
        description: What kind of help is needed
        priority: high, normal, low
        context: Additional context for the helper
        
    Returns:
        HelpRequest if created successfully
    """
    if not _redis_connection_available():
        print("[help_request] Redis not available - cannot create request")
        return None
    
    try:
        r, _ = _get_redis_connection()
        registry = get_agent_registry()
        agent_id = registry.get_current_agent_id() or "unknown"
        
        request_id = f"help_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        request = HelpRequest(
            request_id=request_id,
            from_agent=agent_id,
            help_type=help_type,
            description=description,
            priority=priority,
            context=context or {}
        )
        
        r.lpush(HELP_REQUEST_KEY, json.dumps(request.to_dict()))
        r.expire(HELP_REQUEST_KEY, 86400)
        
        if VECTOR_STORE_AVAILABLE:
            try:
                vs = get_vector_store()
                vs.add_entry(
                    key=f"help_request:{request_id}",
                    model="help_requests",
                    text=f"[{help_type}] {description}",
                    metadata={
                        "type": "help_request",
                        "help_type": help_type,
                        "priority": priority,
                        "from": agent_id
                    }
                )
            except:
                pass
        
        print(f"[help_request] Created: {request_id} ({help_type}) - {description[:50]}...")
        return request
    except Exception as e:
        print(f"[help_request] Failed to create: {e}")
        return None


def get_pending_help_requests(limit: int = 20) -> List[HelpRequest]:
    """Get pending help requests"""
    if not _redis_connection_available():
        return []
    
    try:
        r, _ = _get_redis_connection()
        requests_raw = r.lrange(HELP_REQUEST_KEY, 0, limit - 1)
        
        requests = []
        for req_json in requests_raw:
            try:
                requests.append(HelpRequest.from_dict(json.loads(req_json)))
            except:
                pass
        
        return [r for r in requests if r.status == "pending"]
    except:
        return []


def respond_to_help_request(request_id: str, helper_id: str) -> bool:
    """Mark a help request as responded to"""
    if not _redis_connection_available():
        return False
    
    try:
        r, _ = _get_redis_connection()
        requests_raw = r.lrange(HELP_REQUEST_KEY, 0, 100)
        
        for req_json in requests_raw:
            try:
                req = HelpRequest.from_dict(json.loads(req_json))
                if req.request_id == request_id:
                    req.status = "responded"
                    req.responded_at = datetime.now().isoformat()
                    req.helper_id = helper_id
                    
                    r.lrem(HELP_REQUEST_KEY, 1, req_json)
                    r.lpush(HELP_REQUEST_KEY, json.dumps(req.to_dict()))
                    return True
            except:
                pass
        return False
    except:
        return False


def spawn_helper_agent(
    help_type: str,
    description: str,
    context: Dict = None,
    auto_launch: bool = True
) -> Optional[str]:
    """
    Request a helper agent to spawn.
    
    This creates a help request AND can optionally auto-launch
    a helper agent via subprocess.
    
    Args:
        help_type: Type of helper needed
        description: What the helper should do
        context: Context to share with the helper
        auto_launch: If True, launch helper immediately
        
    Returns:
        Helper agent_id if spawned, or request_id if queued
    """
    if not _redis_connection_available():
        print("[spawn_helper] Redis not available")
        return None
    
    request = create_help_request(help_type, description, context=context)
    
    if not request:
        return None
    
    if auto_launch:
        import subprocess
        import sys
        
        opencode_paths = [
            r"C:\Users\L5\AppData\Local\Programs\OpenCode\opencode.exe",
            r"C:\Program Files\OpenCode\opencode.exe",
        ]
        opencode_path = None
        for path in opencode_paths:
            if os.path.exists(path):
                opencode_path = path
                break
        
        if not opencode_path:
            print("[spawn_helper] OpenCode not found")
            return request.request_id
        
        env = os.environ.copy()
        env['OPENCODE_AGENT_ROLE'] = help_type
        env['OPENCODE_HELPER_FOR'] = request.request_id
        env['OPENCODE_HELPER_CONTEXT'] = json.dumps(context or {})
        
        try:
            process = subprocess.Popen(
                [opencode_path],
                env=env,
                cwd=os.path.dirname(opencode_path)
            )
            
            respond_to_help_request(request.request_id, f"pid:{process.pid}")
            
            print(f"[spawn_helper] Launched {help_type} helper (PID: {process.pid})")
            return f"pid:{process.pid}"
        except Exception as e:
            print(f"[spawn_helper] Failed to launch: {e}")
    
    return request.request_id


def _redis_connection_available() -> bool:
    """Check if Redis connection is available"""
    try:
        r, available = _get_redis_connection()
        return available
    except:
        return False


def _backup_redis_if_needed(operation: str) -> bool:
    """
    Backup Redis before risky operations.
    
    Per AGENT_PRIMER.md REDIS_BACKUP requirements:
    - ALWAYS BACKUP BEFORE CHANGES
    
    Args:
        operation: Description of the operation being performed
        
    Returns:
        True if backup succeeded or not needed, False on failure
    """
    if not _redis_connection_available():
        return True  # No Redis to backup
    
    try:
        r, _ = _get_redis_connection()
        
        # Check if backup is needed (only if significant data exists)
        key_count = len(r.keys('*'))
        if key_count == 0:
            return True  # Empty Redis, no backup needed
        
        # Check last backup time
        try:
            catalog_path = r"E:\AI-Setup\blackboard_data\redis_backups\backup_catalog.json"
            if os.path.exists(catalog_path):
                import json as json_module
                with open(catalog_path, 'r') as f:
                    catalog = json_module.load(f)
                last_backup = catalog.get('last_backup', {})
                if last_backup:
                    from datetime import datetime
                    last_time = datetime.fromisoformat(last_backup.get('timestamp', '2000-01-01'))
                    elapsed = (datetime.now() - last_time).total_seconds()
                    if elapsed < 300:  # Less than 5 minutes since last backup
                        print(f"[redis_backup] Last backup {int(elapsed)}s ago - skipping")
                        return True
        except:
            pass  # Catalog check failed, proceed with backup
        
        # Trigger Redis SAVE
        try:
            r.execute_command('SAVE')
            print(f"[redis_backup] Triggered SAVE before: {operation}")
        except:
            pass  # SAVE failed, but don't block the operation
        
        return True
    except Exception as e:
        print(f"[redis_backup] Backup check failed: {e}")
        return True  # Don't block operation on backup failure


# ============================================================================
# SINGLETON ACCESSORS
# ============================================================================

def get_agent_registry() -> AgentRegistry:
    """Get AgentRegistry singleton"""
    return AgentRegistry.get_instance()


def get_message_bus() -> MessageBus:
    """Get MessageBus singleton"""
    return MessageBus.get_instance()


def get_shared_workspace() -> SharedWorkspace:
    """Get SharedWorkspace singleton"""
    return SharedWorkspace.get_instance()


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize_multi_agent(session_id: str, session_unique: str, role: str = "general") -> Dict:
    """
    Initialize multi-agent system for this instance.
    
    Should be called once on startup after session_logger is initialized.
    
    Returns:
        Dict with initialization status and current agents
    """
    registry = get_agent_registry()
    bus = get_message_bus()
    workspace = get_shared_workspace()
    
    result = {
        "initialized": False,
        "agent_id": None,
        "role": role,
        "redis_available": registry.is_available,
        "vector_available": VECTOR_STORE_AVAILABLE,
        "active_agents": [],
        "warnings": []
    }
    
    if not registry.is_available:
        result["warnings"].append("Redis not available - single-agent mode")
        print("[multi_agent] Warning: Running in single-agent mode (Redis unavailable)")
        return result
    
    agent_info = registry.register_agent(role, session_id, session_unique)
    
    if agent_info:
        result["initialized"] = True
        result["agent_id"] = agent_info.agent_id
        
        bus.set_agent_id(agent_info.agent_id)
        workspace.set_agent_id(agent_info.agent_id)
        
        registry.send_heartbeat()
        
        result["active_agents"] = [
            a.to_dict() for a in registry.get_active_agents(include_self=False)
        ]
        
        if result["active_agents"]:
            result["warnings"].append(f"{len(result['active_agents'])} other agent(s) active")
            print(f"[multi_agent] {len(result['active_agents'])} other agent(s) detected")
    
    return result


def shutdown_multi_agent():
    """Shutdown multi-agent system - unregister this agent"""
    registry = get_agent_registry()
    registry.unregister_agent()


# ============================================================================
# MAIN / TEST
# ============================================================================

if __name__ == "__main__":
    print("Multi-Agent Communication System")
    print("=" * 50)
    
    registry = get_agent_registry()
    print(f"Redis available: {registry.is_available}")
    
    if registry.is_available:
        result = initialize_multi_agent(
            session_id="test_session",
            session_unique="test_001",
            role="generator"
        )
        print(f"\nInitialization result:")
        print(f"  Initialized: {result['initialized']}")
        print(f"  Agent ID: {result['agent_id']}")
        print(f"  Other agents: {len(result['active_agents'])}")
        
        if result['initialized']:
            print("\nSending test message...")
            bus = get_message_bus()
            msg = bus.send_message(
                to_agent="analyst",
                msg_type="query",
                content="Hello from test agent",
                metadata={"test": True}
            )
            print(f"  Sent: {msg.msg_id if msg else 'FAILED'}")
            
            print("\nSearching messages...")
            results = bus.search_messages("hello")
            print(f"  Found: {len(results)}")
            
            print("\nShared workspace test...")
            ws = get_shared_workspace()
            item = ws.put("test_key", {"hello": "world"})
            print(f"  Put item: {item.item_id if item else 'FAILED'}")
            
            print("\nUnregistering...")
            shutdown_multi_agent()
    
    print("\nDone")
