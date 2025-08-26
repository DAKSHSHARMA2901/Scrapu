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


# Setup Selenium driver for Render
def setup_driver():
    # Auto-install ChromeDriver if not present
    chromedriver_autoinstaller.install()
    
    options = Options()
    
    # Render-specific options
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--window-size=1920,1080")
    
    # Set Chrome binary location for Render
    options.binary_location = "/usr/bin/chromium-browser"
    
    # Anti-detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Performance optimizations
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    driver = webdriver.Chrome(options=options)
    
    # Stealth mode
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}, loadTimes: function() { return {}; }, csi: function() { return {}; }};
            """
        },
    )
    
    # Set timeouts
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    
    return driver


# Extract emails from a website with better error handling
def extract_emails_from_website(driver, website_url, logger):
    if not website_url or website_url == "N/A":
        return "N/A"
    
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    found_emails = set()

    try:
        logger(f"🌐 Visiting website: {website_url}")
        driver.get(website_url)
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        text_content = soup.get_text()
        found_emails.update(email_pattern.findall(text_content))

        # Try common contact pages
        contact_pages = ["contact", "about", "contact-us", "about-us", "support", "contact.html", "about.html"]
        
        for page in contact_pages:
            try:
                contact_url = urljoin(website_url, page)
                logger(f"🔍 Checking contact page: {contact_url}")
                
                driver.get(contact_url)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                found_emails.update(email_pattern.findall(soup.get_text()))
                
            except Exception as e:
                continue

        return list(found_emails)[0] if found_emails else "N/A"
        
    except Exception as e:
        logger(f"❌ Failed to extract emails from website: {e}")
        return "N/A"


# Main scraping function with improved error handling
def scrape_google_maps(query, num_pages=1, logger=print):
    driver = None
    scraped_data = []
    seen_businesses = set()
    
    try:
        driver = setup_driver()
        logger("🚀 Chrome driver initialized successfully")
        
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        logger(f"🔎 Opening: {search_url}")
        
        try:
            driver.get(search_url)
            time.sleep(5)
            logger("✅ Google Maps loaded successfully")
        except Exception as e:
            logger(f"❌ Failed to load Google Maps: {e}")
            return scraped_data

        for page in range(num_pages):
            logger(f"📄 Scraping page {page + 1}/{num_pages}...")
            
            try:
                # Wait for results feed
                scrollable_div = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                )
                logger("✅ Results feed found")
            except Exception as e:
                logger(f"❌ Could not find results feed: {e}")
                break

            # Scroll to load more results
            for i in range(3):
                try:
                    driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", 
                        scrollable_div
                    )
                    logger(f"⬇️ Scrolled {i + 1}/3 times")
                    time.sleep(random.uniform(1, 2))
                except Exception as e:
                    logger(f"⚠️ Scroll failed: {e}")
                    break

            # Find business cards
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                cards = list({card.get_attribute("href"): card for card in cards}.values())
                logger(f"📊 Found {len(cards)} business cards")
            except Exception as e:
                logger(f"❌ Failed to find business cards: {e}")
                break

            for i, card in enumerate(cards):
                try:
                    href = card.get_attribute("href")
                    if not href:
                        continue
                        
                    logger(f"🏢 Processing business {i + 1}/{len(cards)}")
                    
                    # Open business page in new tab
                    driver.execute_script("window.open(arguments[0]);", href)
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(3)

                    # Extract business information
                    business_data = {}
                    
                    try:
                        name_elem = driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf')
                        business_data["Name"] = name_elem.text.strip() if name_elem else "N/A"
                    except:
                        business_data["Name"] = "N/A"

                    try:
                        address_elem = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Address"]')
                        business_data["Address"] = address_elem.text.strip() if address_elem else "N/A"
                    except:
                        business_data["Address"] = "N/A"

                    # Skip duplicates
                    if (business_data["Name"], business_data["Address"]) in seen_businesses:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue
                        
                    seen_businesses.add((business_data["Name"], business_data["Address"]))

                    try:
                        phone_elem = driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Phone"]')
                        business_data["Phone"] = phone_elem.text.strip() if phone_elem else "N/A"
                    except:
                        business_data["Phone"] = "N/A"

                    try:
                        website_elem = driver.find_element(By.CSS_SELECTOR, 'a[data-tooltip*="website"]')
                        business_data["Website"] = website_elem.get_attribute("href") if website_elem else "N/A"
                    except:
                        business_data["Website"] = "N/A"

                    try:
                        rating_elem = driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="stars"]')
                        business_data["Rating"] = rating_elem.get_attribute("aria-label") if rating_elem else "N/A"
                    except:
                        business_data["Rating"] = "N/A"

                    # Extract email
                    try:
                        mailto_elem = driver.find_element(By.CSS_SELECTOR, 'a[href^="mailto:"]')
                        business_data["Email"] = mailto_elem.get_attribute("href").replace("mailto:", "") if mailto_elem else "N/A"
                    except:
                        business_data["Email"] = "N/A"

                    # If no direct email, try to extract from website
                    if business_data["Email"] == "N/A" and business_data["Website"] != "N/A":
                        business_data["Email"] = extract_emails_from_website(driver, business_data["Website"], logger)

                    # Only add if we found an email
                    if business_data["Email"] != "N/A":
                        scraped_data.append(business_data)
                        logger(f"✅ Added: {business_data['Name']}")

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    time.sleep(1)

                except Exception as e:
                    logger(f"⚠️ Error processing business card: {e}")
                    try:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except:
                        pass
                    continue

        logger("🎉 Scraping completed successfully")

    except Exception as e:
        logger(f"❌ Scraping failed with error: {e}")
        logger(traceback.format_exc())
        
    finally:
        if driver:
            try:
                driver.quit()
                logger("🔚 Driver closed")
            except:
                pass
    
    return scraped_data
