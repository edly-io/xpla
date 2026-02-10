.DEFAULT_GOAL := help
.PHONY: help samples test

###### Development

SERVER_JS_SOURCES := $(wildcard samples/*/server.js)
SERVER_WASMS := $(patsubst %/server.js,%/server.wasm,$(SERVER_JS_SOURCES))
CLIENT_BUNDLES := $(shell grep -rl '"client.bundle.js"' samples/*/manifest.json 2>/dev/null | sed 's|manifest.json|client.bundle.js|')

samples: $(SERVER_WASMS) $(CLIENT_BUNDLES) ## Build all sandboxes for sample activities

SANDBOX_LIB := $(wildcard src/sandbox-lib/*.js)

samples/%/server.wasm: samples/%/server.js $(SANDBOX_LIB) src/sandbox-lib/sandbox.d.ts
	./src/tools/js2wasm.py $< --output $@

samples/%/client.bundle.js: samples/%/client.js
	./src/tools/bundle_client.py $< --output $@

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

# This command must be run every time the schema is updated
.PHONY: manifest-types
manifest-types: src/server/activities/manifest_types.py ## Generate manifest types based on schema
src/server/activities/manifest_types.py: src/sandbox-lib/manifest.schema.json 
	datamodel-codegen --input=src/sandbox-lib/manifest.schema.json --input-file-type=jsonschema --formatters=black --formatters=isort --output-model-type=pydantic_v2.BaseModel --output=src/server/activities/manifest_types.py


###### Additional commands

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'
