#!/bin/bash
# MinIO Bucket Setup Script
# Creates bronze, silver, gold buckets for data lake

set -euo pipefail

echo "🚀 Setting up MinIO buckets..."

# Configure MinIO client alias
echo "📝 Configuring MinIO client..."
docker-compose exec minio mc alias set myminio \
    http://minio:9000 minioadmin minioadmin123

# Create buckets
echo "🪣 Creating buckets..."
docker-compose exec minio mc mb myminio/clickstream-bronze
docker-compose exec minio mc mb myminio/clickstream-silver
docker-compose exec minio mc mb myminio/clickstream-gold

# Set bucket policies (optional - public read for demo)
echo "🔒 Setting bucket policies..."
docker-compose exec minio mc anonymous set public myminio/clickstream-bronze
docker-compose exec minio mc anonymous set public myminio/clickstream-silver
docker-compose exec minio mc anonymous set public myminio/clickstream-gold

# Verify buckets
echo "✅ Verifying buckets..."
docker-compose exec minio mc ls myminio

echo ""
echo "=========================================="
echo "✅ MinIO Setup Complete"
echo "=========================================="
echo "Buckets created:"
echo "  - clickstream-bronze (raw data)"
echo "  - clickstream-silver (cleaned data)"
echo "  - clickstream-gold (aggregated data)"
echo ""
echo "Access MinIO Console: http://localhost:9001"
echo "Credentials: minioadmin / minioadmin123"
echo "=========================================="
