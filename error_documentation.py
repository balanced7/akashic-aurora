"""
Error and Fault Documentation System
======================================
Documents all errors by system and type for easier troubleshooting.

Features:
- Connection pooling for Redis
- Caching for get_summary()
- Filter function instead of broken .filter() method

Usage:
    from error_documentation import ErrorDoc
    
    doc = ErrorDoc()
    doc.log_error("launcher", "python_not_found", "Python not found in PATH")
    doc.log_error("verification", "window_not_found", "Window didn't open")
    doc.get_errors_by_system("launcher")
    doc.get_errors_by_type("python")
"""
import json
import os
import time
import redis
from datetime import datetime
from collections import defaultdict

ERROR_LOG = r"E:\AI-Setup\session_logs\errors_and_faults.jsonl"

# Connection pool - reuse connections
_redis_pool = None

def _get_redis_pool():
    """Get or create Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True, max_connections=10)
    return _redis_pool

def _get_redis_client():
    """Get Redis client from pool"""
    try:
        r = redis.Redis(connection_pool=_get_redis_pool())
        r.ping()
        return r, True
    except:
        return None, False


class ErrorDoc:
    """Categorized error documentation"""
    
    # Define error categories
    SYSTEMS = [
        "launcher",      # OpenCode_primed.bat issues
        "verification",  # Launch verification failures
        "logging",      # Session/backup logger issues
        "ocr",          # OCR and screen reading issues
        "ui",           # UI inspection/automation issues
        "redis",        # Redis connection/issues
        "session",      # Session management issues
        "system",       # System-level issues
    ]
    
    ERROR_TYPES = [
        "python_not_found",
        "window_not_found", 
        "process_failed",
        "timeout",
        "connection_failed",
        "file_not_found",
        "parse_error",
        "permission_denied",
        "unknown"
    ]
    
    # Class-level cache for get_summary
    _summary_cache = None
    _summary_cache_time = 0
    CACHE_TTL = 60  # seconds
    
    def __init__(self):
        self.redis, self.redis_available = _get_redis_client()
    
    def _log_entry(self, entry):
        """Write to error log file"""
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        # Also log to Redis for other LLMs
        if self.redis_available:
            try:
                self.redis.rpush("errors:faults", json.dumps(entry))
                self.redis.ltrim("errors:faults", -100, -1)
            except:
                pass
    
    def log_error(self, system, error_type, details, severity="medium"):
        """
        Log an error with categorization.
        
        Args:
            system: One of launcher, verification, logging, ocr, ui, redis, session, system
            error_type: One of python_not_found, window_not_found, etc.
            details: Description of the error
            severity: low, medium, high, critical
        """
        # Validate inputs
        if system not in self.SYSTEMS:
            system = "system"
        if error_type not in self.ERROR_TYPES:
            error_type = "unknown"
        
        entry = {
            "type": "error_doc",
            "system": system,
            "error_type": error_type,
            "severity": severity,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "session": "unknown"
        }
        
        # Try to get current session
        if self.redis_available:
            try:
                sessions = self.redis.hgetall("sessions:active")
                for sid, data in sessions.items():
                    info = json.loads(data)
                    if info.get("status") == "active":
                        entry["session"] = sid
                        break
            except:
                pass
        
        # Invalidate cache on new error
        ErrorDoc._summary_cache = None
        
        self._log_entry(entry)
        return entry
    
    def get_errors_by_system(self, system=None):
        """Get errors filtered by system"""
        errors = []
        if os.path.exists(ERROR_LOG):
            with open(ERROR_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "error_doc":
                            if system is None or entry.get("system") == system:
                                errors.append(entry)
                    except:
                        pass
        return errors
    
    def get_errors_by_type(self, error_type):
        """Get errors filtered by type - FIXED: was using .filter() on list"""
        all_errors = self.get_errors_by_system()
        return [e for e in all_errors if e.get("error_type") == error_type]
    
    def get_recent_errors(self, count=10):
        """Get most recent errors"""
        all_errors = self.get_errors_by_system()
        return all_errors[-count:] if len(all_errors) >= count else all_errors
    
    def get_summary(self, use_cache=True):
        """
        Get error summary by system and severity.
        Results cached for 60 seconds to avoid repeated file reads.
        """
        # Check cache
        if use_cache and ErrorDoc._summary_cache is not None:
            cache_age = time.time() - ErrorDoc._summary_cache_time
            if cache_age < ErrorDoc.CACHE_TTL:
                return ErrorDoc._summary_cache
        
        errors = self.get_errors_by_system()
        
        summary = {
            "total": len(errors),
            "by_system": defaultdict(int),
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "cached_at": datetime.now().isoformat(),
            "cache_age_seconds": 0
        }
        
        for e in errors:
            summary["by_system"][e.get("system", "unknown")] += 1
            summary["by_type"][e.get("error_type", "unknown")] += 1
            summary["by_severity"][e.get("severity", "unknown")] += 1
        
        # Convert defaultdict to dict for JSON serialization
        summary["by_system"] = dict(summary["by_system"])
        summary["by_type"] = dict(summary["by_type"])
        summary["by_severity"] = dict(summary["by_severity"])
        
        # Update cache
        ErrorDoc._summary_cache = summary
        ErrorDoc._summary_cache_time = time.time()
        
        return summary
    
    def clear_cache(self):
        """Manually clear the summary cache"""
        ErrorDoc._summary_cache = None
        ErrorDoc._summary_cache_time = 0
    
    def document_known_issues(self):
        """Document known issues from this session"""
        # Launcher issue - window didn't open properly
        self.log_error("launcher", "window_not_found", 
                      "Primed launcher opened new window but window had 'Python not found' error - PATH issue in new terminal context",
                      severity="high")
        
        # Session logging not persisting
        self.log_error("logging", "file_not_found",
                      "Session logger created per-session files but they were empty - file flush issue",
                      severity="high")
        
        # Verification didn't catch launcher error
        self.log_error("verification", "timeout",
                      "Launch verification didn't detect 'Python not found' error in new window - OCR may not have caught it",
                      severity="medium")
        
        print("Documented known issues from this session")


def create_error_handling_guide():
    """Create a guide for handling different error types"""
    guide = """
# Error Handling Guide

## By System

### Launcher Issues
- **Problem**: New terminal window doesn't open or has errors
- **Check**: Look for "Python was not found" in terminal output
- **Fix**: Use full path to Python in BAT file (already done)
- **Verify**: Run launch_verifier with extended timeout

### Verification Issues  
- **Problem**: Launch appears to succeed but actually fails
- **Check**: Use both process check AND screen OCR
- **Fix**: Check for error keywords in screen text
- **Log**: Use log_error with "verification" system

### Logging Issues
- **Problem**: Logs not persisting to files
- **Check**: File exists but is empty
- **Fix**: Use f.flush() and os.fsync() after writes (already done)
- **Verify**: Check file immediately after log call

### OCR Issues
- **Problem**: Can't read screen text
- **Check**: Tesseract installed, screen has visible text
- **Fix**: Try multiple OCR methods (tesseract, windows, naturo)
- **Log**: Use log_error with "ocr" system

### UI Issues
- **Problem**: Naturo can't find elements
- **Check**: Window is accessible, not minimized
- **Fix**: Use different backend (uia, msaa, cdp)
- **Log**: Use log_error with "ui" system

## By Error Type

| Error Type | Common Cause | Solution |
|------------|--------------|----------|
| python_not_found | PATH issue in new terminal | Use full path |
| window_not_found | Window not created | Check process list |
| process_failed | App crashed on launch | Check error output |
| timeout | Operation took too long | Increase timeout |
| connection_failed | Redis not running | Check docker status |
"""
    
    # Save guide
    guide_path = r"E:\AI-Setup\ERROR_HANDLING_GUIDE.md"
    with open(guide_path, "w") as f:
        f.write(guide)
    
    return guide_path


if __name__ == "__main__":
    doc = ErrorDoc()
    
    print("=== ERROR DOCUMENTATION SYSTEM ===\n")
    
    # Document known issues
    doc.document_known_issues()
    
    # Get summary (uses cache)
    summary = doc.get_summary()
    print(f"\nError Summary (cached):")
    print(f"  Total: {summary['total']}")
    print(f"  By System: {summary['by_system']}")
    print(f"  By Severity: {summary['by_severity']}")
    
    # Create guide
    guide_path = create_error_handling_guide()
    print(f"\nCreated: {guide_path}")
    
    print("\n[OK] Error documentation system ready!")
