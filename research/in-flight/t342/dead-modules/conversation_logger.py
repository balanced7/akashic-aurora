"""
Conversation Logger - Automatic Backup Logger
===============================================
This runs alongside OpenCode to automatically log conversations.
Creates a SEPARATE log file that can be used to verify automatic logging works.

Usage:
    # Run in separate terminal:
    python E:\AI-Setup\conversation_logger.py
    
    # Or import and use:
    from conversation_logger import ConversationLogger
    logger = ConversationLogger()
    logger.log("user", "message")
    logger.log("assistant", "response")
"""
import os
import sys
import time
import json
import redis
from datetime import datetime

sys.path.insert(0, r"E:\AI-Setup")

# Separate log file for verification - SEPARATE file for conversation_logger
LOG_DIR = r"E:\AI-Setup\session_logs"
CONVERSATION_LOG = os.path.join(LOG_DIR, "conversation_only.jsonl")  # SEPARATE file!
os.makedirs(LOG_DIR, exist_ok=True)

# Session ID for this logger - can be overridden to continue existing session
LOGGER_SESSION = None  # Will try to find existing or create new

class ConversationLogger:
    """Automatic conversation logger - backup verification"""
    
    def __init__(self):
        # Try to find existing active session from Redis first
        try:
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            sessions = r.hgetall("sessions:active")
            for sid, data in sessions.items():
                try:
                    info = json.loads(data)
                    if info.get("status") == "active":
                        self.session_id = sid
                        break
                except:
                    pass
            
            if not self.session_id:
                self.session_id = f"convo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        except:
            self.session_id = f"convo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.start_time = datetime.now()
        self.message_count = 0
        
        # Try connect to Redis
        try:
            self.redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis.ping()
            self.redis_ok = True
        except:
            self.redis = None
            self.redis_ok = False
            print("[ConversationLogger] Redis not available - file only")
        
        # Log startup with session info
        self._log_entry({
            "type": "logger_startup",
            "session": self.session_id,
            "unique_id": f"{self.session_id}_{self.start_time.strftime('%H%M%S')}",
            "redis": self.redis_ok,
            "timestamp": self.start_time.isoformat()
        })
    
    def _log_entry(self, entry):
        """Write to file (always works even without Redis)"""
        with open(CONVERSATION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def log(self, role, message, metadata=None):
        """
        Log a conversation message.
        
        Args:
            role: "user" or "assistant"
            message: The message text
            metadata: Optional dict with extra info
        """
        self.message_count += 1
        
        entry = {
            "type": "conversation_message",
            "session": self.session_id,
            "unique_id": f"{self.session_id}_{self.start_time.strftime('%H%M%S')}",
            "role": role,
            "message": message[:500],  # Truncate long messages
            "message_length": len(message),
            "sequence": self.message_count,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Always write to file
        self._log_entry(entry)
        
        # Also try Redis
        if self.redis_ok:
            try:
                self.redis.rpush("convo:backup:messages", json.dumps({
                    "role": role,
                    "message": message[:500],
                    "session": self.session_id,
                    "timestamp": datetime.now().isoformat()
                }))
                self.redis.ltrim("convo:backup:messages", -2000, -1)
            except:
                pass
        
        return entry
    
    def log_user(self, message):
        """Log user message"""
        return self.log("user", message)
    
    def log_assistant(self, message, context=None):
        """Log assistant response"""
        return self.log("assistant", message, context)
    
    # ============ MATCH SESSION_LOGGER API ============
    def log_action(self, action, description="", data=None):
        """Log an action (matches session_logger.log)"""
        entry = {
            "type": "action",
            "timestamp": datetime.now().isoformat(),
            "session": self.session_id,
            "unique_id": f"{self.session_id}_{self.start_time.strftime('%H%M%S')}",
            "action": action,
            "description": description,
            "data": data or {}
        }
        self._log_entry(entry)
        return entry
    
    def log_error(self, error_type, details=None):
        """Log an error (matches session_logger.log_error)"""
        import traceback
        entry = {
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "session": self.session_id,
            "unique_id": f"{self.session_id}_{self.start_time.strftime('%H%M%S')}",
            "error_type": error_type,
            "details": details or str(error_type),
            "traceback": traceback.format_exc()
        }
        self._log_entry(entry)
        return entry
    
    def log_screenshot(self, reason, tag=None, filepath=None):
        """Log screenshot (matches session_logger.log_screenshot)"""
        entry = {
            "type": "screenshot",
            "timestamp": datetime.now().isoformat(),
            "session": self.session_id,
            "unique_id": f"{self.session_id}_{self.start_time.strftime('%H%M%S')}",
            "reason": reason,
            "tag": tag,
            "filepath": filepath
        }
        self._log_entry(entry)
        return entry
    
    def verify_other_loggers(self):
        """Compare this log with session_logger to verify it's working"""
        results = {
            "file_log_count": self.message_count,
            "redis_chat_count": 0,
            "session_logger_count": 0,
            "discrepancy": False
        }
        
        # Check Redis chat:history
        if self.redis_ok:
            try:
                results["redis_chat_count"] = self.redis.llen("chat:history")
            except:
                pass
            
            # Check session logger actions
            try:
                sessions = self.redis.hgetall("sessions:active")
                for sid, data in sessions.items():
                    actions = self.redis.lrange(f"session:{sid}:actions", 0, -1)
                    results["session_logger_count"] += len(actions)
            except:
                pass
        
        # Calculate discrepancy
        if results["file_log_count"] != results["redis_chat_count"]:
            results["discrepancy"] = True
            results["difference"] = results["redis_chat_count"] - results["file_log_count"]
        
        return results
    
    def get_summary(self):
        """Get logging summary"""
        return {
            "logger_session": self.session_id,
            "messages_logged": self.message_count,
            "redis_connected": self.redis_ok,
            "log_file": CONVERSATION_LOG
        }
    
    def close(self):
        """Log shutdown"""
        self._log_entry({
            "type": "logger_shutdown",
            "session": self.session_id,
            "total_messages": self.message_count,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "timestamp": datetime.now().isoformat()
        })


def auto_monitor():
    """Run continuous monitoring - logs all conversation changes"""
    logger = ConversationLogger()
    
    print(f"Conversation Logger Started")
    print(f"Session: {logger.session_id}")
    print(f"Log file: {CONVERSATION_LOG}")
    print(f"Redis: {'Connected' if logger.redis_ok else 'Not available'}")
    print()
    print("Monitoring chat:history for new messages...")
    print("Press Ctrl+C to stop")
    print()
    
    last_count = 0
    
    try:
        while True:
            if logger.redis_ok:
                try:
                    current_count = logger.redis.llen("chat:history")
                    
                    if current_count > last_count:
                        # New messages detected!
                        new_messages = logger.redis.lrange("chat:history", -(current_count - last_count), -1)
                        
                        for msg_json in new_messages:
                            try:
                                msg = json.loads(msg_json)
                                role = msg.get("role", "?")
                                text = msg.get("message", "")[:80].replace('\n', ' ')
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] {role}: {text}")
                                
                                # Log to our backup
                                logger.log(role, msg.get("message", ""))
                            except:
                                pass
                        
                        last_count = current_count
                        
                except:
                    pass
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopping logger...")
        verification = logger.verify_other_loggers()
        print(f"\nVerification: {verification}")
        logger.close()
        print("Logger stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--monitor":
        auto_monitor()
    else:
        # Test run
        logger = ConversationLogger()
        
        print("Testing conversation logger...")
        
        # Simulate user message
        logger.log_user("This is a test user message")
        
        # Simulate assistant response
        logger.log_assistant("This is a test assistant response - verifying backup logging works!")
        
        # Verify
        summary = logger.get_summary()
        print(f"\nLogger summary: {summary}")
        
        verification = logger.verify_other_loggers()
        print(f"\nVerification against other loggers: {verification}")
        
        # Show recent entries
        print(f"\nRecent entries in {CONVERSATION_LOG}:")
        with open(CONVERSATION_LOG, "r") as f:
            lines = f.readlines()
            for line in lines[-3:]:
                entry = json.loads(line)
                print(f"  {entry.get('type')}: {entry.get('role', '')} - {entry.get('message', '')[:40]}...")
        
        logger.close()
        print("\n[OK] Conversation logger test complete!")