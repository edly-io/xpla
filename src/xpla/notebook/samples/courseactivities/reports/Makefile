build: sandbox.wasm ui.bundle.js

ui.bundle.js: ui.js node_modules
	npx esbuild ui.js --bundle --format=esm --outfile=ui.bundle.js

sandbox.bundle.js: sandbox.js
	npx esbuild sandbox.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=sandbox.bundle.js

sandbox.wasm: sandbox.bundle.js xpla.wit
	npx componentize-js sandbox.bundle.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o sandbox.wasm

node_modules: package.json
	npm install
