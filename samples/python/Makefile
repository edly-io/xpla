REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/xpla/lib/sandbox/*.js)


PYODIDE_VERSION := 0.29.3
PYODIDE_URL := https://github.com/pyodide/pyodide/releases/download/$(PYODIDE_VERSION)/pyodide-$(PYODIDE_VERSION).tar.bz2

build: server.component.wasm client.bundle.js assets/pyodide/pyodide.mjs

server.bundle.js: server.js
	npx esbuild server.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=server.bundle.js

server.component.wasm: server.bundle.js xpla.wit
	npx componentize-js server.bundle.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o server.component.wasm

client.bundle.js: client.js node_modules
	npx esbuild client.js --bundle --format=esm --loader:.css=text --loader:.svg=text --outfile=client.bundle.js

node_modules: package.json
	npm install

assets/pyodide/pyodide.mjs:
	mkdir -p assets
	curl -L $(PYODIDE_URL) | tar xjf - -C assets
