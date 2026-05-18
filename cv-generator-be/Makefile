.PHONY: db-up db-down db-reset migrate dev logs

db-up:
	docker compose up -d postgres adminer

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d postgres
	sleep 3
	uv run alembic -c app/alembic.ini upgrade head

migrate:
	uv run alembic -c app/alembic.ini upgrade head

dev:
	uvicorn app.main:app --reload

logs:
	docker compose logs -f postgres
