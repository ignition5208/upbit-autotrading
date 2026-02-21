-- ============================================================
-- Dashboard DB schema init (MariaDB/MySQL)
-- - Drops and recreates tables used by dashboard-api inserts
-- - Safe types: LONGTEXT for JSON payloads for compatibility
-- ============================================================

-- (선택) 사용할 DB 지정
-- CREATE DATABASE IF NOT EXISTS dashboard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE dashboard;

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Drop tables (order matters if FK added later)
-- ----------------------------
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS regime_snapshots;

SET FOREIGN_KEY_CHECKS=1;

-- ----------------------------
-- regime_snapshots
-- ----------------------------
CREATE TABLE regime_snapshots (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ts            DATETIME(6)      NOT NULL,
  market        VARCHAR(32)      NOT NULL,   -- e.g. KRW-BTC
  regime_id     INT              NOT NULL,   -- numeric regime id
  regime_label  VARCHAR(64)      NULL,       -- e.g. Bull/Bear/Neutral/Sideways
  confidence    DOUBLE           NULL,       -- 0~1
  metrics_json  LONGTEXT         NULL,       -- json string

  PRIMARY KEY (id),
  KEY idx_regime_snapshots_ts (ts),
  KEY idx_regime_snapshots_market_ts (market, ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- events
-- ----------------------------
CREATE TABLE events (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  ts           DATETIME(6)      NOT NULL,

  source_type  VARCHAR(32)      NULL,   -- e.g. regime/trader/system
  source_name  VARCHAR(64)      NULL,   -- e.g. KRW-BTC or trader name/id
  level        VARCHAR(16)      NULL,   -- INFO/WARN/ERROR
  event_type   VARCHAR(64)      NULL,   -- snapshot/action/etc
  message      TEXT             NULL,
  payload_json LONGTEXT         NULL,   -- json string

  PRIMARY KEY (id),
  KEY idx_events_ts (ts),
  KEY idx_events_source (source_type, source_name, ts),
  KEY idx_events_level_type (level, event_type, ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
