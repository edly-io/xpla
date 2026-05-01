build: sandbox.wasm ui.bundle.js

ui.bundle.js: ui.js node_modules
	npx esbuild ui.js --bundle --format=esm --outfile=ui.bundle.js

sandbox.wasm: sandbox.js xpla.wit
	npx componentize-js sandbox.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o sandbox.wasm

node_modules: package.json
	npm install
