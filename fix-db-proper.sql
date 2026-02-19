-- Add missing columns and fix schema
ALTER TABLE telegram_accounts 
ADD COLUMN IF NOT EXISTS comments_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS health_score INTEGER NOT NULL DEFAULT 100,
ADD COLUMN IF NOT EXISTS last_comment_time TIMESTAMPTZ;

-- Update existing records to have reasonable defaults
UPDATE telegram_accounts 
SET comments_count = 0, 
    health_score = CASE 
        WHEN session_status = 'authorized' THEN 85 
        ELSE 50 
    END
WHERE comments_count IS NULL OR health_score IS NULL;

-- Add sample accounts for testing
INSERT INTO telegram_accounts (account_name, phone_number, health_score, session_status, comments_count) VALUES 
('account1', '+1234567890', 85, 'authorized', 5),
('account2', '+2345678901', 90, 'authorized', 3),
('account3', '+3456789012', 75, 'authorized', 8)
ON CONFLICT (account_name) DO UPDATE SET
    health_score = EXCLUDED.health_score,
    session_status = EXCLUDED.session_status,
    comments_count = EXCLUDED.comments_count;

-- Show the updated table structure
\d telegram_accounts;

-- Show sample data
SELECT id, account_name, phone_number, health_score, session_status, comments_count, 
       COALESCE(last_comment_time::text, 'never') as last_activity
FROM telegram_accounts 
LIMIT 5;
