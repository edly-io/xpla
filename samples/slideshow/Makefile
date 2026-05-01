REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/pxc/lib/sandbox/*.js)


REVEAL_SRC := node_modules/reveal.js/dist

build: sandbox.wasm assets/reveal/reveal.js

sandbox.bundle.js: sandbox.js
	npx esbuild sandbox.js --bundle --format=esm --platform=neutral '--external:pxc:sandbox/*' --outfile=sandbox.bundle.js

sandbox.wasm: sandbox.bundle.js pxc.wit
	npx componentize-js sandbox.bundle.js --wit pxc.wit --world-name activity --disable http --disable fetch-event -o sandbox.wasm

assets/reveal/reveal.js: node_modules
	mkdir -p assets/reveal/theme/fonts
	cp $(REVEAL_SRC)/reset.css assets/reveal/
	cp $(REVEAL_SRC)/reveal.css assets/reveal/
	cp $(REVEAL_SRC)/theme/white.css assets/reveal/theme/
	cp $(REVEAL_SRC)/reveal.js assets/reveal/
	cp -r $(REVEAL_SRC)/theme/fonts/source-sans-pro/ assets/reveal/theme/fonts/

node_modules: package.json
	npm install
