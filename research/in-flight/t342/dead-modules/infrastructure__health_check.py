"""
Startup Diagnostics: Report on initialization health

Semantic Relationship: StartupDiagnostics documents_initialization_health

Provides visibility into what loaded, what failed, and how fast it was.
Helps debug initialization issues and understand system state.

Collects timing metrics for each startup phase, tracks failures, and generates
health report with recommendations for optimization.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os
import json

log_dir = Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "session_logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[STARTUP_DIAGNOSTICS] [%(asctime)s] %(message)s'
)
logger = logging.getLogger("startup_diagnostics")


class StartupDiagnostics:
    """
    Collects startup metrics and generates diagnostics report.

    Semantic Relationship: StartupDiagnostics documents_agent_initialization (timing and failures)
    """

    def __init__(self, agent_id: str):
        """Initialize diagnostics collector"""
        self.agent_id = agent_id
        self.start_time = time.time()
        self.phases: List[Dict[str, Any]] = []
        self.logger = logger

    def record_startup_phase_with_metrics(self, phase_name: str, success: bool, duration_ms: float,
                    details: Optional[str] = None) -> None:
        """
        Record a startup phase.

        Semantic Relationship: RecordedPhase documents_startup_timeline

        Args:
            phase_name: Name of the phase (e.g., "load_briefing")
            success: Whether phase succeeded
            duration_ms: How long it took (milliseconds)
            details: Optional details/error message
        """
        self.phases.append({
            "phase": phase_name,
            "success": success,
            "duration_ms": duration_ms,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        })

    # Backward compatibility alias
    def record_phase(self, phase_name: str, success: bool, duration_ms: float,
                    details: Optional[str] = None) -> None:
        """Deprecated: Use record_startup_phase_with_metrics() instead"""
        return self.record_startup_phase_with_metrics(phase_name, success, duration_ms, details)

    def get_total_startup_time_in_milliseconds(self) -> float:
        """
        Get total startup time in milliseconds.

        Semantic Relationship: TotalTime derived_from StartTime (elapsed)

        Returns:
            Elapsed time in milliseconds since initialization
        """
        return (time.time() - self.start_time) * 1000

    # Backward compatibility alias
    def get_total_time(self) -> float:
        """Deprecated: Use get_total_startup_time_in_milliseconds() instead"""
        return self.get_total_startup_time_in_milliseconds()

    def generate_startup_diagnostics_report(self) -> Dict[str, Any]:
        """
        Generate complete startup diagnostics report.

        Semantic Relationship: DiagnosticsReport derived_from StartupPhases (analyzed)

        Returns:
            Report dict with timeline, metrics, recommendations
        """
        total_time = self.get_total_startup_time_in_milliseconds()
        passed = sum(1 for p in self.phases if p["success"])
        total = len(self.phases)

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.agent_id,
            "total_startup_time_ms": total_time,
            "phases_passed": passed,
            "phases_total": total,
            "phases": self.phases,
            "success_rate": (passed / total * 100) if total > 0 else 0,
        }

        # Identify slow phases
        slow_phases = [p for p in self.phases if p["duration_ms"] > 100]
        if slow_phases:
            report["slow_phases"] = slow_phases

        # Identify failed phases
        failed_phases = [p for p in self.phases if not p["success"]]
        if failed_phases:
            report["failed_phases"] = failed_phases

        # Generate recommendations
        report["recommendations"] = self._derive_recommendations_from_diagnostics(report)

        return report

    # Backward compatibility alias
    def generate_report(self) -> Dict[str, Any]:
        """Deprecated: Use generate_startup_diagnostics_report() instead"""
        return self.generate_startup_diagnostics_report()

    def print_diagnostic_report_for_agent(self) -> None:
        """
        Print human-readable startup diagnostics.

        Semantic Relationship: PrintedReport documents_diagnostics (human readable format)
        """
        report = self.generate_startup_diagnostics_report()

        print(f"\n{'='*70}")
        print(f"STARTUP DIAGNOSTICS - {self.agent_id}")
        print(f"{'='*70}\n")

        print(f"Total Time: {report['total_startup_time_ms']:.0f}ms")
        print(f"Phases: {report['phases_passed']}/{report['phases_total']} passed ({report['success_rate']:.0f}%)\n")

        print("TIMELINE:")
        for phase in report['phases']:
            status = "OK" if phase['success'] else "FAIL"
            print(f"  {status} {phase['phase']:<30} {phase['duration_ms']:>6.0f}ms")
            if phase['details']:
                print(f"     {phase['details']}")

        if report.get('slow_phases'):
            print(f"\nSLOW PHASES (>100ms):")
            for phase in report['slow_phases']:
                print(f"  WARN {phase['phase']}: {phase['duration_ms']:.0f}ms")

        if report.get('failed_phases'):
            print(f"\nFAILED PHASES:")
            for phase in report['failed_phases']:
                print(f"  FAIL {phase['phase']}")
                if phase['details']:
                    print(f"       {phase['details']}")

        if report['recommendations']:
            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")

        print(f"\n{'='*70}\n")

        # Log the report
        self._persist_diagnostics_report_to_file(report)

    # Backward compatibility alias
    def print_report(self) -> None:
        """Deprecated: Use print_diagnostic_report_for_agent() instead"""
        return self.print_diagnostic_report_for_agent()

    def _derive_recommendations_from_diagnostics(self, report: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on diagnostics.

        Semantic Relationship: DerivedRecommendations created_from DiagnosticsReport

        Args:
            report: Generated diagnostics report

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        if report['total_startup_time_ms'] > 1000:
            recommendations.append("Startup took >1s. Consider optimizing slow phases.")

        slow_phases = report.get('slow_phases', [])
        for phase in slow_phases:
            if "redis" in phase['phase'].lower():
                recommendations.append("Redis connection slow. Check network/Redis health.")
            elif "learning" in phase['phase'].lower():
                recommendations.append("Learning load slow. Consider archiving old learnings.")
            elif "briefing" in phase['phase'].lower():
                recommendations.append("Briefing load slow. Consider compressing context.")

        failed_phases = report.get('failed_phases', [])
        for phase in failed_phases:
            if "redis" in phase['phase'].lower():
                recommendations.append("Redis unavailable. File fallback in use.")
            elif "briefing" in phase['phase'].lower():
                recommendations.append("No previous briefing available. Starting fresh.")

        if not recommendations:
            recommendations.append("Startup healthy. No issues detected.")

        return recommendations

    # Backward compatibility alias
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Deprecated: Use _derive_recommendations_from_diagnostics() instead"""
        return self._derive_recommendations_from_diagnostics(report)

    def _persist_diagnostics_report_to_file(self, report: Dict[str, Any]) -> None:
        """
        Save diagnostics report to file.

        Semantic Relationship: PersistedReport saved_to LocalStorage

        Args:
            report: Report dict to persist
        """
        try:
            report_file = log_dir / f"startup_diagnostics_{self.agent_id}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            self.logger.info(f"Diagnostics report saved to {report_file}")
        except Exception as e:
            self.logger.error(f"Could not save diagnostics: {e}")

    # Backward compatibility alias
    def _save_report(self, report: Dict[str, Any]) -> None:
        """Deprecated: Use _persist_diagnostics_report_to_file() instead"""
        return self._persist_diagnostics_report_to_file(report)


class StartupTimer:
    """Context manager for timing startup phases"""

    def __init__(self, diagnostics: StartupDiagnostics, phase_name: str):
        self.diagnostics = diagnostics
        self.phase_name = phase_name
        self.start_time = time.time()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        success = exc_type is None

        if exc_type:
            details = f"{exc_type.__name__}: {exc_val}"
        else:
            details = None

        self.diagnostics.record_phase(self.phase_name, success, duration_ms, details)
        return False  # Don't suppress exceptions


def create_startup_diagnostics_collector(agent_id: str) -> StartupDiagnostics:
    """
    Create and initialize a startup diagnostics collector.

    Semantic Relationship: CreatedCollector enables_phase_tracking

    Args:
        agent_id: ID of agent being initialized

    Returns:
        StartupDiagnostics instance ready to record phases
    """
    return StartupDiagnostics(agent_id)


# Backward compatibility alias
def create_startup_diagnostics(agent_id: str) -> StartupDiagnostics:
    """Deprecated: Use create_startup_diagnostics_collector() instead"""
    return create_startup_diagnostics_collector(agent_id)


def create_phase_timer_for_diagnostics(diagnostics: StartupDiagnostics, phase_name: str):
    """
    Create a phase timer context manager.

    Semantic Relationship: CreatedTimer measures_phase_duration

    Args:
        diagnostics: Diagnostics collector to record into
        phase_name: Name of the phase being timed

    Returns:
        StartupTimer context manager
    """
    return StartupTimer(diagnostics, phase_name)


# Backward compatibility alias
def time_startup_phase(diagnostics: StartupDiagnostics, phase_name: str):
    """Deprecated: Use create_phase_timer_for_diagnostics() instead"""
    return create_phase_timer_for_diagnostics(diagnostics, phase_name)


def check_infrastructure_health(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    timeout_seconds: float = 2.0,
) -> Dict[str, Any]:
    """
    Probe ancillary infrastructure and report what is available.

    Semantic Relationship: HealthCheck reports_availability_of Infrastructure

    Fail-fast by design: every probe uses an aggressive timeout so a dead
    dependency never blocks startup. Downstream systems read this dict to
    decide whether to use Redis (fast path) or fall back to files.

    Args:
        redis_host: Redis server host (default: localhost)
        redis_port: Redis server port (default: 6379)
        timeout_seconds: Per-probe timeout, max wait before declaring DOWN

    Returns:
        {
            "redis": {"available": bool, "latency_ms": float|None, "error": str|None},
            "healthy": bool,          # True if at least one persistence path works
            "checked_at": ISO timestamp,
        }
    """
    report: Dict[str, Any] = {
        "redis": {"available": False, "latency_ms": None, "error": None},
        "healthy": False,
        "checked_at": datetime.utcnow().isoformat(),
    }

    # --- Redis probe (fail-fast) ---
    # Delegates to the foundation's canonical fail-fast connector, which gates
    # on a raw-socket reachability probe so a dead Redis fails fast instead of
    # stalling ~48s on Windows TCP SYN retransmission.
    start = time.time()
    try:
        from core.foundation.redis_connection import connect_to_redis_with_fail_fast

        client = connect_to_redis_with_fail_fast(
            host=redis_host, port=redis_port, timeout_seconds=timeout_seconds
        )
        if client is not None:
            report["redis"]["available"] = True
            report["redis"]["latency_ms"] = round((time.time() - start) * 1000, 2)
        else:
            report["redis"]["error"] = "unreachable (fail-fast probe)"
    except Exception as e:
        report["redis"]["error"] = f"{type(e).__name__}: {e}"

    # File fallback is always available, so the system is "healthy" regardless
    # of Redis. The flag tells callers a usable persistence path exists.
    report["healthy"] = True
    return report
