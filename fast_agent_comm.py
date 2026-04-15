"""
Fast Agent Communication - Redis Streams Based
==========================================
High-bandwidth, low-latency inter-agent communication using Redis Streams.

Features:
- Redis Streams for persistent, reliable messaging
- Consumer groups for multi-agent consumption
- Direct, broadcast, and request/response patterns
- Message priorities and TTL
- Automatic message cleanup

Author: Senior Systems Architect
Version: 1.0 High-Performance
"""

import os
import sys
import json
import time
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading

sys.path.insert(0, r'E:\AI-Setup')

# Configuration
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
STREAM_KEY = "agent_comm:stream"
STREAM_GROUP = "agent_consumers"
MESSAGE_TTL = 3600  # 1 hour

class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class FastMessage:
    """High-performance message structure"""
    msg_id: str
    from_agent: str
    to_agent: str  # "broadcast" for all
    msg_type: str
    content: Any
    priority: int
    timestamp: str
    reply_to: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        return {
            "msg_id": self.msg_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "msg_type": self.msg_type,
            "content": self.content,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "expires_at": self.expires_at,
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'FastMessage':
        return cls(
            msg_id=d["msg_id"],
            from_agent=d["from_agent"],
            to_agent=d["to_agent"],
            msg_type=d["msg_type"],
            content=d["content"],
            priority=d.get("priority", 1),
            timestamp=d["timestamp"],
            reply_to=d.get("reply_to"),
            expires_at=d.get("expires_at"),
            metadata=d.get("metadata")
        )


class FastAgentComm:
    """
    High-performance agent communication using Redis Streams.
    
    Key improvements over basic pub/sub:
    1. Messages persist until acknowledged
    2. Consumer groups for parallel processing
    3. Message priorities
    4. Request/response with correlation IDs
    5. Automatic cleanup of old messages
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._redis = None
        self._available = False
        self._agent_id = None
        self._pending_responses: Dict[str, threading.Event] = {}
        self._pending_results: Dict[str, Any] = {}
        
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            self._redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=3
            )
            self._redis.ping()
            self._available = True
            
            # Create consumer group if not exists
            try:
                self._redis.xgroup_create(STREAM_KEY, STREAM_GROUP, id='0', mkstream=True)
            except:
                pass  # Group already exists
            
            print("[fast_comm] Redis Streams connected")
        except Exception as e:
            print(f"[fast_comm] Redis not available: {e}")
            self._available = False
    
    @classmethod
    def get_instance(cls) -> 'FastAgentComm':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def set_agent_id(self, agent_id: str):
        """Set this agent's ID"""
        self._agent_id = agent_id
    
    def _generate_msg_id(self) -> str:
        """Generate unique message ID"""
        return f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    # =========================================================================
    # SEND MESSAGES
    # =========================================================================
    
    def send_direct(
        self,
        to_agent: str,
        msg_type: str,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict = None,
        reply_to: str = None
    ) -> Optional[str]:
        """
        Send direct message to specific agent.
        Returns message ID if successful.
        """
        if not self._available or not self._agent_id:
            print(f"[fast_comm] Cannot send - not connected")
            return None
        
        msg = FastMessage(
            msg_id=self._generate_msg_id(),
            from_agent=self._agent_id,
            to_agent=to_agent,
            msg_type=msg_type,
            content=content,
            priority=priority.value,
            timestamp=datetime.now().isoformat(),
            reply_to=reply_to,
            metadata=metadata
        )
        
        try:
            msg_json = json.dumps(msg.to_dict())
            self._redis.xadd(
                STREAM_KEY,
                {
                    "type": "direct",
                    "to": to_agent,
                    "data": msg_json
                },
                maxlen=10000,  # Cap stream at 10k messages
                approximate=True
            )
            
            print(f"[fast_comm] Sent to {to_agent}: [{msg_type}]")
            return msg.msg_id
        except Exception as e:
            print(f"[fast_comm] Send failed: {e}")
            return None
    
    def send_broadcast(
        self,
        msg_type: str,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict = None
    ) -> Optional[str]:
        """Broadcast to all agents"""
        if not self._available or not self._agent_id:
            return None
        
        msg = FastMessage(
            msg_id=self._generate_msg_id(),
            from_agent=self._agent_id,
            to_agent="broadcast",
            msg_type=msg_type,
            content=content,
            priority=priority.value,
            timestamp=datetime.now().isoformat(),
            metadata=metadata
        )
        
        try:
            msg_json = json.dumps(msg.to_dict())
            self._redis.xadd(
                STREAM_KEY,
                {
                    "type": "broadcast",
                    "to": "broadcast",
                    "data": msg_json
                },
                maxlen=10000,
                approximate=True
            )
            
            print(f"[fast_comm] Broadcast: [{msg_type}]")
            return msg.msg_id
        except Exception as e:
            print(f"[fast_comm] Broadcast failed: {e}")
            return None
    
    def send_request(
        self,
        to_agent: str,
        msg_type: str,
        content: Any,
        timeout: float = 30
    ) -> Optional[Any]:
        """
        Send request and wait for response.
        Uses correlation ID for matching responses.
        """
        if not self._available or not self._agent_id:
            return None
        
        correlation_id = str(uuid.uuid4())[:8]
        
        # Send the message
        msg_id = self.send_direct(
            to_agent=to_agent,
            msg_type=msg_type,
            content=content,
            metadata={"correlation_id": correlation_id},
            reply_to=None
        )
        
        if not msg_id:
            return None
        
        # Wait for response
        event = threading.Event()
        self._pending_responses[correlation_id] = event
        
        # Poll for response (in production, use proper async)
        start = time.time()
        while time.time() - start < timeout:
            if correlation_id in self._pending_results:
                result = self._pending_results.pop(correlation_id)
                self._pending_responses.pop(correlation_id, None)
                return result
            
            time.sleep(0.01)  # 10ms polling
        
        # Timeout
        self._pending_responses.pop(correlation_id, None)
        print(f"[fast_comm] Request timeout: {correlation_id}")
        return None
    
    def respond_to(self, correlation_id: str, content: Any):
        """Send response to a request"""
        if not self._available or not self._agent_id:
            return
        
        # Check if someone is waiting
        if correlation_id in self._pending_responses:
            self._pending_results[correlation_id] = content
            self._pending_responses[correlation_id].set()
        else:
            # Send as direct message with reply_to
            self.send_direct(
                to_agent="unknown",  # Would need to track original sender
                msg_type="response",
                content=content,
                reply_to=correlation_id
            )
    
    # =========================================================================
    # RECEIVE MESSAGES
    # =========================================================================
    
    def receive(self, timeout: float = 0, block: bool = True) -> List[FastMessage]:
        """
        Receive messages for this agent.
        
        Args:
            timeout: Max time to wait in ms (0 = non-blocking)
            block: If True, block until message available
            
        Returns:
            List of FastMessage objects
        """
        if not self._available or not self._agent_id:
            return []
        
        messages = []
        
        try:
            # Read new messages for this consumer
            if block and timeout == 0:
                timeout = 1000  # Default 1 second
            
            results = self._redis.xreadgroup(
                STREAM_GROUP,
                self._agent_id[:12],  # Consumer name (shortened)
                {STREAM_KEY: ">"},  # New messages only
                count=10,
                block=timeout if block else None
            )
            
            for stream, msgs in results or []:
                for msg_id, fields in msgs:
                    try:
                        msg_data = json.loads(fields["data"])
                        msg = FastMessage.from_dict(msg_data)
                        
                        # Filter by destination
                        if msg.to_agent in [self._agent_id, "broadcast"]:
                            messages.append(msg)
                            
                            # Acknowledge processing
                            self._redis.xack(STREAM_KEY, STREAM_GROUP, msg_id)
                            
                            # Handle response waiting
                            if msg.reply_to and msg.reply_to in self._pending_responses:
                                self._pending_results[msg.reply_to] = msg.content
                                self._pending_responses[msg.reply_to].set()
                                
                    except Exception as e:
                        print(f"[fast_comm] Parse error: {e}")
                        
        except Exception as e:
            pass  # No messages available
        
        return messages
    
    def get_recent(self, count: int = 10) -> List[FastMessage]:
        """Get recent messages (last N)"""
        if not self._available:
            return []
        
        messages = []
        
        try:
            results = self._redis.xrevrange(STREAM_KEY, "+", "-", count=count)
            
            for msg_id, fields in results or []:
                try:
                    msg_data = json.loads(fields["data"])
                    msg = FastMessage.from_dict(msg_data)
                    
                    if msg.to_agent in [self._agent_id, "broadcast"]:
                        messages.append(msg)
                except:
                    pass
        except:
            pass
        
        return messages
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def get_stream_info(self) -> Dict:
        """Get stream statistics"""
        if not self._available:
            return {}
        
        try:
            info = self._redis.xinfo_stream(STREAM_KEY)
            groups = self._redis.xinfo_groups(STREAM_KEY)
            
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry", None),
                "last_entry": info.get("last-entry", None),
                "consumer_groups": len(groups),
                "groups": groups
            }
        except:
            return {}
    
    def get_pending_count(self) -> int:
        """Get count of pending messages for this consumer"""
        if not self._available or not self._agent_id:
            return 0
        
        try:
            pending = self._redis.xpending(STREAM_KEY, STREAM_GROUP)
            return pending.get("pending", 0)
        except:
            return 0
    
    def cleanup_old(self, max_age_seconds: int = 3600):
        """Delete messages older than max_age_seconds"""
        if not self._available:
            return
        
        try:
            cutoff = time.time() - max_age_seconds
            cutoff_id = str(int(cutoff * 1000000))  # Microseconds
            
            deleted = self._redis.xtrim(STREAM_KEY, minid=cutoff_id)
            if deleted > 0:
                print(f"[fast_comm] Cleaned {deleted} old messages")
        except Exception as e:
            print(f"[fast_comm] Cleanup error: {e}")
    
    def ping(self) -> bool:
        """Check if Redis is responsive"""
        if not self._redis:
            return False
        try:
            self._redis.ping()
            return True
        except:
            return False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_fast_comm() -> FastAgentComm:
    """Get FastAgentComm singleton"""
    return FastAgentComm.get_instance()


def send_to(agent_id: str, msg_type: str, content: Any) -> Optional[str]:
    """Send direct message"""
    comm = get_fast_comm()
    return comm.send_direct(agent_id, msg_type, content)


def broadcast(msg_type: str, content: Any) -> Optional[str]:
    """Broadcast to all agents"""
    comm = get_fast_comm()
    return comm.send_broadcast(msg_type, content)


def receive_all(timeout: float = 0) -> List[FastMessage]:
    """Receive all messages for this agent"""
    return get_fast_comm().receive(timeout=timeout)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Fast Agent Communication - Redis Streams")
    print("=" * 50)
    
    comm = get_fast_comm()
    print(f"Redis available: {comm.is_available}")
    
    if comm.is_available:
        comm.set_agent_id("test_agent")
        
        # Test broadcast
        print("\nTesting broadcast...")
        msg_id = comm.send_broadcast("test", {"hello": "world"})
        print(f"Broadcast ID: {msg_id}")
        
        # Test direct
        print("\nTesting direct...")
        msg_id = comm.send_direct("other_agent", "test", {"hello": "direct"})
        print(f"Direct ID: {msg_id}")
        
        # Get stream info
        print("\nStream info:")
        info = comm.get_stream_info()
        for k, v in info.items():
            print(f"  {k}: {v}")
        
        # Receive
        print("\nReceiving messages...")
        msgs = comm.receive(timeout=1000)
        print(f"Received {len(msgs)} messages")
        for m in msgs:
            print(f"  [{m.from_agent}] {m.msg_type}: {m.content}")
    else:
        print("Redis not available - cannot test")
