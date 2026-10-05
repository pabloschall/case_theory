TERRAFORM ?= ./scripts/terraform

.PHONY: dev test test-backend test-frontend migrate migration seed lint format typecheck terraform-fmt terraform-validate preview-recent-case preview-historical-case preview-paranormal-case create-recent-case create-historical-case create-paranormal-case preview-reel render-reel publish-reel

dev:
	docker compose up --build

test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm test

migrate:
	cd backend && alembic upgrade head

migration:
	cd backend && alembic revision --autogenerate -m "$(name)"

seed:
	cd backend && python -m app.db.seed

preview-recent-case:
	docker compose run --rm backend python -m app.scheduled_cases recent --dry-run

preview-historical-case:
	docker compose run --rm backend python -m app.scheduled_cases historical --dry-run

preview-paranormal-case:
	docker compose run --rm backend python -m app.scheduled_cases paranormal --dry-run

create-recent-case:
	docker compose run --rm backend python -m app.scheduled_cases recent

create-historical-case:
	docker compose run --rm backend python -m app.scheduled_cases historical

create-paranormal-case:
	docker compose run --rm backend python -m app.scheduled_cases paranormal

preview-reel:
	docker compose run --rm backend python -m app.scheduled_reels --dry-run

render-reel:
	docker compose run --rm backend python -m app.scheduled_reels --skip-upload

publish-reel:
	docker compose run --rm backend python -m app.scheduled_reels

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

typecheck:
	cd backend && mypy app
	cd frontend && npm run typecheck

terraform-fmt:
	$(TERRAFORM) fmt -recursive infra

terraform-validate:
	$(TERRAFORM) -chdir=infra/bootstrap init -backend=false
	$(TERRAFORM) -chdir=infra/bootstrap validate
	$(TERRAFORM) -chdir=infra/environments/staging init -backend=false
	$(TERRAFORM) -chdir=infra/environments/staging validate
