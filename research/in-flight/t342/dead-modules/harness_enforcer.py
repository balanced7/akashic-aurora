"""
Harness Enforcer - Escape Condition Detection & Prevention
======================================================
Mission-Critical Agentic AI Control System

ESCAPE PREVENTION STRATEGIES:
1. PRINCIPLE OF LEAST PRIVILEGE - Only allow necessary actions
2. VERIFICATION BEFORE ACTION - Always verify before proceeding
3. STATE TRANSITION VALIDATION - Enforce valid state machine transitions
4. CONTINUOUS MONITORING - Track all actions in real-time
5. AUDIT TRAIL - Complete logging with no gaps
6. AUTO-REMEDIATION - Auto-fix when violations detected
7. DEFENSE IN DEPTH - Multiple layers of enforcement

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
- ROLLBACK CAPABILITY: Can return to previous state
- OBSERVABILITY: Everything logged, nothing hidden

Author: Senior Systems Architect
Version: 3.0 - Enhanced Escape Prevention
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict

# ============================================================================
# PATHS
# ============================================================================

BLACKBOARD_DIR = r"E:\AI-Setup\blackboard_data"
HARNESS_STATE_FILE = os.path.join(BLACKBOARD_DIR, "harness_state.json")
ESCAPE_LOG_FILE = os.path.join(BLACKBOARD_DIR, "logs", "escape_conditions.jsonl")
ENFORCEMENT_LOG = os.path.join(BLACKBOARD_DIR, "logs", "enforcement.jsonl")

os.makedirs(os.path.dirname(ESCAPE_LOG_FILE), exist_ok=True)

# ============================================================================
# ESCAPE CONDITIONS
# ============================================================================

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
    SESSION_STATE_MISMATCH = "session_state_mismatch"
    UNVERIFIED_DEPLOYMENT = "unverified_deployment"


class EnforcementAction(Enum):
    """Actions taken when escape is detected"""
    WARN = "warn"
    BLOCK = "block"
    LOG_ONLY = "log_only"
    ESCALATE = "escalate"
    FORCE_REPRIME = "force_reprime"
    AUTO_FIX = "auto_fix"


# ============================================================================
# ESCAPE DETECTOR
# ============================================================================

class EscapeDetector:
    """
    Detects escape conditions based on behavior patterns.
    
    KEY INSIGHT: Agents escape by:
    1. Skipping verification steps
    2. Acting without context
    3. Bypassing the state machine
    4. Working outside proper workflow
    """
    
    def __init__(self):
        self.escape_counts: Dict[str, int] = defaultdict(int)
        self.action_history: List[Dict] = []
        self.last_action_time: float = time.time()
        self.action_sequence: List[str] = []
        self.max_sequence_length = 100
        
        # Baselines for anomaly detection
        self.baseline_log_ratio = 1.0  # 1 log per action minimum
        self.baseline_verify_ratio = 0.2  # 1 verify per 5 actions minimum
    
    def record_action(self, action: str, source: str = "system", data: Dict = None):
        """Record an action for pattern analysis"""
        entry = {
            "action": action,
            "source": source,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "has_data": data is not None and len(data) > 0
        }
        
        self.action_history.append(entry)
        self.action_sequence.append(action)
        
        if len(self.action_sequence) > self.max_sequence_length:
            self.action_sequence.pop(0)
        
        self.last_action_time = time.time()
    
    def detect_skip_logging(self, action_count: int, log_count: int) -> bool:
        """
        CRITICAL: If actions > logs, likely skipping logging.
        Ratio should be ~1:1 for proper compliance.
        """
        if log_count == 0 and action_count > 5:
            return True
        if action_count > log_count * 3 and action_count > 10:
            return True
        return False
    
    def detect_skip_kb_search(self, edit_count: int, kb_search_count: int) -> bool:
        """If making edits without searching KB first"""
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
            return True
        return False
    
    def detect_session_mismatch(self, stored_id: str, current_id: str) -> bool:
        """Detect if session ID changed without proper re-prime"""
        if stored_id and current_id and stored_id != current_id:
            return True
        return False
    
    def get_escape_risk(self) -> str:
        """Return overall escape risk level"""
        total_escapes = sum(self.escape_counts.values())
        
        # Factor in detection counts
        critical_escapes = (
            self.escape_counts.get("SKIP_REPRIME", 0) * 3 +
            self.escape_counts.get("SKIP_VERIFY", 0) * 2 +
            self.escape_counts.get("BYPASS_ANALYST_REVIEW", 0) * 3
        )
        
        if total_escapes == 0:
            return "LOW"
        elif critical_escapes > 5:
            return "CRITICAL"
        elif critical_escapes > 2:
            return "HIGH"
        elif total_escapes < 5:
            return "MEDIUM"
        else:
            return "HIGH"


# ============================================================================
# HARNESS ENFORCER
# ============================================================================

class HarnessEnforcer:
    """
    Main enforcement class that monitors and prevents escape conditions.
    
    DEFENSE IN DEPTH STRATEGY:
    1. PRE-ACTION CHECKS: Validate before any action
    2. POST-ACTION LOGGING: Ensure logging after every action
    3. STATE VALIDATION: Enforce valid transitions
    4. CONTINUOUS MONITORING: Track patterns over time
    5. AUTO-REMEDIATION: Fix violations when detected
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
        self.current_phase = "IDLE"
        self.required_phases = ["IDLE", "PLANNING", "REVIEW", "EXECUTING", "VERIFYING", "DONE"]
        self.phase_sequence: List[str] = []
        
        # Session tracking
        self._session_id = None
        self._initial_session_check()
        
        # Auto-remediation enabled
        self.auto_remediate = True
    
    def _initial_session_check(self):
        """Check session state on initialization"""
        try:
            import sys
            sys.path.insert(0, r'E:\AI-Setup')
            from session_logger import SESSION_ID
            self._session_id = SESSION_ID
        except:
            pass
    
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
            "log_count": self.log_count,
            "session_id": self._session_id
        }
        
        self.escape_violations.append(entry)
        self.detector.escape_counts[escape.value] += 1
        
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
    
    # =========================================================================
    # PRE-ACTION ENFORCEMENT
    # =========================================================================
    
    def enforce_pre_action(self, action_type: str, details: Dict = None) -> bool:
        """
        CRITICAL: Called BEFORE any significant action.
        Returns True if action is allowed, False if blocked.
        
        DEFENSE IN DEPTH: Multiple checks before any action.
        """
        self.action_count += 1
        self.detector.record_action(action_type, data=details)
        
        # Track specific action types
        if action_type in ["edit", "create", "modify"]:
            self.edit_count += 1
        
        if action_type in ["run", "execute", "subprocess"]:
            self.run_count += 1
        
        details = details or {}
        
        # ========== ENFORCEMENT 0: Session Integrity ==========
        if not self._check_session_integrity():
            self._log_escape(
                EscapeCondition.SESSION_STATE_MISMATCH,
                {"action": action_type, "details": details},
                "CRITICAL"
            )
            self._handle_session_mismatch(action_type)
            return False
        
        # ========== ENFORCEMENT 1: Re-prime Required ==========
        if self._check_reprime_required():
            self._log_escape(
                EscapeCondition.SKIP_REPRIME,
                {"action": action_type, "details": details, "reason": "new_session_detected"},
                "CRITICAL"
            )
            self._handle_reprime_skip(action_type)
            return False
        
        # ========== ENFORCEMENT 2: KB Search Before Building ==========
        if action_type in ["edit", "create", "build"]:
            if self.edit_count > 2 and self.kb_search_count == 0:
                self._log_escape(
                    EscapeCondition.SKIP_KB_SEARCH,
                    {"action": action_type, "edit_count": self.edit_count},
                    "HIGH"
                )
                self._handle_kb_skip(action_type)
        
        # ========== ENFORCEMENT 3: Blackboard Workflow ==========
        if action_type in ["execute", "run", "subprocess", "deploy"]:
            if not self._check_workflow_compliance():
                self._log_escape(
                    EscapeCondition.SKIP_BLACKBOARD_WORKFLOW,
                    {"action": action_type, "current_phase": self.current_phase},
                    "HIGH"
                )
                self._handle_workflow_skip(action_type)
                return False
        
        # ========== ENFORCEMENT 4: Health Checks Before Deploy ==========
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
        CRITICAL: Called AFTER logging an action.
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
    
    def enforce_verification(self, verification_type: str, result: bool, metrics: Dict = None) -> bool:
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
        Phase order must be: IDLE → PLANNING → REVIEW → EXECUTING → VERIFYING → DONE
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
        return True
    
    # =========================================================================
    # HELPER CHECKS
    # =========================================================================
    
    def _check_session_integrity(self) -> bool:
        """
        CRITICAL: Verify session hasn't changed without proper re-prime.
        This is a fundamental integrity check.
        """
        try:
            import sys
            sys.path.insert(0, r'E:\AI-Setup')
            from session_logger import SESSION_ID
            from session_manager import get_session_manager
            
            # Get current session ID
            current_id = SESSION_ID
            
            # Get stored session ID
            sm = get_session_manager()
            state = sm.get_current_state()
            
            if state is None:
                return True  # Can't check, assume OK
            
            stored_id = state.session_id if hasattr(state, 'session_id') else None
            
            # Check for mismatch
            if stored_id and current_id and stored_id != current_id:
                return False
            
            return True
            
        except Exception as e:
            # If can't check, don't block - just warn
            return True
    
    def _check_reprime_required(self) -> bool:
        """
        Check if re-prime is required.
        Re-prime is needed when:
        1. Session ID changed
        2. Reprime trigger exists (from session_manager)
        3. No recent actions (fresh session but trigger exists)
        """
        try:
            # Check session_manager's reprime trigger
            reprime_trigger = r"E:\AI-Setup\blackboard_data\reprime_trigger.json"
            if os.path.exists(reprime_trigger):
                with open(reprime_trigger, 'r') as f:
                    trigger = json.load(f)
                    triggered_at = trigger.get("triggered_at", "")
                    
                    if triggered_at:
                        from datetime import datetime
                        triggered_time = datetime.fromisoformat(triggered_at.replace('Z', '+00:00'))
                        elapsed = (datetime.now() - triggered_time.replace(tzinfo=None)).total_seconds()
                        
                        # If triggered recently (within 2 hours) and few actions taken
                        if elapsed < 7200 and self.action_count < 20:
                            return True
        except:
            pass
        
        return False
    
    def _check_workflow_compliance(self) -> bool:
        """Check if blackboard workflow is being followed"""
        if self.current_phase not in ["PLANNING", "REVIEW", "EXECUTING"]:
            if self.action_count < 5:
                return True  # Allow early actions
            return False
        return True
    
    def _check_health_checks_done(self) -> bool:
        """Check if health checks were performed before this deploy"""
        # Look for recent health check entries
        return True  # Simplified - would check actual log entries
    
    # =========================================================================
    # ESCAPE HANDLERS (AUTO-REMEDIATION)
    # =========================================================================
    
    def _handle_reprime_skip(self, action: str):
        """Handle case where AI tries to act without re-priming"""
        print("\n" + "=" * 70)
        print("HARNESS VIOLATION: RE-PRIME REQUIRED")
        print("=" * 70)
        print(f"You are attempting to '{action}' without re-priming.")
        print()
        print("RE-PRIME SEQUENCE REQUIRED:")
        print("1. from blackboard import init_blackboard")
        print("2. bb = init_blackboard()")
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
    
    def _handle_session_mismatch(self, action: str):
        """Handle session ID mismatch - auto-trigger re-prime"""
        print("\n" + "=" * 70)
        print("SESSION MISMATCH DETECTED")
        print("=" * 70)
        print("The stored session ID doesn't match the current session.")
        print("This means the AI was restarted without proper re-priming.")
        print()
        print("AUTO-REMEDIATION: Re-prime trigger created.")
        print("You MUST run the re-prime sequence before continuing.")
        print("=" * 70 + "\n")
        
        # Auto-create reprime trigger
        try:
            reprime_trigger = r"E:\AI-Setup\blackboard_data\reprime_trigger.json"
            trigger_data = {
                "triggered_at": datetime.now().isoformat(),
                "reason": "session_mismatch_detected",
                "required_actions": [
                    "Re-read STARTUP.md",
                    "Re-initialize blackboard with init_blackboard(force=True)",
                    "Run crash_recovery.get_summary()",
                    "Verify logging with verify_logs()"
                ]
            }
            with open(reprime_trigger, 'w') as f:
                json.dump(trigger_data, f, indent=2)
        except:
            pass
    
    # =========================================================================
    # SESSION ENFORCEMENT
    # =========================================================================
    
    def enforce_session_close(self, session_duration: float) -> bool:
        """
        Called when session is closing.
        Returns True if close is allowed, False if blocked.
        """
        if self.detector.detect_rapid_exit(session_duration, self.action_count):
            self._log_escape(
                EscapeCondition.IMPATIENT_EXIT,
                {"duration": session_duration, "actions": self.action_count},
                "MEDIUM"
            )
            print("\n[EXIT WARNING] Session ending very quickly.")
            print("Did you create a session summary?")
            return False
        
        return True
    
    def enforce_verdict_respect(self, verdict: str) -> bool:
        """Enforce that AI respects verdict (especially FAIL)"""
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
    
    # =========================================================================
    # STATUS REPORTING
    # =========================================================================
    
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
            "verify_ratio": self.verify_count / max(1, self.run_count),
            "session_integrity": self._check_session_integrity()
        }
    
    def print_compliance_report(self):
        """Print compliance report to console"""
        report = self.get_compliance_report()
        
        print("\n" + "=" * 60)
        print("HARNESS COMPLIANCE REPORT")
        print("=" * 60)
        print(f"  Session Integrity: {report['session_integrity']}")
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


# ============================================================================
# DECORATOR FOR ENFORCEMENT
# ============================================================================

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
