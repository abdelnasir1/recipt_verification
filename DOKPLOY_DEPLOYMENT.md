# Receipt Verification Service - Dokploy Deployment Guide

## Overview

This is a FastAPI-based receipt verification service designed to run as a containerized microservice in Dokploy. It verifies receipt images by:
- Using OCR (PaddleOCR) to extract text
- Comparing images with a reference receipt (SSIM)
- Validating account number, amount, and transaction date
- Returning success/failure status

## Prerequisites

1. **Dokploy instance** running (self-hosted or cloud)
2. **Supabase project** with:
   - Database with `payments` table
   - Storage bucket for receipt images
   - Service Role Key

## Quick Setup for Dokploy

### 1. Environment Variables

Set these in Dokploy's environment configuration:

```env
# Supabase Configuration (from your Dokploy Supabase instance)
SUPABASE_URL=https://your-dokploy-supabase-url.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Storage & Database
STORAGE_BUCKET=receipts
DATABASE_TABLE=payments

# OCR Settings
OCR_LANGUAGE=en              # "en" for English, "ar" for Arabic
USE_GPU=false                # Set to true only with GPU support

# Verification Thresholds
SSIM_THRESHOLD=0.65          # Image similarity threshold
FUZZY_MATCH_THRESHOLD=85     # Text matching threshold

# Server
PORT=8000
HOST=0.0.0.0
WORKERS=1
DEBUG=false

# Database Updates
UPDATE_DATABASE=true
```

### 2. Database Schema

Create the `payments` table with these columns:

```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  image_path TEXT,
  account_number TEXT NOT NULL,
  amount FLOAT NOT NULL,
  status TEXT,                    -- "success" or "failed"
  reason TEXT,                    -- Failure reason if status=failed
  verified_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. Storage Setup

Create a storage bucket in Supabase:
1. Navigate to **Storage** → **New bucket**
2. Name it `receipts`
3. Make it **private**
4. Upload your `reference_receipt.jpg` file

### 4. API Endpoints

#### Health Check
```bash
GET /health
```
Response:
```json
{
  "status": "ok",
  "service": "receipt-verifier",
  "version": "0.1.0"
}
```

#### Verify with Base64 Image (Recommended for Dokploy)
```bash
POST /verify/image
Content-Type: application/json

{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
  "account_number": "123456789",
  "amount": 500.00,
  "payment_id": "550e8400-e29b-41d4-a716-446655440000"  # optional
}
```

Response:
```json
{
  "status": "success",
  "verified": true,
  "reason": "",
  "amount": 500.00,
  "account": "123456789",
  "timestamp": "2026-08-18T10:30:00.123456",
  "payment_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Verify with Image from Storage
```bash
POST /verify/storage
Content-Type: application/json

{
  "image_path": "receipts/payment-123.jpg",
  "account_number": "123456789",
  "amount": 500.00,
  "payment_id": "550e8400-e29b-41d4-a716-446655440000"  # optional
}
```

## Dokploy Networking Setup

### Service-to-Service Communication

If both services are in the same Dokploy deployment:

```
1. Receipt Verifier Container → Supabase Container
   - Internal network communication
   - Use: http://supabase:5432 (for direct DB)
   - Or: https://supabase-service:3000 (for REST API)
```

### DNS Setup in Dokploy

Dokploy automatically creates DNS names:
- `service-name.internal` - Internal only
- `service-name.dokploy.app` - Public (if exposed)

**Example for this project:**
- Internal: `receipt-verifier.internal:8000`
- Public: `receipt-verifier.yourdomain.com` (if port exposed)

### Network Architecture

```
┌─────────────────────────────────────┐
│       Dokploy Environment           │
│                                     │
│  ┌──────────────────┐               │
│  │ Receipt Verifier │───────┐       │
│  │   (Port 8000)    │       │       │
│  └──────────────────┘       │       │
│                              │       │
│  ┌──────────────────┐       │       │
│  │   Supabase       │◄──────┘       │
│  │   Container      │               │
│  │ (Port 5432)      │               │
│  └──────────────────┘               │
│                                     │
└─────────────────────────────────────┘
```

## How to Integrate with Your App

### From Your Frontend/Backend

1. **Upload receipt to Supabase Storage:**
```javascript
const { data, error } = await supabase.storage
  .from('receipts')
  .upload(`payment-${paymentId}.jpg`, file);
```

2. **Call verification endpoint:**
```javascript
const response = await fetch('https://receipt-verifier.yourdomain.com/verify/storage', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image_path: `payment-${paymentId}.jpg`,
    account_number: '123456789',
    amount: 500.00,
    payment_id: paymentId
  })
});

const result = await response.json();
console.log(result.status);  // "success" or "failed"
```

**OR send base64 directly:**
```javascript
const reader = new FileReader();
reader.onload = async (e) => {
  const base64 = e.target.result.split(',')[1];
  const response = await fetch('https://receipt-verifier.yourdomain.com/verify/image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_base64: base64,
      account_number: '123456789',
      amount: 500.00,
      payment_id: paymentId
    })
  });
};
reader.readAsDataURL(file);
```

## Monitoring & Logging

Check container logs in Dokploy:
```bash
# In Dokploy dashboard → Services → receipt-verifier → Logs
```

Log lines show:
- `Verifying receipt for account XXX, amount XXX`
- `Verification complete: success/failed - reason`
- Any errors during processing

## Troubleshooting

### "Configuration error: SUPABASE_URL is required"
- ✅ Set `SUPABASE_URL` in Dokploy environment variables
- ✅ Make sure it's not empty or has trailing spaces

### "Failed to download image from storage"
- ✅ Verify Supabase Storage bucket exists and is named `receipts`
- ✅ Check image path is correct
- ✅ Ensure Service Role Key has storage permissions

### "OCR failed – no text found"
- ✅ Image quality too low
- ✅ Reference receipt format doesn't match
- ✅ OCR language setting doesn't match receipt

### Slow verification
- ✅ First request loads PaddleOCR model (~200MB) - normal
- ✅ Consider using smaller reference image
- ✅ Enable GPU if available: `USE_GPU=true`

## Performance Tips for Dokploy

1. **Container Resources:**
   - CPU: Minimum 1 core (2+ recommended)
   - Memory: Minimum 2GB (4GB recommended for OCR)
   - Disk: 5GB for PaddleOCR models

2. **Workers:**
   - Default: 1 worker
   - For parallel requests: increase `WORKERS` based on CPU cores

3. **Caching:**
   - Models are cached in container
   - Use volume mount for persistence across restarts

## Production Checklist

- [ ] `.env` file with all variables configured
- [ ] `reference_receipt.jpg` uploaded to container
- [ ] Database schema created with migrations
- [ ] Storage bucket created in Supabase
- [ ] Dokploy networking configured
- [ ] Environment variables set in Dokploy
- [ ] Logs configured for monitoring
- [ ] Backup strategy for database

## Local Testing with Docker Compose

```bash
# Copy environment template
cp .env.example .env

# Build image
docker-compose build

# Start services
docker-compose up

# Test endpoint
curl -X POST http://localhost:8000/verify/image \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "...",
    "account_number": "123456789",
    "amount": 500.00
  }'
```

## Support & Documentation

- Dokploy: https://dokploy.com
- FastAPI: https://fastapi.tiangolo.com
- Supabase: https://supabase.com/docs
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
