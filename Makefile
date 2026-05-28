.PHONY: up down api-local redis api-logs

up:
	docker compose up -d --build

down:
	docker compose down

redis:
	docker compose up -d redis

api-logs:
	docker compose logs -f api

api-local:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
