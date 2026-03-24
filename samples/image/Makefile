REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/xpla/lib/sandbox/*.js)
WIT := $(REPO_ROOT)/src/xpla/lib/sandbox/xpla.wit

build: server.component.wasm

server.bundle.js: server.js $(SANDBOX_LIB)
	npx esbuild server.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=server.bundle.js

server.component.wasm: server.bundle.js $(WIT)
	npx componentize-js server.bundle.js --wit $(WIT) --world-name activity --disable http --disable fetch-event -o server.component.wasm
