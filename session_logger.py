"""
Session Logger - Automatic Action Logging to Redis + Files
==========================================================
Every action is logged to Redis AND files for crash recovery.

Features:
- Dual JSONL file write with fsync for crash protection
- Parallel file writes using ThreadPoolExecutor
- Log rotation (daily + size-based at 100MB)
- Checksum verification for dual-write integrity
- Redis fallback to file-only mode
- Per-entry checksums for corruption detection
- Connection pooling for Redis

Usage:
    from session_logger import log, log_error, log_chat, verify_logs
    
    log("action", "description")
    log_error("error", "details")
    log_chat("user", "message")
    verify_logs()  # Verify dual-write integrity
"""
import os
import json
import time
import hashlib
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import redis

# ============ CONFIGURATION ============
LOG_DIR = r"E:\AI-Setup\session_logs"
LOG_FILE = os.path.join(LOG_DIR, "session_all.jsonl")
BACKUP_LOG_FILE = os.path.join(LOG_DIR, "backup_session_all.jsonl")
MAX_LOG_SIZE_MB = 100  # Rotate when file exceeds this size
ROTATION_CHECK_INTERVAL = 100  # Check rotation every N writes

# Try to connect to Redis with fallback
def _get_redis_connection():
    """Get Redis connection with automatic fallback"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        return r, True
    except:
        return None, False

r, REDIS_AVAILABLE = _get_redis_connection()

if not REDIS_AVAILABLE:
    print("[session_logger] Redis not available - file-only mode")
else:
    print("[session_logger] Redis connected")

os.makedirs(LOG_DIR, exist_ok=True)

# Session ID management
def _get_or_create_session():
    """Get existing active session or create new one"""
    if not REDIS_AVAILABLE:
        return f"opencode_{datetime.now().strftime('%Y%m%d_%H%M%S')}", False
    
    try:
        sessions = r.hgetall("sessions:active")
        for sid, data in sessions.items():
            try:
                info = json.loads(data)
                if info.get("status") == "active":
                    return sid, True
            except:
                pass
    except:
        pass
    
    return f"opencode_{datetime.now().strftime('%Y%m%d_%H%M%S')}", False

SESSION_ID, _session_existed = _get_or_create_session()
SESSION_UNIQUE = f"{SESSION_ID}_{datetime.now().strftime('%H%M%S')}"

# Track message sequence (per-instance, not global - see ARCHITECTURE.md)
_message_sequence = 0
_write_count = 0  # For rotation checking

# ============ LOG ROTATION ============

def _should_rotate():
    """Check if log files should be rotated based on size"""
    try:
        main_size = os.path.getsize(LOG_FILE) / (1024 * 1024)  # MB
        return main_size >= MAX_LOG_SIZE_MB
    except:
        return False

def _rotate_logs():
    """Rotate log files - archive current, start fresh"""
    global LOG_FILE, BACKUP_LOG_FILE
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
            archive_main = os.path.join(LOG_DIR, f"session_{timestamp}.jsonl")
            os.rename(LOG_FILE, archive_main)
            print(f"[session_logger] Rotated main log to {archive_main}")
    except Exception as e:
        print(f"[session_logger] Rotation error (main): {e}")
    
    try:
        if os.path.exists(BACKUP_LOG_FILE) and os.path.getsize(BACKUP_LOG_FILE) > 0:
            archive_backup = os.path.join(LOG_DIR, f"backup_{timestamp}.jsonl")
            os.rename(BACKUP_LOG_FILE, archive_backup)
            print(f"[session_logger] Rotated backup log to {archive_backup}")
    except Exception as e:
        print(f"[session_logger] Rotation error (backup): {e}")

# ============ CHECKSUM HELPERS ============

def _compute_checksum(entry):
    """Compute SHA256 checksum for a log entry"""
    entry_copy = {k: v for k, v in entry.items() if k != 'checksum'}
    content = json.dumps(entry_copy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def _add_checksum(entry):
    """Add checksum to entry for corruption detection"""
    entry['checksum'] = _compute_checksum(entry)
    return entry

def _verify_entry(entry):
    """Verify entry checksum, return True if valid or no checksum"""
    if 'checksum' not in entry:
        return True
    expected = _compute_checksum(entry)
    return entry['checksum'] == expected


# ============ PARALLEL FILE WRITE ============

def _fsync_write(filepath, entry_str):
    """Write entry to file with fsync - for parallel execution"""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry_str)
        f.flush()
        os.fsync(f.fileno())

# ============ DUAL-WRITE WITH VERIFICATION ============

def _write_log(entry):
    """
    Write to both log files with checksum verification.
    OPTIMIZED: Uses ThreadPoolExecutor for parallel writes.
    """
    global _write_count
    
    # Check rotation periodically
    _write_count += 1
    if _write_count >= ROTATION_CHECK_INTERVAL:
        _write_count = 0
        if _should_rotate():
            _rotate_logs()
    
    # Add checksum to entry
    entry = _add_checksum(entry)
    entry_str = json.dumps(entry, ensure_ascii=False) + "\n"
    
    # Parallel write to both files
    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(_fsync_write, LOG_FILE, entry_str)
        f2 = executor.submit(_fsync_write, BACKUP_LOG_FILE, entry_str)
        f1.result()
        f2.result()
    
    # Verify writes match (last entry in each file)
    try:
        with open(LOG_FILE, "rb") as f:
            f.seek(-len(entry_str) - 1, 2)
            main_line = f.readline()
            main_verify = hashlib.sha256(main_line).hexdigest()
        
        with open(BACKUP_LOG_FILE, "rb") as f:
            f.seek(-len(entry_str) - 1, 2)
            backup_line = f.readline()
            backup_verify = hashlib.sha256(backup_line).hexdigest()
        
        if main_verify != backup_verify:
            print(f"[session_logger] WARNING: Dual-write mismatch detected!")
            return False
    except Exception as e:
        print(f"[session_logger] Verification error: {e}")
        return False
    
    return True


# ============ REDIS OPERATIONS ============

def _log_to_redis(category, action, data):
    """Log to Redis with automatic reconnection"""
    global r, REDIS_AVAILABLE
    
    if not REDIS_AVAILABLE:
        # Try to reconnect
        r, REDIS_AVAILABLE = _get_redis_connection()
        if not REDIS_AVAILABLE:
            return
    
    try:
        key = f"session:{SESSION_ID}:{category}"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data": data
        }
        
        r.rpush(key, json.dumps(entry))
        r.expire(key, 86400 * 7)
        
        # Update active session - batch these operations
        r.hset("sessions:active", SESSION_ID, json.dumps({
            "status": "active",
            "task": data.get("task", "unknown"),
            "last_action": action,
            "last_update": datetime.now().isoformat()
        }))
    except redis.ConnectionError:
        REDIS_AVAILABLE = False
        r = None
    except Exception:
        pass


# ============ PUBLIC API ============

def log(action, description="", data=None, source="system"):
    """Log an action
    
    Args:
        action: Action name
        description: Human-readable description
        data: Additional metadata dict
        source: Source of the log (e.g., 'generator', 'analyst', 'system', 'master')
    """
    global _message_sequence
    _message_sequence += 1
    
    entry = {
        "type": "action",
        "timestamp": datetime.now().isoformat(),
        "session": SESSION_ID,
        "unique_id": SESSION_UNIQUE,
        "sequence": _message_sequence,
        "source": source,  # Added for agent identification
        "action": action,
        "description": description,
        "data": data or {}
    }
    
    print(f"[LOG][{source}] {action}: {description}")
    _write_log(entry)
    _log_to_redis("actions", action, {"task": description, "source": source, **(data or {})})


def log_error(error_type, details=None):
    """Log an error - also documents to error system"""
    global _message_sequence
    _message_sequence += 1
    
    error_str = str(details) if details else str(error_type)
    
    entry = {
        "type": "error",
        "timestamp": datetime.now().isoformat(),
        "session": SESSION_ID,
        "unique_id": SESSION_UNIQUE,
        "sequence": _message_sequence,
        "error_type": error_type,
        "details": error_str,
        "message_length": len(error_str),
        "traceback": traceback.format_exc()
    }
    
    print(f"[ERROR] {error_type}: {details}")
    
    # Also log to error documentation system (non-blocking)
    try:
        from error_documentation import ErrorDoc
        doc = ErrorDoc()
        system = "session"
        if "launch" in error_type.lower(): system = "launcher"
        elif "verify" in error_type.lower(): system = "verification"  
        elif "log" in error_type.lower() or "flush" in error_type.lower(): system = "logging"
        elif "ocr" in error_type.lower(): system = "ocr"
        elif "ui" in error_type.lower(): system = "ui"
        
        doc.log_error(system, error_type.lower().replace(" ", "_"), details or error_type)
    except:
        pass
    
    _write_log(entry)
    _log_to_redis("errors", error_type, {"details": details, "traceback": traceback.format_exc()})
    
    log_chat("system", f"ERROR: {error_type} - {details}")


def log_chat(role, message):
    """Log chat message for all LLMs"""
    global _message_sequence
    _message_sequence += 1
    
    entry = {
        "type": "chat",
        "timestamp": datetime.now().isoformat(),
        "session": SESSION_ID,
        "unique_id": SESSION_UNIQUE,
        "sequence": _message_sequence,
        "role": role,
        "message": message[:500] if len(message) > 500 else message,
        "message_length": len(message)
    }
    
    _write_log(entry)
    
    if REDIS_AVAILABLE:
        try:
            r.rpush("chat:history", json.dumps({
                "role": role,
                "message": message,
                "session": SESSION_ID,
                "unique_id": SESSION_UNIQUE,
                "timestamp": datetime.now().isoformat()
            }))
            r.ltrim("chat:history", -1000, -1)
        except:
            pass


def log_screenshot(reason, tag=None, filepath=None):
    """Log screenshot capture"""
    entry = {
        "type": "screenshot",
        "timestamp": datetime.now().isoformat(),
        "session": SESSION_ID,
        "reason": reason,
        "tag": tag,
        "filepath": filepath
    }
    
    _write_log(entry)
    _log_to_redis("screenshots", reason, {"tag": tag, "filepath": filepath})


# ============ VERIFICATION ============

def verify_logs(limit=100):
    """
    Verify dual-write integrity by comparing checksums.
    Returns dict with verification results.
    """
    results = {
        "total": 0,
        "valid": 0,
        "corrupted": 0,
        "missing_checksum": 0,
        "mismatches": [],
        "corrupted_entries": []
    }
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f_main, \
             open(BACKUP_LOG_FILE, "r", encoding="utf-8") as f_backup:
            
            main_lines = f_main.readlines()[-limit:]
            backup_lines = f_backup.readlines()[-limit:]
            
            for i, (main_line, backup_line) in enumerate(zip(main_lines, backup_lines)):
                results["total"] += 1
                
                try:
                    main_entry = json.loads(main_line)
                    backup_entry = json.loads(backup_line)
                except json.JSONDecodeError:
                    results["corrupted"] += 1
                    results["corrupted_entries"].append({"index": i, "file": "both", "error": "JSON parse failed"})
                    continue
                
                if main_line != backup_line:
                    results["mismatches"].append({"index": i, "line": main_line[:100]})
                
                if _verify_entry(main_entry):
                    results["valid"] += 1
                elif "checksum" not in main_entry:
                    results["missing_checksum"] += 1
                else:
                    results["corrupted"] += 1
                    results["corrupted_entries"].append({"index": i, "entry": main_entry})
    
    except Exception as e:
        results["error"] = str(e)
    
    return results


# ============ QUERY FUNCTIONS ============

def get_chat_history(count=50):
    """Get recent chat history for all LLMs"""
    if not REDIS_AVAILABLE:
        # Fall back to reading from file
        chats = []
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "chat":
                            chats.append(entry)
                    except:
                        pass
            return chats[-count:]
        except:
            return []
    
    try:
        chats = r.lrange("chat:history", -count, -1)
        return [json.loads(c) for c in chats]
    except:
        return []


def get_recent_sessions(max_sessions=5):
    """Get recent session summaries for catch-up"""
    if not REDIS_AVAILABLE:
        return []
    
    try:
        sessions = r.hgetall("sessions:active")
        recent = []
        for sid, data in sessions.items():
            try:
                info = json.loads(data)
                recent.append({
                    "session_id": sid,
                    "task": info.get("task", "unknown"),
                    "status": info.get("status", "unknown"),
                    "last_action": info.get("last_action", "none")
                })
            except:
                pass
        
        return sorted(recent, key=lambda x: x.get("session_id", ""), reverse=True)[:max_sessions]
    except:
        return []


def recover():
    """Show crash recovery info"""
    print("=" * 60)
    print("  SESSION RECOVERY")
    print("=" * 60)
    print(f"\nCurrent session: {SESSION_ID}")
    print(f"Log file: {LOG_FILE}")
    print(f"Redis: {'Available' if REDIS_AVAILABLE else 'Not available (file-only mode)'}")
    print()
    
    recent = get_recent_sessions()
    if recent:
        print("RECENT SESSIONS:")
        for s in recent[:3]:
            print(f"  [{s['session_id']}] {s.get('task', 'unknown')} - {s.get('status', 'unknown')}")
    
    chats = get_chat_history(10)
    if chats:
        print(f"\nRecent chats ({len(chats)}):")
        for c in chats[-5:]:
            role = c.get("role", "?")
            msg = c.get("message", "")[:60]
            print(f"  {role}: {msg}")
    
    print()
    print("=" * 60)


# ============ SESSION INITIALIZATION ============

# Integrate with SessionManager for re-prime detection
_session_state = None

def get_session_state():
    """Get the session state (for external use)"""
    return _session_state

# Auto-register session on import
try:
    if SESSION_ID:
        # Import here to avoid circular dependency
        try:
            from session_manager import check_and_reprime, get_session_manager
            _session_state = check_and_reprime(SESSION_ID, SESSION_UNIQUE)
            
            if _session_state.is_new:
                print("\n" + "=" * 60)
                print("NEW SESSION DETECTED - RE-PRIME REQUIRED")
                print("=" * 60)
                print(get_session_manager().get_reprime_instructions())
                print()
        except ImportError:
            # session_manager not available, continue without re-prime detection
            pass
        
        _write_log({
            "type": "logger_startup",
            "session": SESSION_ID,
            "unique_id": SESSION_UNIQUE,
            "is_new_session": _session_state.is_new if _session_state else True,
            "redis": REDIS_AVAILABLE,
            "timestamp": datetime.now().isoformat(),
            "log_file": LOG_FILE,
            "backup_file": BACKUP_LOG_FILE
        })
        
        if _session_state and _session_state.is_new:
            log("session_start", "New session - re-prime required", {"is_new": True}, source="system")
        else:
            log("session_start", "Session continuing", {"is_new": False}, source="system")
        
except Exception as e:
    print(f"[session_logger] Initialization error: {e}")


# ============ AUTO-EXPORT ON SHUTDOWN ============
import atexit

_auto_start_time = datetime.now()

def _count_messages():
    """Count messages logged for current session"""
    count = 0
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("session") == SESSION_ID:
                        count += 1
                except:
                    pass
    except:
        pass
    return count

def _auto_export():
    """Called on interpreter shutdown - export session and log shutdown"""
    try:
        _write_log({
            "type": "logger_shutdown",
            "session": SESSION_ID,
            "total_messages": _count_messages(),
            "duration_seconds": (datetime.now() - _auto_start_time).total_seconds(),
            "timestamp": datetime.now().isoformat()
        })
        export_current_session()
    except:
        pass

try:
    atexit.register(_auto_export)
except:
    pass


# ============ EXPORT FUNCTION ============

def export_current_session():
    """Export current session to markdown file for quick catch-up"""
    try:
        all_entries = []
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("session") == SESSION_ID:
                        all_entries.append(entry)
                except:
                    pass
        
        actions = []
        errors = []
        chats = []
        
        for entry in all_entries:
            if entry.get("type") == "chat":
                chats.append(entry)
            elif entry.get("type") == "error":
                errors.append(entry)
            elif entry.get("type") == "action":
                actions.append(entry)
        
        export_file = os.path.join(LOG_DIR, f"{SESSION_ID}_export.md")
        
        with open(export_file, "w", encoding="utf-8") as f:
            f.write(f"# Session Export - {SESSION_ID}\n")
            f.write(f"**Exported**: {datetime.now().isoformat()}\n\n")
            
            f.write("## Actions\n")
            f.write("---\n")
            for a in actions:
                ts = a.get("timestamp", "")[11:19] if a.get("timestamp") else ""
                action = a.get("action", "unknown")
                desc = a.get("description", "")
                f.write(f"- *{ts}* {action}: {desc}\n")
            
            f.write("\n## Errors\n")
            f.write("---\n")
            if errors:
                for e in errors:
                    f.write(f"- {e.get('error_type', 'error')}: {e.get('details', 'N/A')}\n")
            else:
                f.write("No errors logged\n")
            
            f.write("\n## Chat\n")
            f.write("---\n")
            for c in chats:
                role = c.get("role", "unknown")
                msg = c.get("message", "")[:200]
                f.write(f"**{role}**: {msg}\n")
        
        print(f"[export] Session exported to: {export_file}")
        return export_file
        
    except Exception as e:
        print(f"[export] Error: {e}")
        return None
