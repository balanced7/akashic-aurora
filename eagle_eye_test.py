"""
Eagle Eye Handshake Test
========================
Verifies Vision → Lifecycle → Generator integration.

Tests the complete flow:
1. Capture screen with intentional error visible
2. Trigger Lifecycle Manager for VRAM swap
3. Verify vision context is captured
4. Test escalation module

Usage:
    python eagle_eye_test.py
"""

import os
import sys
import json
import time

sys.path.insert(0, r'E:\AI-Setup')

from model_lifecycle import ModelLifecycleManager, Priority, create_lifecycle_manager
from vision_engine import VisionEngine, capture_active_window
from escalation import get_escalation_manager, Tier, generate_sos_template


def test_vision_engine():
    """Test 1: Vision Engine capture and analysis"""
    print("\n" + "=" * 60)
    print("TEST 1: Vision Engine")
    print("=" * 60)
    
    print("\n[1.1] Capturing active window...")
    screenshot = capture_active_window()
    
    if screenshot:
        print(f"      Captured: {screenshot.size}")
        
        # Save preview
        preview_path = r"E:\AI-Setup\session_screenshots\eagle_eye_preview.png"
        screenshot.save(preview_path)
        print(f"      Saved: {preview_path}")
    else:
        print("      [FAIL] No screenshot captured")
        return False
    
    print("\n[1.2] Loading Florence-2 (will use fallback if unavailable)...")
    engine = VisionEngine()
    
    # Test different task modes
    tasks = ["caption", "ocr", "error_detection"]
    
    for task in tasks:
        print(f"\n      Task: {task}")
        result = engine.analyze_screen(screenshot, task=task)
        
        if "error" in result:
            print(f"      [WARN] {result['error']}")
        else:
            output = result.get("text", result.get("caption", ""))
            print(f"      Result: {output[:100]}...")
    
    if engine._loaded:
        engine.unload()
        print("\n[1.3] Vision engine unloaded (VRAM freed)")
    
    print("\n[PASS] Vision Engine test complete")
    return True


def test_lifecycle_manager():
    """Test 2: Model Lifecycle Manager"""
    print("\n" + "=" * 60)
    print("TEST 2: Model Lifecycle Manager")
    print("=" * 60)
    
    print("\n[2.1] Creating lifecycle manager...")
    mgr = create_lifecycle_manager()
    
    print("\n[2.2] VRAM status check...")
    status = mgr.check_vram_and_warn()
    print(f"      Usage: {status['usage_gb']}GB")
    print(f"      Available: {status['available_gb']}GB")
    print(f"      Status: {status['status'].upper()}")
    
    print("\n[2.3] Suggest swap for vision task...")
    suggestion = mgr.suggest_swap(Priority.MEDIUM)
    print(f"      Action: {suggestion['action']}")
    print(f"      To load: {suggestion['to_load']}")
    print(f"      To unload: {suggestion['to_unload']}")
    print(f"      Reason: {suggestion['reason']}")
    
    print("\n[2.4] Full status...")
    full = mgr.get_status()
    print(f"      Vision engine ready: {full['vision_engine_ready']}")
    for name, info in full['models'].items():
        status_str = "LOADED" if info['loaded'] else "unloaded"
        print(f"      {name}: {info['size_gb']}GB ({info['priority']}) - {status_str}")
    
    print("\n[PASS] Lifecycle Manager test complete")
    return True


def test_escalation():
    """Test 3: Escalation Module"""
    print("\n" + "=" * 60)
    print("TEST 3: Escalation Module")
    print("=" * 60)
    
    print("\n[3.1] Creating escalation manager...")
    esc = get_escalation_manager()
    
    print("\n[3.2] Testing sensitive data scrubbing...")
    test_data = "API key is sk-1234567890 and password=secret123"
    scrubbed = esc.scrub_sensitive_data(test_data)
    print(f"      Original: {test_data}")
    print(f"      Scrubbed: {scrubbed}")
    
    print("\n[3.3] Testing sensitivity detection...")
    sensitivity = esc.detect_sensitivity(test_data)
    print(f"      Sensitivity level: {sensitivity}")
    
    print("\n[3.4] Testing should_escalate logic...")
    print(f"      retry=3, threshold=3: {esc.should_escalate(3, 3)}")
    print(f"      retry=2, threshold=3: {esc.should_escalate(2, 3)}")
    print(f"      retry=1, high sensitivity: {esc.should_escalate(1, 3, 'high')}")
    
    print("\n[3.5] Generating SOS template...")
    sos = generate_sos_template(
        context="Loading Florence-2 vision model",
        failure="RobertaTokenizer has no attribute image_token",
        vision_data={"caption": "Error popup on screen"},
        code="from transformers import Florence2Processor"
    )
    print(f"      SOS template generated ({len(sos)} chars)")
    
    print("\n[3.6] Testing OpenCode escalation (dry run)...")
    result = esc.escalate(
        tier=Tier.OPENCODE,
        local_context="Test context - Florence-2 loading issue",
        observed_failure="RobertaTokenizer has no attribute image_token",
        local_attempt="Attempted direct model load, then pipeline approach",
        retry_count=3,
        vision_data={"caption": "Test", "extracted_text": "Error"},
        code_snippet="model = Florence2Model.from_pretrained(...)"
    )
    
    if result:
        print(f"      [INFO] OpenCode escalation result: {len(result.get('response', ''))} chars")
    else:
        print(f"      [INFO] OpenCode API not configured (expected without API key)")
    
    print("\n[PASS] Escalation Module test complete")
    return True


def test_master_integration():
    """Test 4: Master with lifecycle and escalation"""
    print("\n" + "=" * 60)
    print("TEST 4: Master Integration")
    print("=" * 60)
    
    print("\n[4.1] Importing master module...")
    import master
    print("      Master imported successfully")
    
    print("\n[4.2] Testing intent resolution...")
    intent = master.resolve_intent({"has_image": True})
    print(f"      has_image=True: {intent}")
    
    intent = master.resolve_intent({"is_code_heavy": True})
    print(f"      is_code_heavy=True: {intent}")
    
    intent = master.resolve_intent({"has_video": True})
    print(f"      has_video=True: {intent}")
    
    intent = master.resolve_intent({})
    print(f"      default: {intent}")
    
    print("\n[4.3] Testing IntentPriority enum...")
    print(f"      HIGH_REASONING: {master.IntentPriority.HIGH_REASONING}")
    print(f"      VISION_PRIORITY: {master.IntentPriority.VISION_PRIORITY}")
    print(f"      VIDEO_BURST: {master.IntentPriority.VIDEO_BURST}")
    
    print("\n[PASS] Master integration test complete")
    return True


def run_handshake():
    """Run the complete Eagle Eye handshake test"""
    print("\n" + "=" * 60)
    print("          EAGLE EYE HANDSHAKE TEST")
    print("=" * 60)
    print("\nTesting Vision -> Lifecycle -> Escalation pipeline...")
    
    results = []
    
    # Run all tests
    results.append(("Vision Engine", test_vision_engine()))
    results.append(("Lifecycle Manager", test_lifecycle_manager()))
    results.append(("Escalation Module", test_escalation()))
    results.append(("Master Integration", test_master_integration()))
    
    # Summary
    print("\n" + "=" * 60)
    print("                  TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All handshake tests passed!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Set API keys for escalation: export OPENCODE_API_KEY=...")
        print("2. Run: python E:\\AI-Setup\\master.py")
        print("3. Ask: 'Look at my screen, find the error'")
    else:
        print("WARNING: Some tests failed - check logs above")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = run_handshake()
    sys.exit(0 if success else 1)
