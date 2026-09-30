.PHONY: up up-d down logs ps migrate makemigrations clean

up:
	docker compose up --build

up-d:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose run --rm migrate

makemigrations:
	docker compose run --rm app alembic revision --autogenerate -m "$(m)"

clean:
	docker compose down -v
