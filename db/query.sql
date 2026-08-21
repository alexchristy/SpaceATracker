-- name: UpsertTerminals :batchexec
INSERT INTO discovered_terminals (url)
VALUES ($1)
ON CONFLICT (url)
DO UPDATE SET url = EXCLUDED.url;
