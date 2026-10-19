FROM python:3.10-slim

WORKDIR /app

# Invalidate build cache to force re-running apt-get and dependency installation
ARG CACHE_BUST=20261019

# Install all required system libraries for Chromium & Chrome CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    libxcb1 \
    libx11-6 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8080

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]