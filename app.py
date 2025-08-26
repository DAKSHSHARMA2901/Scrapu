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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Setup Chrome driver for Render
# ------------------------------
def setup_driver():
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Use Google Chrome
        options.binary_location = "/usr/bin/google-chrome-stable"
        
        # Anti-detection settings
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Set user agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # Stealth mode
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {},};
            """
        })
        
        return driver
        
    except Exception as e:
        st.error(f"Failed to setup driver: {e}")
        return None

# ------------------------------
# Email extractor from website
# ------------------------------
def extract_emails_from_website(driver, website_url):
    if not website_url or website_url == "N/A":
        return "N/A"
    
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    found_emails = set()

    try:
        driver.get(website_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        text_content = soup.get_text()
        found_emails.update(email_pattern.findall(text_content))

        # Try common contact pages
        for link in ["contact", "about", "contact-us", "about-us", "contact.html", "about.html"]:
            try:
                contact_url = urljoin(website_url, link)
                driver.get(contact_url)
                time.sleep(1)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                found_emails.update(email_pattern.findall(soup.get_text()))
            except:
                continue

        return list(found_emails)[0] if found_emails else "N/A"
        
    except Exception as e:
        return "N/A"

# ------------------------------
# Real Google Maps Scraper
# ------------------------------
def scrape_google_maps_real(query, num_pages=1, progress_callback=None):
    driver = setup_driver()
    if not driver:
        return []
    
    scraped_data = []
    seen_businesses = set()

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        if progress_callback:
            progress_callback(f"🔍 Searching: {query}")
        
        driver.get(search_url)
        time.sleep(5)

        for page in range(num_pages):
            if progress_callback:
                progress_callback(f"📄 Page {page + 1}/{num_pages}")
            
            try:
                # Wait for and scroll the results
                scrollable_div = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                )
                
                # Scroll to load more results
                for i in range(3):
                    driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div
                    )
                    if progress_callback:
                        progress_callback(f"⬇️ Scrolling ({i + 1}/3)")
                    time.sleep(random.uniform(1, 2))
                
                # Find business cards
                cards = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
                if progress_callback:
                    progress_callback(f"📊 Found {len(cards)} businesses")
                
                for i, card in enumerate(cards):
                    try:
                        # Click on the card to expand details
                        card.click()
                        time.sleep(2)
                        
                        # Extract business information
                        business_data = {}
                        
                        try:
                            name_elem = driver.find_element(By.CSS_SELECTOR, "h1")
                            business_data["Name"] = name_elem.text.strip()
                        except:
                            business_data["Name"] = "N/A"
                            
                        try:
                            address_elem = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]')
                            business_data["Address"] = address_elem.text.strip()
                        except:
                            business_data["Address"] = "N/A"
                        
                        # Skip duplicates
                        if (business_data["Name"], business_data["Address"]) in seen_businesses:
                            continue
                        seen_businesses.add((business_data["Name"], business_data["Address"]))
                        
                        try:
                            phone_elem = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"]')
                            business_data["Phone"] = phone_elem.text.strip()
                        except:
                            business_data["Phone"] = "N/A"
                            
                        try:
                            website_elem = driver.find_element(By.CSS_SELECTOR, 'a[href*="://"]')
                            business_data["Website"] = website_elem.get_attribute("href")
                        except:
                            business_data["Website"] = "N/A"
                            
                        try:
                            rating_elem = driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="star"]')
                            business_data["Rating"] = rating_elem.get_attribute("aria-label")
                        except:
                            business_data["Rating"] = "N/A"
                        
                        # Extract email
                        business_data["Email"] = "N/A"
                        if business_data["Website"] != "N/A":
                            business_data["Email"] = extract_emails_from_website(driver, business_data["Website"])
                        
                        # Only add if we have valid data
                        if business_data["Name"] != "N/A" and business_data["Email"] != "N/A":
                            scraped_data.append(business_data)
                            if progress_callback:
                                progress_callback(f"✅ Found: {business_data['Name']}")
                        
                    except Exception as e:
                        continue
                        
            except TimeoutException:
                if progress_callback:
                    progress_callback("⏰ Timeout waiting for results")
                break
            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠️ Error on page {page + 1}: {e}")
                continue
                
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Scraping failed: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
            
    return scraped_data

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(
    page_title="Google Maps Lead Scraper - REAL DATA",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google Maps Lead Scraper - REAL DATA")
st.write("Enter a search query to find real business leads with email addresses.")

# Initialize session state
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []
if 'scraping' not in st.session_state:
    st.session_state.scraping = False

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    query = st.text_input("Search query", "restaurants in mumbai", key="query")
    pages = st.number_input("Pages to scrape", min_value=1, max_value=3, value=1, key="pages")
    
    start_btn = st.button("🚀 Start Real Scraping", key="start_btn", type="primary", use_container_width=True)
    
    st.warning("""
    **Important:** 
    - Real scraping takes 2-5 minutes per page
    - Only businesses with emails are collected
    - Cloud scraping may be detected sometimes
    - Be patient during scraping
    """)

# Main content
if start_btn:
    st.session_state.scraping = True
    st.session_state.scraping_complete = False
    st.session_state.scraped_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_placeholder = st.empty()
    
    def update_progress(message, progress=None):
        status_text.write(f"**{message}**")
        if progress is not None:
            progress_bar.progress(progress)
    
    # Start real scraping
    scraped_data = scrape_google_maps_real(
        query, 
        pages, 
        progress_callback=update_progress
    )
    
    st.session_state.scraped_data = scraped_data
    st.session_state.scraping_complete = True
    st.session_state.scraping = False
    
    update_progress("✅ Scraping complete!", 100)

# Display results if scraping is complete
if st.session_state.scraping_complete:
    if st.session_state.scraped_data:
        df = pd.DataFrame(st.session_state.scraped_data)
        
        st.success(f"🎉 Successfully scraped {len(df)} real leads!")
        
        # Display results
        st.dataframe(df, use_container_width=True)
        
        # Show statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Leads", len(df))
        with col2:
            st.metric("With Email", f"{len(df)}/{len(df)}")
        with col3:
            st.metric("Success Rate", "100%")
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"real_leads_{query.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("❌ No businesses with email addresses were found. Try a different search query or location.")

else:
    # Show instructions when not scraping
    st.info("👆 Click 'Start Real Scraping' to begin searching for REAL business leads")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("""
        ### 📋 How to use:
        1. Enter your search query
        2. Select number of pages (1-3)
        3. Click "Start Real Scraping"
        4. Wait 2-5 minutes
        5. Download real leads
        """)
    
    with col2:
        st.write("""
        ### 🎯 Best search examples:
        - "restaurants mumbai"
        - "hotels in delhi"
        - "it companies bangalore"
        - "dentists near me"
        - "marketing agencies"
        - "cafe pune"
        """)

# Add footer
st.markdown("---")
st.caption("🔍 Scraping real data from Google Maps - This may take several minutes")
