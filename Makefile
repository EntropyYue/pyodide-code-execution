.PHONY: lint-format
lint-format: lint format

.PHONY: lint
lint:
	ruff check --fix .

.PHONY: format
format:
	ruff format .
