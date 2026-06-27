import torch
print("CUDA available:", torch.cuda.is_available())
print("ROCm available:", hasattr(torch, "hip"))
if torch.cuda.is_available():
    print("GPU device:", torch.cuda.get_device_name(0))
    print("VRAM:", torch.cuda.get_device_properties(0).total_memory / 1e9, "GB")
device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
print("Using device:", device)