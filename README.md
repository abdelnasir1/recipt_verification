# Receipt verification service

The API accepts a Supabase Storage image path and the payment row ID, then queues OCR work and immediately returns HTTP `200` with an empty body.

## Request

```http
POST /verify/storage
Content-Type: application/json
```

```json
{
  "image_url": "payments/receipt.jpg",
  "payment_id": "payment-uuid"
}
```

`image_url` is the path inside the bucket configured by `STORAGE_BUCKET`. The result is written to the matching row in `DATABASE_TABLE` (`payments` by default) using `status`, `reason`, and `verified_at`.

## Configuration

Set these values in `.env` before starting Compose:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
ACCOUNT_NUMBER=expected-account-number
AMOUNT=100.00
```

`ACCOUNT_NUMBER` and `AMOUNT` are the expected values used by OCR verification. Redis is provided by Compose through `REDIS_URL=redis://redis:6379/0`.

## Run

```bash
docker compose up --build
```

The API listens on `http://localhost:8000`. The `receipt-worker` service performs image download, OCR, and database updates asynchronously.