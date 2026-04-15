import sys
sys.path.insert(0, r'E:\AI-Setup')
from error_documentation import ErrorDoc

doc = ErrorDoc()
doc.log_error(
    system='vision',
    error_type='gpu_detection_fix',
    details='Added DirectML support for AMD GPU on Windows. torch_directml properly detects AMD 9070 XT as privateuseone:0. However model inference still runs on CPU - DirectML tensor ops work but transformers model must stay on CPU due to architecture compatibility.',
    severity='low'
)
print('Logged: GPU detection fix with DirectML')
