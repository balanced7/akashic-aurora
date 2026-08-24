"""
Blackboard Architecture - Hybrid Signal & Payload v2
================================================
Uses local files for state (fast, reliable) + Redis for signals/locks.

Signal: Redis Key - "proposal_ready" flag for atomic reads
Payload: Local JSON file - The actual proposal content

Key improvements:
- proposal_ready flag for atomic reads (Analyst won't read mid-write)
- source tags in JSONL for debugging
- Lightweight Master state machine (not an LLM)
"""

import json
import os
import time
import uuid
import hashlib
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
import redis

# Paths
BLACKBOARD_DIR = r"E:\AI-Setup\blackboard_data"
PAYLOAD_FILE = os.path.join(BLACKBOARD_DIR, "proposal.json")
STATE_FILE = os.path.join(BLACKBOARD_DIR, "state.json")
VERDICT_FILE = os.path.join(BLACKBOARD_DIR, "verdict.json")
HISTORY_DIR = os.path.join(BLACKBOARD_DIR, "history")

# Redis Keys
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_SIGNAL_KEY = "blackboard:signal"
REDIS_PROPOSAL_READY = "blackboard:proposal_ready"
REDIS_VERDICT_READY = "blackboard:verdict_ready"

# Phases
PHASE_IDLE = "IDLE"
PHASE_PLANNING = "PLANNING"
PHASE_REVIEW = "REVIEW"
PHASE_EXECUTING = "EXECUTING"
PHASE_VERIFYING = "VERIFYING"
PHASE_DONE = "DONE"
PHASE_ERROR = "ERROR"

ALL_PHASES = [PHASE_IDLE, PHASE_PLANNING, PHASE_REVIEW, PHASE_EXECUTING, PHASE_VERIFYING, PHASE_DONE, PHASE_ERROR]


def _ensure_dirs():
    """Ensure blackboard directories exist"""
    os.makedirs(BLACKBOARD_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)


class Blackboard:
    """
    Hybrid blackboard using local files for state + Redis for signals/locks.
    
    Locking protocol:
    1. Generator writes proposal.json
    2. Generator sets blackboard:proposal_ready = "1" (atomic)
    3. Analyst sees ready flag, reads proposal.json
    4. Analyst sets blackboard:verdict_ready = "1"
    5. Generator sees verdict ready, reads verdict.json
    """
    
    def __init__(self, host=REDIS_HOST, port=REDIS_PORT):
        self.host = host
        self.port = port
        self._redis = None
        self._ensure_connection()
        _ensure_dirs()
    
    def _ensure_connection(self):
        """Try to connect to Redis, but don't fail if unavailable"""
        try:
            self._redis = redis.Redis(host=self.host, port=self.port, db=0, 
                                     decode_responses=True, socket_connect_timeout=2)
            self._redis.ping()
        except (redis.ConnectionError, redis.TimeoutError):
            self._redis = None
            print("[blackboard] Redis unavailable - running in local-only mode")
    
    def _set_redis_flag(self, key: str, value: str, ex: int = 3600):
        """Set Redis flag (best effort)"""
        if self._redis:
            try:
                self._redis.set(key, value, ex=ex)
            except:
                pass
    
    def _get_redis_flag(self, key: str) -> Optional[str]:
        """Get Redis flag"""
        if self._redis:
            try:
                return self._redis.get(key)
            except:
                return None
        return None
    
    def initialize(self, force=False):
        """
        Initialize blackboard state.
        
        GHOST PROPOSAL PURGE: Always delete proposal.json and verdict.json
        to prevent stale data from previous sessions being misread.
        """
        _ensure_dirs()
        
        if not force and os.path.exists(STATE_FILE):
            return False
        
        state = {
            "phase": PHASE_IDLE,
            "turn": 0,
            "initialized_at": datetime.now().isoformat(),
            "version": "2.0"
        }
        
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        # GHOST PROPOSAL PURGE: Physically delete stale files
        # This ensures that if a Redis signal is tripped by glitch,
        # the Analyst is guaranteed to be looking at fresh data
        for stale_file in [PAYLOAD_FILE, VERDICT_FILE]:
            if os.path.exists(stale_file):
                os.remove(stale_file)
                print(f"[blackboard] Purged stale file: {stale_file}")
        
        # Archive old history (keep last 10 turns only)
        self._prune_history(keep=10)
        
        # Clear Redis flags
        self._set_redis_flag(REDIS_PROPOSAL_READY, "0")
        self._set_redis_flag(REDIS_VERDICT_READY, "0")
        
        return True
    
    def _prune_history(self, keep=10):
        """Prune old history files, keeping only the most recent N"""
        if not os.path.exists(HISTORY_DIR):
            return
        
        history_files = sorted(
            [f for f in os.listdir(HISTORY_DIR) if f.startswith('turn_') and f.endswith('.json')],
            reverse=True
        )
        
        for old_file in history_files[keep:]:
            try:
                os.remove(os.path.join(HISTORY_DIR, old_file))
                print(f"[blackboard] Pruned history: {old_file}")
            except:
                pass
    
    def get_state(self) -> str:
        """Get current phase"""
        if not os.path.exists(STATE_FILE):
            return PHASE_IDLE
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        return state.get("phase", PHASE_IDLE)
    
    def get_turn(self) -> int:
        """Get current turn number"""
        if not os.path.exists(STATE_FILE):
            return 0
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        return state.get("turn", 0)
    
    def get_proposal(self) -> Dict:
        """Get current proposal (only if ready flag is set)"""
        # Check if proposal is ready to read
        ready = self._get_redis_flag(REDIS_PROPOSAL_READY)
        if ready != "1":
            return {}
        
        if not os.path.exists(PAYLOAD_FILE):
            return {}
        with open(PAYLOAD_FILE, 'r') as f:
            return json.load(f)
    
    def get_verdict(self) -> Dict:
        """Get current verdict (only if ready flag is set)"""
        # Check if verdict is ready to read
        ready = self._get_redis_flag(REDIS_VERDICT_READY)
        if ready != "1":
            return {"status": "PENDING", "reason": ""}
        
        if not os.path.exists(VERDICT_FILE):
            return {"status": "PENDING", "reason": ""}
        with open(VERDICT_FILE, 'r') as f:
            return json.load(f)
    
    def _save_state(self, phase: str):
        """Save state to file"""
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        state["phase"] = phase
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _increment_turn(self):
        """Increment turn counter"""
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        state["turn"] = state.get("turn", 0) + 1
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return state["turn"]
    
    def transition_to(self, new_phase: str, agent: str, reason: str = "") -> bool:
        """Transition to new phase"""
        if new_phase not in ALL_PHASES:
            raise ValueError(f"Invalid phase: {new_phase}")
        
        old_phase = self.get_state()
        self._save_state(new_phase)
        print(f"[blackboard] Phase: {old_phase} -> {new_phase} ({reason})")
        return True
    
    def submit_proposal(self, agent: str, title: str, description: str, 
                       steps: List[Dict], metadata: Dict = None) -> bool:
        """
        Submit a proposal with proper locking.
        Writes to file, then sets proposal_ready flag.
        """
        current = self.get_state()
        if current not in [PHASE_IDLE, PHASE_DONE, PHASE_ERROR]:
            return False
        
        turn = self._increment_turn()
        
        proposal = {
            "turn": turn,
            "agent": agent,
            "title": title,
            "description": description,
            "steps": steps,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4()),
            "checksum": ""
        }
        
        # Add checksum for integrity
        proposal["checksum"] = hashlib.sha256(
            json.dumps(proposal, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        # Clear verdict first
        with open(VERDICT_FILE, 'w') as f:
            json.dump({"status": "PENDING", "reason": ""}, f)
        
        # Write proposal to file
        with open(PAYLOAD_FILE, 'w') as f:
            json.dump(proposal, f, indent=2)
        
        # Set ready flag LAST (atomic)
        self._set_redis_flag(REDIS_PROPOSAL_READY, "1")
        self._set_redis_flag(REDIS_VERDICT_READY, "0")
        
        self.transition_to(PHASE_REVIEW, agent, f"Proposal: {title}")
        
        return True
    
    def submit_verdict(self, agent: str, status: str, reason: str, 
                      checks_performed: List[str] = None) -> bool:
        """
        Submit audit verdict with proper locking.
        """
        current = self.get_state()
        if current != PHASE_REVIEW:
            return False
        
        verdict = {
            "status": status,  # PASS, FAIL, NEEDS_WORK
            "reason": reason,
            "checks": checks_performed or [],
            "agent": agent,
            "timestamp": datetime.now().isoformat()
        }
        
        # Write verdict to file
        with open(VERDICT_FILE, 'w') as f:
            json.dump(verdict, f, indent=2)
        
        # Set verdict ready flag LAST (atomic)
        self._set_redis_flag(REDIS_VERDICT_READY, "1")
        
        if status == "PASS":
            self.transition_to(PHASE_EXECUTING, agent, reason)
        elif status == "FAIL":
            self.transition_to(PHASE_ERROR, agent, reason)
        else:
            self.transition_to(PHASE_PLANNING, agent, reason)
        
        return True
    
    def mark_execution_complete(self, agent: str, success: bool, results: Dict = None) -> bool:
        """Mark execution complete"""
        current = self.get_state()
        if current != PHASE_EXECUTING:
            return False
        
        if success:
            self.transition_to(PHASE_VERIFYING, agent, "Execution complete")
        else:
            self.transition_to(PHASE_ERROR, agent, "Execution failed")
            return True
        
        proposal = self.get_proposal()
        proposal["execution_results"] = results or {}
        proposal["execution_complete"] = True
        with open(PAYLOAD_FILE, 'w') as f:
            json.dump(proposal, f, indent=2)
        
        return True
    
    def mark_verified(self, agent: str, success: bool, details: str = "") -> bool:
        """Mark verification complete"""
        current = self.get_state()
        if current != PHASE_VERIFYING:
            return False
        
        if success:
            self.transition_to(PHASE_DONE, agent, details)
        else:
            self.transition_to(PHASE_ERROR, agent, details)
        return True
    
    def reset(self) -> bool:
        """Reset to IDLE (archive current turn)"""
        current = self.get_state()
        if current == PHASE_IDLE:
            return True
        
        turn = self.get_turn()
        history_file = os.path.join(HISTORY_DIR, f"turn_{turn}.json")
        
        archive = {
            "turn": turn,
            "proposal": self.get_proposal(),
            "verdict": self.get_verdict(),
            "final_state": current,
            "archived_at": datetime.now().isoformat()
        }
        
        with open(history_file, 'w') as f:
            json.dump(archive, f, indent=2)
        
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        state["phase"] = PHASE_IDLE
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        if os.path.exists(PAYLOAD_FILE):
            os.remove(PAYLOAD_FILE)
        
        with open(VERDICT_FILE, 'w') as f:
            json.dump({"status": "PENDING", "reason": ""}, f)
        
        self._set_redis_flag(REDIS_PROPOSAL_READY, "0")
        self._set_redis_flag(REDIS_VERDICT_READY, "0")
        
        return True
    
    def full_reset(self) -> bool:
        """Full reset"""
        for f in [STATE_FILE, PAYLOAD_FILE, VERDICT_FILE]:
            if os.path.exists(f):
                os.remove(f)
        
        if os.path.exists(HISTORY_DIR):
            for f in os.listdir(HISTORY_DIR):
                os.remove(os.path.join(HISTORY_DIR, f))
        
        self.initialize(force=True)
        return True
    
    def get_fault_learnings(self) -> List[Dict]:
        """Get fault learnings from errors_and_faults.jsonl"""
        faults = []
        fault_file = r"E:\AI-Setup\session_logs\errors_and_faults.jsonl"
        
        if os.path.exists(fault_file):
            with open(fault_file, 'r') as f:
                for line in f:
                    try:
                        faults.append(json.loads(line.strip()))
                    except:
                        pass
        
        return faults[-20:]
    
    def is_proposal_ready(self) -> bool:
        """Check if proposal is ready to read"""
        return self._get_redis_flag(REDIS_PROPOSAL_READY) == "1"
    
    def is_verdict_ready(self) -> bool:
        """Check if verdict is ready to read"""
        return self._get_redis_flag(REDIS_VERDICT_READY) == "1"
    
    def clear_proposal_ready(self):
        """Clear proposal ready flag (after reading)"""
        self._set_redis_flag(REDIS_PROPOSAL_READY, "0")
    
    def clear_verdict_ready(self):
        """Clear verdict ready flag (after reading)"""
        self._set_redis_flag(REDIS_VERDICT_READY, "0")
    
    def get_status(self) -> Dict:
        """Get full blackboard status"""
        return {
            "state": self.get_state(),
            "turn": self.get_turn(),
            "proposal_ready": self.is_proposal_ready(),
            "verdict_ready": self.is_verdict_ready(),
            "proposal_title": self.get_proposal().get("title", ""),
            "verdict_status": self.get_verdict().get("status", "PENDING"),
            "fault_learnings_count": len(self.get_fault_learnings())
        }
    
    def wait_for_verdict(self, timeout=300, poll_interval=1) -> Dict:
        """Wait for analyst verdict by polling Redis flag"""
        start = time.time()
        
        while time.time() - start < timeout:
            if self.is_verdict_ready():
                verdict = self.get_verdict()
                self.clear_verdict_ready()
                return verdict
            time.sleep(poll_interval)
        
        return {"status": "TIMEOUT", "reason": "Waited too long for verdict"}
    
    def wait_for_proposal(self, timeout=300, poll_interval=1) -> Dict:
        """Wait for generator proposal (for Analyst)"""
        start = time.time()
        
        while time.time() - start < timeout:
            if self.is_proposal_ready():
                proposal = self.get_proposal()
                self.clear_proposal_ready()
                return proposal
            time.sleep(poll_interval)
        
        return {}
    
    def wait_for_phase(self, phase: str, timeout=300, poll_interval=1) -> bool:
        """Wait for specific phase"""
        start = time.time()
        while time.time() - start < timeout:
            if self.get_state() == phase:
                return True
            time.sleep(poll_interval)
        return False


def init_blackboard() -> Blackboard:
    """Initialize and return blackboard instance"""
    bb = Blackboard()
    bb.initialize()
    return bb


if __name__ == "__main__":
    bb = init_blackboard()
    print("Blackboard initialized:")
    print(json.dumps(bb.get_status(), indent=2))
