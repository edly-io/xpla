REVEAL_SRC := node_modules/reveal.js/dist

assets/reveal/reveal.js: node_modules
	mkdir -p assets/reveal/theme/fonts
	cp $(REVEAL_SRC)/reset.css assets/reveal/
	cp $(REVEAL_SRC)/reveal.css assets/reveal/
	cp $(REVEAL_SRC)/theme/white.css assets/reveal/theme/
	cp $(REVEAL_SRC)/reveal.js assets/reveal/
	cp -r $(REVEAL_SRC)/theme/fonts/source-sans-pro/ assets/reveal/theme/fonts/

node_modules: package.json
	npm install
