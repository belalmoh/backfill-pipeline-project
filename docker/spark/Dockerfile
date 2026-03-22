FROM bitnamilegacy/spark:3.5.0-debian-12-r17

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    boto3==1.34.34 \
    great-expectations==0.18.21 \
    delta-spark==3.1.0 \
    pyarrow==15.0.0

# Download MinIO client
RUN wget -q https://dl.min.io/client/mc/release/linux-amd64/mc \
    && chmod +x mc \
    && mv mc /usr/local/bin/mc

# Run as root (no special user in this image)
# USER root
