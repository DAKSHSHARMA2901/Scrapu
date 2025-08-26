FROM python:3.11-slim

# Install Chrome and dependencies for Render
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium browser
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libgbm1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Detect Chromium version and install matching ChromeDriver
RUN CHROMIUM_VERSION=$(chromium --version | grep -oP 'Chromium \K\d+\.\d+\.\d+\.\d+') \
    && echo "Detected Chromium version: $CHROMIUM_VERSION" \
    && MAJOR_VERSION=$(echo $CHROMIUM_VERSION | cut -d. -f1) \
    && echo "Major version: $MAJOR_VERSION" \
    # Download the matching ChromeDriver version
    && wget -q --continue -O /tmp/chromedriver-linux64.zip \
       "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROMIUM_VERSION}/linux64/chromedriver-linux64.zip" \
    || wget -q --continue -O /tmp/chromedriver-linux64.zip \
       "https://storage.googleapis.com/chrome-for-testing-public/${CHROMIUM_VERSION}/linux64/chromedriver-linux64.zip" \
    || { echo "Failed to download ChromeDriver for version ${CHROMIUM_VERSION}"; exit 1; } \
    && unzip /tmp/chromedriver-linux64.zip -d /tmp/ \
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver-linux64.zip /tmp/chromedriver-linux64/ \
    && echo "ChromeDriver installed successfully"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["streamlit", "run", "app.py", "--server.port=10000", "--server.address=0.0.0.0"]
