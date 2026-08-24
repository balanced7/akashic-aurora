"""
Florence-2 Video Keyframe Extraction Test
========================================
Tests the vision engine's ability to extract and analyze keyframes from video.

Usage:
    # Test with a video file
    python test_video_keyframes.py --video path/to/video.mp4
    
    # Test with screen recording
    python test_video_keyframes.py --screen-record

Note: Requires OpenCV (cv2) to be installed.
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vision_engine import (
    VisionEngine,
    capture_active_window,
    extract_keyframes,
    analyze_video_keyframes,
    encode_image_base64,
    SCREENSHOT_DIR
)


def test_screenshot_keyframes():
    """Test keyframe extraction from a series of screenshots"""
    print("=" * 60)
    print("Florence-2 Video Keyframe Extraction Test")
    print("=" * 60)
    
    print("\n[1] Capturing screen frames...")
    frames = []
    
    # Capture 5 frames with slight delays (simulating video)
    for i in range(5):
        screenshot = capture_active_window()
        if screenshot:
            # Resize for faster processing
            screenshot = screenshot.resize(
                (screenshot.width // 2, screenshot.height // 2),
                method=0  # NEAREST for speed
            )
            frames.append(screenshot)
            print(f"    Frame {i+1}: {screenshot.size}")
        time.sleep(0.5)
    
    if not frames:
        print("[ERROR] No frames captured")
        return False
    
    print(f"\n[2] Loading Florence-2...")
    engine = VisionEngine()
    if not engine.load():
        print("[ERROR] Failed to load vision model")
        return False
    
    print(f"\n[3] Analyzing {len(frames)} frames with different tasks...")
    
    # Test different analysis tasks
    tasks = ["caption", "detailed_caption", "ocr"]
    
    for task in tasks:
        print(f"\n    Task: {task}")
        for i, frame in enumerate(frames[:2]):  # First 2 frames only
            result = engine.analyze_screen(frame, task=task)
            if "error" in result:
                print(f"      Frame {i+1}: ERROR - {result['error']}")
            else:
                output = result.get("caption", result.get("text", ""))
                if len(output) > 100:
                    output = output[:100] + "..."
                print(f"      Frame {i+1}: {output}")
    
    print(f"\n[4] Full keyframe analysis...")
    results = analyze_video_keyframes(frames, task="detailed_caption")
    
    print(f"    Frames analyzed: {results['frame_count']}")
    print(f"    Summary: {results['summary'][:200]}...")
    
    # Cleanup
    engine.unload()
    
    print("\n" + "=" * 60)
    print("Video Keyframe Test Complete")
    print("=" * 60)
    
    return True


def test_video_file_keyframes(video_path: str):
    """Test keyframe extraction from a video file"""
    print("=" * 60)
    print(f"Video Keyframe Test: {video_path}")
    print("=" * 60)
    
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found: {video_path}")
        return False
    
    print("\n[1] Extracting keyframes...")
    start_time = time.time()
    keyframes = extract_keyframes(video_path, max_frames=8)
    extract_time = time.time() - start_time
    
    if not keyframes:
        print("[ERROR] No keyframes extracted")
        return False
    
    print(f"    Extracted {len(keyframes)} keyframes in {extract_time:.2f}s")
    
    print("\n[2] Analyzing keyframes with Florence-2...")
    results = analyze_video_keyframes(keyframes, task="detailed_caption")
    
    print(f"    Summary: {results['summary']}")
    
    # Save keyframes for inspection
    keyframe_dir = os.path.join(SCREENSHOT_DIR, "keyframes")
    os.makedirs(keyframe_dir, exist_ok=True)
    
    for i, kf in enumerate(keyframes):
        path = os.path.join(keyframe_dir, f"keyframe_{i:02d}.png")
        kf.save(path)
        print(f"    Saved: {path}")
    
    print("\n" + "=" * 60)
    print("Video File Test Complete")
    print("=" * 60)
    
    return True


def test_screen_recording():
    """Test by recording a short screen recording"""
    print("=" * 60)
    print("Screen Recording Keyframe Test")
    print("=" * 60)
    
    print("\n[INFO] This test captures a real-time screen recording")
    print("[INFO] Recording 3 seconds of screen activity...")
    
    frames = []
    import time
    
    start = time.time()
    while time.time() - start < 3:
        screenshot = capture_active_window()
        if screenshot:
            frames.append(screenshot)
        time.sleep(0.1)  # 10 FPS
    
    print(f"\n[1] Captured {len(frames)} frames")
    
    if len(frames) < 3:
        print("[ERROR] Not enough frames captured")
        return False
    
    print("\n[2] Extracting keyframes (scene changes)...")
    # Use OpenCV for proper scene detection
    try:
        import cv2
        
        # Save frames temporarily
        temp_video = os.path.join(SCREENSHOT_DIR, "temp_recording.mp4")
        
        # Write video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video, fourcc, 10, 
                             (frames[0].width, frames[0].height))
        
        for frame in frames:
            # Convert to BGR for cv2
            import numpy as np
            frame_rgb = np.array(frame)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
        
        out.release()
        print(f"    Saved temporary video: {temp_video}")
        
        # Extract keyframes from video
        keyframes = extract_keyframes(temp_video, max_frames=6)
        
        # Cleanup
        os.remove(temp_video)
        
    except Exception as e:
        print(f"    OpenCV not available, using frame sampling: {e}")
        # Fallback: sample frames evenly
        step = len(frames) // 6
        keyframes = frames[::step][:6]
    
    print(f"    Found {len(keyframes)} keyframes")
    
    if not keyframes:
        print("[ERROR] No keyframes extracted")
        return False
    
    print("\n[3] Analyzing keyframes...")
    results = analyze_video_keyframes(keyframes, task="detailed_caption")
    
    print(f"    Summary: {results['summary'][:300]}...")
    
    # Save keyframes
    keyframe_dir = os.path.join(SCREENSHOT_DIR, "recording_keyframes")
    os.makedirs(keyframe_dir, exist_ok=True)
    
    for i, kf in enumerate(keyframes):
        path = os.path.join(keyframe_dir, f"frame_{i:02d}.png")
        kf.save(path)
    
    print(f"    Saved {len(keyframes)} keyframes to {keyframe_dir}")
    
    print("\n" + "=" * 60)
    print("Screen Recording Test Complete")
    print("=" * 60)
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Florence-2 Video Keyframe Test")
    parser.add_argument("--video", type=str, help="Path to video file")
    parser.add_argument("--screen-record", action="store_true", 
                       help="Record screen and analyze")
    parser.add_argument("--screenshot", action="store_true", default=True,
                       help="Test with screenshots (default)")
    
    args = parser.parse_args()
    
    if args.video:
        success = test_video_file_keyframes(args.video)
    elif args.screen_record:
        success = test_screen_recording()
    else:
        success = test_screenshot_keyframes()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
