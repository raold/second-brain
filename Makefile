.PHONY: build up down logs restart test lint ci

build:
	docker compose build

up:
	docker compose up --build -d

down:
	docker compose down

bash:
	docker exec -it second_brain /bin/bash

logs:
	docker compose logs -f

test:
	PYTHONPATH=. pytest --cov=app tests/

restart:
	docker compose down
	docker compose build
	docker compose up -d

lint:
	ruff check .

ci:
	lint test
