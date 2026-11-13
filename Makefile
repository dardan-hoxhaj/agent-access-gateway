.PHONY: up demo test down lint

up:
	docker compose up -d --build

down:
	docker compose down -v

test:
	pytest -q --cov=gateway --cov-report=term-missing
	opa test policies/ -v

lint:
	ruff check gateway tests

demo:
	bash scripts/demo.sh
