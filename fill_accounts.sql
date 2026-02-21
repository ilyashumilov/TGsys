-- SQL to populate telegram_accounts from session files and proxies
-- Assuming session files are named with phone numbers (e.g., +12345678901.session)
-- Adjust phone numbers to match actual session file names
-- Proxies are cycled through the available ones

INSERT INTO telegram_accounts (account_name, phone_number, session_file, is_active, health_score, session_status, proxy_type, proxy_host, proxy_port, proxy_username, proxy_password) VALUES
('account_12345678901', '+12345678901', 'account1.session', true, 100, 'authorized', 'socks5', '166.1.168.172', 64993, 'SDzQ3bTS', 'JJi5thpa'),
('account_12345678902', '+12345678902', 'account2.session', true, 100, 'authorized', 'socks5', '142.111.3.23', 62945, 'SDzQ3bTS', 'JJi5thpa'),
('account_12345678903', '+12345678903', 'account3.session', true, 100, 'authorized', 'socks5', '142.111.128.167', 64887, 'SDzQ3bTS', 'JJi5thpa'),
('account_12345678904', '+12345678904', 'account4.session', true, 100, 'authorized', 'socks5', '172.120.169.6', 64347, 'SDzQ3bTS', 'JJi5thpa');
