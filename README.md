# Receipt Verification Service

Receipt verification microservice built with FastAPI and PaddleOCR. Designed for Dokploy deployment to verify receipt images against database records.

## Features

- 🔍 **OCR Text Extraction** - Uses PaddleOCR for multilingual text recognition
- 🎯 **Image Comparison** - SSIM-based receipt verification
- 💰 **Transaction Validation** - Account number and amount verification
- 📅 **Date Checking** - Validates transaction date (within last 7 days)
- 🐳 **Docker Ready** - Optimized for Dokploy containerized deployment
- 🔐 **Supabase Integration** - Direct database and storage integration
- 📊 **REST API** - Simple HTTP endpoints for integration
- 🔄 **Auto Database Updates** - Automatic status recording in database

## Quick Start

### Prerequisites
- Docker & Docker Compose (for local testing)
- Dokploy instance with Supabase
- `reference_receipt.jpg` sample image

### Local Testing

1. **Clone and setup:**
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

2. **Run with Docker Compose:**
```bash
docker-compose up
```

3. **Test the endpoint:**
```bash
curl -X GET http://localhost:8000/health
```

### Dokploy Deployment

See [DOKPLOY_DEPLOYMENT.md](./DOKPLOY_DEPLOYMENT.md) for complete setup guide.

## API Endpoints

### Health Check
```bash
GET /health
```

### Verify with Base64 Image
```bash
POST /verify/image
Content-Type: application/json

{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
  "account_number": "123456789",
  "amount": 500.00,
  "payment_id": "optional-uuid"
}
```

### Verify with Storage URL
```bash
POST /verify/storage
Content-Type: application/json

{
  "image_path": "receipts/payment-123.jpg",
  "account_number": "123456789",
  "amount": 500.00,
  "payment_id": "optional-uuid"
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | - | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | - | Service role key for API access |
| `STORAGE_BUCKET` | `receipts` | Supabase storage bucket name |
| `OCR_LANGUAGE` | `en` | OCR language: `en` or `ar` |
| `USE_GPU` | `false` | Enable GPU for OCR processing |
| `SSIM_THRESHOLD` | `0.65` | Image similarity threshold |
| `FUZZY_MATCH_THRESHOLD` | `85` | Text matching threshold |
| `UPDATE_DATABASE` | `true` | Auto-update payment status |
| `DATABASE_TABLE` | `payments` | Database table name |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Debug logging |

## Database Schema

```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  image_path TEXT,
  account_number TEXT NOT NULL,
  amount FLOAT NOT NULL,
  status TEXT,
  reason TEXT,
  verified_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Response Format

```json
{
  "status": "success",
  "verified": true,
  "reason": "",
  "amount": 500.00,
  "account": "123456789",
  "timestamp": "2026-08-18T10:30:00.123456",
  "payment_id": "optional-uuid"
}
```

### Status Codes
- `status: "success"` - Receipt verified ✅
- `status: "failed"` - Verification failed ❌
- Common failure reasons:
  - `"image quality too low or not a receipt"` - SSIM score below threshold
  - `"can't find transaction id"` - Transaction ID not in receipt
  - `"transaction older than one week"` - Date validation failed
  - `"another account"` - Account number mismatch
  - `"not enough amount"` - Amount less than expected
  - `"invalid image"` - Image decode error

## Development

### Install Dev Dependencies
```bash
pip install -r requirements-dev.txt
```

### Run Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
black app/
flake8 app/
mypy app/
isort app/
```

## Architecture

```
┌─────────────────────────────────────────┐
│        FastAPI Application              │
│  ┌───────────────────────────────────┐  │
│  │  Endpoint /verify/image           │  │
│  │  ↓                                │  │
│  │  verify_receipt()                 │  │
│  │  ├─ OCR Extract Text              │  │
│  │  ├─ SSIM Image Compare            │  │
│  │  ├─ Validate Account              │  │
│  │  ├─ Validate Amount               │  │
│  │  └─ Check Date                    │  │
│  │  ↓                                │  │
│  │  Update Database (optional)       │  │
│  │  ↓                                │  │
│  │  Return VerificationResponse      │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
        ↓              ↓           ↓
    Supabase      PaddleOCR    OpenCV
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs receipt-verifier

# Common issues:
# - Missing reference_receipt.jpg
# - Invalid Supabase credentials
# - Port already in use
```

### OCR not extracting text
- Ensure receipt image is clear and well-lit
- Check that OCR language matches receipt
- Verify reference image format matches

### Database not updating
- Check `UPDATE_DATABASE=true` is set
- Verify service role key has database permissions
- Check database table schema

## Performance

- **First request**: ~3-5 seconds (model loading)
- **Subsequent requests**: ~1-2 seconds
- **Memory usage**: ~2-4GB per worker
- **Recommended resources**: 2 CPU cores, 4GB RAM

## License

MIT

## Support

For issues or questions:
1. Check [DOKPLOY_DEPLOYMENT.md](./DOKPLOY_DEPLOYMENT.md)
2. Review logs in Dokploy dashboard
3. Verify environment variables
4. Test with `/health` endpoint
