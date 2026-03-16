REVEAL_SRC := node_modules/reveal.js/dist

static/reveal/reveal.js: node_modules
	mkdir -p static/reveal/theme/fonts
	cp $(REVEAL_SRC)/reset.css static/reveal/
	cp $(REVEAL_SRC)/reveal.css static/reveal/
	cp $(REVEAL_SRC)/theme/white.css static/reveal/theme/
	cp $(REVEAL_SRC)/reveal.js static/reveal/
	cp -r $(REVEAL_SRC)/theme/fonts/source-sans-pro/ static/reveal/theme/fonts/

node_modules: package.json
	npm install
