"""
Session Checkpoint: crash-recovery checkpoint system (renamed from session_state.py 2026-07-07 to
end the module-basename collision with core/comm/session_state.py -- the live-Bifrost-session snapshot,
a different concern; the shared name was a latent import-shadowing hazard, arch-triage-2026-07-07).

Semantic Relationship: Checkpoint version tracking for agent recovery

Saves agent progress and state so it can resume from crashes.
This enables "pick up where you left off" behavior even if agent dies mid-task.

Checkpoint Versioning:
- Each checkpoint is a version of agent state at a point in time
- Checkpoints created by agents during task execution
- Checkpoints enable recovery from crashes
- Checkpoints mark progress and decisions made

Usage:
    from core.state.session_checkpoint import SessionState, CheckpointRecovery

    # Create and save checkpoint
    state = SessionState("agent_id")
    state.create_checkpoint_version_of_current_state(
        task="code review",
        progress=45,
        blockers=["waiting for approval"]
    )

    # Recover from checkpoint
    recovery = CheckpointRecovery.derive_recovery_plan_from_checkpoint("agent_id")
    if recovery:
        print(f"Resume from {recovery['resume_from_progress']}%")
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import os
from core.paths import repo_root

log_dir = repo_root() / "session_logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[SESSION_STATE] [%(asctime)s] %(message)s'
)
logger = logging.getLogger("session_state")


class SessionState:
    """
    Manages agent session checkpoints and recovery.

    Saves progress periodically so agent can recover from crashes/interruptions.
    """

    def __init__(self, agent_id: str):
        """
        Initialize session state manager.

        Args:
            agent_id: Unique agent identifier
        """
        self.agent_id = agent_id
        self.state_file = log_dir / f"state_{agent_id}.json"
        self.checkpoint_dir = log_dir / "checkpoints" / agent_id
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self._current_state = self._load_state_from_checkpoint_file()
        self.logger = logger

    def create_checkpoint_version_of_current_state(self,
                       task: Optional[str] = None,
                       progress: int = 0,
                       blockers: Optional[List[str]] = None,
                       decisions_made: int = 0,
                       outputs: Optional[Dict[str, Any]] = None,
                       notes: Optional[str] = None) -> bool:
        """
        Create a checkpoint version of current agent state.

        Semantic Relationship: Checkpoint is_version_of CurrentState

        Saves progress periodically so agent can recover from crashes/interruptions.
        Each checkpoint is a timestamped version capturing:
        - Task being worked on
        - Progress percentage
        - Current blockers
        - Decisions made
        - Generated outputs
        - Free-form notes

        Args:
            task: Current task being worked on
            progress: Progress percentage (0-100)
            blockers: List of current blockers
            decisions_made: Number of decisions made in this session
            outputs: Any outputs generated so far
            notes: Free-form notes about current state

        Returns:
            True if checkpoint created and saved successfully
        """
        checkpoint = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.agent_id,
            "task": task,
            "progress": progress,
            "blockers": blockers or [],
            "decisions_made": decisions_made,
            "outputs": outputs or {},
            "notes": notes,
            "is_checkpoint": True,
        }

        try:
            # Save as current state
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)

            # Also save as timestamped checkpoint
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            checkpoint_file = self.checkpoint_dir / f"checkpoint_{timestamp}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2)

            self._current_state = checkpoint

            msg = f"[{self.agent_id}] Checkpoint saved: {task} ({progress}% complete)"
            if blockers:
                msg += f", blockers: {blockers}"
            self.logger.info(msg)
            return True

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            return False

    # Backward compatibility alias
    def save_checkpoint(self,
                       task: Optional[str] = None,
                       progress: int = 0,
                       blockers: Optional[List[str]] = None,
                       decisions_made: int = 0,
                       outputs: Optional[Dict[str, Any]] = None,
                       notes: Optional[str] = None) -> bool:
        """Deprecated: Use create_checkpoint_version_of_current_state() instead"""
        return self.create_checkpoint_version_of_current_state(
            task, progress, blockers, decisions_made, outputs, notes
        )

    def load_checkpoint_created_after_crash(self) -> Optional[Dict[str, Any]]:
        """
        Load the most recent checkpoint created after crash.

        Semantic Relationship: Checkpoint created_by CrashRecoveryProcess

        Returns:
            Checkpoint dict if available, None otherwise
        """
        return self._load_state_from_checkpoint_file()

    # Backward compatibility alias
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Deprecated: Use load_checkpoint_created_after_crash() instead"""
        return self.load_checkpoint_created_after_crash()

    def checkpoint_exists_for_recovery(self) -> bool:
        """
        Check if there's a saved checkpoint available for recovery.

        Semantic Relationship: Checkpoint enables Recovery

        Returns:
            True if a checkpoint exists and is available for recovery
        """
        return self.state_file.exists() and self._load_state_from_checkpoint_file() is not None

    # Backward compatibility alias
    def has_checkpoint(self) -> bool:
        """Deprecated: Use checkpoint_exists_for_recovery() instead"""
        return self.checkpoint_exists_for_recovery()

    def get_task_from_last_checkpoint(self) -> Optional[str]:
        """
        Get the last task being worked on from checkpoint.

        Semantic Relationship: Task derived_from LastCheckpoint

        Returns:
            Task name from last checkpoint, or None if no checkpoint
        """
        state = self._load_state_from_checkpoint_file()
        if state:
            return state.get("task")
        return None

    # Backward compatibility alias
    def get_last_task(self) -> Optional[str]:
        """Deprecated: Use get_task_from_last_checkpoint() instead"""
        return self.get_task_from_last_checkpoint()

    def get_progress_from_last_checkpoint(self) -> int:
        """
        Get last recorded progress percentage from checkpoint.

        Semantic Relationship: Progress derived_from LastCheckpoint

        Returns:
            Progress percentage (0-100) from last checkpoint, or 0 if none
        """
        state = self._load_state_from_checkpoint_file()
        if state:
            return state.get("progress", 0)
        return 0

    # Backward compatibility alias
    def get_progress(self) -> int:
        """Deprecated: Use get_progress_from_last_checkpoint() instead"""
        return self.get_progress_from_last_checkpoint()

    def get_blockers_from_last_checkpoint(self) -> List[str]:
        """
        Get current blockers from last checkpoint.

        Semantic Relationship: Blockers derived_from LastCheckpoint

        Returns:
            List of current blockers from checkpoint, or empty list if none
        """
        state = self._load_state_from_checkpoint_file()
        if state:
            return state.get("blockers", [])
        return []

    # Backward compatibility alias
    def get_blockers(self) -> List[str]:
        """Deprecated: Use get_blockers_from_last_checkpoint() instead"""
        return self.get_blockers_from_last_checkpoint()

    def load_all_checkpoints_created_in_session(self) -> List[Dict[str, Any]]:
        """
        Load all historical checkpoint versions created in this session.

        Semantic Relationship: Checkpoints are_versions_of SessionHistory

        Returns:
            List of all checkpoint dicts in chronological order, or empty list if none
        """
        checkpoints = []
        if self.checkpoint_dir.exists():
            for checkpoint_file in sorted(self.checkpoint_dir.glob("checkpoint_*.json")):
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoints.append(json.load(f))
                except Exception as e:
                    self.logger.warning(f"Could not load checkpoint {checkpoint_file}: {e}")
        return checkpoints

    # Backward compatibility alias
    def get_all_checkpoints(self) -> List[Dict[str, Any]]:
        """Deprecated: Use load_all_checkpoints_created_in_session() instead"""
        return self.load_all_checkpoints_created_in_session()

    def clear_checkpoint_and_mark_session_complete(self) -> bool:
        """
        Clear the current checkpoint and mark session as complete.

        Semantic Relationship: Clear checkpoint → Marks session_complete

        When cleared, indicates the agent has finished its task and no recovery is needed.

        Returns:
            True if checkpoint cleared successfully, False otherwise
        """
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            self._current_state = None
            self.logger.info(f"[{self.agent_id}] Checkpoint cleared, session marked complete")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear checkpoint: {e}")
            return False

    # Backward compatibility alias
    def clear_checkpoint(self) -> bool:
        """Deprecated: Use clear_checkpoint_and_mark_session_complete() instead"""
        return self.clear_checkpoint_and_mark_session_complete()

    def print_recovery_info_from_checkpoint(self) -> None:
        """
        Print human-readable recovery information from checkpoint.

        Semantic Relationship: Recovery information derived_from Checkpoint

        Displays all relevant recovery details including task, progress, blockers, and next steps.
        """
        state = self._load_state_from_checkpoint_file()
        if not state:
            print(f"\nNo checkpoint for {self.agent_id}")
            return

        print(f"\n{'='*70}")
        print(f"SESSION RECOVERY INFO - {self.agent_id}")
        print(f"{'='*70}\n")

        print(f"Last Activity: {state.get('timestamp', 'unknown')}")
        print(f"Task: {state.get('task', 'none')}")
        print(f"Progress: {state.get('progress', 0)}%")

        blockers = state.get('blockers', [])
        if blockers:
            print(f"Blockers: {blockers}")

        print(f"Decisions Made: {state.get('decisions_made', 0)}")

        notes = state.get('notes')
        if notes:
            print(f"Notes: {notes}")

        print(f"\nRecovery: Run initialize() to reload context")
        print(f"         Then resume from {state.get('progress', 0)}%\n")
        print(f"{'='*70}\n")

    # Backward compatibility alias
    def print_recovery_info(self) -> None:
        """Deprecated: Use print_recovery_info_from_checkpoint() instead"""
        return self.print_recovery_info_from_checkpoint()

    def _load_state_from_checkpoint_file(self) -> Optional[Dict[str, Any]]:
        """
        Load state from checkpoint file (internal).

        Semantic Relationship: State derived_from CheckpointFile
        """
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load state: {e}")
        return None

    # Backward compatibility alias for internal use
    def _load_state(self) -> Optional[Dict[str, Any]]:
        """Deprecated internal method: Use _load_state_from_checkpoint_file()"""
        return self._load_state_from_checkpoint_file()


class CheckpointRecovery:
    """
    Helper: derive a resume-PLAN from a crash CHECKPOINT (renamed from SessionRecovery 2026-07-07 to
    end the class-name collision with core/state/session_recovery.py's SessionRecovery, a DIFFERENT
    concern -- session-history recovery from local files; arch-triage P2). This one is checkpoint-scoped.

    Semantic Relationship: Recovery derived_from Checkpoint

    Provides quick snapshot of what needs to be resumed by analyzing checkpoint state.
    """

    @staticmethod
    def derive_recovery_plan_from_checkpoint(agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Derive a recovery plan for the agent from its checkpoint.

        Semantic Relationship: RecoveryPlan derived_from Checkpoint

        Generates recovery plan showing where agent should resume from, what was being done,
        and what blockers need to be addressed.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Recovery plan dict if checkpoint exists, None otherwise
        """
        state_manager = SessionState(agent_id)
        checkpoint = state_manager.load_checkpoint_created_after_crash()

        if not checkpoint:
            return None

        return {
            "agent_id": agent_id,
            "should_resume": True,
            "task": checkpoint.get("task"),
            "resume_from_progress": checkpoint.get("progress", 0),
            "blockers_to_address": checkpoint.get("blockers", []),
            "previous_decisions": checkpoint.get("decisions_made", 0),
            "timestamp": checkpoint.get("timestamp"),
            "notes": checkpoint.get("notes"),
        }

    @staticmethod
    def get_recovery_plan(agent_id: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Use derive_recovery_plan_from_checkpoint() instead"""
        return CheckpointRecovery.derive_recovery_plan_from_checkpoint(agent_id)

    @staticmethod
    def print_recovery_summary_for_agent(agent_id: str) -> None:
        """
        Print summary of what needs recovery for agent.

        Semantic Relationship: Summary derived_from RecoveryPlan

        Displays formatted recovery information including task, progress, blockers, and next steps.
        """
        recovery_plan = CheckpointRecovery.derive_recovery_plan_from_checkpoint(agent_id)

        if not recovery_plan:
            print(f"No recovery needed for {agent_id}")
            return

        print(f"\n{'='*70}")
        print(f"RECOVERY NEEDED - {agent_id}")
        print(f"{'='*70}\n")

        print(f"Task: {recovery_plan['task']}")
        print(f"Resume from: {recovery_plan['resume_from_progress']}% complete")
        print(f"Previous work: {recovery_plan['previous_decisions']} decisions made")

        if recovery_plan['blockers_to_address']:
            print(f"Blockers to address: {recovery_plan['blockers_to_address']}")

        print(f"\nTo resume:")
        print(f"  1. initialize('{agent_id}')")
        print(f"  2. context = api.load_context_derived_from_startup_sources()")
        print(f"  3. state = SessionState('{agent_id}').load_checkpoint_created_after_crash()")
        print(f"  4. Resume from progress: {recovery_plan['resume_from_progress']}%\n")
        print(f"{'='*70}\n")

    @staticmethod
    def print_recovery_summary(agent_id: str) -> None:
        """Deprecated: Use print_recovery_summary_for_agent() instead"""
        return CheckpointRecovery.print_recovery_summary_for_agent(agent_id)
