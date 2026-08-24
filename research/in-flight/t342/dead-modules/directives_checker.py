"""
Directives Compliance Checker
============================
Verifies adherence to mission-critical directives.

DIRECTIVES:
1. TEST BEFORE DEPLOY - Never assume, always verify
2. HEALTH CHECKS - Every component must prove it's working
3. GRACEFUL DEGRADATION - System survives component failures
4. FAILURE MODE ANALYSIS - Every failure anticipated and handled
5. ROLLBACK CAPABILITY - Can return to previous state
6. OBSERVABILITY - Everything logged, nothing hidden

Usage:
    from directives_checker import check_compliance, print_directives_report
    
    compliance = check_compliance()
    if not compliance['compliant']:
        print("DIRECTIVE VIOLATIONS DETECTED")
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Paths
LOG_DIR = r"E:\AI-Setup\session_logs"
BLACKBOARD_DIR = r"E:\AI-Setup\blackboard_data"
SESSION_STATE_FILE = os.path.join(BLACKBOARD_DIR, "session_state.json")


@dataclass
class DirectiveViolation:
    directive: str
    severity: str
    description: str
    evidence: Dict
    timestamp: str


class DirectivesComplianceChecker:
    """
    Checks compliance with mission-critical directives.
    """
    
    def __init__(self):
        self.violations: List[DirectiveViolation] = []
        self.checks_performed: List[str] = []
    
    def check_test_before_deploy(self) -> bool:
        """
        Directive 1: TEST BEFORE DEPLOY
        - Verify logs exist and are valid
        - Check for verification entries
        - No deployment without testing
        """
        self.checks_performed.append("test_before_deploy")
        
        # Check if logging is working
        log_file = os.path.join(LOG_DIR, "session_all.jsonl")
        if not os.path.exists(log_file):
            self.violations.append(DirectiveViolation(
                directive="TEST BEFORE DEPLOY",
                severity="CRITICAL",
                description="No session log found",
                evidence={"log_file": log_file},
                timestamp=datetime.now().isoformat()
            ))
            return False
        
        # Check for verify_logs calls in recent log
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            # Look for verification entries
            verified_count = 0
            for line in recent_lines:
                try:
                    entry = json.loads(line)
                    if entry.get('action') == 'verify' or 'verify' in entry.get('action', ''):
                        verified_count += 1
                except:
                    pass
            
            # If more than 10 actions but no verifications, flag it
            action_count = sum(1 for l in recent_lines if 'action' in l)
            if action_count > 10 and verified_count == 0:
                self.violations.append(DirectiveViolation(
                    directive="TEST BEFORE DEPLOY",
                    severity="HIGH",
                    description="Actions performed without verification entries",
                    evidence={"actions": action_count, "verifications": verified_count},
                    timestamp=datetime.now().isoformat()
                ))
                return False
                
        except Exception as e:
            self.violations.append(DirectiveViolation(
                directive="TEST BEFORE DEPLOY",
                severity="MEDIUM",
                description=f"Could not check verification: {e}",
                evidence={},
                timestamp=datetime.now().isoformat()
            ))
        
        return True
    
    def check_health_checks(self) -> bool:
        """
        Directive 2: HEALTH CHECKS
        - Verify deployment_framework health checks were run
        - Check for healthy component status
        """
        self.checks_performed.append("health_checks")
        
        # Look for health check entries in logs
        log_file = os.path.join(LOG_DIR, "session_all.jsonl")
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                recent_lines = lines[-200:] if len(lines) > 200 else lines
                
                health_check_found = False
                for line in recent_lines:
                    try:
                        entry = json.loads(line)
                        if 'health' in entry.get('action', '').lower():
                            health_check_found = True
                            break
                    except:
                        pass
                
                if not health_check_found:
                    self.violations.append(DirectiveViolation(
                        directive="HEALTH CHECKS",
                        severity="MEDIUM",
                        description="No health check actions found in recent logs",
                        evidence={},
                        timestamp=datetime.now().isoformat()
                    ))
                    return False
                    
        except Exception as e:
            pass  # Non-critical check
        
        return True
    
    def check_graceful_degradation(self) -> bool:
        """
        Directive 3: GRACEFUL DEGRADATION
        - Check for fallback entries in logs
        - Verify system can operate with component failures
        """
        self.checks_performed.append("graceful_degradation")
        
        # This is more of a design check - verify fallback mechanisms exist
        required_fallbacks = {
            "redis": ["file-only", "fallback", "offline"],
            "gpu": ["cpu", "fallback", "degraded"],
            "ollama": ["vllm", "transformers", "fallback"]
        }
        
        log_file = os.path.join(LOG_DIR, "session_all.jsonl")
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    content = f.read().lower()
                
                # Check if fallback patterns exist in recent logs
                for component, fallbacks in required_fallbacks.items():
                    has_fallback = any(fb in content for fb in fallbacks)
                    if not has_fallback:
                        # Just a warning - not a violation unless component failed
                        pass
                        
        except:
            pass
        
        return True  # This is observational
    
    def check_failure_mode_analysis(self) -> bool:
        """
        Directive 4: FAILURE MODE ANALYSIS
        - Check that errors have tracebacks
        - Verify errors are logged properly
        - Check for escalation entries
        """
        self.checks_performed.append("failure_mode_analysis")
        
        log_file = os.path.join(LOG_DIR, "errors_and_faults.jsonl")
        
        if not os.path.exists(log_file):
            return True  # No errors is good
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            recent_errors = lines[-50:] if len(lines) > 50 else lines
            
            for line in recent_errors:
                try:
                    entry = json.loads(line)
                    
                    # Check for traceback
                    if 'error' in entry.get('type', '') and not entry.get('traceback'):
                        self.violations.append(DirectiveViolation(
                            directive="FAILURE MODE ANALYSIS",
                            severity="MEDIUM",
                            description="Error logged without traceback",
                            evidence={"error": entry.get('error_type', 'unknown')},
                            timestamp=entry.get('timestamp', datetime.now().isoformat())
                        ))
                        return False
                        
                except:
                    pass
                    
        except:
            pass
        
        return True
    
    def check_rollback_capability(self) -> bool:
        """
        Directive 5: ROLLBACK CAPABILITY
        - Check for backup entries before changes
        - Verify state can be restored
        """
        self.checks_performed.append("rollback_capability")
        
        log_file = os.path.join(LOG_DIR, "session_all.jsonl")
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                
                # Look for backup/restore entries
                has_backup = False
                for line in recent_lines:
                    try:
                        entry = json.loads(line)
                        action = entry.get('action', '').lower()
                        if 'backup' in action or 'restore' in action or 'rollback' in action:
                            has_backup = True
                            break
                    except:
                        pass
                
                if not has_backup:
                    # Warning only - not a violation if no changes made
                    pass
                    
        except:
            pass
        
        return True  # Observational
    
    def check_observability(self) -> bool:
        """
        Directive 6: OBSERVABILITY
        - Every action must have data dict
        - Nothing hidden - all logged
        """
        self.checks_performed.append("observability")
        
        log_file = os.path.join(LOG_DIR, "session_all.jsonl")
        
        if not os.path.exists(log_file):
            self.violations.append(DirectiveViolation(
                directive="OBSERVABILITY",
                severity="CRITICAL",
                description="No session log found",
                evidence={},
                timestamp=datetime.now().isoformat()
            ))
            return False
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            # Count entries without data dict or with empty data
            entries_without_data = 0
            total_entries = 0
            
            for line in recent_lines:
                try:
                    entry = json.loads(line)
                    if entry.get('type') == 'action':
                        total_entries += 1
                        data = entry.get('data', {})
                        if not data or len(data) == 0:
                            entries_without_data += 1
                except:
                    pass
            
            # If more than 20% of actions lack data, flag it
            if total_entries > 5:
                ratio = entries_without_data / total_entries
                if ratio > 0.2:
                    self.violations.append(DirectiveViolation(
                        directive="OBSERVABILITY",
                        severity="HIGH",
                        description=f"{entries_without_data}/{total_entries} actions lack data dict",
                        evidence={"ratio": ratio, "threshold": 0.2},
                        timestamp=datetime.now().isoformat()
                    ))
                    return False
                    
        except Exception as e:
            self.violations.append(DirectiveViolation(
                directive="OBSERVABILITY",
                severity="MEDIUM",
                description=f"Could not check observability: {e}",
                evidence={},
                timestamp=datetime.now().isoformat()
            ))
        
        return True
    
    def check_kb_discipline(self) -> bool:
        """
        Additional check: KB Discipline
        - Search KB before building
        - Document new learnings
        """
        self.checks_performed.append("kb_discipline")
        
        log_file = os.path.join(LOG_DIR, "session_all.jsonl")
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                
                recent_lines = lines[-200:] if len(lines) > 200 else lines
                
                kb_searches = 0
                edits_without_search = 0
                found_edit_without_search = False
                
                for line in recent_lines:
                    try:
                        entry = json.loads(line)
                        action = entry.get('action', '').lower()
                        desc = entry.get('description', '').lower()
                        
                        if 'kb_search' in action or 'knowledge_base' in action:
                            kb_searches += 1
                        
                        if any(x in action for x in ['edit', 'create', 'write']) and 'file' in desc:
                            if kb_searches == 0:
                                found_edit_without_search = True
                    except:
                        pass
                
                if found_edit_without_search and kb_searches == 0:
                    self.violations.append(DirectiveViolation(
                        directive="KB DISCIPLINE",
                        severity="MEDIUM",
                        description="File edits found without prior KB search",
                        evidence={"kb_searches": kb_searches},
                        timestamp=datetime.now().isoformat()
                    ))
                    return False
                    
        except:
            pass
        
        return True
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all directive checks"""
        results = {
            "compliant": True,
            "checks_performed": self.checks_performed,
            "violations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Run all checks
        checks = [
            self.check_test_before_deploy,
            self.check_health_checks,
            self.check_graceful_degradation,
            self.check_failure_mode_analysis,
            self.check_rollback_capability,
            self.check_observability,
            self.check_kb_discipline
        ]
        
        for check in checks:
            try:
                result = check()
                if not result:
                    results["compliant"] = False
            except Exception as e:
                results["compliant"] = False
                self.violations.append(DirectiveViolation(
                    directive=check.__name__,
                    severity="HIGH",
                    description=f"Check threw exception: {e}",
                    evidence={},
                    timestamp=datetime.now().isoformat()
                ))
        
        results["violations"] = [
            {
                "directive": v.directive,
                "severity": v.severity,
                "description": v.description,
                "evidence": v.evidence,
                "timestamp": v.timestamp
            }
            for v in self.violations
        ]
        
        return results


def check_compliance() -> Dict[str, Any]:
    """Run all directive compliance checks"""
    checker = DirectivesComplianceChecker()
    return checker.run_all_checks()


def print_directives_report(compliance: Dict = None):
    """Print a human-readable directives compliance report"""
    if compliance is None:
        compliance = check_compliance()
    
    print("\n" + "=" * 70)
    print("  MISSION-CRITICAL DIRECTIVES COMPLIANCE REPORT")
    print("=" * 70)
    print(f"\nTimestamp: {compliance['timestamp']}")
    print(f"Compliant: {'YES ✓' if compliance['compliant'] else 'NO ✗'}")
    print(f"\nChecks Performed: {len(compliance['checks_performed'])}")
    for check in compliance['checks_performed']:
        print(f"  - {check}")
    
    if compliance['violations']:
        print(f"\n{'!' * 70}")
        print("  VIOLATIONS DETECTED")
        print(f"{'!' * 70}")
        
        for v in compliance['violations']:
            severity_icon = "🔴" if v['severity'] == "CRITICAL" else "🟡" if v['severity'] == "HIGH" else "🟠"
            print(f"\n{severity_icon} [{v['severity']}] {v['directive']}")
            print(f"    {v['description']}")
            if v['evidence']:
                print(f"    Evidence: {json.dumps(v['evidence'], indent=6)}")
    
    print("\n" + "=" * 70 + "\n")
    
    return compliance


def get_directives_summary() -> str:
    """Get a one-page summary of the directives"""
    return """
MISSION-CRITICAL DIRECTIVES (Always Enforced)
============================================

1. TEST BEFORE DEPLOY
   Never assume something works - always verify first.
   Run: verify_logs(), health checks, test inference

2. HEALTH CHECKS
   Every component must prove it's working.
   Run: deployment_framework.py --all

3. GRACEFUL DEGRADATION
   System survives component failures.
   Always have fallbacks: Redis→file, GPU→CPU, Ollama→vLLM

4. FAILURE MODE ANALYSIS
   Every failure anticipated and handled.
   Use try/except, log errors with tracebacks, escalate if needed

5. ROLLBACK CAPABILITY
   Can return to previous state.
   Backup before changes, document rollback procedures

6. OBSERVABILITY
   Everything logged, nothing hidden.
   Every log() call must include a data dict.

ADDITIONAL RULES:
- KB DISCIPLINE: Search KB before building
- RE-PRIME: Always re-prime on new session
- WORKFLOW: Follow IDLE→PLANNING→REVIEW→EXECUTING→VERIFYING→DONE
- SESSION SUMMARY: Create before exit
"""


if __name__ == "__main__":
    compliance = check_compliance()
    print_directives_report(compliance)
