"""
Escalate Review Bridge Script
===========================
Sends local context + Florence-2 vision data to external Senior Architect reviewer.

This bridges the local multi-agent system with high-level external review
when local agents hit roadblock after 2 visual error attempts.

Usage:
    python escalate_review.py --issue "Python import failing" --vision path/to/vision.json

Or programmatically:
    from escalate_review import send_to_senior_architect
    result = send_to_senior_architect(issue, vision_data)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from escalation import (
    get_escalation_manager,
    escalate_to_architect,
    generate_sos_template,
    Tier,
    ESCALATION_DIR
)


HARDWARE_CONTEXT = "AMD 9950X3D + Sapphire Nitro+ 9070 XT (16GB VRAM)"



def send_to_senior_architect(
    issue_description: str,
    vision_json: Optional[Dict[str, Any]] = None,
    local_attempt: str = "",
    use_opencode: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Sends local context + Florence-2 vision data to an external reviewer.
    
    Args:
        issue_description: What the user is trying to solve
        vision_json: Florence-2 vision analysis 
        local_attempt: What the local agent tried that failed
        use_opencode: If True, use OpenCode instead of Gemini
    
    Returns:
        Dict with response or None if API unavailable
    """
    print("=" * 60)
    print("ESCALATE TO SENIOR ARCHITECT")
    print("=" * 60)
    
    print(f"\n[1] Issue: {issue_description[:100]}...")
    
    if vision_json:
        print(f"[2] Vision data: {len(vision_json)} fields")
        if 'caption' in vision_json:
            print(f"    Caption: {vision_json['caption'][:50]}...")
        if 'extracted_text' in vision_json:
            print(f"    Text: {vision_json['extracted_text'][:50]}...")
    else:
        print("[2] No vision data provided")
    
    print(f"[3] Hardware: {HARDWARE_CONTEXT}")
    
    # Use escalate_to_architect
    result = escalate_to_architect(
        issue_description=issue_description,
        vision_json=vision_json,
        local_attempt=local_attempt,
        hardware_context=HARDWARE_CONTEXT
    )
    
    if result:
        print(f"\n[4] Response received ({len(result.get('response', ''))} chars)")
        print(f"    Request ID: {result.get('request_id')}")
        
        # Print first 500 chars of response
        response_preview = result.get('response', '')[:500]
        print(f"\n[5] Response Preview:")
        print("-" * 40)
        print(response_preview)
        print("-" * 40)
        
        return result
    else:
        print("\n[!] External API not available")
        print("    Set GEMINI_API_KEY or OPENCODE_API_KEY environment variable")
        return None


def send_sos_to_gemini(
    issue_description: str,
    vision_json: Optional[Dict[str, Any]] = None,
    code_snippet: Optional[str] = None
) -> Optional[str]:
    """
    Generate SOS template and send to Gemini for strategic review.
    
    Args:
        issue_description: What needs to be solved
        vision_json: Florence-2 analysis
        code_snippet: Relevant code
    
    Returns:
        Gemini response or None
    """
    esc = get_escalation_manager()
    
    sos = generate_sos_template(
        context=f"Hardware: {HARDWARE_CONTEXT}\n\nUser Issue:\n{issue_description}",
        failure="Local agent failed after multiple attempts",
        vision_data=vision_json,
        code=code_snippet
    )
    
    print("\n" + "=" * 60)
    print("SOS TEMPLATE GENERATED")
    print("=" * 60)
    print(sos)
    print("=" * 60)
    
    # Try Gemini API
    response = esc.call_gemini_api(sos)
    
    if response:
        print(f"\n[RESPONSE] ({len(response)} chars)")
        print(response[:1000])
        return response
    
    return None


def review_from_file(vision_file: str, issue: str) -> Optional[Dict[str, Any]]:
    """
    Load vision data from file and send to architect.
    
    Args:
        vision_file: Path to JSON file with vision data
        issue: Issue description
    
    Returns:
        Review response
    """
    with open(vision_file, 'r') as f:
        vision_json = json.load(f)
    
    return send_to_senior_architect(issue, vision_json)


def main():
    parser = argparse.ArgumentParser(description="Escalate to Senior Architect reviewer")
    parser.add_argument("--issue", type=str, required=True,
                       help="Issue description")
    parser.add_argument("--vision", type=str,
                       help="Path to vision JSON file")
    parser.add_argument("--attempt", type=str, default="",
                       help="What local agent tried")
    parser.add_argument("--opencode", action="store_true",
                       help="Use OpenCode instead of Gemini")
    parser.add_argument("--sos", action="store_true",
                       help="Generate SOS template instead of sending")
    
    args = parser.parse_args()
    
    # Load vision data if provided
    vision_json = None
    if args.vision:
        if os.path.exists(args.vision):
            with open(args.vision, 'r') as f:
                vision_json = json.load(f)
            print(f"Loaded vision data from: {args.vision}")
        else:
            print(f"Warning: Vision file not found: {args.vision}")
    
    # Generate SOS or send to architect
    if args.sos:
        result = send_sos_to_gemini(
            issue_description=args.issue,
            vision_json=vision_json
        )
        if result:
            print("\n[SOS sent to Gemini]")
    else:
        result = send_to_senior_architect(
            issue_description=args.issue,
            vision_json=vision_json,
            local_attempt=args.attempt,
            use_opencode=args.opencode
        )
    
    if result:
        print("\n" + "=" * 60)
        print("ESCALATION COMPLETE")
        print("=" * 60)
        print(f"Request ID: {result.get('request_id')}")
        
        # Save to escalation history
        response_file = os.path.join(
            ESCALATION_DIR,
            f"senior_architect_{result.get('request_id')}.json"
        )
        with open(response_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved to: {response_file}")
    else:
        print("\nEscalation failed - check API keys")
        sys.exit(1)


if __name__ == "__main__":
    main()
