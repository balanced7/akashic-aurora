#!/usr/bin/env python3
"""Test PyTorch ROCm GPU detection and basic inference."""
import os
import sys

os.environ['ROCM_PATH'] = '/opt/rocm'
os.environ['HSA_ENABLE_DXG_DETECTION'] = '1'
os.environ['LD_LIBRARY_PATH'] = '/opt/rocm/lib:/opt/rocm/lib64:' + os.environ.get('LD_LIBRARY_PATH', '')

print("=== GPU Detection Test ===")
print(f"ROCM_PATH: {os.environ.get('ROCM_PATH')}")
print(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH')}")

try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"ROCm available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"GPU count: {torch.cuda.device_count()}")
        print(f"GPU name: {torch.cuda.get_device_name(0)}")
        print(f"GPU capability: {torch.cuda.get_device_capability(0)}")
        print(f"Memory allocated: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")
        
        # Test tensor operation on GPU
        print("\n=== GPU Tensor Test ===")
        x = torch.randn(1000, 1000, device='cuda')
        y = torch.randn(1000, 1000, device='cuda')
        z = torch.matmul(x, y)
        print(f"Matrix multiply result shape: {z.shape}")
        print(f"Result device: {z.device}")
        print("GPU tensor operations: SUCCESS")
        
        # Test memory access
        print(f"\n=== Memory Test ===")
        print(f"Memory reserved: {torch.cuda.memory_reserved(0) / 1e9:.2f} GB")
        print(f"Memory allocated: {torch.cuda.memory_allocated(0) / 1e9:.2f} GB")
        
    else:
        print("ERROR: CUDA not available!")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== All GPU tests passed ===")
