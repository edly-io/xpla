REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/xpla/lib/sandbox/*.js)
WIT := $(REPO_ROOT)/src/xpla/lib/sandbox/xpla.wit

build: server.component.wasm client.bundle.js

server.bundle.js: server.js $(SANDBOX_LIB)
	npx esbuild server.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=server.bundle.js

server.component.wasm: server.bundle.js $(WIT)
	npx componentize-js server.bundle.js --wit $(WIT) --world-name activity --disable http --disable fetch-event -o server.component.wasm

client.bundle.js: client.js node_modules
	npx esbuild client.js --bundle --format=esm --loader:.css=text --loader:.svg=text --outfile=client.bundle.js

node_modules: package.json
	npm install
