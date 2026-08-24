"""
Fast OCR Tool using PaddleOCR
=============================
Fast, accurate OCR for screen captures.

Usage:
    python fast_ocr.py
"""

import os
import time

os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_pir_apply_inplace_program'] = '1'

import mss

def capture_screen():
    """Capture screenshot"""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        path = os.path.expanduser("~\\fast_ocr_temp.png")
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=path)
        return path

def read_with_paddleocr():
    """Read text using PaddleOCR"""
    from paddleocr import PaddleOCR
    
    print("Initializing PaddleOCR (first run - may download models)...")
    ocr = PaddleOCR(lang='en')
    
    print("Processing image...")
    img_path = capture_screen()
    
    result = ocr.predict(img_path)
    
    # Extract text
    texts = []
    if result and result[0]:
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            texts.append(f"{text} ({confidence:.2f})")
    
    # Cleanup
    try:
        os.remove(img_path)
    except:
        pass
    
    return texts

def read_with_easyocr():
    """Fallback: Read text using EasyOCR"""
    import easyocr
    
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=False)
    
    print("Processing image...")
    img_path = capture_screen()
    
    result = reader.readtext(img_path)
    
    texts = []
    for detection in result:
        text = detection[1]
        confidence = detection[2]
        texts.append(f"{text} ({confidence:.2f})")
    
    try:
        os.remove(img_path)
    except:
        pass
    
    return texts

def main():
    print("=" * 60)
    print("  Fast OCR Tool - PaddleOCR")
    print("=" * 60)
    print()
    
    start = time.time()
    
    try:
        texts = read_with_paddleocr()
        elapsed = time.time() - start
        
        print(f"\n[DONE] OCR completed in {elapsed:.2f} seconds")
        print(f"Found {len(texts)} text regions")
        print()
        
        print("=" * 60)
        print("  DETECTED TEXT:")
        print("=" * 60)
        
        for i, text in enumerate(texts[:30]):  # Show first 30
            print(f"{i+1}. {text}")
        
        # Save to file
        output = os.path.expanduser("~\\Desktop\\ocr_output.txt")
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(texts))
        
        print()
        print(f"Saved to: {output}")
        
    except Exception as e:
        print(f"[ERROR] PaddleOCR failed: {e}")
        print("\nTrying EasyOCR as fallback...")
        
        try:
            texts = read_with_easyocr()
            print(f"Found {len(texts)} text regions")
            for t in texts[:10]:
                print(t)
        except Exception as e2:
            print(f"[ERROR] EasyOCR also failed: {e2}")

def read_with_tesseract():
    """Fast OCR using Tesseract"""
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    from PIL import Image
    
    print("Processing image with Tesseract...")
    img_path = capture_screen()
    
    img = Image.open(img_path)
    text = pytesseract.image_to_string(img)
    
    try:
        os.remove(img_path)
    except:
        pass
    
    return [text.strip()] if text.strip() else []

def read_with_paddleocr():
    """Read text using PaddleOCR"""
    from paddleocr import PaddleOCR
    
    print("Initializing PaddleOCR...")
    ocr = PaddleOCR(lang='en')
    
    print("Processing image...")
    img_path = capture_screen()
    
    result = ocr.predict(img_path)
    
    texts = []
    if result and result[0]:
        for line in result[0]:
            text = line[1][0]
            confidence = line[1][1]
            texts.append(f"{text} ({confidence:.2f})")
    
    try:
        os.remove(img_path)
    except:
        pass
    
    return texts

def read_with_easyocr():
    """Fallback: Read text using EasyOCR"""
    import easyocr
    
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=False)
    
    print("Processing image...")
    img_path = capture_screen()
    
    result = reader.readtext(img_path)
    
    texts = []
    for detection in result:
        text = detection[1]
        confidence = detection[2]
        texts.append(f"{text} ({confidence:.2f})")
    
    try:
        os.remove(img_path)
    except:
        pass
    
    return texts

def main():
    print("=" * 60)
    print("  Fast OCR Tool")
    print("=" * 60)
    print()
    
    start = time.time()
    texts = []
    
    # Try Tesseract first (fastest)
    try:
        texts = read_with_tesseract()
    except Exception as e:
        print(f"[Tesseract] {e}")
        
        # Try PaddleOCR second (highest accuracy)
        try:
            print("[Trying PaddleOCR...]")
            texts = read_with_paddleocr()
        except Exception as e2:
            print(f"[PaddleOCR] {e2}")
            
            # Try EasyOCR last (fallback)
            try:
                print("[Trying EasyOCR...]")
                texts = read_with_easyocr()
            except Exception as e3:
                print(f"[EasyOCR] All failed: {e3}")
                return
    
    elapsed = time.time() - start
    
    print(f"\n[DONE] OCR completed in {elapsed:.2f} seconds")
    print(f"Found {len(texts)} text regions")
    print()
    
    print("=" * 60)
    print("  DETECTED TEXT:")
    print("=" * 60)
    
    for i, text in enumerate(texts[:30]):
        print(f"{i+1}. {text}")
    
    output = os.path.expanduser("~\\Desktop\\ocr_output.txt")
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(texts))
    
    print()
    print(f"Saved to: {output}")

if __name__ == "__main__":
    main()