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
import threading
from flask import Flask, Response
import time

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route('/health')
def health():
    return 'OK', 200

def run_flask_app():
    flask_app.run(host='0.0.0.0', port=8080)

# Start Flask in a separate thread for health checks
flask_thread = threading.Thread(target=run_flask_app, daemon=True)
flask_thread.start()

# ------------------------------
# Setup Selenium Chrome driver for Render
# ------------------------------
def setup_driver():
    # Install correct ChromeDriver version automatically
    chromedriver_autoinstaller.install()

    options = Options()
    options.add_argument("--headless=new")  # required for Render
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

    # Set Chrome binary for Render
    options.binary_location = "/usr/bin/chromium-browser"

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
def scrape_google_maps(query, num_pages=1, progress_callback=None):
    driver = setup_driver()
    scraped_data = []
    seen_businesses = set()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        if progress_callback:
            progress_callback(f"🔎 Searching: {query}")
        
        driver.get(search_url)
        time.sleep(5)

        for page in range(num_pages):
            if progress_callback:
                progress_callback(f"📄 Page {page + 1}/{num_pages}")
            
            scrollable_div = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
            
            for i in range(3):
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
                )
                if progress_callback:
                    progress_callback(f"⬇️ Scrolling page {page + 1} ({i + 1}/3)")
                time.sleep(random.uniform(1, 2))

            cards = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
            cards = list({card.get_attribute("href"): card for card in cards}.values())
            
            if progress_callback:
                progress_callback(f"📊 Found {len(cards)} businesses on page {page + 1}")

            for i, card in enumerate(cards):
                try:
                    href = card.get_attribute("href")
                    driver.execute_script("window.open(arguments[0]);", href)
                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(3)

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

                    if email != "N/A":
                        scraped_data.append({
                            "Name": name,
                            "Address": address,
                            "Phone": phone,
                            "Website": website,
                            "Email": email,
                            "Rating": rating,
                        })
                        if progress_callback:
                            progress_callback(f"✅ Found email for: {name}")

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    time.sleep(1)

                except Exception as e:
                    try:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except:
                        pass
                    continue

        driver.quit()
        return scraped_data

    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        if progress_callback:
            progress_callback(f"❌ Error: {str(e)}")
        return scraped_data


# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(
    page_title="Google Maps Lead Scraper",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google Maps Lead Scraper")
st.write("Enter a search query and number of pages to scrape. Only results with emails are collected.")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    query = st.text_input("Search query", "IT services in Delhi", key="query")
    pages = st.number_input("Pages to scrape", min_value=1, max_value=3, value=1, key="pages")
    start_btn = st.button("🚀 Start Scraping", key="start_btn", type="primary")
    
    st.info("""
    **Note:** 
    - Scraping may take 2-5 minutes per page
    - Only businesses with emails are collected
    - Results are downloaded as CSV
    """)

# Main content
if start_btn:
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_placeholder = st.empty()
    
    def update_progress(message, progress=None):
        status_text.text(message)
        if progress is not None:
            progress_bar.progress(progress)
    
    update_progress("🔄 Initializing scraper...", 10)
    
    # Use session state to store scraped data
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = []
    if 'scraping_error' not in st.session_state:
        st.session_state.scraping_error = None
    
    # Run scraping directly (simpler approach without threading issues)
    try:
        scraped_data = scrape_google_maps(
            query, 
            pages, 
            progress_callback=update_progress
        )
        st.session_state.scraped_data = scraped_data
        st.session_state.scraping_error = None
        
    except Exception as e:
        st.session_state.scraping_error = str(e)
        st.session_state.scraped_data = []
    
    # Display results
    if st.session_state.scraping_error:
        update_progress(f"❌ Error: {st.session_state.scraping_error}", 100)
        st.error(f"Scraping failed: {st.session_state.scraping_error}")
        
    elif st.session_state.scraped_data:
        update_progress(f"✅ Scraping complete! Found {len(st.session_state.scraped_data)} leads with emails.", 100)
        
        df = pd.DataFrame(st.session_state.scraped_data)
        st.success(f"🎉 Successfully scraped {len(df)} leads!")
        
        # Display results
        st.dataframe(df, use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"leads_{query.replace(' ', '_')}.csv",
            mime="text/csv",
        )
    else:
        update_progress("❌ No results found with emails.", 100)
        st.warning("No businesses with email addresses were found. Try a different search query.")

else:
    st.info("👆 Click 'Start Scraping' to begin")
    st.write("""
    ### How it works:
    1. Enter your search query (e.g., "restaurants in new york")
    2. Select how many pages to scrape (1-3 recommended)
    3. Click "Start Scraping" and wait for results
    4. Download your leads as CSV
    
    ### Features:
    - Extracts business name, address, phone, website, email, and rating
    - Automatically visits websites to find email addresses
    - Filters out duplicates
    - Export results to CSV
    """)

# Add health status
st.sidebar.markdown("---")
st.sidebar.caption("🟢 System status: Online")
