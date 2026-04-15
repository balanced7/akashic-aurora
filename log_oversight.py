import sys
sys.path.insert(0, r'E:\AI-Setup')
from error_documentation import ErrorDoc

doc = ErrorDoc()
doc.log_error(
    system='gemini_bridge',
    error_type='wrong_error_message',
    details='Barked Connection failed when actually just doing screen capture - wrong troubleshooting path. Should verify actual screen state before assuming connection issue.',
    severity='low'
)
print('Logged: gemini_bridge wrong_error_message')
