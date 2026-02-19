.PHONY: up down recreate logs

up:
	docker compose --env-file .env up -d --build

down:
	docker compose --env-file .env down

recreate:
	docker compose --env-file .env up -d --build --force-recreate

logs:
	docker compose logs -f --tail=200
