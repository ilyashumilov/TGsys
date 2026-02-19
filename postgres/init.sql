-- Telegram channels to track + last seen message id
CREATE TABLE IF NOT EXISTS telegram_channels (
  id BIGSERIAL PRIMARY KEY,
  identifier TEXT NOT NULL UNIQUE,
  tg_channel_id BIGINT,
  last_message_id BIGINT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Insert sample channels (will be ignored if they already exist)
INSERT INTO telegram_channels (identifier) VALUES 
  ('@durov'),
  ('@telegram')
ON CONFLICT (identifier) DO NOTHING;

-- Telegram accounts for comment posting
CREATE TABLE IF NOT EXISTS telegram_accounts (
  id BIGSERIAL PRIMARY KEY,
  api_id BIGINT,
  api_hash TEXT,
  phone_number TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  last_comment_time TIMESTAMPTZ,
  comments_count INTEGER NOT NULL DEFAULT 0,
  health_score INTEGER NOT NULL DEFAULT 100 CHECK (health_score >= 0 AND health_score <= 100),
  session_status TEXT NOT NULL DEFAULT 'authorized', -- 'authorized', 'session_missing', 'banned', etc.
  proxy_type TEXT, -- 'http', 'socks4', 'socks5'
  proxy_host TEXT,
  proxy_port INTEGER,
  proxy_username TEXT,
  proxy_password TEXT
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_telegram_accounts_active ON telegram_accounts(is_active, session_status, health_score) 
WHERE is_active = TRUE AND session_status = 'authorized' AND health_score > 70;

CREATE INDEX IF NOT EXISTS idx_telegram_accounts_selection ON telegram_accounts(last_comment_time, comments_count, health_score) 
WHERE is_active = TRUE AND health_score > 70;

CREATE INDEX IF NOT EXISTS idx_telegram_accounts_cooldown 
ON telegram_accounts(last_comment_time) 
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_telegram_channels_active 
ON telegram_channels(is_active) 
WHERE is_active = TRUE;

