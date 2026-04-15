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

try:
    print("[1] Connected")
    
    handles = driver.window_handles
    for handle in handles:
        driver.switch_to.window(handle)
        if "gemini" in driver.current_url.lower():
            driver.get("https://gemini.google.com/app")
            time.sleep(3)
            print("[2] Page loaded")
            
            # Check initial state
            inp_text = driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "return inp ? inp.innerText : 'no_input';"
            )
            print("[3] Input text:", repr(inp_text))
            
            # Type
            driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "if (inp) inp.innerText = 'What is 2+2?';"
            )
            
            inp_text = driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "return inp ? inp.innerText : 'no_input';"
            )
            print("[4] Input after typing:", repr(inp_text))
            
            # Submit using a different approach - click the send button if exists
            btn_clicked = driver.execute_script(
                "var btn = document.querySelector(\"button[aria-label*='Send']\") || "
                "document.querySelector(\"button[aria-label*='send']\") || "
                "document.querySelector(\"div[role='button'][aria-label*='Send'\");"
                "if (btn) { btn.click(); return 'clicked'; } return 'no_button';"
            )
            print("[5] Button click result:", btn_clicked)
            
            if btn_clicked == 'no_button':
                # Try Enter key via keyboard event
                driver.execute_script(
                    "var inp = document.querySelector(\"div[role='textbox']\");"
                    "if (inp) { inp.focus(); }"
                )
                time.sleep(0.5)
                driver.execute_script(
                    "var inp = document.querySelector(\"div[role='textbox']\");"
                    "var e = new KeyboardEvent('keypress', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13});"
                    "if (inp) inp.dispatchEvent(e);"
                )
                print("[5b] Sent via keypress")
            
            time.sleep(10)
            
            # Check what happened
            inp_text = driver.execute_script(
                "var inp = document.querySelector(\"div[role='textbox']\");"
                "return inp ? inp.innerText : 'no_input';"
            )
            print("[6] Input after submit:", repr(inp_text))
            
            # Check page content
            body_len = driver.execute_script("return document.body.innerText.length;")
            print("[7] Body text length:", body_len)
            
            # Check for any new content
            all_divs = driver.execute_script(
                "var divs = document.querySelectorAll('div');"
                "var texts = [];"
                "for (var i = 0; i < divs.length; i++) {"
                "  if (divs[i].innerText.length > 50 && divs[i].innerText.length < 500) {"
                "    texts.push(divs[i].innerText.slice(0, 100));"
                "  }"
                "}"
                "return JSON.stringify(texts.slice(0, 5));"
            )
            print("[8] Sample div texts:", all_divs[:200] if all_divs else "none")
            
            # Capture vision context
            from vision_engine import get_screen_context_for_analyst, capture_active_window
            screenshot = capture_active_window()
            context = get_screen_context_for_analyst(screenshot)
            print("[9] Vision caption:", context.get("caption", "N/A")[:150])
            if context.get("extracted_text"):
                print("[10] Vision text:", context["extracted_text"][:150])
            
            break
    
    driver.quit()
    print("[11] Done")
except Exception as e:
    print("Error:", str(e)[:300])
    import traceback
    traceback.print_exc()
    try:
        driver.quit()
    except:
        pass
