.PHONY: up down logs trader-image
up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f --tail=200
trader-image:
	docker build -t upbit-trader:latest ./services/trader
