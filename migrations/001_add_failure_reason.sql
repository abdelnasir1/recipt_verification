-- Add column to payments table for failure reason
ALTER TABLE payments ADD COLUMN IF NOT EXISTS failure_reason TEXT;

-- Add column for receipt_url (backup URL from cloud storage)
ALTER TABLE payments ADD COLUMN IF NOT EXISTS receipt_url TEXT;

-- Update table structure
-- payment_id: UUID - primary key
-- receipt_url: TEXT - URL or path to receipt image (this will be passed to verifier)
-- account_number: TEXT - account to verify
-- amount: FLOAT - amount to verify
-- status: TEXT - 'pending', 'success', 'failed'
-- failure_reason: TEXT - reason if verification failed
-- verified_at: TIMESTAMP - when verification completed
-- created_at: TIMESTAMP - when payment record created
