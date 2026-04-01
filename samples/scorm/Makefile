REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/xpla/lib/sandbox/*.js)


build: server.component.wasm

node_modules: package.json
	npm install

server.bundle.js: server.js node_modules
	npx esbuild server.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=server.bundle.js

server.component.wasm: server.bundle.js xpla.wit
	npx componentize-js server.bundle.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o server.component.wasm
