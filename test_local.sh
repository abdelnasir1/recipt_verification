#!/bin/bash
# Test script for Receipt Verifier container

set -e

BASE_URL="http://localhost:8000"

echo "=== Receipt Verifier - Local Testing ==="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${YELLOW}[1] Testing Health Endpoint${NC}"
echo "GET $BASE_URL/health"
curl -s -X GET "$BASE_URL/health" | jq . || echo "Failed"
echo ""

# Test 2: Verify with Base64 Image (using a sample placeholder)
echo -e "${YELLOW}[2] Testing Verify with Base64 Image${NC}"
echo "POST $BASE_URL/verify/image"
echo "Note: Using placeholder base64. Replace with actual receipt image."
echo ""

# Create a minimal valid JPEG in base64 for testing
SAMPLE_BASE64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

curl -s -X POST "$BASE_URL/verify/image" \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"$SAMPLE_BASE64\",
    \"account_number\": \"123456789\",
    \"amount\": 500.00,
    \"payment_id\": \"test-payment-123\"
  }" | jq . || echo "Failed"
echo ""

# Test 3: Verify with Storage URL (if you have an image in Supabase)
echo -e "${YELLOW}[3] Testing Verify with Storage URL${NC}"
echo "POST $BASE_URL/verify/storage"
echo "Note: Requires actual image in Supabase storage 'receipts' bucket"
echo ""

curl -s -X POST "$BASE_URL/verify/storage" \
  -H "Content-Type: application/json" \
  -d "{
    \"image_path\": \"ea5c952e-a573-4d09-af07-b2e51b883d6f/1786882688847.jpg\",
    \"account_number\": \"123456789\",
    \"amount\": 500.00,
    \"payment_id\": \"test-payment-456\"
  }" | jq . || echo "Failed"
echo ""

echo -e "${GREEN}=== Tests Complete ===${NC}"
echo ""
echo "Container Status:"
docker ps --filter "name=receipt_verifier" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
