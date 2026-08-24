"""
vLLM Deployment Script for AMD RX 9070 XT (ROCm 6.x)
==================================================
Deploys vLLM with PagedAttention for high-throughput inference.

Requirements:
- AMD RX 9070 XT (16GB VRAM)
- ROCm 6.0+ driver
- ROCm-compatible PyTorch

Usage:
    # Option 1: Direct Docker
    docker run --rm \
        --device /dev/kfd --device /dev/dri \
        --group-add video \
        -p 8000:8000 \
        -v $HOME/.cache/huggingface:/root/.cache/huggingface \
        rocm/vllm:latest \
        --model deepseek-ai/deepseek-coder-v2-16b \
        --gpu-memory-utilization 0.90 \
        --max-model-len 16384
    
    # Option 2: Use this script
    python deploy_vllm.py --model deepseek-ai/deepseek-coder-v2-16b
"""

import os
import sys
import argparse
import subprocess
from typing import Optional

# Configuration
VLLM_IMAGE = "rocm/vllm:latest"
DEFAULT_MODEL = "deepseek-ai/deepseek-coder-v2-16b"
HUGGINGFACE_CACHE = os.path.expanduser("~/.cache/huggingface")
API_PORT = 8000

# VRAM Settings
GPU_MEMORY_UTILIZATION = 0.90  # Use 90% of VRAM
MAX_MODEL_LEN = 32768  # 32k context

# Model Catalog for VRAM Optimization
MODELS = {
    "deepseek-ai/deepseek-coder-v2-16b": {
        "vram_gb": 8.9,
        "recommended_len": 32768,
        "quantization": "fp16"
    },
    "meta-llama/Llama-3.2-3B-Instruct": {
        "vram_gb": 2.0,
        "recommended_len": 8192,
        "quantization": "fp16"
    },
    "microsoft/Florence-2-large": {
        "vram_gb": 1.5,
        "recommended_len": 2048,
        "quantization": "fp16"
    },
}


def check_rocm() -> bool:
    """Check if ROCm is available"""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showdrammouse"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def check_rocm_pytorch() -> bool:
    """Check if ROCm PyTorch is installed"""
    try:
        import torch
        return torch.cuda.is_available() and torch.version.hip
    except:
        return False


def get_gpu_vram() -> Optional[float]:
    """Get total GPU VRAM in GB"""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showid", "--json"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            for gpu_id, info in data.items():
                if 'vram_used' in info:
                    vram_str = info.get('vram_total', '16384MB')
                    vram_gb = float(vram_str.replace('MB', '')) / 1024
                    return vram_gb
    except:
        pass
    return None


def calculate_memory_fraction(model_name: str, vram_gb: float) -> float:
    """
    Calculate optimal gpu-memory-utilization for a model.
    
    Leaves room for:
    - Model weights
    - KV cache
    - Activation memory
    """
    if model_name in MODELS:
        model_vram = MODELS[model_name]["vram_gb"]
    else:
        # Estimate based on parameter count
        model_vram = 8.0  # Default assumption
    
    # Use 90% of available VRAM minus a small buffer
    buffer = 0.5  # GB buffer for system
    available = vram_gb - buffer
    fraction = min(0.95, available / vram_gb)
    
    return fraction


def generate_docker_run(model: str, port: int = API_PORT, 
                       tensor_parallel: int = 1,
                       enforce_eager: bool = False) -> str:
    """
    Generate docker run command for vLLM with AMD ROCm.
    """
    cmd = [
        "docker run --rm",
        "--name vllm-server",
        "--device /dev/kfd",
        "--device /dev/dri",
        "--group-add video",
        f"-p {port}:8000",
        f"-v {HUGGINGFACE_CACHE}:/root/.cache/huggingface",
        "-e HF_TOKEN=$HF_TOKEN",  # Optional: for gated models
        VLLM_IMAGE,
        "--model", model,
        f"--gpu-memory-utilization {GPU_MEMORY_UTILIZATION}",
        f"--max-model-len {MAX_MODEL_LEN}",
        f"--tensor-parallel-size {tensor_parallel}",
        "--dtype float16",
        "--enforce-eager" if enforce_eager else "",
        "--trust-remote-code",
        "--seed 42",
    ]
    
    # Filter empty strings
    cmd = [c for c in cmd if c]
    return " \\\n    ".join(cmd)


def generate_docker_compose(model: str, port: int = API_PORT) -> str:
    """
    Generate docker-compose.yml for vLLM with AMD ROCm.
    """
    compose = f'''version: '3.8'

services:
  vllm:
    image: {VLLM_IMAGE}
    container_name: vllm-server
    restart: unless-stopped
    ports:
      - "{port}:8000"
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    environment:
      - HF_TOKEN=${{HF_TOKEN:-}}
    devices:
      - /dev/kfd:/dev/kfd
      - /dev/dri:/dev/dri
    group_add:
      - video
    command: >
      --model {model}
      --gpu-memory-utilization {GPU_MEMORY_UTILIZATION}
      --max-model-len {MAX_MODEL_LEN}
      --dtype float16
      --trust-remote-code
      --seed 42
    deploy:
      resources:
        reservations:
          devices:
            - driver: amd
              count: all
              capabilities: [gpu, rocm]
'''
    return compose


def deploy_direct(model: str, port: int = API_PORT) -> int:
    """
    Deploy vLLM directly using python -m vllm.
    Requires: pip install vllm[rocm]
    """
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--gpu-memory-utilization", str(GPU_MEMORY_UTILIZATION),
        "--max-model-len", str(MAX_MODEL_LEN),
        "--dtype", "float16",
        "--trust-remote-code",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--seed", "42",
    ]
    
    print(f"[vLLM] Starting server...")
    print(f"[vLLM] Command: {' '.join(cmd)}")
    
    return subprocess.run(cmd).returncode


def test_connection(port: int = API_PORT) -> bool:
    """Test if vLLM server is responding"""
    import urllib.request
    import json
    
    try:
        # Check models endpoint
        url = f"http://localhost:{port}/v1/models"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            models = data.get("data", [])
            print(f"[vLLM] Connected! Available models: {len(models)}")
            for m in models:
                print(f"  - {m.get('id', 'unknown')}")
            return True
    except Exception as e:
        print(f"[vLLM] Connection failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Deploy vLLM on AMD ROCm")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model to deploy")
    parser.add_argument("--port", type=int, default=API_PORT, help="API port")
    parser.add_argument("--docker", action="store_true", help="Use Docker (default)")
    parser.add_argument("--direct", action="store_true", help="Deploy directly with Python")
    parser.add_argument("--compose", action="store_true", help="Generate docker-compose.yml")
    parser.add_argument("--print-cmd", action="store_true", help="Print docker command and exit")
    parser.add_argument("--test", action="store_true", help="Test if server is running")
    parser.add_argument("--tensor-parallel", type=int, default=1, help="Tensor parallel size")
    parser.add_argument("--enforce-eager", action="store_true", help="Enforce eager mode (no CUDA graphs)")
    
    args = parser.parse_args()
    
    # Handle --test separately
    if args.test:
        success = test_connection(args.port)
        sys.exit(0 if success else 1)
    
    # Generate docker-compose if requested
    if args.compose:
        compose = generate_docker_compose(args.model, args.port)
        print(compose)
        compose_path = "vllm-docker-compose.yml"
        with open(compose_path, "w") as f:
            f.write(compose)
        print(f"[vLLM] docker-compose.yml written to {compose_path}")
        print(f"[vLLM] Run with: docker-compose -f {compose_path} up -d")
        sys.exit(0)
    
    # Print command if requested
    if args.print_cmd:
        cmd = generate_docker_run(args.model, args.port, args.tensor_parallel, args.enforce_eager)
        print(cmd)
        sys.exit(0)
    
    # Pre-flight checks
    print("=" * 50)
    print("vLLM AMD ROCm Deployment")
    print("=" * 50)
    
    print(f"\n[1] Checking ROCm...")
    if not check_rocm():
        print("[!] ROCm not detected. Install ROCm 6.0+")
        sys.exit(1)
    print("[OK] ROCm detected")
    
    vram = get_gpu_vram()
    if vram:
        print(f"[OK] GPU VRAM: {vram:.1f} GB")
    
    if args.direct:
        print(f"\n[2] Deploying vLLM directly...")
        sys.exit(deploy_direct(args.model, args.port))
    else:
        print(f"\n[2] Generating Docker command...")
        cmd = generate_docker_run(args.model, args.port, args.tensor_parallel, args.enforce_eager)
        print(cmd)
        
        print(f"\n[3] To deploy, run:")
        print(f"    {cmd}")
        
        print(f"\n[4] Or use docker-compose:")
        print(f"    python {sys.argv[0]} --compose --model '{args.model}'")
        print(f"    docker-compose -f vllm-docker-compose.yml up -d")
        
        print(f"\n[5] Test with:")
        print(f"    curl http://localhost:{args.port}/v1/models")


if __name__ == "__main__":
    main()
