.PHONY: build up down logs restart test lint ci

build:
	docker compose build

up:
	docker compose up --build -d

down:
	docker compose down

bash:
<<<<<<< HEAD
	docker exec -it llm_output_processor /bin/bash
=======
	docker exec -it second_brain /bin/bash
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01

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
