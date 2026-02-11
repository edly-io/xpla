PYODIDE_VERSION := 0.29.3
PYODIDE_URL := https://github.com/pyodide/pyodide/releases/download/$(PYODIDE_VERSION)/pyodide-$(PYODIDE_VERSION).tar.bz2

static/pyodide/pyodide.mjs:
	mkdir -p static
	curl -L $(PYODIDE_URL) | tar xjf - -C static
