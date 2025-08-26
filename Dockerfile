FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome using modern approach
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub > /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y \
    google-chrome-stable \
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

# Install ChromeDriver that matches Chrome version
RUN CHROME_VERSION=$(google-chrome --version | grep -oP 'Google Chrome \K\d+\.\d+\.\d+\.\d+') \
    && echo "Detected Chrome version: $CHROME_VERSION" \
    && MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) \
    && echo "Major version: $MAJOR_VERSION" \
    # Try to get the exact version from Chrome for Testing
    && wget -q --continue -O /tmp/chromedriver-linux64.zip \
       "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip" \
    # If exact version fails, try major version
    || wget -q --continue -O /tmp/chromedriver-linux64.zip \
       "https://storage.googleapis.com/chrome-for-testing-public/${MAJOR_VERSION}.0.0.0/linux64/chromedriver-linux64.zip" \
    # If that fails, use a known working version for Chrome 139
    || (echo "Using fallback version for Chrome 139" \
        && wget -q --continue -O /tmp/chromedriver-linux64.zip \
           "https://storage.googleapis.com/chrome-for-testing-public/139.0.7258.154/linux64/chromedriver-linux64.zip") \
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
