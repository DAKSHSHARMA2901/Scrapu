import re
import time
import random
import traceback
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller

# Setup Selenium driver
def setup_driver():
    chromedriver_autoinstaller.install()
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option(
        "prefs",
        {
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.images": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        },
    )

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """
        },
    )
    return driver

# Extract emails from a website
def extract_emails_from_website(driver, website_url):
    if not website_url or website_url == "N/A":
        return "N/A"
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    found_emails = set()

    try:
        driver.get(website_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        found_emails.update(email_pattern.findall(soup.get_text()))

        for link in ["contact", "about", "support"]:
            try:
                driver.get(urljoin(website_url, link))
                time.sleep(1.5)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                found_emails.update(email_pattern.findall(soup.get_text()))
            except:
                pass

        return list(found_emails)[0] if found_emails else "N/A"
    except:
        return "N/A"

# Main scraping function
def scrape_google_maps(query, num_pages=1, logger=print):
    driver = setup_driver()
    scraped_data = []
    seen_businesses = set()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        logger(f"🔎 Opening: {search_url}")
        driver.get(search_url)
        time.sleep(15)

        for page in range(num_pages):
            logger(f"📄 Scraping page {page+1}...")
            scrollable_div = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )

            last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
            while True:
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
                time.sleep(random.uniform(1.5, 2.5))
                new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                if new_height == last_height:
                    break
                last_height = new_height

            cards = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a[href*="/maps/place/"]'))
            )
            cards = list({card.get_attribute("href"): card for card in cards}.values())

            for i, card in enumerate(cards):
                try:
                    href = card.get_attribute("href")
                    driver.execute_script("window.open(arguments[0]);", href)
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(2)

                    try:
                        name = driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf').text.strip()
                    except:
                        name = "N/A"

                    try:
                        address = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Address"]').text.strip()
                    except:
                        address = "N/A"

                    if (name, address) in seen_businesses:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue
                    seen_businesses.add((name, address))

                    try:
                        phone = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Phone"]').text.strip()
                    except:
                        phone = "N/A"

                    try:
                        website = driver.find_element(By.CSS_SELECTOR, 'a[data-tooltip="Open website"]').get_attribute("href")
                    except:
                        website = "N/A"

                    try:
                        rating = driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="star rating"]').text.strip()
                    except:
                        rating = "N/A"

                    try:
                        email = driver.find_element(By.CSS_SELECTOR, 'a[href^="mailto:"]').get_attribute("href").replace("mailto:", "")
                    except:
                        email = "N/A"
                    if email == "N/A" and website != "N/A":
                        email = extract_emails_from_website(driver, website)

                    scraped_data.append({
                        "Name": name,
                        "Address": address,
                        "Phone": phone,
                        "Website": website,
                        "Email": email,
                        "Rating": rating
                    })
                    if email == "N/A":
                        logger(f"Skipped {name}: No email found")

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                except Exception as e:
                    logger(f"⚠️ Error scraping business card {i+1}: {str(e)}")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

    except Exception as e:
        logger(f"❌ Scraping failed: {str(e)}")
        logger(traceback.format_exc())
    finally:
        driver.quit()

    return scraped_data
