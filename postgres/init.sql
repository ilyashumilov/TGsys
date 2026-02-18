-- Telegram channels to track + last seen message id
CREATE TABLE IF NOT EXISTS telegram_channels (
  id BIGSERIAL PRIMARY KEY,
  identifier TEXT NOT NULL UNIQUE,
  tg_channel_id BIGINT,
  last_message_id BIGINT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Update updated_at automatically (simple approach: update it in app)

-- Example channels (edit identifiers to your channels, then restart postgres volume or insert manually):
-- INSERT INTO telegram_channels (identifier) VALUES ('@somechannel');
-- INSERT INTO telegram_channels (identifier) VALUES ('https://t.me/somechannel');

