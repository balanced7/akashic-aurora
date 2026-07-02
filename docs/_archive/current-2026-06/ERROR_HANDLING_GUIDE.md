
# Error Handling Guide

## By System

### Launcher Issues
- **Problem**: New terminal window doesn't open or has errors
- **Check**: Look for "Python was not found" in terminal output
- **Fix**: Use full path to Python in BAT file (already done)
- **Verify**: Run launch_verifier with extended timeout

### Verification Issues  
- **Problem**: Launch appears to succeed but actually fails
- **Check**: Use both process check AND screen OCR
- **Fix**: Check for error keywords in screen text
- **Log**: Use log_error with "verification" system

### Logging Issues
- **Problem**: Logs not persisting to files
- **Check**: File exists but is empty
- **Fix**: Use f.flush() and os.fsync() after writes (already done)
- **Verify**: Check file immediately after log call

### OCR Issues
- **Problem**: Can't read screen text
- **Check**: Tesseract installed, screen has visible text
- **Fix**: Try multiple OCR methods (tesseract, windows, naturo)
- **Log**: Use log_error with "ocr" system

### UI Issues
- **Problem**: Naturo can't find elements
- **Check**: Window is accessible, not minimized
- **Fix**: Use different backend (uia, msaa, cdp)
- **Log**: Use log_error with "ui" system

## By Error Type

| Error Type | Common Cause | Solution |
|------------|--------------|----------|
| python_not_found | PATH issue in new terminal | Use full path |
| window_not_found | Window not created | Check process list |
| process_failed | App crashed on launch | Check error output |
| timeout | Operation took too long | Increase timeout |
| connection_failed | Redis not running | Check docker status |
