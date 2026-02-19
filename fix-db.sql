-- Fix missing columns in telegram_accounts table
ALTER TABLE telegram_accounts 
ADD COLUMN IF NOT EXISTS proxy_type TEXT,
ADD COLUMN IF NOT EXISTS proxy_host TEXT,
ADD COLUMN IF NOT EXISTS proxy_port INTEGER,
ADD COLUMN IF NOT EXISTS proxy_username TEXT,
ADD COLUMN IF NOT EXISTS proxy_password TEXT;

-- Add some sample accounts for testing
INSERT INTO telegram_accounts (api_id, api_hash, phone_number, health_score, session_status) VALUES 
(12345678, 'abc123hash', '+1234567890', 85, 'authorized'),
(23456789, 'def456hash', '+2345678901', 90, 'authorized'),
(34567890, 'ghi789hash', '+3456789012', 75, 'authorized')
ON CONFLICT (api_id) DO NOTHING;

-- Show the table structure
\d telegram_accounts;
