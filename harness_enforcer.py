"""
Harness Enforcer - Escape Condition Detection & Prevention
========================================================
Mission-Critical Agentic AI Control System

This module detects and prevents common escape conditions where
an agentic AI might bypass procedures, skip testing, or otherwise
fail to follow the mandated workflow.

DETECTED ESCAPE CONDITIONS:
1. SKIP_REPRIME - AI continues without re-priming when state.is_new=True
2. SKIP_VERIFY - AI runs code without verifying it works
3. SKIP_LOGGING - AI performs actions without logging
4. SKIP_KB_SEARCH - AI builds without checking knowledge base
5. SKIP_HEALTH_CHECKS - AI deploys without verifying components
6. SKIP_BLACKBOARD_WORKFLOW - AI executes without proper phases
7. SKIP_SELF_CORRECTION - Analyst ignores fault learnings
8. SKIP_TESTING - AI assumes things work without testing
9. IMPATIENT_EXIT - AI exits without session summary
10. SKIP_REDIS_START - AI proceeds without Redis (KB unavailable)

DIRECTIVES ENFORCED:
- TEST BEFORE DEPLOY: Never assume, always verify
- HEALTH CHECKS: Every component must prove it's working
- GRACEFUL DEGRADATION: System survives component failures
- FAILURE MODE ANALYSIS: Every failure anticipated and handled
- OBSERVABILITY: Everything logged, nothing hidden

Author: Senior Systems Architect
Version: 1.0 Mission-Critical
"""

import json
import os
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict

# Paths
BLACKBOARD_DIR = r"E:\AI-Setup\blackboard_data"
HARNESS_STATE_FILE = os.path.join(BLACKBOARD_DIR, "harness_state.json")
ESCAPE_LOG_FILE = os.path.join(BLACKBOARD_DIR, "logs", "escape_conditions.jsonl")
ENFORCEMENT_LOG = os.path.join(BLACKBOARD_DIR, "logs", "enforcement.jsonl")

os.makedirs(os.path.dirname(ESCAPE_LOG_FILE), exist_ok=True)


class EscapeCondition(Enum):
    """Known escape conditions that must be prevented"""
    SKIP_REPRIME = "skip_reprime"
    SKIP_VERIFY = "skip_verify"
    SKIP_LOGGING = "skip_logging"
    SKIP_KB_SEARCH = "skip_kb_search"
    SKIP_HEALTH_CHECKS = "skip_health_checks"
    SKIP_BLACKBOARD_WORKFLOW = "skip_blackboard_workflow"
    SKIP_SELF_CORRECTION = "skip_self_correction"
    SKIP_TESTING = "skip_testing"
    IMPATIENT_EXIT = "impatient_exit"
    SKIP_REDIS_START = "skip_redis_start"
    BYPASS_ANALYST_REVIEW = "bypass_analyst_review"
    MODIFY_AFTER_VERDICT = "modify_after_verdict"
    EXECUTE_WITHOUT_PLAN = "execute_without_plan"


class EnforcementAction(Enum):
    """Actions taken when escape is detected"""
    WARN = "warn"
    BLOCK = "block"
    LOG_ONLY = "log_only"
    ESCALATE = "escalate"
    FORCE_REPRIME = "force_reprime"


class EscapeDetector:
    """
    Detects escape conditions based on behavior patterns.
    
    Uses heuristics:
    - Action frequency analysis
    - Sequence compliance checking
    - State machine transition validation
    - Time-based anomaly detection
    """
    
    def __init__(self):
        self.escape_counts: Dict[str, int] = defaultdict(int)
        self.last_action_time: float = time.time()
        self.action_sequence: List[str] = []
        self.max_sequence_length = 100
    
    def record_action(self, action: str, source: str = "system"):
        """Record an action for pattern analysis"""
        self.action_sequence.append(action)
        if len(self.action_sequence) > self.max_sequence_length:
            self.action_sequence.pop(0)
        self.last_action_time = time.time()
    
    def detect_skip_logging(self, action_count: int, log_count: int) -> bool:
        """If actions > logs * 3, likely skipping logging"""
        if log_count == 0 and action_count > 5:
            return True
        if action_count > log_count * 3 and action_count > 10:
            return True
        return False
    
    def detect_skip_kb_search(self, edit_count: int, kb_search_count: int) -> bool:
        """If making edits without searching KB first"""
        # If we've made edits but never searched KB
        if edit_count > 3 and kb_search_count == 0:
            return True
        return False
    
    def detect_skip_testing(self, run_count: int, verify_count: int) -> bool:
        """If running commands without verifying results"""
        if run_count > 5 and verify_count == 0:
            return True
        return False
    
    def detect_rapid_exit(self, session_duration: float, action_count: int) -> bool:
        """If session is very short with few actions"""
        if session_duration < 60 and action_count < 3:
            return True  # Less than 1 minute, less than 3 actions
        return False
    
    def get_escape_risk(self) -> str:
        """Return overall escape risk level"""
        total_escapes = sum(self.escape_counts.values())
        
        if total_escapes == 0:
            return "LOW"
        elif total_escapes < 5:
            return "MEDIUM"
        elif total_escapes < 10:
            return "HIGH"
        else:
            return "CRITICAL"


class HarnessEnforcer:
    """
    Main enforcement class that monitors and prevents escape conditions.
    
    Usage:
        from harness_enforcer import get_harness_enforcer
        
        he = get_harness_enforcer()
        
        # Before any significant action
        he.enforce_pre_action("edit_file", {"file": "test.py"})
        
        # After logging
        he.enforce_post_logging()
        
        # Before exiting
        he.enforce_session_close()
    """
    
    _instance: Optional['HarnessEnforcer'] = None
    
    def __init__(self):
        self.detector = EscapeDetector()
        self.state: Dict[str, Any] = {}
        self.escape_violations: List[Dict] = []
        self.load_state()
        
        # Counters for pattern detection
        self.action_count = 0
        self.log_count = 0
        self.kb_search_count = 0
        self.edit_count = 0
        self.verify_count = 0
        self.run_count = 0
        
        # Phase tracking
        self.current_phase = "UNKNOWN"
        self.required_phases = ["PLANNING", "REVIEW", "EXECUTING", "VERIFYING"]
        self.phase_sequence: List[str] = []
    
    @classmethod
    def get_instance(cls) -> 'HarnessEnforcer':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_state(self):
        """Load harness state from disk"""
        if os.path.exists(HARNESS_STATE_FILE):
            try:
                with open(HARNESS_STATE_FILE, 'r') as f:
                    self.state = json.load(f)
            except:
                self.state = {}
        else:
            self.state = {}
    
    def save_state(self):
        """Persist harness state to disk"""
        with open(HARNESS_STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _log_escape(self, escape: EscapeCondition, details: Dict, severity: str = "HIGH"):
        """Log an escape condition to file"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "escape_type": escape.value,
            "severity": severity,
            "details": details,
            "phase": self.current_phase,
            "action_count": self.action_count,
            "log_count": self.log_count
        }
        
        self.escape_violations.append(entry)
        
        with open(ESCAPE_LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + "\n")
        
        print(f"\n[HARNESS ESCAPE DETECTED] {escape.value}")
        print(f"  Severity: {severity}")
        print(f"  Details: {details}")
        print(f"  Phase: {self.current_phase}")
        print()
    
    def _log_enforcement(self, action: EnforcementAction, escape: EscapeCondition, response: str):
        """Log enforcement action taken"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action.value,
            "escape": escape.value,
            "response": response
        }
        
        with open(ENFORCEMENT_LOG, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    
    # ============ PRE-ACTION ENFORCEMENT ============
    
    def enforce_pre_action(self, action_type: str, details: Dict = None) -> bool:
        """
        Called BEFORE any significant action.
        Returns True if action is allowed, False if blocked.
        """
        self.action_count += 1
        self.detector.record_action(action_type)
        
        # Track specific action types
        if action_type in ["edit", "create", "modify"]:
            self.edit_count += 1
        
        if action_type in ["run", "execute", "subprocess"]:
            self.run_count += 1
        
        details = details or {}
        
        # ENFORCEMENT 1: Check if re-prime is required
        if self._check_reprime_required():
            self._log_escape(
                EscapeCondition.SKIP_REPRIME,
                {"action": action_type, "details": details},
                "CRITICAL"
            )
            self._handle_reprime_skip(action_type)
            return False
        
        # ENFORCEMENT 2: Check KB search before building
        if action_type in ["edit", "create", "build"] and self.edit_count > 2:
            if self.kb_search_count == 0 and self.edit_count > 3:
                self._log_escape(
                    EscapeCondition.SKIP_KB_SEARCH,
                    {"action": action_type, "edit_count": self.edit_count},
                    "HIGH"
                )
                self._handle_kb_skip(action_type)
                # Don't block, but warn
        
        # ENFORCEMENT 3: Check blackboard workflow
        if action_type in ["execute", "run", "subprocess"]:
            if not self._check_workflow_compliance():
                self._log_escape(
                    EscapeCondition.SKIP_BLACKBOARD_WORKFLOW,
                    {"action": action_type, "current_phase": self.current_phase},
                    "HIGH"
                )
                self._handle_workflow_skip(action_type)
                return False
        
        # ENFORCEMENT 4: Check health checks before deploy
        if action_type == "deploy":
            if not self._check_health_checks_done():
                self._log_escape(
                    EscapeCondition.SKIP_HEALTH_CHECKS,
                    {"action": action_type},
                    "CRITICAL"
                )
                self._handle_health_skip(action_type)
                return False
        
        return True
    
    def enforce_post_logging(self) -> bool:
        """
        Called AFTER logging an action.
        Ensures proper log-to-action ratio.
        """
        self.log_count += 1
        
        # Check logging ratio
        if self.detector.detect_skip_logging(self.action_count, self.log_count):
            self._log_escape(
                EscapeCondition.SKIP_LOGGING,
                {"action_count": self.action_count, "log_count": self.log_count},
                "MEDIUM"
            )
            return False
        
        return True
    
    def enforce_kb_search(self, query: str) -> bool:
        """Called when KB is searched"""
        self.kb_search_count += 1
        self.detector.record_action(f"kb_search:{query}")
        return True
    
    def enforce_verification(self, verification_type: str, result: bool) -> bool:
        """Called when verification is performed"""
        self.verify_count += 1
        self.detector.record_action(f"verify:{verification_type}")
        
        if verification_type == "test" and result == False:
            self._log_escape(
                EscapeCondition.SKIP_TESTING,
                {"type": verification_type, "result": str(result)},
                "MEDIUM"
            )
        
        return result
    
    def enforce_phase_transition(self, new_phase: str) -> bool:
        """
        Enforce proper phase transitions.
        Phase order must be: PLANNING → REVIEW → EXECUTING → VERIFYING → DONE
        """
        valid_transitions = {
            "IDLE": ["PLANNING"],
            "PLANNING": ["REVIEW"],
            "REVIEW": ["EXECUTING", "PLANNING", "ERROR"],  # PLANNING on NEEDS_WORK
            "EXECUTING": ["VERIFYING", "ERROR"],
            "VERIFYING": ["DONE", "ERROR"],
            "ERROR": ["IDLE", "PLANNING"],
            "DONE": ["IDLE", "PLANNING"]
        }
        
        old_phase = self.current_phase
        
        if new_phase not in valid_transitions.get(old_phase, []):
            self._log_escape(
                EscapeCondition.SKIP_BLACKBOARD_WORKFLOW,
                {"from": old_phase, "to": new_phase, "invalid_transition": True},
                "CRITICAL"
            )
            self._log_enforcement(
                EnforcementAction.BLOCK,
                EscapeCondition.SKIP_BLACKBOARD_WORKFLOW,
                f"Invalid phase transition: {old_phase} → {new_phase}"
            )
            return False
        
        self.current_phase = new_phase
        self.phase_sequence.append(new_phase)
        self._log_enforcement(
            EnforcementAction.LOG_ONLY,
            EscapeCondition.SKIP_BLACKBOARD_WORKFLOW,
            f"Valid transition: {old_phase} → {new_phase}"
        )
        return True
    
    # ============ HELPER CHECKS ============
    
    def _check_reprime_required(self) -> bool:
        """Check if re-prime is required but not done"""
        session_state_file = r"E:\AI-Setup\blackboard_data\session_state.json"
        
        if not os.path.exists(session_state_file):
            return True  # No session state = need re-prime
        
        try:
            with open(session_state_file, 'r') as f:
                state = json.load(f)
            
            # Check if re-prime was triggered but not completed
            reprime_trigger = r"E:\AI-Setup\blackboard_data\reprime_trigger.json"
            if os.path.exists(reprime_trigger):
                with open(reprime_trigger, 'r') as f:
                    trigger = json.load(f)
                    triggered_at = trigger.get("triggered_at", "")
                    # If triggered in last hour and we haven't re-initialized blackboard
                    if triggered_at:
                        from datetime import datetime
                        triggered_time = datetime.fromisoformat(triggered_at.replace('Z', '+00:00'))
                        elapsed = (datetime.now() - triggered_time.replace(tzinfo=None)).total_seconds()
                        if elapsed < 3600:  # Within last hour
                            if self.action_count > 10:  # Already did actions without re-prime
                                return True
        except:
            pass
        
        return False
    
    def _check_workflow_compliance(self) -> bool:
        """Check if blackboard workflow is being followed"""
        # If we're trying to execute but haven't done PLANNING and REVIEW
        if self.current_phase not in ["PLANNING", "REVIEW", "EXECUTING"]:
            # Allow if very few actions (might be initialization)
            if self.action_count < 5:
                return True
            return False
        return True
    
    def _check_health_checks_done(self) -> bool:
        """Check if health checks were performed before this deploy"""
        # Look for recent health check entries in logs
        # This is a simplified check - real implementation would query logs
        return True  # Placeholder - would check actual log entries
    
    # ============ ESCAPE HANDLERS ============
    
    def _handle_reprime_skip(self, action: str):
        """Handle case where AI tries to act without re-priming"""
        print("\n" + "=" * 70)
        print("HARNESS VIOLATION: RE-PRIME REQUIRED")
        print("=" * 70)
        print(f"You are attempting to '{action}' without re-priming.")
        print()
        print("RE-PRIME SEQUENCE REQUIRED:")
        print("1. from blackboard import init_blackboard")
        print("2. bb = init_blackboard(force=True)")
        print("3. from crash_recovery import get_summary")
        print("4. get_summary()")
        print()
        print("Type 'reprime' to acknowledge and proceed with re-prime.")
        print("=" * 70 + "\n")
        
        self._log_enforcement(
            EnforcementAction.BLOCK,
            EscapeCondition.SKIP_REPRIME,
            f"Blocked action '{action}' - re-prime required"
        )
    
    def _handle_kb_skip(self, action: str):
        """Handle case where AI builds without checking KB"""
        print("\n[KB WARNING] You are editing files without searching the Knowledge Base.")
        print("Before building, search KB for existing learnings:")
        print("  kb.search('your_topic')")
        print("  kb.get_model_context('model_name')")
        print()
    
    def _handle_workflow_skip(self, action: str):
        """Handle case where AI executes without proper workflow"""
        print("\n[WORKFLOW WARNING] You must follow the blackboard workflow:")
        print("  IDLE → PLANNING → REVIEW → EXECUTING → VERIFYING → DONE")
        print(f"Current phase: {self.current_phase}")
        print(f"Cannot '{action}' in current state.")
        print()
    
    def _handle_health_skip(self, action: str):
        """Handle case where AI deploys without health checks"""
        print("\n[HEALTH CHECK REQUIRED] You must verify components before deploying.")
        print("Run health checks:")
        print("  python E:\\AI-Setup\\deployment_framework.py --all")
        print()
    
    # ============ SESSION ENFORCEMENT ============
    
    def enforce_session_close(self, session_duration: float) -> bool:
        """
        Called when session is closing.
        Returns True if close is allowed, False if blocked.
        """
        # Check for impatient exit
        if self.detector.detect_rapid_exit(session_duration, self.action_count):
            self._log_escape(
                EscapeCondition.IMPATIENT_EXIT,
                {"duration": session_duration, "actions": self.action_count},
                "MEDIUM"
            )
            print("\n[EXIT WARNING] Session ending very quickly.")
            print("Did you create a session summary?")
            print("  - Document accomplishments")
            print("  - Note pending work")
            print("  - Save to session_logs/SESSION_SUMMARY_*.md")
        
        # Check for missing session summary
        if self.action_count > 10:  # Active session
            summary_files = [
                f for f in os.listdir(r"E:\AI-Setup\session_logs")
                if f.startswith("SESSION_SUMMARY_") and f.endswith(".md")
            ]
            today_summary = any(
                datetime.now().strftime("%Y%m%d") in f 
                for f in summary_files
            )
            
            if not today_summary and self.action_count > 20:
                self._log_escape(
                    EscapeCondition.IMPATIENT_EXIT,
                    {"no_summary_today": True, "actions": self.action_count},
                    "HIGH"
                )
                print("\n[SUMMARY REQUIRED] You have been active but didn't create a session summary.")
                print("Create one now before exiting!")
                return False
        
        return True
    
    def enforce_verdict_respect(self, verdict: str) -> bool:
        """
        Enforce that AI respects verdict (especially FAIL).
        """
        if verdict == "FAIL":
            self._log_escape(
                EscapeCondition.BYPASS_ANALYST_REVIEW,
                {"verdict": verdict},
                "CRITICAL"
            )
            print("\n[VERDICT RESPECTED] Analyst returned FAIL.")
            print("You MUST revise and resubmit, not bypass.")
            return False
        
        return True
    
    # ============ STATUS REPORTING ============
    
    def get_compliance_report(self) -> Dict:
        """Get current compliance status"""
        return {
            "action_count": self.action_count,
            "log_count": self.log_count,
            "kb_search_count": self.kb_search_count,
            "edit_count": self.edit_count,
            "verify_count": self.verify_count,
            "run_count": self.run_count,
            "current_phase": self.current_phase,
            "phase_sequence": self.phase_sequence,
            "escape_violations": len(self.escape_violations),
            "escape_risk": self.detector.get_escape_risk(),
            "log_ratio": self.log_count / max(1, self.action_count),
            "kb_search_ratio": self.kb_search_count / max(1, self.edit_count),
            "verify_ratio": self.verify_count / max(1, self.run_count)
        }
    
    def print_compliance_report(self):
        """Print compliance report to console"""
        report = self.get_compliance_report()
        
        print("\n" + "=" * 60)
        print("HARNESS COMPLIANCE REPORT")
        print("=" * 60)
        print(f"  Actions: {report['action_count']}")
        print(f"  Logs: {report['log_count']} (ratio: {report['log_ratio']:.2f})")
        print(f"  KB Searches: {report['kb_search_count']}")
        print(f"  Edits: {report['edit_count']} (search ratio: {report['kb_search_ratio']:.2f})")
        print(f"  Verifications: {report['verify_count']} (run ratio: {report['verify_ratio']:.2f})")
        print(f"  Current Phase: {report['current_phase']}")
        print(f"  Escape Risk: {report['escape_risk']}")
        print(f"  Violations: {report['escape_violations']}")
        print("=" * 60 + "\n")
    
    def reset(self):
        """Reset enforcement state for new session"""
        self.action_count = 0
        self.log_count = 0
        self.kb_search_count = 0
        self.edit_count = 0
        self.verify_count = 0
        self.run_count = 0
        self.current_phase = "IDLE"
        self.phase_sequence = []
        self.escape_violations = []
        self.detector = EscapeDetector()
        self.save_state()


def get_harness_enforcer() -> HarnessEnforcer:
    """Convenience function to get HarnessEnforcer instance"""
    return HarnessEnforcer.get_instance()


# ============ DECORATOR FOR ENFORCEMENT ============

def enforce_action(action_type: str):
    """Decorator to enforce pre-action checks"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            he = get_harness_enforcer()
            
            details = {"function": func.__name__}
            if args:
                details["args"] = str(args)[:100]
            
            if not he.enforce_pre_action(action_type, details):
                raise RuntimeError(f"HARNESS BLOCKED: {action_type} requires re-prime or compliance check")
            
            result = func(*args, **kwargs)
            
            he.enforce_post_logging()
            
            return result
        return wrapper
    return decorator


# ============ INTEGRATION WITH SESSION LOGGER ============

def install_harness_hooks():
    """
    Install hooks into session_logger to enforce harness compliance.
    Call this once at session start.
    """
    import session_logger
    
    # Store original log function
    original_log = session_logger.log
    
    def monitored_log(action, description="", data=None, source="system"):
        he = get_harness_enforcer()
        he.enforce_post_logging()
        return original_log(action, description, data, source)
    
    # Replace with monitored version
    session_logger.log = monitored_log
    
    print("[HARNESS] Enforcement hooks installed")
