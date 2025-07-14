.PHONY: build up down logs restart test lint

build:
	docker compose build

up:
	docker compose up --build -d

down:
	docker compose down

bash:
	docker exec -it llm_output_processor /bin/bash

logs:
	docker compose logs -f

test:
	docker exec llm_output_processor pytest

restart:
	docker compose down
	docker compose build
	docker compose up -d

test:
	pytest tests/

lint:
	black app/ tests/
