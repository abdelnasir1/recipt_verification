# Supabase Edge Function Configuration

## Setup for Local Development

### Prerequisites
- Dokploy with Supabase Edge Functions container
- Receipt Verifier container running on the same network

### Environment Variables

Set these in your Edge Function environment (Dokploy Supabase settings):

```env
RECEIPT_VERIFIER_URL=http://receipt-verifier:8000
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Local Settings Configuration

For **local development only** (not Dokploy), edit `supabase/config.toml`:

```toml
[functions.verify-receipt]
enabled = true
verify_jwt = false  # Set to true for production
grant = "postgres"

[[functions]]
slug = "verify-receipt"
verification_type = "none"  # For local testing - change to "jwt" for production
```

### How It Works

1. **Trigger**: When a new payment record is inserted with a `receipt_url`
2. **Processing**: Edge Function calls the Receipt Verifier service
3. **Verification**: Receipt Verifier downloads image, runs OCR, validates
4. **Update**: Results are written back to the payment record:
   - `status`: "success" or "failed"
   - `failure_reason`: Error message if failed
   - `verified_at`: Timestamp of verification

### Database Schema

Required columns in `payments` table:

```sql
- id: UUID PRIMARY KEY
- receipt_url: TEXT (path to image in storage, e.g., "receipts/payment-123.jpg")
- account_number: TEXT (account to verify against)
- amount: FLOAT (amount to verify)
- status: TEXT (verification status)
- failure_reason: TEXT (reason if failed)
- verified_at: TIMESTAMP (when verification completed)
- created_at: TIMESTAMP (record creation time)
```

### Testing the Edge Function

**1. From your app:**
```typescript
const { data, error } = await supabase
  .functions
  .invoke('verify-receipt', {
    body: { payment_id: 'your-payment-uuid' }
  })

console.log(data)  // { success: true, verification: {...} }
```

**2. From curl:**
```bash
curl -X POST https://your-project.supabase.co/functions/v1/verify-receipt \
  -H "Authorization: Bearer $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "payment_id": "uuid-here" }'
```

### Network Architecture (Dokploy)

```
┌─────────────────────────────────────┐
│    Dokploy Services Network         │
│                                     │
│  ┌──────────────────────┐           │
│  │ Supabase Edge Func   │           │
│  │ (verify-receipt)     │──────┐    │
│  └──────────────────────┘      │    │
│                                │    │
│  ┌──────────────────────┐      │    │
│  │ Receipt Verifier     │◄─────┘    │
│  │ (port 8000)          │           │
│  └──────────────────────┘           │
│         ↓                           │
│  ┌──────────────────────┐           │
│  │ Supabase DB + Storage│           │
│  └──────────────────────┘           │
│                                     │
└─────────────────────────────────────┘
```

### Local Testing Setup

**1. Start services:**
```bash
docker-compose up -d

# Make sure Supabase edge functions container is also running
```

**2. Test by inserting a payment:**
```sql
INSERT INTO payments (id, receipt_url, account_number, amount, status)
VALUES (
  gen_random_uuid(),
  'receipts/test-receipt.jpg',
  '123456789',
  500.00,
  'pending'
)
```

**3. Trigger the edge function:**
```sql
SELECT * FROM payments 
WHERE id = 'your-payment-id'
-- Status should change to 'success' or 'failed' after a few seconds
```

### Troubleshooting

**Edge Function not triggering:**
- Check network connectivity between Edge Function and Receipt Verifier containers
- Verify `RECEIPT_VERIFIER_URL` environment variable is set correctly
- Check Edge Function logs in Dokploy

**Service communication error:**
- Ensure Receipt Verifier container is running: `docker ps | grep receipt_verifier`
- Use internal network name: `http://receipt-verifier:8000` (not localhost)
- Verify port 8000 is exposed in docker-compose

**Verification fails but shouldn't:**
- Check Receipt Verifier logs
- Verify receipt image quality
- Ensure account_number and amount match receipt

**Database update fails:**
- Verify SUPABASE_SERVICE_ROLE_KEY is correct
- Check `failure_reason` column exists in payments table
- Ensure Edge Function has database update permissions

### Production Deployment

When deploying to production Dokploy:

1. Set `verify_jwt = true` in Edge Function config
2. Use signed JWTs for authentication
3. Enable CORS restrictions
4. Add rate limiting if needed
5. Set up monitoring and alerting
6. Use service role key securely (not in logs)
