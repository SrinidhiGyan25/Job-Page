# Use an official Python base image
FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    curl unzip wget gnupg2 fonts-liberation libappindicator3-1 \
    libasound2 libatk-bridge2.0-0 libnspr4 libnss3 libxss1 libxtst6 \
    xdg-utils --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 5000

# Start the Flask app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
