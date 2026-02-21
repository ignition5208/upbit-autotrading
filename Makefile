.PHONY: up down logs build trader-image trainer-image ps

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

ps:
	docker compose ps

trader-image:
	docker build -t upbit-trader:latest ./trader

trainer-image:
	docker build -t upbit-trainer:latest ./trainer
