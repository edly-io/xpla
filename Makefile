.DEFAULT_GOAL := help
.PHONY: help test

###### Development

format: ## Format code with black
	black src/

test: test-lint test-unit test-types test-format ## Run all tests

test-lint: ## Run pylint tests
	pylint --disable=all --enable=E --enable=unused-import,unused-argument,f-string-without-interpolation src/

test-unit: ## Run unit tests
	pytest src/tests

test-types: ## Run mypy tests
	mypy --ignore-missing-imports --implicit-reexport --strict src/

test-format: # Run formatting tests
	black --check src/

###### Additional commands

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'
