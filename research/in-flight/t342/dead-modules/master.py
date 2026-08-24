"""
Master State Machine - Traffic Controller v2
==========================================
Lightweight Python script that manages handoffs between Generator and Analyst.

Features:
- VRAM monitoring
- Loop prevention (3 fails = pivot)
- Automatic garbage collection on resource pressure
"""

import json
import os
import sys
import time
import subprocess
import gc
from enum import Enum
from typing import Dict, Optional
from datetime import datetime

sys.path.insert(0, r'E:\AI-Setup')

from blackboard import Blackboard, init_blackboard, PHASE_IDLE, PHASE_PLANNING, PHASE_REVIEW, PHASE_EXECUTING, PHASE_VERIFYING, PHASE_DONE, PHASE_ERROR
from session_logger import log
from model_lifecycle import ModelLifecycleManager, Priority
from escalation import get_escalation_manager, Tier

# Complexity thresholds for Analyst "Co-Sign"
COMPLEXITY_STEPS_THRESHOLD = 5  # If > 5 steps, mark as complex
COMPLEXITY_CODE_LINES_THRESHOLD = 50  # If proposal has > 50 lines of code, mark as complex


def get_vram_usage():
    """Get VRAM usage in GB. Returns None if unavailable."""
    try:
        # Try AMD ROCm (WSL2)
        result = subprocess.run(
            ['wsl', '-d', 'Ubuntu-24.04', '-e', 'rocm-smi', '--showid', '--json'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for gpu_id, info in data.items():
                if 'vram_used' in info:
                    return float(info['vram_used'].replace('MB', '')) / 1024  # Convert to GB
    except:
        pass
    
    try:
        # Try NVIDIA
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return float(result.stdout.strip()) / 1024  # MB to GB
    except:
        pass
    
    return None


class IntentPriority(Enum):
    """Task intent priorities for routing"""
    HIGH_REASONING = "HIGH_REASONING"      # Generator + Analyst
    VISION_PRIORITY = "VISION_PRIORITY"    # Florence-2 active
    LOGIC_MAX = "LOGIC_MAX"                # Max VRAM for code
    VIDEO_BURST = "VIDEO_BURST"           # Video generation
    IDLE = "IDLE"                         # Nothing active


def resolve_intent(prompt_metadata: dict) -> IntentPriority:
    """
    Determines the VRAM budget based on user intent.
    
    This is the "Smart Router" logic for JIT inference.
    
    Args:
        prompt_metadata: Dict with flags like:
            - has_image: bool
            - has_video: bool
            - is_code_heavy: bool
            - is_troubleshooting: bool
    
    Returns:
        IntentPriority enum value
    """
    # Video generation has highest priority - kill everything
    if prompt_metadata.get("has_video"):
        return IntentPriority.VIDEO_BURST
    
    # Vision tasks - load Florence-2
    if prompt_metadata.get("has_image") or prompt_metadata.get("is_vision_task"):
        return IntentPriority.VISION_PRIORITY
    
    # Code-heavy tasks - maximize reasoning VRAM
    if prompt_metadata.get("is_code_heavy") or prompt_metadata.get("is_complex"):
        return IntentPriority.LOGIC_MAX
    
    # Default - keep generator + analyst
    return IntentPriority.HIGH_REASONING


class Master:
    """
    Traffic controller with VRAM monitoring and loop prevention.
    """
    
    def __init__(self):
        self.bb = init_blackboard()
        self.running = False
        self.poll_interval = 0.5  # 500ms
        self.fail_counts = {}  # task -> fail_count
        self.max_fails = 3
        self.vram_threshold = 14.5  # GB
        self.last_vram_check = 0
        
        # VRAM Lifecycle Manager (Swap-Shop)
        self.lifecycle = ModelLifecycleManager()
        
        # Escalation Manager (Multi-Layer Review)
        self.escalation = get_escalation_manager()
        self.escalation_tier = Tier.OPENCODE  # Default: OpenCode review
        self.escalation_threshold = 3  # Escalate after 3 failures
    
    def start(self):
        log("master_started", "Master state machine v2 started", source="master")
        self.running = True
        self.run_loop()
    
    def stop(self):
        self.running = False
        log("master_stopped", "Master stopped", source="master")
    
    def run_loop(self):
        while self.running:
            try:
                self.tick()
            except Exception as e:
                log("master_error", str(e), source="master")
            time.sleep(self.poll_interval)
    
    def tick(self):
        state = self.bb.get_state()
        
        # Check VRAM every 5 seconds
        if time.time() - self.last_vram_check > 5:
            self.check_vram()
            self.last_vram_check = time.time()
        
        if state == PHASE_IDLE:
            pass
        elif state == PHASE_PLANNING:
            self.on_planning()
        elif state == PHASE_REVIEW:
            self.on_review()
        elif state == PHASE_EXECUTING:
            self.on_executing()
        elif state == PHASE_VERIFYING:
            self.on_verifying()
        elif state == PHASE_DONE:
            self.on_done()
        elif state == PHASE_ERROR:
            self.on_error()
    
    def check_vram(self):
        """Monitor VRAM usage with lifecycle manager"""
        vram = get_vram_usage()
        
        # Use lifecycle manager for smarter monitoring
        status = self.lifecycle.check_vram_and_warn()
        
        if status["status"] in ["warning", "critical", "emergency"]:
            log("vram_warning", 
                f"VRAM at {status['usage_gb']}GB ({status['status']}) - {status['available_gb']}GB free",
                source="master")
        
        if status["status"] == "critical":
            log("vram_critical", "Forcing garbage collection", source="master")
            gc.collect()
        
        if status["status"] == "emergency":
            # Emergency: unload vision model if loaded
            if self.lifecycle.vision_loaded:
                log("vram_emergency", "Unloading vision model", source="master")
                self.lifecycle.unload_vision_model()
                gc.collect()
    
    def on_planning(self):
        """Generator is writing proposal"""
        log("master_phase", "Generator is planning", source="master")
    
    def on_review(self):
        """Analyst reviewing proposal"""
        proposal = self.bb.get_proposal()
        if not proposal:
            return
        
        # ANALYST CO-SIGN: Check complexity and write flag file
        self._check_complexity(proposal)
        
        # Check for loop prevention
        title = proposal.get("title", "unknown")
        verdict = self.bb.get_verdict()
        
        if verdict.get("status") == "FAIL":
            self.fail_counts[title] = self.fail_counts.get(title, 0) + 1
            
            if self.fail_counts[title] >= self.max_fails:
                log("loop_prevented", f"Task '{title}' failed {self.fail_counts[title]} times - forcing pivot", 
                    source="master")
                
                # Force a pivot by clearing the proposal
                self.bb.reset()
                self.fail_counts[title] = 0  # Reset for next attempt
        elif verdict.get("status") == "PASS":
            # Reset fail count on success
            self.fail_counts[title] = 0
    
    def _check_complexity(self, proposal):
        """
        ANALYST CO-SIGN: If proposal is complex, write a flag file.
        
        This tells the Analyst: "This is a complex script. Do not PASS
        unless you have verified the library imports and dependencies."
        """
        complexity_file = r"E:\AI-Setup\blackboard_data\complexity.json"
        
        step_count = len(proposal.get("steps", []))
        
        # Count code lines across all steps
        code_lines = 0
        for step in proposal.get("steps", []):
            code = step.get("target", "")
            code_lines += code.count('\n') + 1 if code else 0
        
        is_complex = (step_count > COMPLEXITY_STEPS_THRESHOLD or 
                     code_lines > COMPLEXITY_CODE_LINES_THRESHOLD)
        
        complexity_data = {
            "is_complex": is_complex,
            "step_count": step_count,
            "code_lines": code_lines,
            "threshold_steps": COMPLEXITY_STEPS_THRESHOLD,
            "threshold_lines": COMPLEXITY_CODE_LINES_THRESHOLD,
            "warning": "COMPLEX PROPOSAL: Verify all library imports before PASS" if is_complex else None
        }
        
        with open(complexity_file, 'w') as f:
            json.dump(complexity_data, f, indent=2)
        
        if is_complex:
            log("complexity_warning", 
                f"Complex proposal detected: {step_count} steps, {code_lines} lines",
                source="master", data=complexity_data)
        
        return is_complex
    
    def on_executing(self):
        """Generator executing"""
        proposal = self.bb.get_proposal()
        log("master_phase", f"Executing: {proposal.get('title', 'Unknown')}", source="master")
    
    def on_verifying(self):
        """Analyst verifying"""
        log("master_phase", "Analyst verifying execution", source="master")
    
    def on_done(self):
        """Task complete"""
        proposal = self.bb.get_proposal()
        title = proposal.get("title", "unknown") if proposal else "unknown"
        log("master_complete", f"Task complete: {title}", source="master")
        self.fail_counts[title] = 0  # Reset on success
    
    def on_error(self):
        """Error occurred - capture vision context and check escalation"""
        verdict = self.bb.get_verdict()
        proposal = self.bb.get_proposal()
        title = proposal.get("title", "unknown") if proposal else "unknown"
        
        log("master_error_phase", verdict.get("reason", "Unknown error"), 
            source="master", data={"task": title})
        
        # VISION SIGNAL: Capture screen and analyze for visual context
        self._capture_vision_context()
        
        # Log to errors_and_faults.jsonl
        try:
            from error_documentation import ErrorDoc
            doc = ErrorDoc()
            doc.log_error("master", "task_failed", verdict.get("reason", "Unknown"), "high")
        except:
            pass
        
        # Check if escalation is needed
        self.fail_counts[title] = self.fail_counts.get(title, 0) + 1
        
        if self.escalation.should_escalate(
            retry_count=self.fail_counts[title],
            tier_threshold=self.escalation_threshold
        ):
            self._trigger_escalation(title, verdict, proposal)
    
    def _trigger_escalation(self, title: str, verdict: Dict, proposal: Dict):
        """
        Trigger escalation to external review API.
        
        Called when local agent fails after threshold retries.
        """
        log("escalation_triggered", 
            f"Escalating after {self.fail_counts[title]} failures to {self.escalation_tier.name}",
            source="master",
            data={"task": title})
        
        # Get vision context if available
        vision_data = None
        try:
            active_buffer = r"E:\AI-Setup\blackboard_data\active_buffer.json"
            if os.path.exists(active_buffer):
                with open(active_buffer, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            if data.get("type") == "vision_context":
                                vision_data = data.get("vision", {})
                                break
                        except:
                            pass
        except:
            pass
        
        # Trigger escalation
        result = self.escalation.escalate(
            tier=self.escalation_tier,
            local_context=f"Task: {title}\nProposal: {json.dumps(proposal, indent=2)}",
            observed_failure=verdict.get("reason", "Unknown error"),
            local_attempt=f"Failed after {self.fail_counts[title]} attempts",
            retry_count=self.fail_counts[title],
            vision_data=vision_data,
            code_snippet=proposal.get("steps", [{}])[0].get("target", "") if proposal.get("steps") else None
        )
        
        if result:
            log("escalation_success", 
                f"Response received from {self.escalation_tier.name}",
                source="master",
                data={"request_id": result.get("request_id")})
        else:
            log("escalation_failed", 
                "External API unavailable",
                source="master")
    
    def _capture_vision_context(self):
        """
        VISION-SIGNAL HANDOFF
        
        When an error occurs, capture the screen and run vision analysis.
        The Analyst receives this context to understand WHAT the error
        looks like visually, not just the text output.
        
        Flow:
        1. Capture active window screenshot
        2. Run Florence-2 analysis (OCR + Caption + Detection)
        3. Write to active_buffer.json for Analyst
        4. Log vision context captured
        """
        active_buffer = r"E:\AI-Setup\blackboard_data\active_buffer.json"
        
        try:
            from vision_engine import (
                capture_active_window, 
                get_screen_context_for_analyst,
                encode_image_base64
            )
            
            # Capture screen
            screenshot = capture_active_window()
            if screenshot is None:
                log("vision_capture", "Failed to capture screenshot", source="master")
                return
            
            # Get comprehensive vision context
            context = get_screen_context_for_analyst(screenshot)
            
            if "error" in context:
                log("vision_error", context["error"], source="master")
                return
            
            # Write to active_buffer.json (append vision context)
            buffer_data = {
                "type": "vision_context",
                "vision": {
                    "screenshot_b64": context.get("screenshot_b64", ""),
                    "caption": context.get("caption", ""),
                    "extracted_text": context.get("extracted_text", ""),
                    "error_detection": context.get("error_detection", {}),
                    "ui_elements_count": context.get("ui_elements_count", 0)
                },
                "timestamp": context.get("timestamp", ""),
                "model": context.get("vision_model", "")
            }
            
            with open(active_buffer, 'a') as f:
                f.write(json.dumps(buffer_data) + "\n")
            
            # Log success
            log("vision_context_captured", 
                f"Error visual context captured - {context.get('error_detection', {}).get('confidence', 'unknown')} confidence",
                source="master", 
                data={
                    "has_error": context.get("error_detection", {}).get("has_error", False),
                    "error_keywords": context.get("error_detection", {}).get("error_keywords", []),
                    "caption": context.get("caption", "")[:100]
                })
            
            print(f"[master] Vision context saved to active_buffer.json")
            
        except Exception as e:
            log("vision_capture_failed", str(e), source="master")


def check_prerequisites():
    """Check all prerequisites"""
    checks = []
    
    # Redis
    try:
        result = subprocess.run(['docker', 'exec', 'ai-redis', 'redis-cli', 'ping'],
                              capture_output=True, text=True, timeout=5)
        checks.append(("Redis", "OK" if 'PONG' in result.stdout else "FAILED"))
    except:
        checks.append(("Redis", "NOT RESPONDING"))
    
    # Ollama
    try:
        result = subprocess.run(['docker', 'exec', 'ai-ollama', 'ollama', 'list'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            models = [l for l in result.stdout.split('\n') if 'NAME' not in l and l.strip()]
            checks.append(("Ollama", f"OK ({len(models)} models)"))
        else:
            checks.append(("Ollama", "FAILED"))
    except:
        checks.append(("Ollama", "NOT RESPONDING"))
    
    # Blackboard
    try:
        bb = init_blackboard()
        checks.append(("Blackboard", f"OK ({bb.get_state()})"))
    except Exception as e:
        checks.append(("Blackboard", f"FAILED: {e}"))
    
    # VRAM
    vram = get_vram_usage()
    if vram:
        checks.append(("VRAM", f"{vram:.1f}GB"))
    else:
        checks.append(("VRAM", "Cannot detect"))
    
    return checks


if __name__ == "__main__":
    print("=" * 50)
    print("Master State Machine v2")
    print("=" * 50)
    
    print("\nPrerequisites:")
    for name, status in check_prerequisites():
        print(f"  {name}: {status}")
    
    print("\nStarting master loop...")
    print("Press Ctrl+C to stop\n")
    
    master = Master()
    try:
        master.start()
    except KeyboardInterrupt:
        master.stop()
        print("\nMaster stopped.")
