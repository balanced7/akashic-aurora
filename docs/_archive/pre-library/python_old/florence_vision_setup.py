"""
Florence-2 Vision Setup for OpenCode Test
Lightweight vision for understanding screenshots during testing
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("FLORENCE-2 VISION SETUP FOR OPENCODE TEST")
print("=" * 70)

# Check if we can import required packages
try:
    import torch
    print("✓ PyTorch available")
except ImportError:
    print("✗ PyTorch not found. Installing...")
    os.system("pip install torch torchvision")
    import torch

try:
    from PIL import Image
    print("✓ Pillow (image processing) available")
except ImportError:
    print("✗ Pillow not found. Installing...")
    os.system("pip install pillow")
    from PIL import Image

try:
    from transformers import AutoProcessor, AutoModelForCausalLM
    print("✓ Transformers available")
except ImportError:
    print("✗ Transformers not found. Installing...")
    os.system("pip install transformers")
    from transformers import AutoProcessor, AutoModelForCausalLM

print("\n" + "=" * 70)
print("Downloading Florence-2 model (one-time, ~2GB)...")
print("=" * 70)

try:
    # Load Florence-2 model
    model_id = "microsoft/Florence-2-base"

    print(f"Loading model: {model_id}")
    print("(First time will download ~2GB - this may take 2-5 minutes)")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True, torch_dtype=torch.float16).to(device)

    print("✓ Florence-2 model loaded successfully")

except Exception as e:
    print(f"✗ Error loading model: {e}")
    print("Trying without GPU...")

    device = "cpu"
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True).to(device)

    print("✓ Florence-2 model loaded on CPU")

print("\n" + "=" * 70)
print("Testing with a sample screenshot")
print("=" * 70)

# Test function
def analyze_screenshot(image_path: str, task: str = "open_vocabulary_detection") -> dict:
    """
    Analyze a screenshot with Florence-2

    Args:
        image_path: Path to screenshot
        task: What to analyze
               - "open_vocabulary_detection" = Find objects
               - "region_classification" = Classify regions
               - "vqa" = Answer questions

    Returns:
        Analysis results
    """

    if not os.path.exists(image_path):
        return {"error": f"Image not found: {image_path}"}

    try:
        image = Image.open(image_path).convert("RGB")

        # Prepare input
        if task == "vqa":
            prompt = "<QUESTION> What is in this screenshot? </QUESTION>"
        elif task == "open_vocabulary_detection":
            prompt = "<OPEN_VOCABULARY_DETECTION>"
        else:
            prompt = "<REGION_CLASSIFICATION>"

        inputs = processor(text=prompt, images=image, return_tensors="pt").to(device)

        # Generate response
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            early_stopping=False,
            do_sample=False,
            num_beams=3,
        )

        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]

        return {
            "success": True,
            "task": task,
            "analysis": generated_text
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Test with a simple image if possible
test_image_path = "E:\\AI-Setup\\test_screenshot.png"

if os.path.exists(test_image_path):
    print(f"Analyzing test image: {test_image_path}")
    result = analyze_screenshot(test_image_path)
    if result.get("success"):
        print("✓ Vision analysis successful!")
        print(f"Result: {result['analysis'][:200]}...")
    else:
        print(f"⚠ Analysis failed: {result.get('error')}")
else:
    print(f"(No test image at {test_image_path}, but model is ready)")

print("\n" + "=" * 70)
print("SETUP COMPLETE - FLORENCE-2 IS READY")
print("=" * 70)

print("""
Usage during OpenCode test:

1. Take a screenshot:
   import mss
   with mss.mss() as sct:
       sct.shot(output='screenshot_opencode_001.png')

2. Analyze screenshot:
   from florence_vision_setup import analyze_screenshot
   result = analyze_screenshot('screenshot_opencode_001.png')
   print(result['analysis'])

3. Extract code understanding:
   - What files are visible?
   - What code is being edited?
   - What errors are shown?
   - Can Florence-2 understand IDE context?

This will help us understand what OpenCode is doing
while it emits framework signals.
""")

print("\nReady to start OpenCode test!")
print("Run this before starting: python florence_vision_setup.py")
