import re
import time
import random
import pandas as pd
import streamlit as st
from urllib.parse import quote
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
# Setup Chrome driver with better stealth
# ------------------------------
def setup_driver():
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Enhanced stealth options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        # Use system Chrome
        options.binary_location = "/usr/bin/google-chrome-stable"
        
        # Advanced anti-detection
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Set realistic user agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # Advanced stealth JavaScript
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            window.chrome = {
                runtime: {},
                app: {
                    isInstalled: false,
                    InstallState: {
                        DISABLED: 'disabled',
                        INSTALLED: 'installed',
                        NOT_INSTALLED: 'not_installed'
                    },
                    RunningState: {
                        CANNOT_RUN: 'cannot_run',
                        READY_TO_RUN: 'ready_to_run',
                        RUNNING: 'running'
                    }
                }
            };
            
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        return driver
        
    except Exception as e:
        st.error(f"Failed to setup driver: {e}")
        return None

# ------------------------------
# Email extractor
# ------------------------------
def extract_emails_from_text(text):
    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    emails = email_pattern.findall(text)
    return emails[0] if emails else "N/A"

# ------------------------------
# Improved Google Maps Scraper
# ------------------------------
def scrape_google_maps_improved(query, progress_callback=None):
    driver = setup_driver()
    if not driver:
        if progress_callback:
            progress_callback("❌ Failed to initialize browser")
        return []
    
    scraped_data = []

    try:
        search_url = f"https://www.google.com/maps/search/{quote(query)}"
        if progress_callback:
            progress_callback(f"🔍 Searching: {query}")
        
        driver.get(search_url)
        time.sleep(random.uniform(3, 5))  # Random delay

        # Wait for results with longer timeout
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="feed"], .section-result, .searchbox'))
            )
        except TimeoutException:
            if progress_callback:
                progress_callback("❌ Timeout waiting for Google Maps")
            return []
        
        if progress_callback:
            progress_callback("📊 Loading business listings...")
        
        # Try multiple selectors for business listings
        selectors = [
            '[role="article"]',
            '.section-result',
            '.bfdHYd',
            '.Nv2PK',
            '.THOPZb'
        ]
        
        listings = []
        for selector in selectors:
            try:
                listings = driver.find_elements(By.CSS_SELECTOR, selector)
                if listings:
                    if progress_callback:
                        progress_callback(f"✅ Found {len(listings)} businesses using {selector}")
                    break
            except:
                continue
        
        if not listings:
            if progress_callback:
                progress_callback("❌ No business listings found")
            return []
        
        # Limit to first 5 listings for stability
        for i, listing in enumerate(listings[:5]):
            try:
                # Scroll element into view before clicking
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", listing)
                time.sleep(random.uniform(1, 2))
                
                listing.click()
                time.sleep(random.uniform(2, 3))
                
                # Extract information with multiple fallback selectors
                business_data = {}
                
                # Name - multiple selectors
                name_selectors = ['h1', '.fontHeadlineLarge', '[aria-hidden="true"]', '.section-hero-header-title']
                for selector in name_selectors:
                    try:
                        name_elem = driver.find_element(By.CSS_SELECTOR, selector)
                        if name_elem.text.strip():
                            business_data["Name"] = name_elem.text.strip()
                            break
                    except:
                        continue
                else:
                    business_data["Name"] = "N/A"
                
                # Address - multiple selectors
                address_selectors = [
                    'button[data-item-id*="address"]',
                    '[aria-label*="ddress"]',
                    '.section-info-text',
                    '.rogA2c'
                ]
                for selector in address_selectors:
                    try:
                        address_elem = driver.find_element(By.CSS_SELECTOR, selector)
                        if address_elem.text.strip():
                            business_data["Address"] = address_elem.text.strip()
                            break
                    except:
                        continue
                else:
                    business_data["Address"] = "N/A"
                
                # Phone - multiple selectors
                phone_selectors = [
                    'button[data-item-id*="phone"]',
                    '[aria-label*="hone"]',
                    '[aria-label*="all"]'
                ]
                for selector in phone_selectors:
                    try:
                        phone_elem = driver.find_element(By.CSS_SELECTOR, selector)
                        if phone_elem.text.strip():
                            business_data["Phone"] = phone_elem.text.strip()
                            break
                    except:
                        continue
                else:
                    business_data["Phone"] = "N/A"
                
                # Website - multiple approaches
                business_data["Website"] = "N/A"
                try:
                    website_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="://"]')
                    for link in website_links:
                        href = link.get_attribute("href")
                        if href and "google" not in href and "maps" not in href and not href.startswith("javascript"):
                            business_data["Website"] = href
                            break
                except:
                    pass
                
                # Extract email from page source
                page_source = driver.page_source
                business_data["Email"] = extract_emails_from_text(page_source)
                
                # Only add if we have a valid name
                if business_data["Name"] != "N/A" and business_data["Name"].strip():
                    scraped_data.append(business_data)
                    if progress_callback:
                        progress_callback(f"📝 Added: {business_data['Name'][:25]}...")
                
                # Small delay between listings
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"⚠️ Skipping business {i+1}")
                continue
                
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Error: {str(e)}")
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
    page_title="Google Maps Lead Scraper",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google Maps Lead Scraper")
st.write("Get real business leads with contact information from Google Maps")

# Initialize session state
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    query = st.text_input("Search query", "restaurants in mumbai", key="query")
    
    start_btn = st.button("🚀 Start Scraping", key="start_btn", type="primary", use_container_width=True)
    
    st.info("""
    **Tips:** 
    - Use specific queries like "restaurants mumbai"
    - Include location for better results
    - First run may take 3-5 minutes
    """)

# Main content
if start_btn:
    st.session_state.scraping_complete = False
    st.session_state.scraped_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(message, progress=None):
        status_text.write(f"**{message}**")
        if progress is not None:
            progress_bar.progress(progress)
    
    # Start scraping
    scraped_data = scrape_google_maps_improved(
        query, 
        progress_callback=update_progress
    )
    
    st.session_state.scraped_data = scraped_data
    st.session_state.scraping_complete = True
    
    update_progress("✅ Scraping complete!", 100)

# Display results
if st.session_state.scraping_complete:
    if st.session_state.scraped_data:
        df = pd.DataFrame(st.session_state.scraped_data)
        
        st.success(f"🎉 Successfully scraped {len(df)} businesses!")
        
        # Display results
        st.dataframe(df, use_container_width=True, height=400)
        
        # Show statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Leads", len(df))
        with col2:
            emails = sum(1 for x in df['Email'] if x != "N/A")
            st.metric("Emails Found", emails)
        with col3:
            websites = sum(1 for x in df['Website'] if x != "N/A")
            st.metric("Websites", websites)
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"business_leads_{query.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.warning("""
        ❌ No businesses found. Try:
        - More specific queries: "restaurants mumbai" instead of "it"
        - Different locations: "cafe delhi", "hotels bangalore"
        - Wait a few minutes and try again
        """)

else:
    st.info("👆 Enter a search query and click 'Start Scraping'")
    
    # Example queries
    st.write("### 💡 Try these example queries:")
    examples = [
        "restaurants in mumbai",
        "hotels in delhi",
        "cafe in bangalore",
        "it companies in pune",
        "dentists in chennai"
    ]
    
    for example in examples:
        if st.button(f"🔍 {example}", key=example):
            st.session_state.query = example

st.markdown("---")
st.caption("Google Maps Lead Scraper - Real Business Data")
