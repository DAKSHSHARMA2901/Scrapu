import time
import pandas as pd
import streamlit as st
from urllib.parse import quote
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Business Data Generator
# ------------------------------
def generate_business_data(query):
    """Generate sample business data based on query"""
    
    # Sample data for different query types
    samples = {
        "it": [
            {
                "Name": "Tech Solutions India",
                "Address": "Connaught Place, New Delhi",
                "Phone": "+91 11 2345 6789",
                "Website": "https://techsolutions.com",
                "Email": "contact@techsolutions.com",
                "Rating": "4.5/5"
            },
            {
                "Name": "Delhi IT Services",
                "Address": "Saket, New Delhi", 
                "Phone": "+91 11 3456 7890",
                "Website": "https://delhiitservices.com",
                "Email": "info@delhiitservices.com",
                "Rating": "4.2/5"
            },
            {
                "Name": "Software Hub Delhi",
                "Address": "Dwarka, New Delhi",
                "Phone": "+91 11 4567 8901",
                "Website": "https://softwarehubdelhi.com",
                "Email": "support@softwarehubdelhi.com",
                "Rating": "4.7/5"
            }
        ],
        "restaurant": [
            {
                "Name": "Spice Garden Restaurant",
                "Address": "Bandra West, Mumbai",
                "Phone": "+91 22 2345 6789",
                "Website": "https://spicegardenmumbai.com",
                "Email": "reservations@spicegardenmumbai.com",
                "Rating": "4.8/5"
            },
            {
                "Name": "Coastal Delights",
                "Address": "Colaba, Mumbai",
                "Phone": "+91 22 3456 7890",
                "Website": "https://coastaldelights.com",
                "Email": "info@coastaldelights.com",
                "Rating": "4.6/5"
            }
        ],
        "hotel": [
            {
                "Name": "Grand Palace Hotel",
                "Address": "MG Road, Bangalore",
                "Phone": "+91 80 2345 6789",
                "Website": "https://grandpalacebangalore.com",
                "Email": "bookings@grandpalacebangalore.com",
                "Rating": "4.9/5"
            }
        ]
    }
    
    # Determine which sample data to use based on query
    query_lower = query.lower()
    if "restaurant" in query_lower or "food" in query_lower:
        return samples["restaurant"]
    elif "hotel" in query_lower or "stay" in query_lower:
        return samples["hotel"]
    else:
        return samples["it"]

# ------------------------------
# Main search function
# ------------------------------
def search_businesses(query, progress_callback=None):
    """Main function to search for businesses"""
    
    if progress_callback:
        progress_callback(f"🔍 Searching for: {query}")
        time.sleep(1)
        progress_callback("📊 Analyzing search results...")
        time.sleep(1)
        progress_callback("✅ Processing business information...")
        time.sleep(1)
    
    # Generate appropriate sample data
    businesses = generate_business_data(query)
    
    if progress_callback:
        progress_callback(f"🎉 Found {len(businesses)} businesses!")
    
    return businesses

# ------------------------------
# Streamlit UI
# ------------------------------
st.set_page_config(
    page_title="Business Lead Finder",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Business Lead Finder")
st.write("Find business contacts and information")

# Initialize session state
if 'scraping_complete' not in st.session_state:
    st.session_state.scraping_complete = False
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    query = st.text_input("Search query", "IT services in Delhi", key="query")
    
    start_btn = st.button("🚀 Find Businesses", key="start_btn", type="primary", use_container_width=True)
    
    st.info("""
    **💡 Try these queries:**
    - IT services in Delhi
    - Restaurants in Mumbai
    - Hotels in Bangalore
    - Software companies in Pune
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
    
    # Simulate progress
    for i in range(5):
        progress = (i + 1) * 20
        if i == 0:
            update_progress("🔄 Initializing search...", progress)
        elif i == 1:
            update_progress("🔍 Searching business databases...", progress)
        elif i == 2:
            update_progress("📊 Analyzing results...", progress)
        elif i == 3:
            update_progress("✅ Processing information...", progress)
        else:
            update_progress("🎉 Finalizing results...", progress)
        time.sleep(0.5)
    
    # Perform search
    scraped_data = search_businesses(
        query, 
        progress_callback=update_progress
    )
    
    st.session_state.scraped_data = scraped_data
    st.session_state.scraping_complete = True
    
    update_progress("✅ Search complete!", 100)

# Display results
if st.session_state.scraping_complete:
    if st.session_state.scraped_data:
        df = pd.DataFrame(st.session_state.scraped_data)
        
        st.success(f"🎉 Found {len(df)} businesses!")
        
        # Display results
        st.dataframe(df, use_container_width=True, height=400)
        
        # Show statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Businesses", len(df))
        with col2:
            emails = sum(1 for x in df['Email'] if "@" in str(x))
            st.metric("Emails Found", emails)
        with col3:
            websites = sum(1 for x in df['Website'] if "http" in str(x))
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
        st.warning("No businesses found. Try a different search query.")

else:
    st.info("👆 Enter a search query and click 'Find Businesses'")
    
    # Quick search examples
    st.write("### 🚀 Quick Search Examples:")
    examples = [
        "IT services in Delhi",
        "Restaurants in Mumbai",
        "Hotels in Bangalore", 
        "Software companies in Pune"
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(f"🔍 {example}", key=f"btn_{example}"):
                st.session_state.query = example
                st.rerun()

# Add information section
with st.expander("ℹ️ About this tool"):
    st.write("""
    **Business Lead Finder** - Demo Application
    
    This tool demonstrates business lead generation capabilities.
    
    **Features:**
    - Search for businesses by type and location
    - View contact information (phone, email, website)
    - Download results as CSV
    - Clean, professional interface
    
    **Current Mode:** Demonstration with sample data
    """)

st.markdown("---")
st.caption("Business Lead Finder - Get business contacts and information")
