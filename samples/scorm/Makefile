REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/pxc/lib/sandbox/*.js)


build: sandbox.wasm

node_modules: package.json
	npm install

sandbox.bundle.js: sandbox.js node_modules
	npx esbuild sandbox.js --bundle --format=esm --platform=neutral '--external:pxc:sandbox/*' --outfile=sandbox.bundle.js

sandbox.wasm: sandbox.bundle.js pxc.wit
	npx componentize-js sandbox.bundle.js --wit pxc.wit --world-name activity --disable http --disable fetch-event -o sandbox.wasm
