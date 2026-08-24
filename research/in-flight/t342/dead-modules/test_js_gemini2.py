import sys
sys.path.insert(0, r'E:\AI-Setup')
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

chromedriver_path = r"C:\Users\L5\.chromedriver-autoinstaller\chromedriver-win64\chromedriver.exe"

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

def find_response(driver):
    """Try multiple selectors to find response"""
    selectors = [
        "div.model-response-text",
        "div[class*='response']",
        "div[class*='model']",
        "article",
        "div[role='region']",
        "div.model-response",
        "gc-response-text",
        "div.result"
    ]
    
    for sel in selectors:
        try:
            els = driver.find_elements("css selector", sel)
            for el in els:
                text = el.text
                if text and len(text) > 20 and "typing" not in text.lower():
                    return sel, text
        except:
            pass
    return None, None

try:
    print("[1] Connected")
    
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        if "gemini" in driver.current_url.lower():
            # Fresh page
            driver.get("https://gemini.google.com/app")
            time.sleep(3)
            print("[2] Page loaded")
            
            # Type via JS
            driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) { inp.innerText = \"What is the capital of France?\"; }"
            )
            print("[3] Typed")
            
            # Submit via JS
            driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) { inp.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13})); }"
                "if (inp) { inp.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', keyCode: 13})); }"
            )
            print("[4] Submitted, waiting for response...")
            
            # Poll for response for up to 15 seconds
            for i in range(15):
                time.sleep(1)
                sel, text = find_response(driver)
                if text:
                    print(f"[5] Response found ({sel}): {text[:150]}...")
                    break
                print(f"  Waiting... {i+1}s - no response yet")
            else:
                print("[5] No response after 15s")
                
                # Capture page state via JS
                page_state = driver.execute_script(
                    "return {"
                    "  title: document.title,"
                    "  url: window.location.href,"
                    "  bodyText: document.body.innerText.slice(0, 500)"
                    "};"
                )
                print("Page state:", page_state)
            
            break
    
    driver.quit()
    print("[6] Done")
except Exception as e:
    print("Error:", str(e)[:300])
    try:
        driver.quit()
    except:
        pass
