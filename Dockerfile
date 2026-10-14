# Use official lightweight Python 3.10 image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Install essential system dependencies including WeasyPrint requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Tell Python where to find the backend modules automatically
ENV PYTHONPATH=/app/backend

# Expose port 8080 for Railway production
EXPOSE 8080

# Run Uvicorn server pointing to backend app
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]