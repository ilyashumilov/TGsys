-- Fix missing columns in telegram_accounts table
ALTER TABLE telegram_accounts 
ADD COLUMN IF NOT EXISTS proxy_type TEXT,
ADD COLUMN IF NOT EXISTS proxy_host TEXT,
ADD COLUMN IF NOT EXISTS proxy_port INTEGER,
ADD COLUMN IF NOT EXISTS proxy_username TEXT,
ADD COLUMN IF NOT EXISTS proxy_password TEXT;

-- Add some sample accounts for testing
INSERT INTO telegram_accounts (account_name, phone_number, health_score, session_status) VALUES 
('account1', '+1234567890', 85, 'authorized'),
('account2', '+2345678901', 90, 'authorized'),
('account3', '+3456789012', 75, 'authorized')
ON CONFLICT (account_name) DO NOTHING;

-- Show the table structure
\d telegram_accounts;
