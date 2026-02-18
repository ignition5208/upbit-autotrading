CREATE TABLE IF NOT EXISTS accounts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL,
  access_key TEXT NOT NULL,
  secret_key TEXT NOT NULL,
  is_shared TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS traders (
  id INT AUTO_INCREMENT PRIMARY KEY,
  trader_id VARCHAR(64) NOT NULL,
  display_name VARCHAR(128) NULL,
  mode VARCHAR(16) NOT NULL DEFAULT 'PAPER',
  strategy_mode VARCHAR(16) NOT NULL DEFAULT 'STANDARD',
  account_id INT NULL,
  krw_alloc_limit BIGINT NOT NULL DEFAULT 0,
  is_enabled TINYINT NOT NULL DEFAULT 1,
  is_paused TINYINT NOT NULL DEFAULT 1,
  trade_enabled TINYINT NOT NULL DEFAULT 0,
  heartbeat_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_traders_trader_id (trader_id),
  CONSTRAINT fk_traders_account FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS config_versions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  trader_id VARCHAR(64) NOT NULL,
  version INT NOT NULL,
  config_json LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_cfgver (trader_id, version)
);

CREATE TABLE IF NOT EXISTS config_current (
  trader_id VARCHAR(64) NOT NULL,
  version INT NOT NULL,
  config_json LONGTEXT NOT NULL,
  applied_at DATETIME NOT NULL,
  apply_mode VARCHAR(32) NOT NULL DEFAULT 'restart',
  PRIMARY KEY (trader_id)
);

CREATE TABLE IF NOT EXISTS events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  trader_id VARCHAR(64) NULL,
  level VARCHAR(16) NOT NULL,
  code VARCHAR(64) NOT NULL,
  message TEXT NOT NULL,
  detail_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_events_trader_time (trader_id, created_at)
);

-- Minimal placeholders (for hard delete cleanup)
CREATE TABLE IF NOT EXISTS orders (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  trader_id VARCHAR(64) NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  state VARCHAR(16) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_orders_trader_time (trader_id, created_at)
);

CREATE TABLE IF NOT EXISTS trades (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  trader_id VARCHAR(64) NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_trades_trader_time (trader_id, created_at)
);

CREATE TABLE IF NOT EXISTS positions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  trader_id VARCHAR(64) NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  state VARCHAR(16) NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_positions_trader (trader_id)
);

CREATE TABLE IF NOT EXISTS scores (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  trader_id VARCHAR(64) NOT NULL,
  symbol VARCHAR(32) NOT NULL,
  score DOUBLE NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_scores_trader_time (trader_id, created_at)
);
