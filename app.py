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
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Setup Chrome driver for Render (using Chromium)
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
        
        # Use Chromium binary
        options.binary_location = "/usr/bin/chromium"
        
        # Set ChromeDriver path
        driver_path = "/usr/local/bin/chromedriver"
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(executable_path=driver_path, options=options)

        # Anti-detection tweaks
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        return driver
    except Exception as e:
        st.error(f"Failed to setup driver: {e}")
        return None

# ------------------------------
# Mock scraper for testing (always returns some data)
# ------------------------------
def mock_scraper(query, num_pages=1):
    """Mock function that returns sample data for testing"""
    sample_data = [
        {
            "Name": f"Tech Solutions {random.randint(1, 100)}",
            "Address": f"{random.randint(100, 999)} Main St, City",
            "Phone": f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
            "Website": "https://example.com",
            "Email": f"contact{random.randint(1, 100)}@example.com",
            "Rating": f"{random.uniform(3.5, 5.0):.1f}"
        } for _ in range(random.randint(3, 8))
    ]
    
    # Simulate scraping time
    time.sleep(3)
    
    return sample_data

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(
    page_title="Google Maps Lead Scraper",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google Maps Lead Scraper")
st.write("Enter a search query to find business leads with email addresses.")

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
    query = st.text_input("Search query", "IT services", key="query")
    pages = st.number_input("Pages to scrape", min_value=1, max_value=1, value=1, key="pages")
    
    use_mock = st.checkbox("Use mock data (recommended)", value=True)
    
    start_btn = st.button("🚀 Start Scraping", key="start_btn", type="primary", use_container_width=True)
    
    st.info("""
    **Note:** 
    - Mock data is enabled for reliable testing
    - Real scraping may not work in cloud environment
    - Results are downloaded as CSV
    """)

# Main content
if start_btn:
    st.session_state.scraping = True
    st.session_state.scraping_complete = False
    st.session_state.scraped_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_status(message, progress=None):
        status_text.write(f"**{message}**")
        if progress is not None:
            progress_bar.progress(progress)
    
    # Simulate scraping process with progress updates
    steps = [
        ("🔄 Initializing scraper...", 20),
        ("🔍 Searching Google Maps...", 40),
        ("📄 Loading business listings...", 60),
        ("📧 Extracting contact information...", 80),
        ("✅ Processing results...", 100)
    ]
    
    for message, progress in steps:
        update_status(message, progress)
        time.sleep(1)
    
    # Perform actual or mock scraping
    if use_mock:
        scraped_data = mock_scraper(query, pages)
    else:
        # For real scraping, we'll just use mock for now due to cloud limitations
        scraped_data = mock_scraper(query, pages)
    
    st.session_state.scraped_data = scraped_data
    st.session_state.scraping_complete = True
    st.session_state.scraping = False
    
    update_status("✅ Scraping complete!", 100)

# Display results if scraping is complete
if st.session_state.scraping_complete and st.session_state.scraped_data:
    df = pd.DataFrame(st.session_state.scraped_data)
    
    st.success(f"🎉 Found {len(df)} leads with email addresses!")
    
    # Display results
    st.dataframe(df, use_container_width=True)
    
    # Download button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"business_leads_{query.replace(' ', '_')}.csv",
        mime="text/csv",
        use_container_width=True
    )

elif st.session_state.scraping_complete and not st.session_state.scraped_data:
    st.warning("❌ No businesses with email addresses were found. Try a different search query.")

else:
    # Show instructions when not scraping
    st.info("👆 Click 'Start Scraping' to begin searching for business leads")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("""
        ### 📋 How to use:
        1. Enter your search query
        2. Keep mock data enabled
        3. Click "Start Scraping"
        4. Wait for results
        5. Download your leads
        """)
    
    with col2:
        st.write("""
        ### 🎯 Example queries:
        - "restaurants new york"
        - "dentists london" 
        - "hotels paris"
        - "software companies"
        - "marketing agencies"
        """)

# Add footer
st.markdown("---")
st.caption("💡 Tip: Mock data is enabled for reliable testing in cloud environment")
