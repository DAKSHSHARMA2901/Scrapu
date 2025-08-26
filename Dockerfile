FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies with debugging
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    gnupg \
    build-essential \
    libnss3 \
    libasound2 \
    libxss1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxdamage1 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libglib2.0-0 \
    libx11-6 \
    libxext6 \
    libsm6 \
    libxrender1 \
    libxshmfence1 \
    fonts-liberation \
    chromium \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    || { echo "apt-get install failed"; cat /var/log/apt/term.log; exit 1; }

# Install specific ChromeDriver version matching Chromium
RUN CHROMIUM_VERSION=$(chromium --version | grep -oP 'Chromium \K\d+' || echo "120") \
    && wget -q --continue -P /tmp "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROMIUM_VERSION}" \
    && CHROMEDRIVER_VERSION=$(cat /tmp/LATEST_RELEASE_${CHROMIUM_VERSION}) \
    && wget -q --continue -P /usr/bin "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver-linux64.zip" \
    && unzip /usr/bin/chromedriver-linux64.zip -d /usr/bin/ \
    && rm /usr/bin/chromedriver-linux64.zip /tmp/LATEST_RELEASE_${CHROMIUM_VERSION} \
    && chmod +x /usr/bin/chromedriver \
    || { echo "ChromeDriver download failed"; exit 1; }

# Env vars for Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

EXPOSE 8501
ENV STREAMLIT_DISABLE_EMAIL_CAPTURE=true

# Debug Chrome versions
CMD ["sh", "-c", "chromium --version && chromedriver --version && streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.maxUploadSize=100 --server.headless=true"]
