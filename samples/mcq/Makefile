REPO_ROOT := ../..


build: server.component.wasm

server.bundle.js: server.js
	npx esbuild server.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=server.bundle.js

server.component.wasm: server.bundle.js xpla.wit
	npx componentize-js server.bundle.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o server.component.wasm
