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
import logging
import subprocess

# Set up logging to display in Streamlit
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ------------------------------
# Setup Selenium Chrome driver
# ------------------------------
def setup_driver(timeout=60):
    chromedriver_autoinstaller.install()
    logger.info("Installing ChromeDriver...")

    # Get Chromium version
    try:
        chrom_version = subprocess.check_output(['chromium', '--version']).decode().strip()
        logger.info(f"Chromium version: {chrom_version}")
    except Exception as e:
        logger.error(f"Failed to get Chromium version: {str(e)}")
        chrom_version = "unknown"

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

    try:
        driver = webdriver.Chrome(options=options)
        logger.info("ChromeDriver initialized successfully.")
    except Exception as e:
        logger.error(f"ChromeDriver initialization failed: {str(e)}. Attempting manual setup...")
        # Manual ChromeDriver download (example for Chromium 120)
        import os
        chromedriver_path = "/usr/bin/chromedriver"
        if not os.path.exists(chromedriver_path):
            logger.error("Manual ChromeDriver setup not implemented. Please update Dockerfile.")
            raise
        driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)

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

    driver.set_page_load_timeout(timeout)
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
            except Exception as e:
                logger.error(f"Error navigating to {link}: {str(e)}")
                continue

        return list(found_emails)[0] if found_emails else "N/A"
    except Exception as e:
        logger.error(f"Error extracting emails from {website_url}: {str(e)}")
        return "N/A"

# ------------------------------
# Google Maps Scraper
# ------------------------------
def scrape_google_maps(query, num_pages=1):
    logger.info(f"Starting scraping for query: {query} over {num_pages} pages.")
    driver = setup_driver()
    scraped_data = []
    seen_businesses = set()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        logger.info(f"Navigating to: {search_url}")
        driver.get(search_url)
        time.sleep(3)

        for page in range(num_pages):
            try:
                scrollable_div = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                )
                logger.info(f"Found scrollable div on page {page + 1}")
                last_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                for _ in range(5):
                    driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
                    )
                    time.sleep(random.uniform(1, 2))
                    new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_div)
                    if new_height == last_height:
                        break
                    last_height = new_height
                logger.info(f"Finished scrolling on page {page + 1}")

                cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                cards = list({card.get_attribute("href"): card for card in cards}.values())
                logger.info(f"Found {len(cards)} cards on page {page + 1}")

                for i, card in enumerate(cards):
                    try:
                        href = card.get_attribute("href")
                        logger.info(f"Opening business link {i + 1}: {href}")
                        driver.execute_script("window.open(arguments[0]);", href)
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(2)

                        try:
                            name = driver.find_element(By.CSS_SELECTOR, "h1.DUwDvf").text.strip()
                        except Exception as e:
                            name = "N/A"
                            logger.error(f"Error getting name: {str(e)}")

                        try:
                            address = driver.find_element(
                                By.CSS_SELECTOR, 'button[aria-label*="Address"]'
                            ).text.strip()
                        except Exception as e:
                            address = "N/A"
                            logger.error(f"Error getting address: {str(e)}")

                        if (name, address) in seen_businesses:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue
                        seen_businesses.add((name, address))

                        try:
                            phone = driver.find_element(
                                By.CSS_SELECTOR, 'button[aria-label*="Phone"]'
                            ).text.strip()
                        except Exception as e:
                            phone = "N/A"
                            logger.error(f"Error getting phone: {str(e)}")

                        try:
                            website = driver.find_element(
                                By.CSS_SELECTOR, 'a[data-tooltip="Open website"]'
                            ).get_attribute("href")
                        except Exception as e:
                            website = "N/A"
                            logger.error(f"Error getting website: {str(e)}")

                        try:
                            rating = driver.find_element(
                                By.CSS_SELECTOR, 'span[aria-label*="star rating"]'
                            ).text.strip()
                        except Exception as e:
                            rating = "N/A"
                            logger.error(f"Error getting rating: {str(e)}")

                        try:
                            email = driver.find_element(
                                By.CSS_SELECTOR, 'a[href^="mailto:"]'
                            ).get_attribute("href").replace("mailto:", "")
                        except Exception as e:
                            email = "N/A"
                            logger.error(f"Error getting email: {str(e)}")

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
                        logger.error(f"⚠️ Error processing card {i + 1}: {str(e)}")
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue

            except Exception as e:
                logger.error(f"Error processing page {page + 1}: {str(e)}")
                continue

        driver.quit()
        logger.info(f"Scrape completed with {len(scraped_data)} results.")
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
        # Display logs in Streamlit for debugging
        st.write("### Debug Logs")
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                for record in handler.stream.getvalue().splitlines() if hasattr(handler.stream, 'getvalue') else []:
                    st.write(record)

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
