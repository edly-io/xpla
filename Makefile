.DEFAULT_GOAL := help
.PHONY: help samples test

###### Development

SERVER_JS_SOURCES := $(wildcard samples/*/server.js)
SERVER_WASMS := $(patsubst %/server.js,%/server.wasm,$(SERVER_JS_SOURCES))
CLIENT_BUNDLES := $(shell grep -rl '"client.bundle.js"' samples/*/manifest.json 2>/dev/null | sed 's|manifest.json|client.bundle.js|')
SAMPLE_PKGS := $(wildcard samples/*/package.json)
SAMPLE_MODULES := $(patsubst %/package.json,%/node_modules/.package-lock.json,$(SAMPLE_PKGS))

samples: install-samples $(SERVER_WASMS) $(CLIENT_BUNDLES) ## Build all sandboxes for sample activities

install-samples: $(SAMPLE_MODULES) ## Install dependencies for sample activities

samples/%/node_modules/.package-lock.json: samples/%/package.json
	cd samples/$* && npm install

SANDBOX_LIB := $(wildcard src/xpla/lib/sandbox/*.js)

samples/%/server.wasm: samples/%/server.js $(SANDBOX_LIB) src/xpla/lib/sandbox/sandbox.d.ts
	./src/xpla/tools/js2wasm.py $< --output $@

samples/%/client.bundle.js: samples/%/client.js
	./src/xpla/tools/bundle_client.py $< --output $@

demo-server: ## Run a development server for the demo app
	fastapi dev src/xpla/demo/app.py --host=127.0.0.1 --port=9752

notebook-server: ## Run the notebook server (port 9753) — build frontend first with notebook-frontend-build
	fastapi dev src/xpla/notebook/app.py --host=127.0.0.1 --port=9753

notebook-frontend-build: ## Build the notebook frontend static export
	cd src/xpla/notebook/frontend && npm run build

format: ## Format code with black
	black src/

test: test-lint test-unit test-types test-format test-manifests test-codegen ## Run all tests

test-lint: ## Run pylint tests
	pylint src/

test-unit: ## Run unit tests
	pytest src/

test-types: ## Run mypy tests
	mypy src/

test-format: ## Run formatting tests
	black --check src/

test-manifests: ## Validate all manifest.json files
	@for f in samples/*/manifest.json; do echo "$$f" && ./src/xpla/tools/validate_manifest.py "$$f" || exit 1; done

test-codegen: ## Make sure that manifest types are up-to-date
	$(MAKE) --always-make manifest-types CODEGEN_OPTIONS="--check"

# This command must be run every time the schema is updated
.PHONY: manifest-types
manifest-types: src/xpla/lib/manifest_types.py ## Generate manifest types based on schema
src/xpla/lib/manifest_types.py: src/xpla/lib/sandbox/manifest.schema.json
	datamodel-codegen $(CODEGEN_OPTIONS) \
		--input=src/xpla/lib/sandbox/manifest.schema.json \
		--input-file-type=jsonschema \
		--use-double-quotes \
		--formatters black isort \
		--output-model-type=pydantic_v2.BaseModel \
		--use-annotated \
		--output=src/xpla/lib/manifest_types.py \
		--disable-timestamp

###### Additional commands

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'
