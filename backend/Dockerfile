FROM python:3.10-slim

WORKDIR /app

# Install all required system libraries for Playwright & Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
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
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright along with all required system dependencies and browser binaries
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8080

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]