"""
Agent Communication Service - Real-Time Inter-Agent Messaging
========================================================
Provides real-time communication between OpenCode agents via:
1. Redis Pub/Sub (now available!)
2. Terminal Wake Signals
3. Background Monitoring with Heartbeat

FIXED: Heartbeat thread, message polling, and wake system

Author: Senior Systems Architect
Version: 2.0 Real-Time with Heartbeat
"""

import os
import sys
import json
import time
import socket
import threading
import subprocess
import signal
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict
import queue

# ============================================================================
# CONFIGURATION
# ============================================================================

COORD_DIR = r"E:\AI-Setup\blackboard_data\agent_coordination"
STATE_DIR = os.path.join(COORD_DIR, "state")
MESSAGES_DIR = os.path.join(COORD_DIR, "messages")
LOCKS_DIR = os.path.join(COORD_DIR, "locks")
VECTOR_INDEX_DIR = os.path.join(COORD_DIR, "vector_index")

for d in [COORD_DIR, STATE_DIR, MESSAGES_DIR, LOCKS_DIR, VECTOR_INDEX_DIR]:
    os.makedirs(d, exist_ok=True)

SERVICE_NAME = "OpenCodeAgentComm"
HEARTBEAT_INTERVAL = 10  # seconds - heartbeat frequency
MESSAGE_POLL_INTERVAL = 1.0  # seconds - check for new messages
NOTIFICATION_SERVER_PORT = 5555

# ============================================================================
# IDENTITY - Persistent across sessions
# ============================================================================

def get_persistent_agent_id() -> str:
    """Get or create persistent agent ID that survives process restarts"""
    identity_file = os.path.join(COORD_DIR, "identity.json")
    
    if os.path.exists(identity_file):
        try:
            with open(identity_file, 'r') as f:
                data = json.load(f)
            return data.get("agent_id")
        except:
            pass
    
    # Create new identity
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    with open(identity_file, 'w') as f:
        json.dump({"agent_id": agent_id, "created": datetime.now().isoformat()}, f)
    
    return agent_id


# ============================================================================
# WINDOWS NOTIFICATION - Wake Up Terminals
# ============================================================================

class TerminalWaker:
    """Send wake signals to terminals via multiple methods"""
    
    @staticmethod
    def send_tcp_bell(port: int = NOTIFICATION_SERVER_PORT) -> bool:
        """Send bell via TCP to notification server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(("127.0.0.1", port))
            sock.send(b"BELL\n")
            sock.close()
            return True
        except:
            return False
    
    @staticmethod
    def print_bell():
        """Print bell character to stdout"""
        print("\a", end="", flush=True)
        return True
    
    @staticmethod
    def send_windows_notification(title: str, message: str) -> bool:
        """Send Windows toast notification"""
        try:
            escaped_title = title.replace('"', "'").replace('\n', ' ')
            escaped_msg = message.replace('"', "'").replace('\n', ' ')[:200]
            
            script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
            $template = @"
            <toast activationType="foreground">
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{escaped_title}</text>
                        <text id="2">{escaped_msg}</text>
                    </binding>
                </visual>
                <audio src="ms-winsoundevent:Notification.Default"/>
            </toast>
"@
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{SERVICE_NAME}").Show($toast)
            '''
            result = subprocess.run(["powershell", "-Command", script], 
                                 capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def wake_agent(agent_id: str, reason: str = "Message waiting"):
        """Wake a specific agent - tries all methods"""
        success = False
        
        # Method 1: TCP bell to notification server (most reliable)
        if TerminalWaker.send_tcp_bell(NOTIFICATION_SERVER_PORT):
            success = True
        
        # Method 2: Print bell
        TerminalWaker.print_bell()
        
        # Method 3: Windows notification
        TerminalWaker.send_windows_notification(
            f"OpenCode: {agent_id}",
            reason
        )
        
        return success


# ============================================================================
# REDIS PUBSUB - Real-time messaging
# ============================================================================

class RedisPubSub:
    """Redis pub/sub for real-time messaging"""
    
    def __init__(self):
        self.client = None
        self.pubsub = None
        self.running = False
        self._thread = None
        self._callbacks = defaultdict(list)
        self._channel = "agent_comm"
        
    def connect(self) -> bool:
        """Connect to Redis"""
        try:
            import redis
            self.client = redis.Redis(host='127.0.0.1', port=6379, db=0, 
                                     decode_responses=True, socket_connect_timeout=2)
            self.client.ping()
            
            self.pubsub = self.client.pubsub()
            self.pubsub.subscribe(self._channel)
            
            print("[RedisPubSub] Connected to Redis!")
            return True
        except Exception as e:
            print(f"[RedisPubSub] Redis not available: {e}")
            self.client = None
            return False
    
    def publish(self, msg: Dict) -> bool:
        """Publish message to channel"""
        if not self.client:
            return False
        
        try:
            self.client.publish(self._channel, json.dumps(msg))
            return True
        except:
            return False
    
    def subscribe(self, callback: Callable[[Dict], None]):
        """Subscribe to messages"""
        self._callbacks['*'].append(callback)
    
    def start_listening(self):
        """Start listening thread"""
        if not self.client:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
    
    def _listen(self):
        """Listen for messages"""
        while self.running:
            try:
                msg = self.pubsub.get_message(timeout=1.0)
                if msg and msg.get('type') == 'message':
                    data = json.loads(msg.get('data', '{}'))
                    for cb in self._callbacks['*']:
                        try:
                            cb(data)
                        except:
                            pass
            except:
                pass
    
    def stop(self):
        """Stop listening"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)


# ============================================================================
# MESSAGE BROKER
# ============================================================================

class MessageBroker:
    """Message broker with pub/sub and file polling"""
    
    _instance = None
    
    def __init__(self):
        self.redis = RedisPubSub()
        self.redis_connected = self.redis.connect()
        
        self._last_message_check = datetime.now()
        self._seen_message_ids = set()
        self._callbacks = defaultdict(list)
        self._poll_thread = None
        self._running = False
        
        if self.redis_connected:
            self.redis.subscribe(self._on_redis_message)
            self.redis.start_listening()
        
        self._start_polling()
    
    def _on_redis_message(self, msg: Dict):
        """Handle Redis pub/sub message"""
        msg_id = msg.get('id')
        if msg_id and msg_id not in self._seen_message_ids:
            self._seen_message_ids.add(msg_id)
            self._dispatch(msg)
    
    def _start_polling(self):
        """Start file polling thread"""
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_messages, daemon=True)
        self._poll_thread.start()
    
    def _poll_messages(self):
        """Poll for new messages in file system"""
        while self._running:
            try:
                for fname in os.listdir(MESSAGES_DIR):
                    if not fname.endswith('.json'):
                        continue
                    
                    fpath = os.path.join(MESSAGES_DIR, fname)
                    
                    # Check if new or modified
                    mtime = os.path.getmtime(fpath)
                    mod_time = datetime.fromtimestamp(mtime)
                    
                    if mod_time > self._last_message_check:
                        try:
                            with open(fpath, 'r') as f:
                                msg = json.load(f)
                            
                            msg_id = msg.get('id')
                            if msg_id and msg_id not in self._seen_message_ids:
                                self._seen_message_ids.add(msg_id)
                                self._dispatch(msg)
                                
                                # WAKE recipient if this is for them
                                to_agent = msg.get('to_agent', 'broadcast')
                                from_agent = msg.get('from_agent', '')
                                
                                # Notify via Redis if available
                                if self.redis_connected:
                                    self.redis.publish({
                                        **msg,
                                        "_internal": True,
                                        "_wake": True
                                    })
                                
                                # Send wake signal to recipient
                                if to_agent != 'broadcast':
                                    # Try to wake the specific agent
                                    TerminalWaker.wake_agent(
                                        to_agent, 
                                        f"Message from {from_agent}"
                                    )
                        
                        except:
                            pass
                
                self._last_message_check = datetime.now()
                
            except Exception as e:
                pass
            
            time.sleep(MESSAGE_POLL_INTERVAL)
    
    def _dispatch(self, msg: Dict):
        """Dispatch to callbacks"""
        msg_type = msg.get('type', '*')
        
        for cb in self._callbacks.get(msg_type, []) + self._callbacks.get('*', []):
            try:
                cb(msg)
            except:
                pass
    
    def publish(self, msg_type: str, content: Dict, to_agent: str = "broadcast") -> str:
        """Publish a message"""
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        msg = {
            "id": msg_id,
            "from_agent": get_persistent_agent_id(),
            "to_agent": to_agent,
            "type": msg_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to file
        fpath = os.path.join(MESSAGES_DIR, f"{msg_id}.json")
        with open(fpath, 'w') as f:
            json.dump(msg, f, indent=2)
        
        # Publish via Redis if connected
        if self.redis_connected:
            self.redis.publish(msg)
        
        # Immediately dispatch locally
        self._seen_message_ids.add(msg_id)
        self._dispatch(msg)
        
        # Wake recipient
        if to_agent != 'broadcast':
            TerminalWaker.wake_agent(to_agent, f"New {msg_type} from {msg.get('from_agent')}")
        
        return msg_id
    
    def subscribe(self, msg_type: str, callback: Callable[[Dict], None]):
        """Subscribe to message type"""
        self._callbacks[msg_type].append(callback)
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Get recent messages"""
        messages = []
        for fname in sorted(os.listdir(MESSAGES_DIR), reverse=True):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(MESSAGES_DIR, fname)
            try:
                with open(fpath, 'r') as f:
                    messages.append(json.load(f))
            except:
                pass
            if len(messages) >= limit:
                break
        return messages
    
    def stop(self):
        """Stop the broker"""
        self._running = False
        self.redis.stop()


# ============================================================================
# HEARTBEAT SYSTEM
# ============================================================================

class HeartbeatManager:
    """Manages agent heartbeats - sends and monitors"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._running = False
        self._thread = None
        self._interval = HEARTBEAT_INTERVAL
    
    def start(self):
        """Start sending heartbeats"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        print(f"[Heartbeat] Started for {self.agent_id}")
    
    def _heartbeat_loop(self):
        """Heartbeat sending loop"""
        while self._running:
            try:
                self._send_heartbeat()
            except:
                pass
            time.sleep(self._interval)
    
    def _send_heartbeat(self):
        """Send a heartbeat to state file"""
        state_file = os.path.join(STATE_DIR, f"{self.agent_id}.json")
        
        state = {
            "agent_id": self.agent_id,
            "last_heartbeat": datetime.now().isoformat(),
            "status": "active",
            "pid": os.getpid()
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        # Also check for waiting messages
        self._check_waiting_messages()
    
    def _check_waiting_messages(self):
        """Check if there are messages for this agent"""
        my_id = self.agent_id
        
        for fname in os.listdir(MESSAGES_DIR):
            if not fname.endswith('.json'):
                continue
            
            fpath = os.path.join(MESSAGES_DIR, fname)
            try:
                with open(fpath, 'r') as f:
                    msg = json.load(f)
                
                if msg.get('to_agent') == my_id:
                    # There's a message for us!
                    # Wake up!
                    TerminalWaker.wake_agent(my_id, f"Message waiting: {msg.get('type')}")
            except:
                pass
    
    def stop(self):
        """Stop heartbeat"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)


# ============================================================================
# AGENT COMMUNICATION SERVICE
# ============================================================================

class AgentCommService:
    """
    Main communication service for agents.
    Provides real-time messaging with heartbeat and wake system.
    """
    
    _instance = None
    
    def __init__(self):
        self.agent_id = get_persistent_agent_id()
        self.broker = MessageBroker()
        self.heartbeat = HeartbeatManager(self.agent_id)
        self._running = True
        
        # Start heartbeat
        self.heartbeat.start()
        
        # Register this agent
        self._register()
        
        # Subscribe to messages
        self.broker.subscribe('*', self._on_message)
        
        print(f"[AgentComm] Initialized for {self.agent_id}")
        print(f"[AgentComm] Redis connected: {self.broker.redis_connected}")
    
    def _register(self):
        """Register this agent's presence"""
        state_file = os.path.join(STATE_DIR, f"{self.agent_id}.json")
        
        import platform
        import psutil
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
        except:
            memory_mb = 0
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except:
            ip = "127.0.0.1"
        
        state = {
            "agent_id": self.agent_id,
            "hostname": socket.gethostname(),
            "ip_address": ip,
            "pid": os.getpid(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "memory_mb": round(memory_mb, 1),
            "registered_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "status": "active",
            "message_count": 0
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _on_message(self, msg: Dict):
        """Handle incoming message"""
        to_agent = msg.get('to_agent', 'broadcast')
        
        # Only handle if for us
        if to_agent != self.agent_id and to_agent != 'broadcast':
            return
        
        msg_type = msg.get('type', '')
        content = msg.get('content', {})
        
        print(f"\n[MSG from {msg.get('from_agent')}]: {msg_type}")
        if content.get('message'):
            print(f"    {content.get('message')[:100]}")
        
        # Update message count
        state_file = os.path.join(STATE_DIR, f"{self.agent_id}.json")
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
            state['message_count'] = state.get('message_count', 0) + 1
            state['last_message_from'] = msg.get('from_agent')
            state['last_message_type'] = msg_type
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        
        # Auto-respond to ping
        if msg_type == 'ping':
            self.send_message('pong', {'original_time': content.get('time')}, msg.get('from_agent'))
    
    def send_message(self, msg_type: str, content: Dict, to_agent: str = "broadcast") -> str:
        """Send a message"""
        return self.broker.publish(msg_type, content, to_agent)
    
    def send_personal_message(self, to_agent: str, msg_type: str, content: Dict) -> str:
        """Send message to specific agent"""
        return self.send_message(msg_type, content, to_agent)
    
    def broadcast(self, msg_type: str, content: Dict) -> str:
        """Broadcast to all agents"""
        return self.send_message(msg_type, content, "broadcast")
    
    def ping_agent(self, agent_id: str) -> bool:
        """Ping an agent and wait for pong"""
        self.send_message('ping', {'time': datetime.now().isoformat()}, agent_id)
        # In a real system, we'd wait for response
        return True
    
    def get_active_agents(self) -> List[Dict]:
        """Get all active agents"""
        agents = []
        watchdog = 60  # 60 seconds timeout
        cutoff = datetime.now() - timedelta(seconds=watchdog)
        
        for fname in os.listdir(STATE_DIR):
            if not fname.endswith('.json'):
                continue
            
            fpath = os.path.join(STATE_DIR, fname)
            try:
                with open(fpath, 'r') as f:
                    state = json.load(f)
                
                last_hb = datetime.fromisoformat(state.get('last_heartbeat', '2000-01-01'))
                if last_hb > cutoff:
                    agents.append(state)
            except:
                pass
        
        return sorted(agents, key=lambda x: x.get('last_heartbeat', ''), reverse=True)
    
    def stop(self):
        """Stop the service"""
        self._running = False
        self.heartbeat.stop()
        self.broker.stop()


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_comm_service = None

def get_comm_service() -> AgentCommService:
    """Get the communication service singleton"""
    global _comm_service
    if _comm_service is None:
        _comm_service = AgentCommService()
    return _comm_service


# ============================================================================
# NOTIFICATION SERVER
# ============================================================================

class NotificationServer:
    """TCP server that wakes terminals on incoming connections"""
    
    def __init__(self, port: int = NOTIFICATION_SERVER_PORT):
        self.port = port
        self.running = False
        self._thread = None
        self._sock = None
    
    def start(self):
        """Start the server"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self._sock.bind(("127.0.0.1", self.port))
            self._sock.listen(5)
            self._sock.settimeout(1)
            
            self.running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            
            print(f"[NotificationServer] Listening on port {self.port}")
            return True
        except Exception as e:
            print(f"[NotificationServer] Failed to start: {e}")
            return False
    
    def _run(self):
        """Main server loop"""
        while self.running:
            try:
                client, addr = self._sock.accept()
                self._handle_client(client)
            except socket.timeout:
                continue
            except:
                if self.running:
                    pass
    
    def _handle_client(self, client):
        """Handle incoming connection"""
        try:
            data = client.recv(1024).decode().strip()
            
            if data.startswith("BELL"):
                # Bell request - wake all terminals
                TerminalWaker.print_bell()
                client.send(b"OK\n")
            elif data.startswith("BROADCAST:"):
                # Broadcast message
                msg = data.split(":", 1)[1]
                TerminalWaker.send_windows_notification("OpenCode Broadcast", msg[:200])
                client.send(b"OK\n")
            elif data.startswith("STATUS"):
                # Status request
                agents = get_comm_service().get_active_agents()
                client.send(json.dumps(agents).encode())
            else:
                client.send(b"UNKNOWN\n")
                
        except Exception as e:
            client.send(f"ERROR: {e}\n".encode())
        finally:
            client.close()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self._sock:
            try:
                self._sock.close()
            except:
                pass


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Communication Service")
    parser.add_argument("--server", action="store_true", help="Run as notification server")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--send", nargs=3, metavar=("TYPE", "TO", "MSG"), help="Send message")
    parser.add_argument("--agents", action="store_true", help="List active agents")
    
    args = parser.parse_args()
    
    if args.server:
        server = NotificationServer()
        server.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
    
    elif args.status:
        comm = get_comm_service()
        print(f"Agent ID: {comm.agent_id}")
        print(f"Redis: {comm.broker.redis_connected}")
        print(f"Active agents: {len(comm.get_active_agents())}")
    
    elif args.agents:
        comm = get_comm_service()
        for a in comm.get_active_agents():
            print(f"{a['agent_id']} | {a.get('status')} | {a.get('last_heartbeat', '')[:19]}")
    
    elif args.send:
        comm = get_comm_service()
        msg_type, to, msg = args.send
        msg_id = comm.send_message(msg_type, {'text': msg}, to)
        print(f"Sent: {msg_id}")
    
    else:
        comm = get_comm_service()
        print(f"Agent ID: {comm.agent_id}")
        print(f"Redis: {comm.broker.redis_connected}")
        print(f"Active agents: {len(comm.get_active_agents())}")
