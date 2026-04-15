#!/bin/bash
# Test PyTorch ROCm in dev container

export HSA_ENABLE_DXG_DETECTION=1
export LD_LIBRARY_PATH=/opt/rocm/lib:/usr/lib/wsl/lib
export ROCM_PATH=/opt/rocm
export HSA_OVERRIDE_GFX_VERSION=12.0.1

python3 << 'PYTHON_EOF'
import os
os.environ['ROCM_PATH'] = '/opt/rocm'
os.environ['HSA_OVERRIDE_GFX_VERSION'] = '12.0.1'

try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"ROCm available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"GPU count: {torch.cuda.device_count()}")
        print(f"GPU name: {torch.cuda.get_device_name(0)}")
        print(f"GPU capability: {torch.cuda.get_device_capability(0)}")
        print(f"Memory allocated: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")
        
        # Test tensor operation
        x = torch.randn(100, 100, device='cuda')
        y = torch.randn(100, 100, device='cuda')
        z = torch.matmul(x, y)
        print(f"Matrix multiply on GPU: SUCCESS, result shape {z.shape}")
    else:
        print("ERROR: CUDA not available")
        exit(1)
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\nGPU test PASSED")
PYTHON_EOF
