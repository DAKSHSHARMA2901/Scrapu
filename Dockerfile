# -------------------------------
# Base Image with Python
# -------------------------------
FROM python:3.11-slim

# -------------------------------
# Install System Dependencies
# -------------------------------
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    curl \
    unzip \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Environment variables for Chromium
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# -------------------------------
# Set Work Directory
# -------------------------------
WORKDIR /app

# -------------------------------
# Install Python Dependencies
# -------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------
# Copy Application Code
# -------------------------------
COPY . .

# -------------------------------
# Expose Streamlit Port
# -------------------------------
EXPOSE 8501

# -------------------------------
# Start Streamlit App
# -------------------------------
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
