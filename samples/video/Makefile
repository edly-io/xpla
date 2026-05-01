REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/pxc/lib/sandbox/*.js)


build: sandbox.wasm ui.bundle.js

sandbox.bundle.js: sandbox.js
	npx esbuild sandbox.js --bundle --format=esm --platform=neutral '--external:pxc:sandbox/*' --outfile=sandbox.bundle.js

sandbox.wasm: sandbox.bundle.js pxc.wit
	npx componentize-js sandbox.bundle.js --wit pxc.wit --world-name activity --disable http --disable fetch-event -o sandbox.wasm

ui.bundle.js: ui.js node_modules
	npx esbuild ui.js --bundle --format=esm --loader:.css=text --loader:.svg=text --outfile=ui.bundle.js

node_modules: package.json
	npm install
