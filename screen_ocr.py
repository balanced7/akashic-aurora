"""
Screen OCR Tool
===============
Reads text from screenshots using Windows built-in OCR.
Fast, reliable, no external dependencies needed.

Usage:
    python screen_ocr.py
    
Or in code:
    from screen_ocr import read_screen_text
    text = read_screen_text()
"""

import subprocess
import sys
import os
import mss
import time

def capture_screen():
    """Capture screenshot to temp file"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        
        # Save to temp
        temp_path = os.path.expanduser("~\\screen_ocr_temp.png")
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=temp_path)
        return temp_path

def read_screen_text():
    """Use Windows OCR to read text from screen"""
    img_path = capture_screen()
    img_path_escaped = img_path.replace("\\", "\\\\")
    
    # Use PowerShell with Windows.Media.Ocr
    ps_script = f'''
Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Windows.winmd

$asyncOp = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if ($asyncOp -eq $null) {{
    Write-Error "OCR not available"
    exit 1
}}

$storageFile = [Windows.Storage.StorageFile]::GetFileFromPathAsync("{img_path_escaped}")
$storageFile.Wait()

$bitmap = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($storageFile.GetResults().AsRandomAccessStream())
$bitmap.Wait()
$img = $bitmap.GetResults()

$result = $asyncOp.GetResults().RecognizeAsync($img)
$result.Wait()

$text = $result.GetResults().Text
Write-Output $text
'''
    
    try:
        result = subprocess.run([
            'powershell', '-Command', ps_script
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return result.stdout
        else:
            # Fallback: use basic image parsing
            return f"[OCR Error: {result.stderr}]"
    except Exception as e:
        return f"[Error: {e}]"
    finally:
        # Cleanup temp file
        try:
            os.remove(img_path)
        except:
            pass

def simple_read():
    """Simple OCR using pytesseract if available"""
    try:
        import pytesseract
        from PIL import Image
        
        img_path = capture_screen()
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        
        os.remove(img_path)
        return text
    except Exception as e:
        return f"[OCR Error: {e}]"

def read_with_ocr():
    """Try Windows OCR first, fallback to simple"""
    print("Capturing screen...")
    img_path = capture_screen()
    print(f"Saved to: {img_path}")
    
    # Try Windows OCR
    print("\nUsing Windows OCR...")
    text = read_screen_text()
    
    if text and "Error" not in text:
        return text
    
    # Try pytesseract
    print("\nFallback to Tesseract OCR...")
    text = simple_read()
    
    return text

if __name__ == "__main__":
    print("=" * 60)
    print("  Screen OCR Tool")
    print("=" * 60)
    print()
    
    text = read_with_ocr()
    
    print("\n" + "=" * 60)
    print("  DETECTED TEXT:")
    print("=" * 60)
    print(text[:2000] if text else "No text detected")
    
    # Save to file
    if text:
        with open(os.path.expanduser("~\\Desktop\\ocr_output.txt"), "w") as f:
            f.write(text)
        print("\nSaved to: Desktop\\ocr_output.txt")