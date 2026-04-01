REPO_ROOT := ../..

# This shim is to build yjs which refers to location.search, but which isn't available here.
LOCATION_SHIM := if(typeof location==="object"){try{void location.search}catch(e){globalThis.location={search:""}}}

build: server.component.wasm client.bundle.js

server.bundle.js: server.js node_modules
	npx esbuild server.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' '--banner:js=$(LOCATION_SHIM)' --outfile=server.bundle.js

server.component.wasm: server.bundle.js xpla.wit
	npx componentize-js server.bundle.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o server.component.wasm

client.bundle.js: client.js node_modules
	npx esbuild client.js --bundle --format=esm --loader:.css=text --loader:.svg=text --outfile=client.bundle.js

node_modules: package.json
	npm install
