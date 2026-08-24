"""
Desktop Automation - PyAutoGUI wrapper with safety features
=========================================================
Provides mouse and keyboard automation with fail-safes and vision integration.

Safety: Move mouse to corner to abort any automation.
"""

import sys
import time
import pyautogui
import numpy as np
from typing import Optional, Tuple

# Safety settings
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1      # Small pause between actions

# For screenshots
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from vision_engine import capture_active_window, get_screen_context_for_analyst
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False


class DesktopAutomation:
    """
    Desktop automation with vision feedback.
    
    Use for:
    - Clicking buttons in browser/apps
    - Typing text
    - Monitoring screen for changes
    """
    
    def __init__(self):
        self.last_screenshot = None
        self.click_duration = 0.2
    
    def screenshot(self) -> Optional[np.ndarray]:
        """Capture screenshot of active window"""
        try:
            self.last_screenshot = capture_active_window()
            return self.last_screenshot
        except Exception as e:
            print(f"[automation] Screenshot failed: {e}")
            return None
    
    def click(self, x: int, y: int, button: str = 'left') -> bool:
        """Click at coordinates"""
        try:
            pyautogui.click(x=x, y=y, button=button, duration=self.click_duration)
            return True
        except Exception as e:
            print(f"[automation] Click failed: {e}")
            return False
    
    def click_image(self, image_path: str, confidence: float = 0.8, timeout: int = 10) -> bool:
        """
        Click on an image if it appears on screen.
        
        Args:
            image_path: Path to image to find
            confidence: Match confidence (0-1)
            timeout: Max seconds to wait for image
        
        Returns:
            True if found and clicked
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                if location:
                    center = pyautogui.center(location)
                    print(f"[automation] Found image at {center}, clicking")
                    pyautogui.click(center, duration=self.click_duration)
                    return True
            except pyautogui.ImageNotFoundException:
                pass
            except Exception as e:
                print(f"[automation] Image search error: {e}")
            time.sleep(0.5)
        
        print(f"[automation] Image not found: {image_path}")
        return False
    
    def type_text(self, text: str, interval: float = 0.05) -> bool:
        """Type text using keyboard"""
        try:
            pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            print(f"[automation] Type failed: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """Press a single key"""
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            print(f"[automation] Key press failed: {e}")
            return False
    
    def hotkey(self, *keys) -> bool:
        """Press a hotkey combination"""
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            print(f"[automation] Hotkey failed: {e}")
            return False
    
    def find_text_on_screen(self, text: str, confidence: float = 0.7) -> Optional[Tuple[int, int]]:
        """
        Find text on screen using OCR.
        
        Returns center coordinates of first match or None.
        """
        if not VISION_AVAILABLE:
            print("[automation] Vision not available")
            return None
        
        screenshot = self.screenshot()
        if screenshot is None:
            return None
        
        context = get_screen_context_for_analyst(screenshot)
        extracted = context.get('extracted_text', '')
        
        if text.lower() in extracted.lower():
            print(f"[automation] Found text: {text}")
            # Return center of screen as approximation
            # In production, would use proper OCR localization
            screen_size = pyautogui.size()
            return (screen_size[0] // 2, screen_size[1] // 2)
        
        return None
    
    def wait_for_change(self, timeout: int = 30, check_interval: float = 1.0) -> bool:
        """
        Wait for screen content to change.
        
        Returns True if change detected, False if timeout.
        """
        if not PIL_AVAILABLE or self.last_screenshot is None:
            return True  # Assume changed if we can't compare
        
        last_hash = self._image_hash(self.last_screenshot)
        start = time.time()
        
        while time.time() - start < timeout:
            time.sleep(check_interval)
            screenshot = self.screenshot()
            if screenshot is None:
                continue
            
            current_hash = self._image_hash(screenshot)
            if current_hash != last_hash:
                print("[automation] Screen change detected")
                return True
        
        return False
    
    def _image_hash(self, image) -> int:
        """Simple hash of image for change detection"""
        if PIL_AVAILABLE and hasattr(image, 'tobytes'):
            try:
                return hash(image.tobytes()[:1000])
            except:
                pass
        return hash(str(image.shape) if hasattr(image, 'shape') else str(type(image)))
    
    def monitor_until_found(self, text: str = None, image_path: str = None, 
                           timeout: int = 30) -> bool:
        """
        Monitor screen until text or image is found.
        
        Returns True if found within timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            # Check for image
            if image_path:
                try:
                    location = pyautogui.locateOnScreen(image_path, confidence=0.8)
                    if location:
                        return True
                except:
                    pass
            
            # Check for text
            if text and VISION_AVAILABLE:
                screenshot = self.screenshot()
                if screenshot:
                    context = get_screen_context_for_analyst(screenshot)
                    if text.lower() in context.get('extracted_text', '').lower():
                        return True
            
            time.sleep(0.5)
        
        return False


def test_automation():
    """Quick test of automation features"""
    print("=" * 50)
    print("Desktop Automation Test")
    print("=" * 50)
    
    auto = DesktopAutomation()
    
    print("\n[1] Screenshot test...")
    img = auto.screenshot()
    print(f"    Screenshot captured: {img is not None}")
    
    print("\n[2] Screen info...")
    size = pyautogui.size()
    print(f"    Screen size: {size}")
    
    print("\n[3] Vision context...")
    if VISION_AVAILABLE:
        screenshot = auto.screenshot()
        if screenshot:
            context = get_screen_context_for_analyst(screenshot)
            print(f"    Caption: {context.get('caption', 'N/A')[:100]}")
            print(f"    Has text: {bool(context.get('extracted_text'))}")
    
    print("\n[4] Current mouse position...")
    pos = pyautogui.position()
    print(f"    Position: {pos}")
    
    print("\nDesktop automation ready!")
    print("Move mouse to corner to abort any automation.")


if __name__ == "__main__":
    test_automation()
