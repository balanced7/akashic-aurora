"""
Vision Engine - Screen Understanding via Florence-2
================================================
Provides semantic spatial awareness for the multi-agent system.

FLORENCE-2 TASK TOKENS:
- <CAPTION>: Brief image description
- <DETAILED_CAPTION>: Full semantic description (e.g., "screenshot of FL Studio with red error peak")
- <MORE_DETAILED_CAPTION>: High-fidelity for video generation prompts
- <OCR>: Extract all text with coordinates
- <OCR_WITH_REGION>: Map text to specific screen coordinates
- <CAPTION_TO_PHRASE_GROUNDING>: Answer "Where is X?" questions
- <OD>: Object detection with bounding boxes
- <GENERAL_OCR>: Error/troubleshooting text extraction

Features:
- Screenshot capture of active window (PyAutoGUI, MSS, PIL fallbacks)
- Florence-2 inference for unified OCR + Detection + Captioning
- Structured JSON output for Analyst consumption
- VRAM-aware: Uses small model (~500MB) to leave room for LLMs
- Model Lifecycle Manager for dynamic loading/unloading

Usage:
    from vision_engine import VisionEngine, capture_active_window
    
    # Quick capture
    screenshot = capture_active_window()
    
    # Full analysis with all modes
    engine = VisionEngine()
    result = engine.analyze_screen(screenshot, task="detailed_caption")
    
    # For error detection
    result = engine.analyze_screen(screenshot, task="error_detection")
    
    # Phrase grounding (find "Where is the error?")
    result = engine.phrase_grounding(screenshot, "error")
"""

import os
import sys
import json
import base64
import io
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import torch
from PIL import Image, ImageGrab
import yaml

# Paths
VISION_CACHE = r"E:\AI-Setup\models\vision"
SCREENSHOT_DIR = r"E:\AI-Setup\session_screenshots"
os.makedirs(VISION_CACHE, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Florence-2 model - microsoft florence-2-base is ~500MB
FLORENCE_MODEL = "microsoft/Florence-2-base"
FLORENCE_LARGE_MODEL = "microsoft/Florence-2-large"


class VisionEngine:
    """
    Vision-language model for screen understanding.
    
    Florence-2 provides:
    - OCR (text recognition)
    - Object Detection  
    - Captioning
    - Structured output generation
    
    All in a single model, ~500MB footprint.
    """
    
    def __init__(self, model_name: str = FLORENCE_MODEL, device: str = None):
        self.model_name = model_name
        self._dml_available = False
        self._pipeline = None
        
        # Check for GPU availability properly (ROCm + CUDA + DirectML)
        if device:
            self.device = device
        elif torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.version, 'hip') and torch.version.hip:
            self.device = "hip"  # AMD ROCm
        else:
            # Check for DirectML as fallback on Windows+AMD
            try:
                import torch_directml
                self.device = torch_directml.device()
                self._dml_available = True
                print("[vision] DirectML available - AMD GPU will be used")
            except ImportError:
                self.device = "cpu"
                self._dml_available = False
        
        self.model = None
        self.processor = None
        self._loaded = False
        
        device_name = str(self.device) if not isinstance(self.device, str) else self.device
        print(f"[vision] Device set to: {device_name}")
        if self.device == "cpu":
            print("[vision] WARNING: Running on CPU - GPU not detected")
            print("[vision] Note: AMD 9070 XT requires ROCm (WSL2) or DirectML for GPU acceleration")
    
    def load(self) -> bool:
        """
        Load Florence-2 model with explicit handling for transformers 5.x.
        
        Uses trust_remote_code=True and explicit tensor handling to avoid
        the image_token attribute error with newer transformers versions.
        """
        if self._loaded:
            return True
        
        try:
            from transformers import AutoModelForCausalLM, AutoProcessor, pipeline
            
            # Determine device for model loading
            if self._dml_available:
                # DirectML has compatibility issues with generate() - use CPU for inference
                # but keep DirectML flag for future when bug is fixed
                device_for_model = "cpu"
                print(f"[vision] DirectML detected but using CPU (DirectML has tensor compatibility bug with Florence-2)")
            elif isinstance(self.device, str) and self.device == "cuda":
                device_for_model = "cuda"
            elif isinstance(self.device, str) and self.device == "hip":
                device_for_model = "hip"
            else:
                device_for_model = "cpu"
            
            print(f"[vision] Loading {self.model_name} (model on {device_for_model})...")
            
            # Track actual device model is on
            self._model_device = device_for_model
            
            # Try pipeline first - handles device placement automatically
            try:
                self._pipeline = pipeline(
                    "image-to-text",
                    model=self.model_name,
                    device=0 if device_for_model == "cuda" else -1,
                    torch_dtype=torch.float16 if device_for_model in ("cuda", "hip") else torch.float32
                )
                self._use_pipeline = True
                print(f"[vision] Model loaded via pipeline")
            except Exception as e:
                print(f"[vision] Pipeline failed: {e}, trying explicit loading...")
                self._use_pipeline = False
                self._pipeline = None
            
            if not self._use_pipeline:
                # Explicit model loading with trust_remote_code
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    trust_remote_code=True,
                    torch_dtype=torch.float16 if device_for_model in ("cuda", "hip") else torch.float32
                )
                
                if device_for_model in ("cuda", "hip"):
                    self.model = self.model.to(device_for_model)
                
                self.model.eval()
                
                # Manually load processor
                self.processor = AutoProcessor.from_pretrained(
                    self.model_name,
                    trust_remote_code=True
                )
                print(f"[vision] Model loaded explicitly on {device_for_model}")
            
            self._loaded = True
            print(f"[vision] Model loaded successfully")
            return True
            
        except Exception as e:
            print(f"[vision] Failed to load model: {e}")
            self._loaded = False
            return False
    
    def unload(self):
        """Unload model to free VRAM"""
        if self.model is not None:
            del self.model
            del self.processor
            self.model = None
            self.processor = None
            self._loaded = False
            self._pipeline = None
            if hasattr(self, '_model_device'):
                del self._model_device
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            print("[vision] Model unloaded, VRAM freed")
    
    def analyze_screen(
        self, 
        image: Image.Image, 
        task: str = "caption",
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        Analyze a screenshot with Florence-2 using explicit tensor handling.
        
        Compatible with transformers 5.x via explicit prompt construction
        and post-processing.
        """
        if not self._loaded:
            if not self.load():
                return {"error": "Failed to load vision model"}
        
        try:
            # Task prompts for Florence-2
            prompts = {
                "caption": "<CAPTION>",
                "detailed_caption": "<DETAILED_CAPTION>",
                "more_detailed_caption": "<MORE_DETAILED_CAPTION>",
                "ocr": "<OCR>",
                "ocr_with_region": "<OCR_WITH_REGION>",
                "error_detection": "<GENERAL_OCR>",
                "ui_elements": "<OD>",
                "phrase_grounding": "<CAPTION_TO_PHRASE_GROUNDING>",
            }
            
            prompt = prompts.get(task, "<CAPTION>")
            
            # Use pipeline if available (handles device placement better)
            if self._pipeline is not None:
                result_text = self._pipeline(
                    image,
                    task=prompt,
                    max_new_tokens=max_tokens
                )
                generated_text = result_text[0]['generated_text']
                parsed = {"text": generated_text}
            else:
                # Determine compute device for tensors
                # If model is loaded on CPU, use CPU even if DirectML is "available"
                # DirectML has compatibility bugs with Florence-2
                if hasattr(self, '_model_device'):
                    compute_device = self._model_device
                elif isinstance(self.device, str) and self._dml_available and self.device != "cpu":
                    compute_device = self.device
                elif isinstance(self.device, str):
                    compute_device = self.device
                else:
                    compute_device = "cpu"
                
                # Explicit prompt construction (avoid image_token error)
                prompt_str = prompt
                
                # Process inputs explicitly
                inputs = self.processor(
                    text=prompt_str,
                    images=image,
                    return_tensors="pt"
                )
                
                # Move inputs to compute device
                inputs = {k: v.to(compute_device) for k, v in inputs.items()}
                
                # Cast pixel_values to float16 for GPU inference
                if "pixel_values" in inputs and isinstance(compute_device, str) and compute_device in ("cuda", "hip"):
                    inputs["pixel_values"] = inputs["pixel_values"].to(torch.float16)
                
                # Generate with explicit parameters
                with torch.no_grad():
                    generated_ids = self.model.generate(
                        input_ids=inputs["input_ids"],
                        pixel_values=inputs["pixel_values"],
                        max_new_tokens=max_tokens,
                        early_stopping=False,
                        do_sample=False,
                        num_beams=3,
                    )
                
                # Decode and post-process
                generated_text = self.processor.batch_decode(
                    generated_ids, 
                    skip_special_tokens=True
                )[0]
                
                # Use post_process_generation for transformers 5.x compatibility
                try:
                    parsed = self.processor.post_process_generation(
                        generated_text,
                        task=prompt,
                        image_size=(image.width, image.height)
                    )
                except AttributeError:
                    # Fallback for older post-process methods
                    parsed = {"text": generated_text}
            
            # Build result based on task
            if task in ["ocr", "error_detection", "ocr_with_region"]:
                result = {
                    "task": task,
                    "text": parsed.get("text", generated_text),
                    "raw": generated_text
                }
            elif task == "ui_elements":
                result = {
                    "task": task,
                    "objects": parsed.get("bboxes", []),
                    "raw": generated_text
                }
            else:
                result = {
                    "task": task,
                    "caption": parsed.get("text", generated_text),
                    "raw": generated_text
                }
            
            result["timestamp"] = datetime.now().isoformat()
            result["model"] = self.model_name
            
            return result
            
        except Exception as e:
            return {"error": str(e), "task": task}
    
    def full_analysis(self, image: Image.Image) -> Dict[str, Any]:
        """
        Run multiple analysis tasks on a single image.
        
        Returns comprehensive screen understanding.
        """
        results = {}
        
        # Run caption first (fast)
        results["caption"] = self.analyze_screen(image, "caption")
        
        # Then OCR for text extraction
        results["text"] = self.analyze_screen(image, "ocr")
        
        # UI element detection
        results["ui"] = self.analyze_screen(image, "ui_elements")
        
        return results
    
    def phrase_grounding(self, image: Image.Image, phrase: str) -> Dict[str, Any]:
        """
        Answer "Where is X?" questions about the screen.
        
        Uses <CAPTION_TO_PHRASE_GROUNDING> to find the phrase in the image.
        
        Args:
            image: PIL Image
            phrase: What to find (e.g., "error dialog", "save button")
        
        Returns:
            Dict with bounding boxes and confidence for found elements
        """
        if not self._loaded:
            if not self.load():
                return {"error": "Failed to load vision model"}
        
        try:
            # Build grounding prompt
            prompt = f"<CAPTION_TO_PHRASE_GROUNDING> {phrase}"
            
            inputs = self.processor(
                text=prompt,
                images=image,
                return_tensors="pt"
            ).to(self.device)
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    input_ids=inputs["input_ids"],
                    pixel_values=inputs["pixel_values"],
                    max_new_tokens=1024,
                    do_sample=False,
                    num_beams=3
                )
            
            generated_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=False
            )[0]
            
            # Parse grounding result
            parsed = self.processor.post_process_grounding(generated_text, phrase)
            
            return {
                "task": "phrase_grounding",
                "phrase": phrase,
                "found": parsed.get("found", False),
                "bboxes": parsed.get("bboxes", []),
                "captions": parsed.get("captions", []),
                "raw": generated_text,
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name
            }
            
        except Exception as e:
            return {"error": str(e), "task": "phrase_grounding"}


def capture_active_window() -> Optional[Image.Image]:
    """
    Capture screenshot of the currently active window.
    
    Uses multiple fallback methods:
    1. pygetwindow + PIL
    2. ImageGrab (PIL)
    3. MSS (fastest)
    
    Returns:
        PIL Image or None if capture fails
    """
    # Try pygetwindow first
    try:
        import pygetwindow as pgw
        
        active = pgw.getActiveWindow()
        if active:
            bbox = active.bbox
            if bbox:
                screenshot = ImageGrab.grab(bbox=bbox, include_layered_windows=False)
                return screenshot
    except Exception as e:
        print(f"[vision] pygetwindow failed: {e}")
    
    # Fallback to ImageGrab (full screen)
    try:
        return ImageGrab.grab(include_layered_windows=False)
    except Exception as e:
        print(f"[vision] ImageGrab failed: {e}")
    
    # Last resort: MSS (fast, low-level)
    try:
        import mss
        
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            return Image.frombytes(
                "RGB",
                screenshot.size,
                screenshot.rgb
            )
    except Exception as e:
        print(f"[vision] MSS failed: {e}")
    
    return None


def capture_region(bbox: tuple) -> Optional[Image.Image]:
    """
    Capture a specific region of the screen.
    
    Args:
        bbox: (left, top, right, bottom) coordinates
    
    Returns:
        PIL Image of the region
    """
    try:
        return ImageGrab.grab(bbox=bbox, include_layered_windows=False)
    except Exception as e:
        print(f"[vision] Region capture failed: {e}")
        return None


def save_screenshot(image: Image.Image, tag: str = "capture") -> str:
    """
    Save screenshot to disk with timestamp.
    
    Args:
        image: PIL Image
        tag: Optional tag for filename
    
    Returns:
        Path to saved screenshot
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"screen_{tag}_{timestamp}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    
    image.save(filepath, "PNG")
    print(f"[vision] Screenshot saved: {filepath}")
    
    return filepath


def encode_image_base64(image: Image.Image, max_size: int = 2048) -> str:
    """
    Encode PIL Image as base64 for transmission to LLM.
    
    Args:
        image: PIL Image
        max_size: Max dimension (maintains aspect ratio)
    
    Returns:
        Base64 encoded string
    """
    # Resize if needed
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.LANCZOS)
    
    # Encode
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    return encoded


def quick_error_detection(image: Image.Image) -> Dict[str, Any]:
    """
    Quick error detection using Florence-2.
    
    Specialized for finding errors in terminal/console output.
    """
    engine = VisionEngine()
    
    if not engine.load():
        return {"error": "Could not load vision model"}
    
    # Run OCR to get all text
    ocr_result = engine.analyze_screen(image, "ocr")
    
    # Run caption for context
    caption_result = engine.analyze_screen(image, "caption")
    
    # Analyze text for common error patterns
    text = ocr_result.get("text", "").lower()
    
    error_patterns = [
        "error",
        "exception",
        "traceback",
        "failed",
        "failure",
        "crash",
        "panic",
        "fatal",
        "critical"
    ]
    
    detected_errors = [p for p in error_patterns if p in text]
    
    result = {
        "has_error": len(detected_errors) > 0,
        "error_keywords": detected_errors,
        "text_preview": text[:500] if text else "",
        "caption": caption_result.get("caption", ""),
        "confidence": "high" if len(detected_errors) > 2 else ("medium" if detected_errors else "low"),
        "timestamp": datetime.now().isoformat()
    }
    
    return result


def get_screen_context_for_analyst(image: Image.Image) -> Dict[str, Any]:
    """
    Get comprehensive screen context formatted for Analyst consumption.
    
    This is the main entry point for the Master to get vision data.
    """
    engine = VisionEngine()
    
    if not engine.load():
        return {"error": "Vision model unavailable"}
    
    # Run full analysis
    analysis = engine.full_analysis(image)
    
    # Quick error check
    error_check = quick_error_detection(image)
    
    # Save screenshot for reference
    screenshot_path = save_screenshot(image, "analyst_context")
    
    # Compile context
    context = {
        "screenshot_path": screenshot_path,
        "screenshot_b64": encode_image_base64(image),
        "error_detection": error_check,
        "caption": analysis["caption"].get("caption", ""),
        "extracted_text": analysis["text"].get("text", "")[:2000],  # Limit length
        "ui_elements_count": len(analysis["ui"].get("objects", [])),
        "timestamp": datetime.now().isoformat(),
        "vision_model": engine.model_name
    }
    
    return context


def create_vision_signal_payload(context: Dict[str, Any]) -> str:
    """
    Create a formatted signal payload for the blackboard.
    
    This gets appended to active_buffer.json for the Analyst.
    """
    payload = {
        "type": "vision_context",
        "source": "vision_engine",
        "data": context,
        "timestamp": datetime.now().isoformat()
    }
    
    return json.dumps(payload, indent=2)


def extract_keyframes(video_path: str, max_frames: int = 8) -> List[Image.Image]:
    """
    Extract keyframes from video for VLM analysis.
    
    Uses OpenCV to detect scene changes and extract representative frames.
    
    Args:
        video_path: Path to video file
        max_frames: Maximum frames to extract
    
    Returns:
        List of PIL Images (keyframes)
    """
    try:
        import cv2
    except ImportError:
        print("[vision] OpenCV not available for keyframe extraction")
        return []
    
    frames = []
    
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            print(f"[vision] Cannot open video: {video_path}")
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Calculate frame interval
        interval = max(1, total_frames // (max_frames * 2))
        
        prev_frame = None
        frame_idx = 0
        
        while len(frames) < max_frames:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Check for significant change (scene detection)
            if prev_frame is not None:
                diff = cv2.absdiff(frame_rgb, prev_frame)
                mean_diff = diff.mean()
                
                # If significant change, this is a keyframe
                if mean_diff > 30 or len(frames) == 0:
                    pil_frame = Image.fromarray(frame_rgb)
                    frames.append(pil_frame)
            
            prev_frame = frame_rgb
            frame_idx += 1
            
            # Skip frames
            for _ in range(interval - 1):
                cap.read()
        
        cap.release()
        
        print(f"[vision] Extracted {len(frames)} keyframes from {video_path}")
        return frames
        
    except Exception as e:
        print(f"[vision] Keyframe extraction failed: {e}")
        return []


def analyze_video_keyframes(keyframes: List[Image.Image], task: str = "detailed_caption") -> Dict[str, Any]:
    """
    Analyze a list of keyframes with Florence-2.
    
    Args:
        keyframes: List of PIL Images
        task: Analysis task (caption, detailed_caption, etc.)
    
    Returns:
        Dict with per-frame analysis and summary
    """
    engine = VisionEngine()
    
    if not engine.load():
        return {"error": "Vision model unavailable"}
    
    results = []
    
    for i, frame in enumerate(keyframes):
        result = engine.analyze_screen(frame, task)
        results.append({
            "frame_idx": i,
            "result": result
        })
    
    # Generate summary
    captions = [r["result"].get("caption", "") for r in results if "caption" in r["result"]]
    summary = " | ".join(captions[:3])  # First 3 frames
    
    return {
        "frame_count": len(results),
        "frames": results,
        "summary": summary,
        "task": task,
        "timestamp": datetime.now().isoformat()
    }


# Quick test
if __name__ == "__main__":
    print("=" * 50)
    print("Vision Engine Test")
    print("=" * 50)
    
    # Capture screen
    print("\n[1] Capturing active window...")
    screenshot = capture_active_window()
    
    if screenshot:
        print(f"    Captured: {screenshot.size}")
        
        # Save preview
        preview_path = os.path.join(SCREENSHOT_DIR, "test_preview.png")
        screenshot.save(preview_path)
        print(f"    Preview saved: {preview_path}")
        
        # Test vision analysis
        print("\n[2] Loading vision model...")
        engine = VisionEngine()
        if engine.load():
            print("\n[3] Running caption analysis...")
            result = engine.analyze_screen(screenshot, "caption")
            print(f"    Caption: {result.get('caption', 'N/A')}")
            
            print("\n[4] Running OCR...")
            result = engine.analyze_screen(screenshot, "ocr")
            text = result.get("text", "")[:200]
            print(f"    Text (first 200 chars): {text}")
            
            print("\n[5] Quick error detection...")
            errors = quick_error_detection(screenshot)
            print(f"    Has error: {errors.get('has_error')}")
            print(f"    Keywords: {errors.get('error_keywords')}")
            
            print("\n[6] Full context for Analyst...")
            context = get_screen_context_for_analyst(screenshot)
            print(f"    Screen captured: {context.get('screenshot_path')}")
            print(f"    Caption: {context.get('caption', '')[:100]}...")
            
            # Unload to free VRAM
            engine.unload()
        else:
            print("    Failed to load model - check installation")
    else:
        print("    Failed to capture screen")
    
    print("\n" + "=" * 50)
    print("Vision Engine test complete")
    print("=" * 50)
