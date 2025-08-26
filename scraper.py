import re
import time
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# -----------------------
# CONFIG
# -----------------------
CHROME_DRIVER_PATH = r"C:\Users\pokhr\Downloads\chromedriver-win64\chromedriver-win64\chromedriver.exe"
CITIES = ['Lucknow', 'Kanpur', 'Nagpur']
KEYWORD = "accounting firms"
MAX_LISTINGS_PER_CITY = 25
SCROLL_TIMES = 10

# -----------------------
# DRIVER SETUP
# -----------------------
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument('--start-maximized')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument('--disable-extensions')
options.add_argument('--disable-plugins')
options.add_experimental_option('excludeSwitches', ['enable-automation'])
options.add_experimental_option('useAutomationExtension', False)
options.add_experimental_option("prefs", {
    "profile.default_content_setting_values.images": 2,
    "profile.managed_default_content_settings.images": 2
})

# Try to install ChromeDriver with webdriver-manager
try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
except Exception as e:
    print(f"Failed to install ChromeDriver automatically: {e}")
    print("Falling back to system Chrome...")
    # Fallback: Use system Chrome if available
    options.binary_location = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    driver = webdriver.Chrome(options=options)

driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
        Object.defineProperty(navigator, "webdriver", {get: () => undefined})
        window.chrome = {
            runtime: {},
            loadTimes: function() { return {}; },
            csi: function() { return {}; }
        };
    '''
})

wait = WebDriverWait(driver, 20)
results = []

# -----------------------
# EMAIL SCRAPER
# -----------------------
def get_email_from_website(url):
    """Try to extract email address from business website."""
    try:
        if not url:
            return ""
        if not url.startswith("http"):
            url = "http://" + url

        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resp.text)
        if emails:
            # Filter common spam/placeholder emails
            for email in emails:
                if not any(x in email.lower() for x in ["example", "test", "noreply", "info@domain.com"]):
                    return email
    except Exception as e:
        print(f"⚠ Email scrape error: {e}")
    return ""

# -----------------------
# SCRAPER LOGIC
# -----------------------
try:
    for city in CITIES:
        query = f"{KEYWORD} in {city}"
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}/"
        driver.get(url)
        print(f"\n🌐 Searching: {query}")

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]')))
        time.sleep(2)

        # Scroll to load more results
        scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)

        for _ in range(SCROLL_TIMES):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(1.5)
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            if new_height == last_height:
                break
            last_height = new_height

        # Collect business links
        cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
        cards = list({card.get_attribute("href"): card for card in cards}.values())  # unique
        cards = cards[:MAX_LISTINGS_PER_CITY]
        print(f"🔍 Found {len(cards)} listings in {city}.")

        for idx, card in enumerate(cards, start=1):
            try:
                href = card.get_attribute("href")
                driver.execute_script("window.open(arguments[0]);", href)
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(3)

                try:
                    name = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.DUwDvf'))).text.strip()
                except: name = ""

                try:
                    phone = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Phone"]').text.strip()
                except: phone = ""

                try:
                    address = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Address"]').text.strip()
                except: address = ""

                try:
                    website = driver.find_element(By.CSS_SELECTOR, 'a[data-tooltip="Open website"]').get_attribute("href")
                except: website = ""

                try:
                    rating = driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="star rating"]').text.strip()
                except: rating = ""

                try:
                    reviews = driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="reviews"]').text.strip()
                except: reviews = ""

                email = get_email_from_website(website)

                if email:  # Skip if no email found
                    results.append({
                        "City": city,
                        "Name": name,
                        "Phone": phone,
                        "Address": address,
                        "Website": website,
                        "Email": email,
                        "Rating": rating,
                        "Reviews": reviews,
                        "Category": KEYWORD
                    })
                    print(f"✅ {name} | {email}")
                else:
                    print(f"⛔ Skipped (No Email): {name}")

                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except Exception as e:
                print(f"❌ Error: {e}")
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(os.path.expanduser("~"), "Desktop", f"Leads_{timestamp}.xlsx")
    pd.DataFrame(results).to_excel(save_path, index=False)
    print(f"\n📁 Saved: {save_path}")

finally:
    driver.quit()
