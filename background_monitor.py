"""
Background Agent Monitor Service
================================
A persistent background service that monitors Redis and notifies agents.

SOLUTION ARCHITECTURE:
1. This service runs as a BACKGROUND PROCESS alongside OpenCode
2. It polls Redis every 100ms for new messages
3. It shows Windows toast notifications for important messages
4. It maintains a MESSAGE INBOX that OpenCode can query
5. It rings terminal bell when terminal IS focused

WHY THIS WORKS FOR CLI:
- OpenCode doesn't need constant polling
- Messages queue up in Redis Streams
- When OpenCode is ready, it queries the inbox
- Notifications appear even when terminal is minimized

Author: Senior Systems Architect
Version: 1.0 Background Monitor
"""

import os
import sys
import json
import time
import uuid
import socket
import subprocess
import threading
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any

sys.path.insert(0, r'E:\AI-Setup')

# Configuration
COORD_DIR = r"E:\AI-Setup\blackboard_data\agent_coordination"
INBOX_DIR = os.path.join(COORD_DIR, "inbox")
MANIFEST_DIR = os.path.join(COORD_DIR, "manifests")
STREAM_KEY = "agent_comm:stream"
MONITOR_INTERVAL = 100  # ms - fast polling
HEARTBEAT_INTERVAL = 30  # seconds

# Notification settings
NOTIFY_HIGH_PRIORITY = True
NOTIFY_BROADCAST = True
NOTIFY_DIRECT = True
NOTIFY_TASK_ASSIGN = True

os.makedirs(INBOX_DIR, exist_ok=True)


class WindowsNotifier:
    """Send Windows toast notifications"""
    
    SERVICE_NAME = "OpenCodeAgent"
    
    @staticmethod
    def show(title: str, message: str, urgency: str = "normal"):
        """Show Windows toast notification"""
        try:
            escaped_title = title.replace('"', "'").replace('\n', ' ')[:50]
            escaped_msg = message.replace('"', "'").replace('\n', ' ')[:200]
            
            # Urgency affects sound
            sound = "Notification.Default" if urgency == "normal" else "Notification.Looping.Alarm"
            
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
    <audio src="ms-winsoundevent:{sound}"/>
</toast>
"@
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{WindowsNotifier.SERVICE_NAME}").Show($toast)
'''
            subprocess.run(["powershell", "-Command", script], 
                         capture_output=True, timeout=5)
            return True
        except Exception as e:
            return False
    
    @staticmethod
    def ring_bell():
        """Ring terminal bell"""
        print("\a", end="", flush=True)


class MessageInbox:
    """
    File-based message inbox that persists across OpenCode invocations.
    
    Structure:
    - inbox/{agent_id}/inbox.json - List of all messages
    - inbox/{agent_id}/unread.json - Unread message IDs
    - inbox/{agent_id}/latest.json - Latest message for quick check
    """
    
    @staticmethod
    def get_inbox_path(agent_id: str) -> str:
        return os.path.join(INBOX_DIR, agent_id)
    
    @staticmethod
    def ensure_inbox(agent_id: str):
        inbox_path = MessageInbox.get_inbox_path(agent_id)
        os.makedirs(inbox_path, exist_ok=True)
        return inbox_path
    
    @staticmethod
    def add_message(agent_id: str, message: Dict):
        """Add message to agent's inbox"""
        inbox_path = MessageInbox.ensure_inbox(agent_id)
        
        inbox_file = os.path.join(inbox_path, "inbox.json")
        unread_file = os.path.join(inbox_path, "unread.json")
        latest_file = os.path.join(inbox_path, "latest.json")
        
        # Load or create inbox
        messages = []
        if os.path.exists(inbox_file):
            try:
                with open(inbox_file, 'r') as f:
                    messages = json.load(f)
            except:
                pass
        
        # Add new message
        messages.append(message)
        
        # Keep only last 100 messages
        messages = messages[-100:]
        
        # Save inbox
        with open(inbox_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        # Update unread
        unread = []
        if os.path.exists(unread_file):
            try:
                with open(unread_file, 'r') as f:
                    unread = json.load(f)
            except:
                pass
        
        unread.append(message.get('msg_id', str(uuid.uuid4())))
        with open(unread_file, 'w') as f:
            json.dump(unread, f, indent=2)
        
        # Update latest
        with open(latest_file, 'w') as f:
            json.dump(message, f, indent=2)
        
        return message
    
    @staticmethod
    def get_messages(agent_id: str, limit: int = 20) -> List[Dict]:
        """Get all messages from inbox"""
        inbox_file = os.path.join(MessageInbox.get_inbox_path(agent_id), "inbox.json")
        
        if not os.path.exists(inbox_file):
            return []
        
        try:
            with open(inbox_file, 'r') as f:
                messages = json.load(f)
            return messages[-limit:]
        except:
            return []
    
    @staticmethod
    def get_unread_count(agent_id: str) -> int:
        """Get count of unread messages"""
        unread_file = os.path.join(MessageInbox.get_inbox_path(agent_id), "unread.json")
        
        if not os.path.exists(unread_file):
            return 0
        
        try:
            with open(unread_file, 'r') as f:
                unread = json.load(f)
            return len(unread)
        except:
            return 0
    
    @staticmethod
    def get_latest(agent_id: str) -> Optional[Dict]:
        """Get latest message"""
        latest_file = os.path.join(MessageInbox.get_inbox_path(agent_id), "latest.json")
        
        if not os.path.exists(latest_file):
            return None
        
        try:
            with open(latest_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    @staticmethod
    def mark_read(agent_id: str, msg_ids: List[str] = None):
        """Mark messages as read"""
        unread_file = os.path.join(MessageInbox.get_inbox_path(agent_id), "unread.json")
        
        if not os.path.exists(unread_file):
            return
        
        try:
            with open(unread_file, 'r') as f:
                unread = json.load(f)
            
            if msg_ids:
                unread = [u for u in unread if u not in msg_ids]
            else:
                unread = []
            
            with open(unread_file, 'w') as f:
                json.dump(unread, f, indent=2)
        except:
            pass


class BackgroundMonitor:
    """
    Background monitor that polls Redis and notifies agents.
    
    Runs as a daemon, polling every MONITOR_INTERVAL ms.
    When messages arrive, it:
    1. Adds to message inbox
    2. Shows Windows notification
    3. Rings bell
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.running = False
        self.thread = None
        self._redis = None
        self._last_msg_id = None
        self._connect_redis()
    
    def _connect_redis(self):
        """Connect to Redis"""
        try:
            import redis
            self._redis = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=3
            )
            self._redis.ping()
            print(f"[monitor] Redis connected")
        except Exception as e:
            print(f"[monitor] Redis connection failed: {e}")
            self._redis = None
    
    def _poll_messages(self):
        """Poll for new messages"""
        if not self._redis:
            self._connect_redis()
            if not self._redis:
                return
        
        try:
            # Get new messages from stream
            results = self._redis.xrevrange(STREAM_KEY, "+", "-", count=10)
            
            for msg_id, fields in reversed(list(results or [])):
                try:
                    # Parse message - data field contains the JSON message
                    msg = json.loads(fields.get("data", "{}"))
                    
                    # Skip if we've seen this before
                    if self._last_msg_id and msg_id <= self._last_msg_id:
                        continue
                    
                    self._last_msg_id = msg_id
                    
                    # Check if message is for us
                    to_agent = msg.get("to_agent", "")
                    if to_agent not in [self.agent_id, "broadcast"]:
                        continue
                    
                    # Add to inbox
                    MessageInbox.add_message(self.agent_id, msg)
                    
                    # Determine notification priority
                    msg_type = msg.get("msg_type", "")
                    content = msg.get("content", {})
                    
                    if isinstance(content, dict):
                        content_str = content.get("message", str(content))[:100]
                    else:
                        content_str = str(content)[:100]
                    
                    # Notify based on type
                    should_notify = False
                    title = f"OpenCode: {msg_type}"
                    
                    # Handle coordination messages
                    if msg_type == "manifest_update":
                        # Update manifest file
                        if isinstance(content, dict):
                            manifest_file = os.path.join(MANIFEST_DIR, content.get('agent_id', 'unknown') + '.json')
                            try:
                                with open(manifest_file, 'w') as f:
                                    json.dump(content, f, indent=2)
                                print(f"[coordination] Manifest updated: {content.get('agent_id')}")
                            except:
                                pass
                        WindowsNotifier.show("Agent Update", f"{content.get('agent_id', 'unknown')}: {content.get('intent', 'updated')}", "low")
                        should_notify = True
                        
                    elif msg_type == "lock_update":
                        if isinstance(content, dict):
                            action = content.get('action', '')
                            lock = content.get('lock', {})
                            resource = lock.get('resource', 'unknown') if isinstance(lock, dict) else 'unknown'
                            if action == 'acquired':
                                print(f"[coordination] Lock acquired: {resource} by {self.agent_id}")
                            elif action == 'released':
                                print(f"[coordination] Lock released: {resource}")
                        should_notify = False  # Don't notify for locks - silent coordination
                        
                    elif msg_type == "help_request":
                        if isinstance(content, dict):
                            WindowsNotifier.show("Help Requested", f"{content.get('requesting_agent', 'unknown')}: {content.get('description', 'help needed')}", "high")
                            WindowsNotifier.ring_bell()
                            should_notify = True
                        else:
                            WindowsNotifier.show("Help Requested", str(content)[:100], "high")
                            should_notify = True
                            
                    elif msg_type == "help_offer":
                        if isinstance(content, dict):
                            WindowsNotifier.show("Help Offered", f"{content.get('offering_agent', 'unknown')}: {content.get('description', 'help available')}", "normal")
                            should_notify = True
                    
                    elif msg_type == "operational_alert":
                        if isinstance(content, dict):
                            action = content.get("action", "")
                            alert_data = content.get("alert", {})
                            alert_type = alert_data.get("alert_type", "unknown")
                            tier = alert_data.get("tier", 3)
                            agent_id = alert_data.get("agent_id", "unknown")
                            description = alert_data.get("description", "")
                            
                            tier_names = {1: "CRITICAL", 2: "HIGH", 3: "NORMAL", 4: "LOW"}
                            tier_name = tier_names.get(tier, "NORMAL")
                            
                            if action == "created":
                                urgency = "high" if tier <= 2 else "normal"
                                WindowsNotifier.show(f"Op Alert [{tier_name}]", f"{agent_id}: {description}", urgency)
                                if tier <= 2:
                                    WindowsNotifier.ring_bell()
                            elif action == "completed":
                                WindowsNotifier.show("Op Complete", f"{agent_id}: {description[:50]}", "low")
                            elif action == "cancelled":
                                WindowsNotifier.show("Op Cancelled", f"{agent_id}: {description[:50]}", "normal")
                            
                            should_notify = True
                    
                    if msg_type == "task_assign":
                        WindowsNotifier.show(title, f"Task: {content_str}", "high")
                        WindowsNotifier.ring_bell()
                        should_notify = True
                    elif msg_type == "request_help":
                        WindowsNotifier.show(title, f"Help needed: {content_str}", "high")
                        WindowsNotifier.ring_bell()
                        should_notify = True
                    elif msg_type == "coordinate":
                        WindowsNotifier.show(title, f"Coordination: {content_str}", "normal")
                        WindowsNotifier.ring_bell()
                        should_notify = True
                    elif msg_type == "broadcast" and NOTIFY_BROADCAST:
                        WindowsNotifier.show(title, content_str, "low")
                        WindowsNotifier.ring_bell()
                        should_notify = True
                    elif to_agent == self.agent_id and NOTIFY_DIRECT:
                        WindowsNotifier.show("OpenCode DM", content_str, "normal")
                        WindowsNotifier.ring_bell()
                        should_notify = True
                    
                    if should_notify:
                        print(f"\n[MESSAGE] [{msg_type}] {content_str}")
                    
                except Exception as e:
                    pass  # Skip malformed messages
        
        except Exception as e:
            pass  # Polling error, will retry
    
    def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            time.sleep(HEARTBEAT_INTERVAL)
            if self.running and self._redis:
                try:
                    # Update heartbeat file
                    hb_file = os.path.join(COORD_DIR, "state", f"{self.agent_id}.json")
                    if os.path.exists(hb_file):
                        with open(hb_file, 'r') as f:
                            state = json.load(f)
                        state["last_heartbeat"] = datetime.now().isoformat()
                        with open(hb_file, 'w') as f:
                            json.dump(state, f, indent=2)
                except:
                    pass
    
    def start(self):
        """Start the background monitor"""
        self.running = True
        
        # Start polling thread
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        print(f"[monitor] Started for {self.agent_id}")
        print(f"[monitor] Polling every {MONITOR_INTERVAL}ms")
        print(f"[monitor] Inbox: {MessageInbox.get_inbox_path(self.agent_id)}")
    
    def _run(self):
        """Main polling loop"""
        while self.running:
            self._poll_messages()
            time.sleep(MONITOR_INTERVAL / 1000.0)  # Convert to seconds
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print(f"[monitor] Stopped")


# ============================================================================
# CLI FUNCTIONS FOR OPENCODE
# ============================================================================

def check_inbox(agent_id: str = None) -> Dict:
    """
    Check inbox for messages - call this from OpenCode.
    
    Returns:
        Dict with unread_count, latest_message, messages
    """
    if not agent_id:
        agent_id = get_my_agent_id()
    
    return {
        "unread_count": MessageInbox.get_unread_count(agent_id),
        "latest": MessageInbox.get_latest(agent_id),
        "messages": MessageInbox.get_messages(agent_id, limit=5)
    }


def get_my_agent_id() -> str:
    """Get this agent's ID from identity file"""
    identity_file = os.path.join(COORD_DIR, "state", "identity.json")
    
    if os.path.exists(identity_file):
        try:
            with open(identity_file, 'r') as f:
                data = json.load(f)
            return data.get("agent_id", "unknown")
        except:
            pass
    
    return "unknown"


def mark_inbox_read(agent_id: str = None, msg_ids: List[str] = None):
    """Mark messages as read"""
    if not agent_id:
        agent_id = get_my_agent_id()
    MessageInbox.mark_read(agent_id, msg_ids)


# ============================================================================
# MAIN - RUN AS BACKGROUND SERVICE
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Background Agent Monitor")
    parser.add_argument("--agent-id", "-a", help="Agent ID to monitor")
    parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground")
    parser.add_argument("--status", "-s", action="store_true", help="Show inbox status")
    parser.add_argument("--check", "-c", action="store_true", help="Check inbox and exit")
    
    args = parser.parse_args()
    
    if args.status:
        # Just show status
        agent_id = args.agent_id or get_my_agent_id()
        print(f"Agent: {agent_id}")
        print(f"Unread: {MessageInbox.get_unread_count(agent_id)}")
        latest = MessageInbox.get_latest(agent_id)
        if latest:
            print(f"Latest: [{latest.get('msg_type')}] {str(latest.get('content', ''))[:60]}")
        print(f"Inbox: {MessageInbox.get_inbox_path(agent_id)}")
        
    elif args.check:
        # Quick check and exit
        result = check_inbox(args.agent_id)
        print(json.dumps(result, indent=2))
        
    else:
        # Start background monitor
        agent_id = args.agent_id or get_my_agent_id()
        
        print("=" * 50)
        print("Background Agent Monitor")
        print("=" * 50)
        print(f"Agent ID: {agent_id}")
        print(f"Monitor interval: {MONITOR_INTERVAL}ms")
        print()
        
        monitor = BackgroundMonitor(agent_id)
        
        if args.foreground:
            print("Running in foreground (Ctrl+C to stop)...")
            try:
                monitor.start()
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
                monitor.stop()
        else:
            monitor.start()
            print("Running in background (daemon mode)...")
            print("To stop: python background_monitor.py --stop")
            try:
                # Run as daemon - just sleep
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                pass
            monitor.stop()
