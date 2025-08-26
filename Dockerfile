# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (for Selenium + lxml + pandas + Chromium)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    unzip \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    chromium \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for Chromium path
ENV CHROME_BIN=/usr/bin/chromium

# Copy dependency files first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port Streamlit runs on
EXPOSE 8501

# Disable Streamlit email capture
ENV STREAMLIT_DISABLE_EMAIL_CAPTURE=true

# Streamlit entrypoint
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
