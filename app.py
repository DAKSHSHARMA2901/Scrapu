import re
import time
import pandas as pd
import streamlit as st
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Setup Chrome driver with WebDriver Manager
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
        
        # Use system Chrome
        options.binary_location = "/usr/bin/google-chrome-stable"
        
        # Anti-detection settings
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Set user agent
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Use WebDriver Manager to handle ChromeDriver automatically
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Stealth mode
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
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
# Simple Google Maps Scraper
# ------------------------------
def scrape_google_maps_simple(query, progress_callback=None):
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
        time.sleep(5)

        # Wait for results
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
        )
        
        if progress_callback:
            progress_callback("📊 Loading business listings...")
        
        # Scroll to load more results
        scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        for i in range(2):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(2)
            if progress_callback:
                progress_callback(f"⬇️ Scrolling ({i + 1}/2)")
        
        # Get business listings
        listings = driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')[:10]  # Limit to 10
        
        if progress_callback:
            progress_callback(f"✅ Found {len(listings)} businesses")
        
        for i, listing in enumerate(listings):
            try:
                listing.click()
                time.sleep(2)
                
                # Extract information
                business_data = {}
                
                # Name
                try:
                    name_elem = driver.find_element(By.CSS_SELECTOR, 'h1')
                    business_data["Name"] = name_elem.text.strip()
                except:
                    business_data["Name"] = "N/A"
                
                # Address
                try:
                    address_btn = driver.find_element(By.XPATH, '//button[contains(@aria-label, "ddress")]')
                    business_data["Address"] = address_btn.text.strip()
                except:
                    business_data["Address"] = "N/A"
                
                # Phone
                try:
                    phone_btn = driver.find_element(By.XPATH, '//button[contains(@aria-label, "hone")]')
                    business_data["Phone"] = phone_btn.text.strip()
                except:
                    business_data["Phone"] = "N/A"
                
                # Website
                try:
                    website_links = driver.find_elements(By.XPATH, '//a[contains(@href, "://")]')
                    for link in website_links:
                        href = link.get_attribute("href")
                        if "google" not in href and "maps" not in href:
                            business_data["Website"] = href
                            break
                    else:
                        business_data["Website"] = "N/A"
                except:
                    business_data["Website"] = "N/A"
                
                # Extract email from page source
                page_source = driver.page_source
                business_data["Email"] = extract_emails_from_text(page_source)
                
                # Only add if we have a valid name
                if business_data["Name"] != "N/A" and business_data["Name"].strip():
                    scraped_data.append(business_data)
                    if progress_callback:
                        progress_callback(f"📝 Added: {business_data['Name'][:20]}...")
                
            except Exception as e:
                continue
                
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Error during scraping")
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
st.write("Get real business leads with contact information")

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
    **Note:** 
    - First run may take 2-3 minutes
    - Results include real business data
    - Be patient during initialization
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
    scraped_data = scrape_google_maps_simple(
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
        st.warning("❌ No businesses found. Try a different search query.")

else:
    st.info("👆 Enter a search query and click 'Start Scraping'")

st.markdown("---")
st.caption("Google Maps Lead Scraper - Real Business Data")
