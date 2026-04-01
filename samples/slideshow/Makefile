REPO_ROOT := ../..
SANDBOX_LIB := $(wildcard $(REPO_ROOT)/src/xpla/lib/sandbox/*.js)


REVEAL_SRC := node_modules/reveal.js/dist

build: server.component.wasm assets/reveal/reveal.js

server.bundle.js: server.js
	npx esbuild server.js --bundle --format=esm --platform=neutral '--external:xpla:sandbox/*' --outfile=server.bundle.js

server.component.wasm: server.bundle.js xpla.wit
	npx componentize-js server.bundle.js --wit xpla.wit --world-name activity --disable http --disable fetch-event -o server.component.wasm

assets/reveal/reveal.js: node_modules
	mkdir -p assets/reveal/theme/fonts
	cp $(REVEAL_SRC)/reset.css assets/reveal/
	cp $(REVEAL_SRC)/reveal.css assets/reveal/
	cp $(REVEAL_SRC)/theme/white.css assets/reveal/theme/
	cp $(REVEAL_SRC)/reveal.js assets/reveal/
	cp -r $(REVEAL_SRC)/theme/fonts/source-sans-pro/ assets/reveal/theme/fonts/

node_modules: package.json
	npm install
