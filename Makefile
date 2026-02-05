.DEFAULT_GOAL := help
.PHONY: help samples test

###### Development

SERVER_JS_SOURCES := $(wildcard samples/*/server.js)
SERVER_WASMS := $(patsubst %/server.js,%/server.wasm,$(SERVER_JS_SOURCES))

samples: $(SERVER_WASMS) ## Build all sandboxes for sample activities

samples/%/server.wasm: samples/%/server.js src/sandbox-lib/sandbox.d.ts
	./src/tools/js2wasm.py $< --output $@

server: ## Run a development server
	fastapi dev src/server/app.py

format: ## Format code with black
	black src/

test: test-lint test-unit test-types test-format test-manifests ## Run all tests

test-lint: ## Run pylint tests
	pylint src/

test-unit: ## Run unit tests
	pytest src/tests

test-types: ## Run mypy tests
	mypy src/

test-format: ## Run formatting tests
	black --check src/

test-manifests: ## Validate all manifest.json files
	@for f in samples/*/manifest.json; do echo "$$f" && ./src/tools/validate_manifest.py "$$f" || exit 1; done

###### Additional commands

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'
