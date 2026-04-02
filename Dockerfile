FROM python:3.11-slim

# System deps: ffmpeg for encoding, and build tools for cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source
COPY . .

# Working dirs are created at runtime by main.py via os.makedirs
# but we pre-create them so the container user owns them
RUN mkdir -p /tmp/mvxy/downloads /tmp/mvxy/encoded /tmp/mvxy/thumbs

CMD ["python", "main.py"]
