"""
Compliance Logger - Auto-logging for Directive Compliance
=====================================================
Ensures all actions are properly logged with required metadata.

Usage:
    from compliance_logger import get_compliance_logger
    
    cl = get_compliance_logger()
    
    # Log with verification
    cl.log_action("deploy", "Deploying service", {
        "service": "redis",
        "verified": True,
        "health_checks": ["redis_ping", "memory_check"]
    })
    
    # Log health check
    cl.log_health_check("redis", True, {"memory": "OK"})
    
    # Log verification
    cl.log_verification("test_inference", True, {"latency_ms": 50})
"""

import sys
sys.path.insert(0, r'E:\AI-Setup')

from session_logger import log
from datetime import datetime


class ComplianceLogger:
    """
    Ensures all log entries comply with OBSERVABILITY directive.
    Every log entry MUST have a data dict with meaningful content.
    """
    
    _instance = None
    
    def __init__(self):
        self.action_count = 0
        self.verification_count = 0
        self.health_check_count = 0
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def log_action(self, action: str, description: str, data: dict, source: str = "system"):
        """
        Log an action with REQUIRED data dict.
        OBSERVABILITY: Every action must have metadata.
        """
        if not data or not isinstance(data, dict):
            raise ValueError(f"OBSERVABILITY VIOLATION: log_action('{action}') requires data dict, got: {data}")
        
        # Add compliance metadata
        data["_logged_at"] = datetime.now().isoformat()
        data["_action_seq"] = self.action_count
        self.action_count += 1
        
        log(action, description, data=data, source=source)
    
    def log_verification(self, verification_type: str, result: bool, metrics: dict = None, source: str = "system"):
        """
        Log a verification action.
        Addresses TEST_BEFORE_DEPLOY directive.
        """
        data = {
            "verification_type": verification_type,
            "result": result,
            "passed": result,
            "metrics": metrics or {}
        }
        
        self.verification_count += 1
        data["_verification_seq"] = self.verification_count
        
        log("verify", f"{verification_type}: {'PASS' if result else 'FAIL'}", 
            data=data, source=source)
    
    def log_health_check(self, component: str, healthy: bool, details: dict = None, source: str = "system"):
        """
        Log a health check.
        Addresses HEALTH_CHECKS directive.
        """
        data = {
            "component": component,
            "healthy": healthy,
            "status": "UP" if healthy else "DOWN",
            "details": details or {}
        }
        
        self.health_check_count += 1
        data["_health_check_seq"] = self.health_check_count
        
        log("health_check", f"{component}: {'UP' if healthy else 'DOWN'}", 
            data=data, source=source)
    
    def log_failure(self, error_type: str, error_message: str, traceback: str = None, 
                   context: dict = None, source: str = "system"):
        """
        Log an error with full failure mode analysis.
        Addresses FAILURE_MODE_ANALYSIS directive.
        """
        data = {
            "error_type": error_type,
            "error_message": error_message,
            "has_traceback": traceback is not None,
            "traceback": traceback or "N/A",
            "context": context or {}
        }
        
        log("error", f"{error_type}: {error_message}", 
            data=data, source=source)
    
    def log_deployment(self, target: str, success: bool, verification_results: dict = None, 
                      source: str = "system"):
        """
        Log a deployment with verification.
        Addresses TEST_BEFORE_DEPLOY directive.
        """
        data = {
            "target": target,
            "success": success,
            "verification_results": verification_results or {},
            "verified": verification_results is not None and len(verification_results) > 0
        }
        
        log("deploy", f"{target}: {'SUCCESS' if success else 'FAILED'}", 
            data=data, source=source)
    
    def get_compliance_stats(self) -> dict:
        """Get compliance statistics"""
        return {
            "actions_logged": self.action_count,
            "verifications_logged": self.verification_count,
            "health_checks_logged": self.health_check_count,
            "compliance_rate": "100%" if self.action_count == self.verification_count else "CHECK REQUIRED"
        }


# Global instance
_compliance_logger = None

def get_compliance_logger() -> ComplianceLogger:
    """Get the compliance logger singleton"""
    global _compliance_logger
    if _compliance_logger is None:
        _compliance_logger = ComplianceLogger()
    return _compliance_logger


# Quick compliance check
def check_my_compliance():
    """Check if current session is compliant"""
    cl = get_compliance_logger()
    stats = cl.get_compliance_stats()
    
    print("\n" + "="*50)
    print("COMPLIANCE STATUS")
    print("="*50)
    print(f"  Actions logged: {stats['actions_logged']}")
    print(f"  Verifications: {stats['verifications_logged']}")
    print(f"  Health checks:  {stats['health_checks_logged']}")
    print(f"  Rate: {stats['compliance_rate']}")
    print("="*50 + "\n")
    
    return stats


if __name__ == "__main__":
    # Test
    cl = get_compliance_logger()
    
    # These will raise if data is missing
    cl.log_action("test", "Testing compliance", {"test": True})
    cl.log_verification("inference", True, {"latency_ms": 50})
    cl.log_health_check("redis", True, {"memory": "OK"})
    cl.log_failure("ValueError", "Invalid input", "traceback here")
    cl.log_deployment("api", True, {"health_check": "OK"})
    
    check_my_compliance()
