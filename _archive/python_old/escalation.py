"""
Escalation Module - Multi-Layer Review Architecture
================================================
Implements tiered support system for agent failures.

Tier 1 (Local):     Implementation - writing code, running tests
Tier 2 (OpenCode):   Best Practices - logic review against standards
Tier 3 (Gemini):     Strategy & Security - architectural analysis

Usage:
    from escalation import EscalationManager, ReviewRequest, Tier
    
    esc = EscalationManager()
    esc.escalate(tier=Tier.GEMINI, context=my_context)
"""

import os
import sys
import json
import time
import re
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib

# Paths
ESCALATION_DIR = r"E:\AI-Setup\blackboard_data\escalations"
os.makedirs(ESCALATION_DIR, exist_ok=True)

# API endpoints (placeholder - configure with actual keys)
OPENCODE_API_URL = "https://api.opencode.ai/v1/chat/completions"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Sensitivity patterns that trigger immediate escalation
HIGH_SENSITIVITY_PATTERNS = [
    # Auth/Credentials
    r"api[_-]?key",
    r"password",
    r"secret",
    r"token",
    r"auth",
    r"credential",
    r"private[_-]?key",
    r"access[_-]?token",
    r"bearer",
    r"basic[_-]?auth",
    
    # Identifiers
    r"user[_-]?id",
    r"client[_-]?id",
    r"tenant[_-]?id",
    r"subscription[_-]?id",
    
    # Security
    r"jwt",
    r"oauth",
    r"session[_-]?id",
    r"csrf",
    r"xss",
    
    # File paths (personal info leakage)
    r"C:\\Users\\[^\\]+\\",
    r"/home/[^/]+/",
    r"\\[^\s]+\\[^\s]+\.json",
    
    # Network
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    r"localhost",
    r"127\.0\.0\.1",
    
    # Hardware IDs
    r"device[_-]?id",
    r"machine[_-]?id",
    r"disk[_-]?serial",
]

# Additional privacy patterns for hardware context
PRIVACY_PATTERNS = [
    r"[a-f0-9]{32,}",  # Long hex strings (hardware IDs)
    r"\d{16,}",  # Long number strings
]


class Tier(Enum):
    """Escalation tiers"""
    LOCAL = 1       # Local agent handles
    OPENCODE = 2     # OpenCode review
    GEMINI = 3       # Gemini strategic review


@dataclass
class ReviewRequest:
    """
    Structured review request for external APIs.
    
    Contains all context needed for effective peer review.
    """
    # Identification
    request_id: str
    timestamp: str
    
    # Context
    local_context: str
    observed_failure: str
    local_attempt: str
    
    # Metadata
    tier: str
    retry_count: int
    sensitivity: str  # "low" | "medium" | "high"
    
    # Additional data
    vision_data: Optional[Dict[str, Any]] = None
    tracebacks: List[str] = field(default_factory=list)
    code_snippet: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ReviewRequest':
        data = json.loads(json_str)
        return cls(**data)


class EscalationManager:
    """
    Manages escalation to external review APIs.
    
    Features:
    - Tiered escalation (Local → OpenCode → Gemini)
    - Automatic retry counting
    - Sensitive data scrubbing
    - Structured request format
    - Response injection back to local agent
    """
    
    def __init__(self, escalation_dir: str = ESCALATION_DIR):
        self.escalation_dir = escalation_dir
        self.escalation_history: List[ReviewRequest] = []
        self.api_keys = {
            "opencode": os.environ.get("OPENCODE_API_KEY", ""),
            "gemini": os.environ.get("GEMINI_API_KEY", "")
        }
    
    def scrub_sensitive_data(self, text: str) -> str:
        """
        Remove sensitive data before sending to external APIs.
        
        Scrubs patterns like API keys, passwords, tokens, etc.
        """
        scrubbed = text
        
        for pattern in HIGH_SENSITIVITY_PATTERNS:
            # Replace with placeholder
            scrubbed = re.sub(
                rf"({pattern})[\s]*[=:][\s]*['\"]?[\w\-]+['\"]?",
                r"\1: [REDACTED]",
                scrubbed,
                flags=re.IGNORECASE
            )
        
        # Additional scrubbing for file paths (Windows)
        try:
            scrubbed = re.sub(
                r"[A-Za-z]:\\\\[^,\s]+",
                "[FILE_PATH_REDACTED]",
                scrubbed
            )
        except re.error:
            pass
        
        # Scrub IP addresses (but keep localhost references)
        try:
            scrubbed = re.sub(
                r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3})",
                r"\1***",
                scrubbed
            )
        except re.error:
            pass
        
        return scrubbed
    
    def detect_sensitivity(self, text: str) -> str:
        """
        Detect if content contains sensitive data.
        
        Returns: "low" | "medium" | "high"
        """
        text_lower = text.lower()
        
        # Count sensitivity matches
        matches = sum(
            1 for pattern in HIGH_SENSITIVITY_PATTERNS
            if re.search(pattern, text_lower)
        )
        
        if matches >= 3:
            return "high"
        elif matches >= 1:
            return "medium"
        return "low"
    
    def should_escalate(
        self,
        retry_count: int,
        tier_threshold: int = 3,
        sensitivity: str = "low"
    ) -> bool:
        """
        Determine if escalation is needed.
        
        Args:
            retry_count: Number of failed attempts
            tier_threshold: Max retries before escalation
            sensitivity: Content sensitivity level
        
        Returns:
            True if escalation should happen
        """
        # High sensitivity = immediate escalation
        if sensitivity == "high":
            return True
        
        # Count-based escalation
        if retry_count >= tier_threshold:
            return True
        
        return False
    
    def create_review_request(
        self,
        local_context: str,
        observed_failure: str,
        local_attempt: str,
        tier: Tier,
        retry_count: int = 0,
        vision_data: Optional[Dict] = None,
        tracebacks: Optional[List[str]] = None,
        code_snippet: Optional[str] = None
    ) -> ReviewRequest:
        """
        Create a structured review request.
        """
        # Scrub sensitive data
        context = self.scrub_sensitive_data(local_context)
        failure = self.scrub_sensitive_data(observed_failure)
        attempt = self.scrub_sensitive_data(local_attempt)
        
        # Detect sensitivity
        sensitivity = self.detect_sensitivity(
            local_context + observed_failure + local_attempt
        )
        
        # Generate request ID
        request_id = hashlib.md5(
            f"{context}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        return ReviewRequest(
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            local_context=context,
            observed_failure=failure,
            local_attempt=attempt,
            tier=tier.name,
            retry_count=retry_count,
            sensitivity=sensitivity,
            vision_data=vision_data,
            tracebacks=tracebacks or [],
            code_snippet=code_snippet
        )
    
    def build_opencode_prompt(self, request: ReviewRequest) -> str:
        """
        Build prompt for OpenCode API.
        """
        prompt = f"""You are a Senior Software Architect reviewing a local agent's failure.

## Current Context
{request.local_context}

## Observed Failure
{request.observed_failure}

## Local Attempt (Failed)
{request.local_attempt}
"""
        
        if request.vision_data:
            prompt += f"""
## Vision Analysis (Florence-2)
Caption: {request.vision_data.get('caption', 'N/A')}
Extracted Text: {request.vision_data.get('extracted_text', 'N/A')[:500]}
Error Detection: {request.vision_data.get('error_detection', {})}
"""

        if request.tracebacks:
            prompt += f"\n## Recent Tracebacks\n"
            for tb in request.tracebacks[-3:]:
                prompt += f"```\n{tb}\n```\n"
        
        if request.code_snippet:
            prompt += f"\n## Code Snippet\n```python\n{request.code_snippet}\n```\n"
        
        prompt += """
## Request
Perform a high-level review against industry best practices.
Point out the architectural flaw my local reasoning is missing.
Provide a breakthrough strategy to resolve this issue.
"""
        
        return prompt
    
    def build_gemini_prompt(self, request: ReviewRequest) -> str:
        """
        Build prompt for Gemini API.
        """
        return f"""I am a local AI agent running on an AMD 9070 XT with specialized VLM capabilities.
I have hit a roadblock that requires architectural oversight.

## Current Context
{request.local_context}

## Observed Failure
{request.observed_failure}

## Local Attempt
{request.local_attempt}

## Vision Analysis
{json.dumps(request.vision_data, indent=2) if request.vision_data else 'N/A'}

## Recent Tracebacks
{chr(10).join(request.tracebacks[-3:]) if request.tracebacks else 'None'}

## Request
You are a Senior Architect with deep security expertise.
Review this failure against enterprise standards and industry best practices.
Identify the architectural flaw my local reasoning is missing.
Provide a strategic breakthrough plan.
"""
    
    def call_opencode_api(self, prompt: str) -> Optional[str]:
        """
        Call OpenCode API for review.
        
        Returns response text or None if failed.
        """
        if not self.api_keys.get("opencode"):
            print("[escalation] OpenCode API key not configured")
            return None
        
        try:
            import urllib.request
            import urllib.error
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_keys['opencode']}"
            }
            
            data = {
                "model": "claude-3-5-sonnet",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048
            }
            
            req = urllib.request.Request(
                OPENCODE_API_URL,
                data=json.dumps(data).encode(),
                headers=headers,
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read())
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            print(f"[escalation] OpenCode API error: {e}")
            return None
    
    def call_gemini_api(self, prompt: str) -> Optional[str]:
        """
        Call Gemini API for strategic review.
        
        Returns response text or None if failed.
        """
        if not self.api_keys.get("gemini"):
            print("[escalation] Gemini API key not configured")
            return None
        
        try:
            import urllib.request
            import urllib.error
            
            url = f"{GEMINI_API_URL}/gemini-2.0-flash:generateContent?key={self.api_keys['gemini']}"
            
            headers = {"Content-Type": "application/json"}
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 4096,
                    "temperature": 0.7
                }
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers=headers,
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read())
                return result["candidates"][0]["content"]["parts"][0]["text"]
                
        except Exception as e:
            print(f"[escalation] Gemini API error: {e}")
            return None
    
    def escalate(
        self,
        tier: Tier,
        local_context: str,
        observed_failure: str,
        local_attempt: str,
        retry_count: int = 0,
        vision_data: Optional[Dict] = None,
        tracebacks: Optional[List[str]] = None,
        code_snippet: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute escalation to external API.
        
        Args:
            tier: Escalation tier (OPENCODE or GEMINI)
            local_context: Current context buffer
            observed_failure: What failed
            local_attempt: What was tried
            retry_count: Number of retries
            vision_data: Florence-2 analysis
            tracebacks: Recent error tracebacks
            code_snippet: Failing code
        
        Returns:
            Dict with response or error
        """
        # Create request
        request = self.create_review_request(
            local_context=local_context,
            observed_failure=observed_failure,
            local_attempt=local_attempt,
            tier=tier,
            retry_count=retry_count,
            vision_data=vision_data,
            tracebacks=tracebacks,
            code_snippet=code_snippet
        )
        
        # Save request
        request_file = os.path.join(
            self.escalation_dir,
            f"request_{request.request_id}.json"
        )
        with open(request_file, 'w') as f:
            f.write(request.to_json())
        
        print(f"[escalation] Created review request: {request.request_id}")
        print(f"[escalation] Tier: {tier.name}, Sensitivity: {request.sensitivity}")
        
        # Build prompt based on tier
        if tier == Tier.OPENCODE:
            prompt = self.build_opencode_prompt(request)
            response = self.call_opencode_api(prompt)
            api_name = "OpenCode"
        elif tier == Tier.GEMINI:
            prompt = self.build_gemini_prompt(request)
            response = self.call_gemini_api(prompt)
            api_name = "Gemini"
        else:
            print(f"[escalation] Unknown tier: {tier}")
            return None
        
        # Save response
        if response:
            response_file = os.path.join(
                self.escalation_dir,
                f"response_{request.request_id}.json"
            )
            with open(response_file, 'w') as f:
                json.dump({
                    "request_id": request.request_id,
                    "timestamp": datetime.now().isoformat(),
                    "tier": tier.name,
                    "response": response
                }, f, indent=2)
            
            print(f"[escalation] {api_name} response saved")
            
            return {
                "request_id": request.request_id,
                "response": response,
                "tier": tier.name,
                "prompt": prompt
            }
        
        return None
    
    def get_escalation_history(self) -> List[Dict[str, Any]]:
        """Get history of escalations"""
        history = []
        
        for filename in os.listdir(self.escalation_dir):
            if filename.startswith("request_"):
                filepath = os.path.join(self.escalation_dir, filename)
                with open(filepath, 'r') as f:
                    history.append(json.load(f))
        
        return sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def clear_history(self):
        """Clear escalation history"""
        for filename in os.listdir(self.escalation_dir):
            filepath = os.path.join(self.escalation_dir, filename)
            os.remove(filepath)
        print("[escalation] History cleared")


# Global instance
_escalation_manager: Optional[EscalationManager] = None


def get_escalation_manager() -> EscalationManager:
    """Get global escalation manager instance"""
    global _escalation_manager
    if _escalation_manager is None:
        _escalation_manager = EscalationManager()
    return _escalation_manager


def escalate_to_opencode(**kwargs) -> Optional[Dict[str, Any]]:
    """Quick escalate to OpenCode"""
    return get_escalation_manager().escalate(Tier.OPENCODE, **kwargs)


def escalate_to_gemini(**kwargs) -> Optional[Dict[str, Any]]:
    """Quick escalate to Gemini"""
    return get_escalation_manager().escalate(Tier.GEMINI, **kwargs)


# SOS Template Generator
def generate_sos_template(
    context: str,
    failure: str,
    vision_data: Optional[Dict] = None,
    code: Optional[str] = None
) -> str:
    """
    Generate structured SOS template for external review.
    
    Use this when manual escalation is needed.
    """
    template = f"""
═══════════════════════════════════════════════════════════════
                    ESCALATION REVIEW REQUEST
═══════════════════════════════════════════════════════════════

## System Context
I am a local agent running on an AMD 9070 XT with:
- DeepSeek-Coder-V2-16B (Generator)
- Llama 3.2-3B (Analyst)
- Florence-2 (Vision)
- Model Lifecycle Manager (VRAM-aware swapping)

## Current Context
{context}

## Observed Failure
{failure}
"""
    
    if vision_data:
        template += f"""
## Vision Analysis (Florence-2)
- Caption: {vision_data.get('caption', 'N/A')}
- Extracted Text: {vision_data.get('extracted_text', 'N/A')[:300]}
- Error Detection: {vision_data.get('error_detection', {})}
"""
    
    if code:
        template += f"""
## Code Snippet
```python
{code}
```
"""
    
    template += """
## Request
Please review this against industry best practices.
Identify the architectural flaw my local reasoning is missing.
Provide a breakthrough strategy.

═══════════════════════════════════════════════════════════════
"""
    
    return template


def escalate_to_architect(
    issue_description: str,
    vision_json: Optional[Dict[str, Any]] = None,
    local_attempt: str = "",
    hardware_context: str = "AMD 9950X3D + 9070 XT"
) -> Optional[Dict[str, Any]]:
    """
    Send local context + Florence-2 vision data to external Senior Architect reviewer.
    
    This is the "Bridge Script" that bundles visual grounding from Florence-2
    with local diagnostic data and ships it to an external high-level reviewer.
    
    Args:
        issue_description: What the user is trying to solve
        vision_json: Florence-2 vision analysis (caption, extracted_text, bboxes, etc.)
        local_attempt: What the local agent tried that failed
        hardware_context: Hardware description for the reviewer
    
    Returns:
        Dict with response or None if API unavailable
    """
    esc = get_escalation_manager()
    
    # Build the architect prompt
    architect_prompt = f"""You are a Senior Architect and SRE reviewing a local AI agent's failure.

## Hardware Context
{hardware_context}

## User's Problem
{issue_description}

## Vision Grounding (Florence-2 Analysis)
"""
    
    if vision_json:
        architect_prompt += f"""
- Caption: {vision_json.get('caption', 'N/A')}
- Extracted Text: {vision_json.get('extracted_text', 'N/A')[:500]}
- Error Detection: {vision_json.get('error_detection', {})}
- UI Elements: {vision_json.get('ui_elements_count', 0)} detected
"""
    else:
        architect_prompt += "No vision data available.\n"
    
    architect_prompt += f"""
## Local Agent's Failed Attempt
{local_attempt if local_attempt else "No local attempts recorded yet."}

## Request
Review this visual state against best practices.
Why is the local agent's proposed fix failing in this hardware environment?
Provide an architectural fix strategy.
"""
    
    # Scrub sensitive data
    scrubbed_prompt = esc.scrub_sensitive_data(architect_prompt)
    
    # Determine tier - prefer Gemini for strategic review
    tier = Tier.GEMINI
    
    # Create request
    request = esc.create_review_request(
        local_context=scrubbed_prompt,
        observed_failure=issue_description,
        local_attempt=local_attempt,
        tier=tier,
        retry_count=0,
        vision_data=vision_json
    )
    
    # Save request
    request_file = os.path.join(
        ESCALATION_DIR,
        f"architect_review_{request.request_id}.json"
    )
    with open(request_file, 'w') as f:
        f.write(request.to_json())
    
    print(f"[escalation] Architect review requested: {request.request_id}")
    
    # Call Gemini
    prompt = esc.build_gemini_prompt(request)
    response = esc.call_gemini_api(prompt)
    
    if response:
        # Save response
        response_file = os.path.join(
            ESCALATION_DIR,
            f"architect_response_{request.request_id}.json"
        )
        with open(response_file, 'w') as f:
            json.dump({
                "request_id": request.request_id,
                "timestamp": datetime.now().isoformat(),
                "tier": tier.name,
                "response": response
            }, f, indent=2)
        
        return {
            "request_id": request.request_id,
            "response": response,
            "tier": tier.name
        }
    
    return None


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("Escalation Module Test")
    print("=" * 60)
    
    esc = get_escalation_manager()
    
    # Test sensitivity detection
    print("\n[1] Testing sensitive data scrubbing:")
    test_text = "My API key is sk-1234567890 and password is secret123"
    scrubbed = esc.scrub_sensitive_data(test_text)
    print(f"    Original: {test_text}")
    print(f"    Scrubbed: {scrubbed}")
    
    # Test sensitivity detection
    print("\n[2] Testing sensitivity detection:")
    sensitivity = esc.detect_sensitivity(test_text)
    print(f"    Sensitivity: {sensitivity}")
    
    # Test should_escalate
    print("\n[3] Testing escalation triggers:")
    print(f"    retry=3, threshold=3: {esc.should_escalate(3, 3)}")
    print(f"    retry=2, threshold=3: {esc.should_escalate(2, 3)}")
    print(f"    retry=1, high sensitivity: {esc.should_escalate(1, 3, 'high')}")
    
    # Test SOS template
    print("\n[4] Testing SOS template:")
    sos = generate_sos_template(
        context="Trying to load Florence-2 vision model",
        failure="RobertaTokenizer has no attribute image_token",
        vision_data={"caption": "Error popup", "extracted_text": "ImportError"},
        code="from transformers import Florence2Processor"
    )
    print(sos[:500] + "...")
    
    print("\n" + "=" * 60)
    print("Escalation Module ready")
    print("=" * 60)
