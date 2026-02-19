INSERT INTO market_regimes(label, score, metrics_json)
SELECT 'RANGE', 50, JSON_OBJECT('seed','yes')
WHERE NOT EXISTS (SELECT 1 FROM market_regimes);
