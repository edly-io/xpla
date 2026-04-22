REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/xpla/lib/sandbox/*.js)


PYODIDE_VERSION := 0.29.3
PYODIDE_URL := https://github.com/pyodide/pyodide/releases/download/$(PYODIDE_VERSION)/pyodide-$(PYODIDE_VERSION).tar.bz2

build: sandbox.wasm ui.bundle.js assets/pyodide/pyodide.mjs

sandbox.bundle.js: sandbox.js
	npx esbuild sandbox.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=sandbox.bundle.js

sandbox.wasm: sandbox.bundle.js xpla.wit
	npx componentize-js sandbox.bundle.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o sandbox.wasm

ui.bundle.js: ui.js node_modules
	npx esbuild ui.js --bundle --format=esm --loader:.css=text --loader:.svg=text --outfile=ui.bundle.js

node_modules: package.json
	npm install

assets/pyodide/pyodide.mjs:
	mkdir -p assets
	curl -L $(PYODIDE_URL) | tar xjf - -C assets
