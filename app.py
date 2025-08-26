import re
import time
import random
import pandas as pd
import streamlit as st
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chromedriver_autoinstaller

# ------------------------------
# Setup Selenium Chrome driver
# ------------------------------
def setup_driver():
    chromedriver_autoinstaller.install()

    options = Options()
    options.add_argument("--headless=new")  # Required for Render
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option(
        "prefs",
        {
            "profile.default_content_setting_values.images": 2,
            "profile.managed_default_content_settings.images": 2,
        },
    )

    driver = webdriver.Chrome(options=options)

    # Anti-detection tweaks
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}, loadTimes: function() { return {}; }, csi: function() { return {}; }};
            """
        },
    )

    return driver

# ------------------------------
# Email extractor from website
# ------------------------------
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

# ------------------------------
# Google Maps Scraper
# ------------------------------
def scrape_google_maps(query, num_pages=1):
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting scraping for query: {query} over {num_pages} pages.")
    driver = setup_driver()
    scraped_data = []
    seen_businesses = set()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        driver.get(search_url)
        time.sleep(3)

        for page in range(num_pages):
            scrollable_div = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
            for _ in range(5):
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
                )
                time.sleep(random.uniform(1, 2))

            cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            cards = list({card.get_attribute("href"): card for card in cards}.values())

            for card in cards:
                try:
                    href = card.get_attribute("href")
                    driver.execute_script("window.open(arguments[0]);", href)
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(2)

                    try:
                        name = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text.strip()
                    except:
                        name = "N/A"

                    try:
                        address = driver.find_element(
                            By.CSS_SELECTOR, 'button[aria-label*="Address"]'
                        ).text.strip()
                    except:
                        address = "N/A"

                    if (name, address) in seen_businesses:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue
                    seen_businesses.add((name, address))

                    try:
                        phone = driver.find_element(
                            By.CSS_SELECTOR, 'button[aria-label*="Phone"]'
                        ).text.strip()
                    except:
                        phone = "N/A"

                    try:
                        website = driver.find_element(
                            By.CSS_SELECTOR, 'a[data-tooltip="Open website"]'
                        ).get_attribute("href")
                    except:
                        website = "N/A"

                    try:
                        rating = driver.find_element(
                            By.CSS_SELECTOR, 'span[aria-label*="star rating"]'
                        ).text.strip()
                    except:
                        rating = "N/A"

                    try:
                        email = driver.find_element(
                            By.CSS_SELECTOR, 'a[href^="mailto:"]'
                        ).get_attribute("href").replace("mailto:", "")
                    except:
                        email = "N/A"

                    if email == "N/A" and website != "N/A":
                        email = extract_emails_from_website(driver, website)

                    # Filter for both email and phone
                    if email != "N/A" and phone != "N/A":
                        scraped_data.append(
                            {
                                "Name": name,
                                "Address": address,
                                "Phone": phone,
                                "Website": website,
                                "Email": email,
                                "Rating": rating,
                            }
                        )
                        logger.info(f"✅ Found: {name} (Email: {email}, Phone: {phone})")

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                except Exception as e:
                    logger.error(f"⚠️ Error scraping card: {str(e)}")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

        driver.quit()
        logger.info(f"Scrape completed.")
        return scraped_data

    except Exception as e:
        logger.error(f"❌ Scraping failed: {str(e)}")
        driver.quit()
        return scraped_data

# ------------------------------
# Streamlit UI
# ------------------------------
st.title("Google Maps Lead Scraper Results")
st.write("Enter a search query and number of pages to scrape. Only results with both email and phone are collected.")

query = st.text_input("Search query", "IT services in Delhi")
pages = st.number_input("Pages to scrape", min_value=1, max_value=5, value=1)
start_btn = st.button("Start Scraping")

if start_btn:
    with st.spinner("Scraping in progress..."):
        data = scrape_google_maps(query, pages)

    if data:
        df = pd.DataFrame(data)
        st.success(f"Scraping complete! {len(df)} results found with email and phone.")
        st.table(df)  # Display as table

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="scraped_leads.csv",
            mime="text/csv",
        )
    else:
        st.warning("No results found with both email and phone.")
