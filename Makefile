.DEFAULT_GOAL := help
.PHONY: help samples test

###### Development

SANDBOX_SOURCES := $(wildcard samples/*/src/sandbox.js)
SANDBOX_WASMS := $(patsubst %/src/sandbox.js,%/sandbox.wasm,$(SANDBOX_SOURCES))

samples: $(SANDBOX_WASMS) ## Build all sandboxes for sample activities

samples/%/sandbox.wasm: samples/%/src/sandbox.js samples/%/src/sandbox.d.ts
	./src/tools/js2wasm.py $< --output $@

server: ## Run a development server
	fastapi dev src/server/app.py

format: ## Format code with black
	black src/

test: test-lint test-unit test-types test-format ## Run all tests

test-lint: ## Run pylint tests
	pylint src/

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
