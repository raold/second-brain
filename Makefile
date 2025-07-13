.PHONY: build up down logs restart test lint

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose down
	docker compose build
	docker compose up -d

test:
	pytest tests/

lint:
	black app/ tests/
