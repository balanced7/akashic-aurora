#!/bin/bash
python3 -c "
import torch
print('PyTorch:', torch.__version__)
print('ROCm:', torch.version.hip if hasattr(torch.version, 'hip') else 'N/A')
print('CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
"