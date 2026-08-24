"""
Vision Engine via ComfyUI - Redis-Cached Florence-2
====================================================

Uses ComfyUI's REST API to run Florence-2 with ZLUDA acceleration.
All results are cached in Redis for fast multi-agent retrieval.

Usage:
    from vision_engine_comfy import ComfyVisionEngine, capture_and_analyze

    engine = ComfyVisionEngine()
    result = engine.analyze_screen(task="ocr")
"""

import os
import json
import hashlib
import base64
import io
import time
import uuid
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from urllib import request, parse
import urllib.error

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from PIL import Image, ImageGrab

COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188
COMFYUI_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PREFIX = "vision:"
CACHE_TTL = 3600

SCREENSHOT_DIR = r"E:\AI-Setup\session_screenshots"
COMFYUI_INPUT_DIR = r"E:\AI-Setup\ComfyUI-Zluda\input"
COMFYUI_OUTPUT_DIR = r"E:\AI-Setup\ComfyUI-Zluda\output"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

FLORENCE_MODEL = "microsoft/Florence-2-large"
FLORENCE_TASK = "ocr"

COMFYUI_AVAILABLE = None


def get_redis():
    if not REDIS_AVAILABLE:
        return None
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
        return r
    except:
        return None


def check_comfyui_running() -> bool:
    global COMFYUI_AVAILABLE
    if COMFYUI_AVAILABLE is not None:
        return COMFYUI_AVAILABLE
    try:
        with request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=2) as resp:
            COMFYUI_AVAILABLE = resp.status == 200
            return COMFYUI_AVAILABLE
    except:
        COMFYUI_AVAILABLE = False
        return False


def upload_image(image_path: str) -> Tuple[bool, str]:
    with open(image_path, 'rb') as f:
        image_data = f.read()
    req = request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=image_data,
        headers={'Content-Type': 'application/octet-stream'}
    )
    try:
        resp = request.urlopen(req)
        result = json.loads(resp.read())
        return True, result.get('name', '')
    except Exception as e:
        print(f"[vision] Upload failed: {e}")
        return False, ""


def queue_prompt(prompt: dict) -> Optional[str]:
    p = {"prompt": prompt}
    data = json.dumps(p).encode('utf-8')
    req = request.Request(f"{COMFYUI_URL}/prompt", data=data)
    try:
        resp = request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get('prompt_id')
    except Exception as e:
        print(f"[vision] Queue failed: {e}")
        return None


def get_history(prompt_id: str) -> Optional[dict]:
    try:
        with request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[vision] History fetch failed: {e}")
        return None


def wait_for_completion(prompt_id: str, timeout: int = 300) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        history = get_history(prompt_id)
        if history and prompt_id in history:
            return True
        time.sleep(1)
    return False


def get_image_output(history: dict, node_id: str) -> Optional[bytes]:
    try:
        outputs = history.get(prompt_id_from_history(history), {}).get('outputs', {})
        if node_id in outputs:
            output = outputs[node_id]
            if 'images' in output:
                img_info = output['images'][0]
                params = parse.urlencode({
                    'filename': img_info['filename'],
                    'subfolder': img_info['subfolder'],
                    'type': img_info.get('type', 'output')
                })
                with request.urlopen(f"{COMFYUI_URL}/view?{params}") as resp:
                    return resp.read()
    except Exception as e:
        print(f"[vision] Image fetch failed: {e}")
    return None


def prompt_id_from_history(history: dict) -> Optional[str]:
    for key in history.keys():
        return key
    return None


def create_florence_workflow(image_filename: str, task: str = "ocr") -> dict:
    return {
        "1": {
            "class_type": "DownloadAndLoadFlorence2Model",
            "inputs": {
                "model": FLORENCE_MODEL,
                "precision": "fp16"
            }
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_filename
            }
        },
        "3": {
            "class_type": "Florence2Run",
            "inputs": {
                "image": ["2", 0],
                "florence2_model": ["1", 0],
                "text_input": "",
                "task": task,
                "fill_mask": True,
                "do_sample": False
            }
        }
    }


class ComfyVisionEngine:
    def __init__(self, model: str = FLORENCE_MODEL):
        self.model = model
        self._redis = get_redis()
        self._workflow_cache = {}

    def analyze(self, image: Image.Image, task: str = "ocr") -> Dict[str, Any]:
        img_hash = hashlib.md5(image.tobytes()).hexdigest()[:12]
        cache_key = f"{REDIS_PREFIX}analysis:{task}:{img_hash}"

        if self._redis:
            cached = self._redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                data["cached"] = True
                return data

        if not check_comfyui_running():
            return {"error": "ComfyUI not running", "task": task}

        temp_path = os.path.join(SCREENSHOT_DIR, f"temp_{img_hash}.png")
        image.save(temp_path, "PNG")

        success, filename = upload_image(temp_path)
        if not success:
            os.remove(temp_path)
            return {"error": "Image upload failed", "task": task}

        os.remove(temp_path)

        workflow = create_florence_workflow(filename, task)
        prompt_id = queue_prompt(workflow)

        if not prompt_id:
            return {"error": "Failed to queue prompt", "task": task}

        if not wait_for_completion(prompt_id, timeout=300):
            return {"error": "Timeout waiting for completion", "task": task}

        history = get_history(prompt_id)
        if not history:
            return {"error": "Failed to get results", "task": task}

        result_text = ""
        try:
            outputs = history.get(prompt_id_from_history(history), {}).get('outputs', {})
            if "3" in outputs:
                result_text = outputs["3"].get("caption", "")
        except Exception as e:
            return {"error": f"Failed to parse results: {e}", "task": task}

        result = {
            "task": task,
            "result": result_text,
            "image_hash": img_hash,
            "device": "ComfyUI+ZLUDA",
            "timestamp": datetime.now().isoformat(),
            "cached": False
        }

        if self._redis and result_text:
            try:
                self._redis.setex(cache_key, CACHE_TTL, json.dumps(result))
            except Exception as e:
                print(f"[vision] Redis cache failed: {e}")

        return result

    def analyze_screen(self, task: str = "ocr") -> Dict[str, Any]:
        image = capture_screen()
        if image is None:
            return {"error": "Screen capture failed"}
        result = self.analyze(image, task)
        result["image_size"] = f"{image.width}x{image.height}"
        return result


def capture_screen() -> Optional[Image.Image]:
    try:
        return ImageGrab.grab(include_layered_windows=False)
    except Exception as e:
        print(f"[vision] Capture failed: {e}")
        return None


def save_to_redis(image: Image.Image, tag: str = "capture") -> str:
    if image is None:
        return None

    img_hash = hashlib.md5(image.tobytes()).hexdigest()[:12]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    disk_path = os.path.join(SCREENSHOT_DIR, f"screen_{tag}_{timestamp}_{img_hash}.png")
    image.save(disk_path, "PNG")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    r = get_redis()
    if r:
        redis_key = f"{REDIS_PREFIX}screenshot:{img_hash}"
        redis_data = {
            "hash": img_hash,
            "tag": tag,
            "timestamp": timestamp,
            "width": image.width,
            "height": image.height,
            "data": b64_data,
            "disk_path": disk_path
        }
        r.setex(redis_key, CACHE_TTL, json.dumps(redis_data))
        r.sadd(f"{REDIS_PREFIX}screenshot_keys", img_hash)
        print(f"[vision] Screenshot {img_hash} saved to Redis + disk")
        return img_hash

    return disk_path


def capture_and_analyze(task: str = "ocr") -> Dict[str, Any]:
    image = capture_screen()
    if image is None:
        return {"error": "Screen capture failed"}

    img_hash = save_to_redis(image, "analysis")

    engine = ComfyVisionEngine()
    result = engine.analyze(image, task)
    result["image_hash"] = img_hash
    result["image_size"] = f"{image.width}x{image.height}"

    r = get_redis()
    if r:
        analysis_key = f"{REDIS_PREFIX}analysis:{img_hash}:{task}"
        r.setex(analysis_key, CACHE_TTL, json.dumps(result))

    return result


def get_cached_analysis(img_hash: str, task: str = "ocr") -> Optional[Dict]:
    r = get_redis()
    if not r:
        return None

    data = r.get(f"{REDIS_PREFIX}analysis:{task}:{img_hash}")
    if data:
        result = json.loads(data)
        result["cached"] = True
        return result
    return None


def quick_ocr() -> str:
    result = capture_and_analyze("ocr")
    return result.get("result", result.get("error", "Failed"))


def quick_caption() -> str:
    result = capture_and_analyze("caption")
    return result.get("result", result.get("error", "Failed"))


if __name__ == "__main__":
    print("=" * 60)
    print("Vision Engine via ComfyUI + Redis")
    print("=" * 60)

    print("\n[1] Checking ComfyUI status...")
    if check_comfyui_running():
        print("    ComfyUI is RUNNING")
    else:
        print("    ComfyUI is NOT running - start it with comfyui-n.bat")
        print("    Then install Florence-2 custom node and run again")
        exit(1)

    print("\n[2] Testing screen capture...")
    image = capture_screen()
    if image:
        print(f"    Captured: {image.size}")
    else:
        print("    Capture failed")
        exit(1)

    print("\n[3] Testing OCR via ComfyUI Florence-2...")
    result = capture_and_analyze("ocr")
    if "error" in result:
        print(f"    Error: {result['error']}")
    else:
        print(f"    OCR result: {result.get('result', '')[:200]}")

    print("\n[4] Testing caption via ComfyUI Florence-2...")
    result = capture_and_analyze("caption")
    if "error" in result:
        print(f"    Error: {result['error']}")
    else:
        print(f"    Caption: {result.get('result', '')[:200]}")

    print("\n" + "=" * 60)
    print("Vision Engine complete!")
    print("=" * 60)